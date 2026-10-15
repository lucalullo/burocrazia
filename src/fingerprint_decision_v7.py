"""Representation-aware page fusion with explicit safety and lazy visual work."""
import hashlib,json,math,re
from functools import lru_cache
from pathlib import Path
from src.document_fingerprints import binding
from src.models import RecognitionResult
from src.fingerprint_v3 import public_index,visual_similarity
from src.fingerprint_pages import RequestPages,field_signature
from src.fingerprint_match_v2 import safety_reason
from src.fingerprint_decision_v3 import entity_evidence as legacy_entity_evidence

VERSION='fingerprint-decision-v7'
PATH=Path(__file__).resolve().parents[1]/'data/recognition_profiles/fingerprint_decision_v7.json'
DEFAULT=dict(digital=.90,ocr=.80,chars=.65,visual=.88,anchors=.25,margin=.04,overlap=16,top_k=25,field_text=.75,conflict_content=.90,conflict_chars=.80,conflict_anchors=.50,conflict_margin=.10)
DEFAULT.update(scan_char=.85,scan_ocr=.50,scan_visual=.94,scan_anchor=.25,multi_page_average=.90,multi_page_margin=.08)
SETTINGS=dict(char_ngram='3',aggregation='max',containment=True)
CONDITIONAL=dict(strict_visual=.98,heading_min_terms=6,heading_disambiguation_terms=3,heading_coverage=.94,heading_window=45,heading_chars=1200)

@lru_cache(maxsize=1)
def profile():
    if not PATH.exists():return dict(thresholds=dict(DEFAULT),settings=dict(SETTINGS),conditional=dict(CONDITIONAL))
    if PATH.is_symlink() or PATH.stat().st_size>64000:raise ValueError('Profilo v7 non sicuro.')
    p=json.loads(PATH.read_bytes());t=p['thresholds'];s=p['settings']
    if p['rules_version']!=VERSION or set(t)!=set(DEFAULT) or any(type(v) not in [int,float] or not math.isfinite(v) or not 0<=v<=100 for v in t.values()):raise ValueError('Profilo v7 non valido.')
    if set(s)!=set(SETTINGS) or s['char_ngram'] not in ['3','4','5'] or s['aggregation'] not in ['max','top2'] or type(s['containment']) is not bool or not 1<=t['top_k']<=50:raise ValueError('Impostazioni v6 non valide.')
    if p.get('conditional')!=CONDITIONAL:raise ValueError('Regole condizionali v7 non valide.')
    return p

def revision():return hashlib.sha256(PATH.read_bytes()).hexdigest() if PATH.exists() else 'development-v7'

def evidence_states(text,document,documents,entities):
    """Unknown evidence grants no issuer/year; explicit conflicts remain vetoes."""
    from src.recognize import normalize_text,_local_entity_conflict
    issuer=normalize_text(document.ente)
    entity='entity_conflict' if (entities and issuer not in entities) or _local_entity_conflict(text[:2000],document.ente) else 'entity_confirmed' if issuer in entities else 'entity_unknown'
    reason=safety_reason(text,document,documents,exact=True,entities=entities)
    if reason and any(word in reason for word in ['version','revision','year']):version='version_conflict'
    elif not document.versione:version='version_confirmed'
    else:
        values=set(re.findall(r'\b(?:versione|version|revisione|rev[.]?|v|anno|annualit[aà]|modello(?:\s+\w+)?)\s*[:=/-]?\s*(\d+(?:[.]\d+)*)\b',text[:2000],re.I))
        version='version_confirmed' if document.versione in values else 'version_unknown'
    return entity,version,reason

def exclusive_heading(text,documents):
    """Complete discriminative title in a bounded opening, independent of truth."""
    from src.title_evidence import title_index,tokens,compact_code
    titles,weights=title_index(tuple(documents));opening=tokens(text[:CONDITIONAL['heading_chars']]);available=set(opening);found={}
    for d in documents:
        needed=titles.get(d.id,frozenset())
        plain_title=d.titolo_ufficiale
        suffix=re.search(r'\s*\[([^]]+)\]\s*$',d.titolo_ufficiale)
        if d.codice and suffix and compact_code(suffix[1]).startswith(compact_code(d.codice)):
            # A structured code annotation has its own exact-code channel.
            # Do not force OCR-confusable code glyphs into title completeness.
            plain_title=d.titolo_ufficiale[:suffix.start()]
            needed=frozenset(tokens(plain_title))
        if len(needed)<CONDITIONAL['heading_disambiguation_terms']:continue
        matched=needed&available;den=sum(weights[t] for t in needed)
        if len(matched)<CONDITIONAL['heading_disambiguation_terms'] or not den or sum(weights[t] for t in matched)/den<CONDITIONAL['heading_coverage']:continue
        sequence=tokens(plain_title);total=sum(weights[t] for t in sequence);ordered=False
        # Country/role relations are ordered: a bag of the same words cannot
        # swap insurer A/B or use a later 'Giudice Tutelare' as the title Tutela.
        for start,term in enumerate(opening):
            if term not in matched:continue
            cursor=start;support=0.;end=min(len(opening),start+CONDITIONAL['heading_window'])
            for title_term in sequence:
                try:position=opening.index(title_term,cursor,end)
                except ValueError:continue
                support+=weights[title_term];cursor=position+1
            if total and support/total>=CONDITIONAL['heading_coverage']:ordered=True;break
        if not ordered:continue
        found[d.id]=len(needed)
    return found

