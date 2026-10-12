"""Representation-aware page fusion with explicit safety and lazy visual work."""
import hashlib,json,math,re
from functools import lru_cache
from pathlib import Path
from src.document_fingerprints import binding
from src.models import RecognitionResult
from src.fingerprint_v3 import public_index,visual_similarity
from src.fingerprint_pages import RequestPages,field_signature
from src.fingerprint_match_v2 import safety_reason
from src.fingerprint_decision_v3 import entity_evidence

VERSION='fingerprint-decision-v4'
PATH=Path(__file__).resolve().parents[1]/'data/recognition_profiles/fingerprint_decision_v4.json'
DEFAULT=dict(digital=.90,ocr=.80,chars=.65,visual=.88,anchors=.25,margin=.04,overlap=16,top_k=25,field_text=.75,conflict_content=.90,conflict_chars=.80,conflict_anchors=.50,conflict_margin=.10)
SETTINGS=dict(char_ngram='4',aggregation='max',containment=True)

@lru_cache(maxsize=1)
def profile():
    if not PATH.exists():return dict(thresholds=dict(DEFAULT),settings=dict(SETTINGS))
    if PATH.is_symlink() or PATH.stat().st_size>64000:raise ValueError('Profilo v4 non sicuro.')
    p=json.loads(PATH.read_bytes());t=p['thresholds'];s=p['settings']
    if p['rules_version']!=VERSION or set(t)!=set(DEFAULT) or any(type(v) not in [int,float] or not math.isfinite(v) or not 0<=v<=100 for v in t.values()):raise ValueError('Profilo v4 non valido.')
    if set(s)!=set(SETTINGS) or s['char_ngram'] not in ['3','4','5'] or s['aggregation'] not in ['max','top2'] or type(s['containment']) is not bool or not 1<=t['top_k']<=50:raise ValueError('Impostazioni v4 non valide.')
    return p

def revision():return hashlib.sha256(PATH.read_bytes()).hexdigest() if PATH.exists() else 'development-v4'

def tier(row,representation,t,*,code=False,unique_fields=False):
    if row['overlap']<t['overlap']:return None
    digital=row['digital'];ocr=row['ocr'];char=row['chars'];anchor=row['anchors'];visual=row['visual']
    if representation in ['digital_pdf','docx','unknown'] and digital>=t['digital'] and char>=t['chars'] and anchor>=t['anchors'] and (code or anchor>=.50):return 'B_digital_char_identity'
    if max(digital,ocr)>=t['ocr'] and char>=t['chars'] and visual>=t['visual'] and anchor>=t['anchors']:return 'B_ocr_char_layout'
    if unique_fields and digital>=t['field_text'] and char>=t['chars'] and anchor>=t['anchors']:return 'C_unique_fields_compatible_identity'
    return None

