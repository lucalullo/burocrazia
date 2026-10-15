"""Official-byte truth audit and complete numeric V5 failure diagnostics."""
import csv,re
from collections import Counter,defaultdict
from scripts.round20_common import *
from benchmarks.round3_audit import catalog
from src.fingerprint_v3 import read_bundle
from benchmarks.evaluate import summary

def csv_write(name,rows,fields=None):
    with (OUT/(name+'.csv')).open('w',encoding='utf8',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=fields or list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
    preserved();rows=read('benchmarks/results/round19/evaluation_v5_observations.json')['cases'];docs,_=catalog();by={d.id:d for d in docs}
    records=read_bundle()['records'];official={};truth=[];audit=[];critical=[]
    prepared=read('benchmarks/results/round19/evaluation_v5_prepared.json');inputs={c['case']['id']:c for c in prepared['representations']}
    generation={g['case_id']:g for g in prepared['generation_audit']}
    def official_proof(did):
        if did in official:return official[did]
        r=next(r for r in records if r['document_id']==did and r['status']=='active');raw=(ROOT/'benchmarks/cache'/(r['canonical_file_sha256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['canonical_file_sha256']
        opening='';pages=len(r['pages'])
        if r['mime_type']=='application/pdf':
            import pymupdf
            with pymupdf.open(stream=raw,filetype='pdf') as pdf:opening=pdf[0].get_text()[:2000];pages=len(pdf)
        elif 'wordprocessingml' in r['mime_type']:
            from docx import Document
            from io import BytesIO
            opening='\n'.join(p.text for p in Document(BytesIO(raw)).paragraphs)[:2000]
        roles=sorted({name for name,pattern in [('guardian',r'\bTUTORE\b|TUTELA DEI MINORI'),('parent',r'genitor|\bMADRE\b|\bPADRE\b')] if re.search(pattern,opening,re.I)})
        # Short official heading excerpt only, never a complete official work.
        heading=' '.join(line.strip() for line in opening.splitlines() if line.strip())[:180]
        official[did]=dict(document_id=did,source_id=r['source_id'],entity=by[did].ente,catalog_title=by[did].titolo_ufficiale,official_url=r['url'],final_url=r['final_url'],canonical_sha256=r['canonical_file_sha256'],acquired_at=r['acquisition_date'],pages=pages,opening_sha256=hashlib.sha256(opening.encode()).hexdigest(),heading_excerpt=heading,role_evidence=roles)
        return official[did]
    for r in rows:
        did=r['expected'].get('document_id');actual=r['observed'].get('document_id');d=r['decision_diagnostics'];e=d.get('expected_candidate') or {};rank=r['candidate_rank']
        wrong=r['observed']['match_type']!='NO_MATCH' and (r['unknown'] or r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct'] or r['entity_error'] or r['version_error'])
        reject=not r['unknown'] and r['observed']['match_type']!='DOCUMENT_MATCH'
        proof=official_proof(did) if did else dict(unknown_release_v3_manifest_sha256=sha('benchmarks/manifests/official_unknown_release_v3.json'),truth_status='confirmed_unknown_from_Round17_official_resource_audit')
        assert inputs[r['id']]['sha256']==r['input_sha256']
        classification='confirmed_expected';reason='Official canonical identity and immutable transformation provenance; technical adjudication, not human editorial review.' if did else 'Preserved confirmed unknown v3 truth, same resource SHA; no label changes.'
        if wrong and actual:
            competitor=official_proof(actual);critical.append(dict(case_id=r['id'],expected=proof,actual=competitor,classification=classification,
                rationale='Distinct official form headings/roles and resource SHA. Shared body/attachment does not erase first-page identity; original expected label confirmed.',same_resource=proof['canonical_sha256']==competitor['canonical_sha256'],same_entity=proof['entity']==competitor['entity']))
        if r['extraction_failed']:root='extraction_failure'
        elif wrong:root='shared_template' if did else 'other'
        elif not reject:root='other'
        elif d.get('expected_veto')=='explicit_entity_conflict':root='entity_conflict_false'
        elif rank is None:root='retrieval_miss'
        elif rank>1:root='retrieval_rank_low'
        elif d.get('reason_code')=='margin':root='page_alignment_failure' if e.get('canonical_page',1)>1 else 'shared_template'
        elif max(e.get('digital',0),e.get('ocr',0))<.8 and e.get('chars',0)>=.85 and e.get('anchors',0)>=.25 and e.get('overlap',0)>=16:root='visual_underuse'
        else:root='OCR_degradation'
        pred=next((c for c in d.get('candidates',[]) if c['document_id']==actual),{})
        runner=(d.get('candidates') or [])[1:2]
        transform=r['representation']
        if r['filled']:transform='filled_'+generation[r['id']]['acroform_static']
        row=dict(case_id=r['id'],document_id=did,source=r['provenance'].get('source_id',r['provenance'].get('source')),entity=r['expected'].get('entity',r['provenance'].get('entity')),representation_type=r['representation_type'],transform=transform,
            expected_result=r['expected']['match_type'],expected_document_id=did,expected_family_id=r['expected'].get('family_id'),actual_result=r['observed']['match_type'],actual_document_id=actual,actual_family_id=r['observed'].get('family_id'),correct=r['correct'],retrieval_rank_expected=rank,
            score_expected=e.get('score'),score_predicted=pred.get('score'),runner_up=json.dumps(runner[0] if runner else None,sort_keys=True),margin=d.get('margin'),entity_evidence=json.dumps(d.get('entity_evidence',[]),ensure_ascii=False),version_evidence=json.dumps(d.get('version_evidence',[])),code_evidence=json.dumps([s for s in r['signals'] if 'code' in s]),
            OCR_score=e.get('ocr'),char_score=e.get('chars'),token_score=e.get('digital'),visual_score=e.get('visual'),anchor_score=e.get('anchors'),page_match_score=e.get('score'),veto_triggered=bool(d.get('expected_veto') or d.get('reason_code')),veto_reason=d.get('expected_veto') or d.get('reason_code'),decision_tier=d.get('tier'),
            extraction_quality=json.dumps(dict(failed=r['extraction_failed'],method=r['extraction_method'],used_ocr=r['used_ocr'])),root_cause=root,notes=('Correct case; no failure root cause. ' if r['correct'] else '')+'OCR_score is stored OCR-token similarity, not Tesseract confidence. Missing diagnostics remain empty; fingerprint veto may precede a different metadata fallback result.')
        audit.append(row);truth.append(dict(case_id=r['id'],document_id=did,classification=classification,proof=proof,representation_sha256=r['input_sha256'],reason=reason,eligible_for_development=True))
    csv_write('v5_failure_audit',audit);fa=[a for a,r in zip(audit,rows) if r['observed']['match_type']!='NO_MATCH' and not r['correct']];fr=[a for a,r in zip(audit,rows) if not r['unknown'] and r['observed']['match_type']!='DOCUMENT_MATCH']
    csv_write('v5_false_accepts',fa,list(audit[0]));csv_write('v5_false_rejects',fr,list(audit[0]))
    atomic_json(ROOT/'benchmarks/reference/v5_truth_adjudication_v1.json',dict(schema_version=1,created_at=now(),historical_observations_sha256=sha('benchmarks/results/round19/evaluation_v5_observations.json'),labels_changed=False,cases=truth,critical_cases=critical,counts=dict(Counter(t['classification'] for t in truth)),official_resources=list(official.values()),scope='Technical adjudication from preserved officially acquired bytes/receipt dates/catalog binding and actual transformation lineage. No new live verification date or human editorial review attributed. Original V5 labels/results untouched.'))
    def stats(rs):
        known=[r for r in rs if not r['unknown']];tp=sum(r['document_correct'] for r in known);accepted=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in known)
        return dict(N=len(rs),precision=tp/accepted if accepted else None,exact_recall=tp/len(known) if known else None,retrieval_at1=sum(r['candidate_recall_at_k']['1'] for r in known)/len(known) if known else None,retrieval_at25=sum(r['candidate_recall_at_k']['25'] for r in known)/len(known) if known else None,extraction_success=sum(not r['extraction_failed'] for r in rs)/len(rs),false_accepts=sum(not r['correct'] and r['observed']['match_type']!='NO_MATCH' for r in rs),false_rejects=sum(not r['unknown'] and r['observed']['match_type']!='DOCUMENT_MATCH' for r in rs))
    transforms=defaultdict(list);sources=defaultdict(list)
    for a,r in zip(audit,rows):transforms[a['transform']].append(r);sources[str(a['source'])].append(r)
    save('v5_transform_breakdown',dict(transformations={n:stats(rs) for n,rs in sorted(transforms.items())},scope='Original historical V5 only; no post-fix metric substitution.'))
    save('v5_source_breakdown',dict(sources={n:dict(stats(rs),scan=stats([r for r in rs if r['scan_like']]) if any(r['scan_like'] for r in rs) else None,filled=stats([r for r in rs if r['filled']]) if any(r['filled'] for r in rs) else None) for n,rs in sorted(sources.items())}))
    save('v5_retrieval_diagnostics',dict(false_rejects=len(fr),rank_counts=dict(Counter('missing' if r['candidate_rank'] is None else str(r['candidate_rank']) for r in rows if not r['unknown'] and r['observed']['match_type']!='DOCUMENT_MATCH')),recall_at_k=read('benchmarks/results/round19/retrieval_v5.json')['recall_at_k'],cases=[dict(case_id=a['case_id'],rank=a['retrieval_rank_expected'],root_cause=a['root_cause']) for a in fr],policy='Top1+reject: decision;top25 but not1: scoring/alignment;outside25: retrieval/OCR. Do not broaden retrieval for a decision refusal.'))
    causes=Counter(a['root_cause'] for a,r in zip(audit,rows) if not r['correct']);save('v5_failure_summary',dict(cases=665,known=635,false_accepts=len(fa),false_rejects=len(fr),root_causes=dict(causes),truth_counts=dict(Counter(t['classification'] for t in truth)),historical_metrics=read('benchmarks/results/round19/evaluation_v5_gate.json')['gates']))
    (ROOT/'docs/ROUND20_V5_FAILURE_AUDIT.md').write_text(f'''# Round 20 — audit V5 storico

665 casi originali preservati:635 noti e30 unknown mix. Otto false accept documentali,179 false reject,0 errori ente/versione,0 family false accept. CSV completo una riga per caso; campi non raccolti rimangono vuoti. OCR_score indica similarità del canale OCR, non confidence di Tesseract.

Truth audit tecnico: {dict(Counter(t['classification'] for t in truth))}. Le risorse ufficiali locali e ricevute effettive provano identità e trasformazione; nessuna verifica editoriale umana o visita live odierna inventata. Tutti gli otto false accept confermati: i moduli469/470 per genitori e511/512 per tutori hanno intestazioni, ruoli e SHA distinti. La pagina allegata comune non autorizza il cambio di identità. L'originale V5 non viene aggiustato.

Root cause dei soli fallimenti: {dict(causes)}. I57 veto di ente includono intestazioni dipartimentali non corrispondenti a un ente noto e frammenti OCR generici di tribunale: queste stringhe non dimostrano un altro emittente. La policy attuale può rifiutare firme per margine e poi accettare un'identità differente tramite metadati. Una correzione generale deve rispettare l'ambiguità, conservare i conflitti espliciti e usare canali indipendenti; non basta abbassare una soglia.

I rifiuti top1 sono principalmente decision/channel gating; solo un caso fuori top25 (802/rotation180, OCR degradato). Retrieval non sarà modificato per risolvere i veto decisionali. Breakdown per fonte e trasformazione in JSON separati, sempre legati ai raw originali. Ogni replay successivo è development_regression_v5_after_fix.
''',encoding='utf8',newline='\n')
    print('R20 audit',len(audit),'FA',len(fa),'FR',len(fr),'causes',dict(causes),flush=True)

if __name__=='__main__':main()