def conditional_tier(row,representation,t,*,rank1=False,heading_terms=0):
    if not rank1 or representation not in ['image','scanned_pdf'] or row['overlap']<t['overlap'] or row['anchors']<t['conflict_anchors']:return None
    # Two strong text channels plus identity anchors; no visual-only exception.
    if max(row['digital'],row['ocr'])>=t['ocr'] and row['chars']>=t['scan_char']:return 'B_scan_strong_multichannel'
    if row['visual']>=CONDITIONAL['strict_visual']:
        if heading_terms>=CONDITIONAL['heading_min_terms']:return 'B_complete_heading_layout'
        if max(row['digital'],row['ocr'])>=t['field_text'] and row['chars']>=t['chars']:return 'B_page_char_strict_layout'
    return None

def corroborated_margin(best,competitors,input_pages,t):
    margin=best['score']-max((r['score'] for r in competitors),default=0.)
    if margin<t['margin'] and input_pages>1 and len(best.get('alignment',()))>=2 and best['top2_average']>=t['multi_page_average']:
        average_runner=max((r['top2_average'] for r in competitors),default=0.)
        if best['top2_average']-average_runner>=t['multi_page_margin']:
            return best['top2_average']-average_runner,True
    return margin,False

def corroborated_content(row,runner,t):
    """Veto contrary metadata; weaker evidence never grants a positive match."""
    return (row['overlap']>=t['overlap'] and row['chars']>=t['chars']
        and max(row['digital'],row['ocr'])>=t['scan_ocr']
        and row['anchors']>=t['conflict_anchors']
        and row['score']-runner>=t['margin'])

def entity_evidence(text,names):
    from src.recognize import normalize_text
    names=tuple(names);known=frozenset(normalize_text(n) for n in names)
    found=legacy_entity_evidence(text,names)
    # Unknown departments are subordinate labels, not a contradictory issuer.
    # A bare/partial prefix of a known court/ministry is not a different entity.
    # Preserve all complete known names and explicit unknown authorities.
    return frozenset(e for e in found if e in known or (not e.startswith('dipartimento ') and not any(n.startswith(e+' ') or n.startswith(e) and len(n)-len(e)<=3 for n in known)))

def tier(row,representation,t,*,code=False,unique_fields=False):
    if row['overlap']<t['overlap']:return None
    digital=row['digital'];ocr=row['ocr'];char=row['chars'];anchor=row['anchors'];visual=row['visual']
    if representation in ['digital_pdf','docx','unknown'] and digital>=t['digital'] and char>=t['chars'] and anchor>=t['anchors'] and (code or anchor>=.50):return 'B_digital_char_identity'
    if max(digital,ocr)>=t['ocr'] and char>=t['chars'] and visual>=t['visual'] and anchor>=t['anchors']:return 'B_ocr_char_layout'
    if unique_fields and digital>=t['field_text'] and char>=t['chars'] and anchor>=t['anchors']:return 'C_unique_fields_compatible_identity'
    if representation in ['image','scanned_pdf'] and char>=t['scan_char'] and max(digital,ocr)>=t['scan_ocr'] and visual>=t['scan_visual'] and anchor>=t['scan_anchor']:return 'B_scan_char_layout'
    return None