def match(text,documents,*,file_sha256=None,pages=None,field_names=(),reference=False,diagnostics=None):
    index=public_index()
    if not index.records:return None
    docs={d.id:d for d in documents if d.stato_verifica not in ['demo','rifiutato']}
    request=pages or RequestPages((text,),field_set=field_signature(field_names))
    counters=request.counters
    from src.recognize import DISTINCT_ENTITY_NAMES
    names=frozenset([d.ente for d in documents]+list(DISTINCT_ENTITY_NAMES))
    entities=request.memo(('fingerprint_entities',text[:2000],names),lambda:entity_evidence(text,sorted(names)))
    from src.title_evidence import exact_code_candidates
    codes=set(exact_code_candidates(text,documents,reference=reference));memo={}
    def safe(row):
        rid=row['resource_index']
        if rid not in memo:
            r=index.records[rid];d=docs.get(r['document_id'])
            memo[rid]='non_operational_or_stale_binding' if d is None or r['catalog_binding_sha256']!=binding(d) else safety_reason(text,d,documents,exact=True,entities=entities)
        return memo[rid] is None
    if file_sha256 and len(index.sha.get(file_sha256,set()))==1:
        did=next(iter(index.sha[file_sha256]));rs=[i for i,r in enumerate(index.records) if r['document_id']==did and r['canonical_file_sha256']==file_sha256 and r['status']=='active']
        if any(safe(dict(resource_index=i)) for i in rs):
            counters.update(candidates_initial=1,candidates_text=0,candidates_visual=0,page_renders=0)
            return RecognitionResult(True,100.,docs[did],('official_file_sha256_exact','fingerprint_v3',VERSION,'A_exact_sha'), 'File ufficiale canonico identico.',score_margin=100.,candidate_ids=(did,))
    p=profile();t=p['thresholds'];s=p['settings'];queries=request.queries()
    if not queries or not any(len(q['tokens'])>=t['overlap'] for q in queries):return None
    def score_pages():
        counts={};base=index.similarities(queries,n=s['char_ngram'],aggregation='max',containment=s['containment'],reference=reference,counters=counts)
        return base,counts
    base,counts=request.memo(('page_scores',id(index),s['char_ngram'],s['containment'],reference),score_pages)
    counters.update(counts)
    # Fusion mutates only fresh row copies; parameterized pure page evidence
    # remains request-local, including when calibration compares configurations.
    rows=[dict(r,score=r['top2_average'] if s['aggregation']=='top2' else r['max_similarity']) for r in base]
    rows.sort(key=lambda r:(-r['score'],r['document_id']))
    unique_ids=index.field_map.get(tuple(request.field_set),set()) if request.field_set else set()
    def choose(r):return tier(r,request.representation,t,code=r['document_id'] in codes,unique_fields=unique_ids=={r['document_id']})
    # Only the bounded shortlist may trigger image decoding/rendering. Text,
    # chars and identity anchors are already computed once per request.
    eligible=[r for r in rows if choose(r) and safe(r)]
    if not eligible and request.raw:
        for r in rows[:int(t['top_k'])]:
            if r['overlap']<t['overlap'] or r['chars']<t['chars'] or r['anchors']<t['anchors'] or max(r['digital'],r['ocr'])<t['ocr'] or not safe(r):continue
            visual=request.visual(r['input_page'])
            r['visual']=visual_similarity(visual,index.pages[r['page_index']]['visual'])
            counters['candidates_visual']+=1
        eligible=[r for r in rows if choose(r) and safe(r)]
    if diagnostics is not None:
        expected_row=next((r for r in rows if r['document_id']==diagnostics.get('expected_id')),None)
        if expected_row:
            safe(expected_row)
            diagnostics['expected_candidate']={k:expected_row[k] for k in ['document_id','canonical_page','digital','ocr','chars','anchors','visual','overlap','score']}
            diagnostics['expected_veto']=memo.get(expected_row['resource_index'])
        visible=rows if not reference else index.similarities(queries,n=s['char_ngram'],aggregation=s['aggregation'],containment=s['containment'])
        diagnostics.update(counters=dict(counters),representation=request.representation,candidate_ids=[r['document_id'] for r in visible],candidates=[{k:r[k] for k in ['document_id','canonical_page','digital','ocr','chars','anchors','visual','overlap','score','max_similarity','top2_average']} for r in visible[:25]],thresholds=t,settings=s,entity_evidence=sorted(entities),version_evidence=sorted(set(re.findall(r'\b(?:versione|version|rev[.]?|revisione|anno|modello)\s*[:=/-]?\s*(\d+(?:[.]\d+)*)\b',text[:2000],re.I))))
    dominant=None
    supported=[r for r in rows if r['overlap']>=t['overlap']]
    if supported:
        first=supported[0];runner=max((r['score'] for r in supported[1:]),default=0.)
        if first['score']>=t['conflict_content'] and max(first['digital'],first['ocr'])>=t['conflict_content'] and first['chars']>=t['conflict_chars'] and first['anchors']>=t['conflict_anchors'] and first['overlap']>=t['overlap'] and first['score']-runner>=t['conflict_margin'] and safe(first):
            dominant=first['document_id']
            if diagnostics is not None:diagnostics['dominant_content_candidate']=dominant
    if not eligible:
        if diagnostics is not None:
            diagnostic_rows=visible if reference else rows
            diagnostics['reason_code']=memo.get(diagnostic_rows[0]['resource_index']) if diagnostic_rows else 'no_candidate'
            diagnostics['tier']='insufficient_channels'
        return None
    best=eligible[0]
    if dominant is not None and best['document_id']!=dominant:
        if diagnostics is not None:diagnostics.update(reason_code='contradictory_content_channels',tier='D_conflict')
        return None
    # Shared resources compete between identities, including below-threshold
    # peers. They require explicit metadata/code disambiguation, never SHA alone.
    competitors=[r for r in rows if r['document_id']!=best['document_id'] and r['score']>=best['score']-t['margin'] and safe(r)]
    if codes=={best['document_id']}:
        competitors=[r for r in competitors if r['document_id'] in codes or not docs[r['document_id']].codice]
    runner=max((r['score'] for r in competitors),default=0.)
    if diagnostics is not None:diagnostics['margin']=best['score']-runner
    if best['score']-runner<t['margin']:
        if diagnostics is not None:diagnostics.update(reason_code='margin',tier='D_ambiguous')
        return None
    r=index.records[best['resource_index']]
    if r['status']=='shared' and not (codes=={best['document_id']} and entities):
        if diagnostics is not None:diagnostics.update(reason_code='shared_resource_ambiguous',tier='D_ambiguous')
        return None
    signals=('content_fingerprint_match','fingerprint_v3',VERSION,choose(best),f"canonical_page:{best['canonical_page']}",*(f'{k}:{best[k]:.4f}' for k in ['digital','ocr','chars','visual','anchors']))
    return RecognitionResult(True,min(99.,80+19*best['score']),docs[best['document_id']],signals,'Firma per pagina: '+choose(best)+'; ente e versione compatibili.',score_margin=100*(best['score']-runner),candidate_ids=tuple(r['document_id'] for r in rows if r['overlap']>=3))