def match(text,documents,*,file_sha256=None,pages=None,field_names=(),reference=False,diagnostics=None,decision_profile=None,policy_version=VERSION):
    index=public_index()
    if not index.records:return None
    docs={d.id:d for d in documents if d.stato_verifica not in ['demo','rifiutato']}
    request=pages or RequestPages((text,),field_set=field_signature(field_names))
    counters=request.counters
    from src.recognize import DISTINCT_ENTITY_NAMES
    names=frozenset([d.ente for d in documents]+list(DISTINCT_ENTITY_NAMES))
    entities=request.memo(('fingerprint_entities_v7',text[:2000],names),lambda:entity_evidence(text,sorted(names)))
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
            return RecognitionResult(True,100.,docs[did],('official_file_sha256_exact','fingerprint_v3',policy_version,'A_exact_sha'), 'File ufficiale canonico identico.',score_margin=100.,candidate_ids=(did,))
    p=profile() if decision_profile is None else decision_profile;t=p['thresholds'];s=p['settings'];queries=request.queries()
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
    def heading():return request.memo(('exclusive_heading_v7',text[:1200],tuple(documents)),lambda:exclusive_heading(text,documents))
    def heading_terms(r):
        h=heading();return h.get(r['document_id'],0) if set(h)=={r['document_id']} else 0
    def choose(r):
        old=tier(r,request.representation,t,code=r['document_id'] in codes,unique_fields=unique_ids=={r['document_id']})
        if old:return old
        rank1=bool(rows and r is rows[0])
        return conditional_tier(r,request.representation,t,rank1=rank1,heading_terms=heading_terms(r) if rank1 and r['visual']>=.98 else 0)
    # Only the bounded shortlist may trigger image decoding/rendering. Text,
    # chars and identity anchors are already computed once per request.
    eligible=[r for r in rows if choose(r) and safe(r)]
    if request.raw and (not eligible or (rows and request.representation in ['image','scanned_pdf'] and not choose(rows[0]))):
        for r in rows[:int(t['top_k'])]:
            legacy_gate=r['chars']>=t['chars'] and r['anchors']>=t['anchors'] and max(r['digital'],r['ocr'])>=t['ocr']
            scan_gate=request.representation in ['image','scanned_pdf'] and r['chars']>=t['scan_char'] and r['anchors']>=t['scan_anchor'] and max(r['digital'],r['ocr'])>=t['scan_ocr']
            strict_layout_gate=r is rows[0] and request.representation in ['image','scanned_pdf'] and r['anchors']>=t['conflict_anchors'] and ((r['chars']>=t['chars'] and max(r['digital'],r['ocr'])>=t['field_text']) or heading_terms(r)>=6)
            if r['overlap']<t['overlap'] or not (legacy_gate or scan_gate or strict_layout_gate) or not safe(r):continue
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
            state=evidence_states(text,docs[expected_row['document_id']],documents,entities)
            diagnostics.update(entity_status=state[0],version_status=state[1])
        visible=rows if not reference else index.similarities(queries,n=s['char_ngram'],aggregation=s['aggregation'],containment=s['containment'])
        diagnostics.update(counters=dict(counters),representation=request.representation,candidate_ids=[r['document_id'] for r in visible],candidates=[{k:r[k] for k in ['document_id','canonical_page','digital','ocr','chars','anchors','visual','overlap','score','max_similarity','top2_average']} for r in visible[:25]],thresholds=t,settings=s,entity_evidence=sorted(entities),version_evidence=sorted(set(re.findall(r'\b(?:versione|version|rev[.]?|revisione|anno|modello)\s*[:=/-]?\s*(\d+(?:[.]\d+)*)\b',text[:2000],re.I))))
    dominant=None
    supported=[r for r in rows if r['overlap']>=t['overlap']]
    if supported:
        first=supported[0];runner=max((r['score'] for r in supported[1:]),default=0.)
        if diagnostics is not None and corroborated_content(first,runner,t) and safe(first):
            diagnostics['corroborated_content_candidate']=first['document_id']
        if first['score']>=t['conflict_content'] and max(first['digital'],first['ocr'])>=t['conflict_content'] and first['chars']>=t['conflict_chars'] and first['anchors']>=t['conflict_anchors'] and first['overlap']>=t['overlap'] and first['score']-runner>=t['conflict_margin'] and safe(first):
            dominant=first['document_id']
            if diagnostics is not None:diagnostics['dominant_content_candidate']=dominant
    if not eligible:
        if diagnostics is not None:
            diagnostic_rows=visible if reference else rows
            diagnostics['reason_code']=(memo.get(diagnostic_rows[0]['resource_index']) or 'insufficient_multichannel_evidence') if diagnostic_rows else 'no_candidate'
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
    if competitors and best is rows[0] and heading_terms(best):
        # The full opening independently identifies the already-leading body.
        # Do not lower the margin; remove peers contradicted by that heading.
        if diagnostics is not None:diagnostics['exclusive_heading_disambiguation']=dict(document_id=best['document_id'],incompatible_peer_ids=[r['document_id'] for r in competitors])
        competitors=[]
    runner=max((r['score'] for r in competitors),default=0.)
    effective_margin,corroborated=corroborated_margin(best,competitors,len(request.texts),t)
    if diagnostics is not None and corroborated:diagnostics['multi_page_margin']=effective_margin
    if diagnostics is not None:diagnostics['margin']=effective_margin
    if effective_margin<t['margin']:
        if diagnostics is not None:diagnostics.update(reason_code='margin',tier='D_ambiguous')
        return None
    r=index.records[best['resource_index']]
    if r['status']=='shared' and not (codes=={best['document_id']} and entities):
        if diagnostics is not None:diagnostics.update(reason_code='shared_resource_ambiguous',tier='D_ambiguous')
        return None
    signals=('content_fingerprint_match','fingerprint_v3',policy_version,choose(best),f"canonical_page:{best['canonical_page']}",*(f'{k}:{best[k]:.4f}' for k in ['digital','ocr','chars','visual','anchors']))
    if diagnostics is not None:diagnostics.update(reason_code='accepted_'+choose(best),tier=choose(best))
    return RecognitionResult(True,min(99.,80+19*best['score']),docs[best['document_id']],signals,'Firma per pagina: '+choose(best)+'; ente e versione compatibili.',score_margin=100*effective_margin,candidate_ids=tuple(r['document_id'] for r in rows if r['overlap']>=3))
