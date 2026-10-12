"""Reconstruct rejected R6 inputs locally; persist numeric/evidence codes only."""
import csv,hashlib,json,os,re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from benchmarks.round3_audit import ROOT,catalog,read,write
from src.extract import extract_document
from src.fingerprint_v2 import public_index,features,thresholds,fused
from src.fingerprint_match_v2 import safety_reason
from src.recognize import _issuer_entities,DISTINCT_ENTITY_NAMES,normalize_text

def one(c):
    did=c['expected']['document_id'];paths=list((ROOT/'benchmarks/work/round6-representations').glob(str(did)+'-'+c['representation']+'.*'))
    p=next(p for p in paths if hashlib.sha256(p.read_bytes()).hexdigest()==c['input_sha256'])
    ex=extract_document(p.read_bytes(),p.name);docs,_=catalog();d=next(d for d in docs if d.id==did)
    q=features(ex.text);s=next(s for s in c['retrieval_scores'] if s['document_id']==did);r=public_index().records[s['resource_index']]
    channels={}
    for k in ['digital','ocr','header','ocr_header']:
        values=r[k];w=public_index().weights;den=sum(w.get(h,1) for h in values)
        channels[k]=sum(w.get(h,1) for h in values if h in q['tokens'])/den if den else 0
    entities=_issuer_entities(ex.text[:2000],[d.ente for d in docs]+list(DISTINCT_ENTITY_NAMES))
    veto=safety_reason(ex.text,d,docs)
    root='version veto too strict' if veto in ['missing_revision','missing_version_year','explicit_or_missing_model_year'] else 'identity veto too strict' if veto else 'channel count requirement'
    if not veto and not fused(s,thresholds()):
        root='OCR score low' if s['text']<thresholds()['text'] else 'containment threshold' if s['chars']<thresholds()['chars'] else 'channel count requirement'
    competitor=max((x['score'] for x in c['retrieval_scores'] if x['document_id']!=did),default=0)
    return dict(case_id=c['id'],document_id=did,rank=c['candidate_rank'],transform=c['representation'],
        **channels,chars=s['chars'],visual=s['visual'],anchors=s['anchors'],combined_score=s['score'],
        entity_evidence='compatible_explicit' if normalize_text(d.ente) in entities else 'other_explicit' if entities else 'missing',
        version_evidence=veto if veto and ('version' in veto or 'revision' in veto or 'year' in veto) else 'compatible_or_not_versioned',
        veto=veto or 'none',threshold=json.dumps(thresholds(),sort_keys=True),margin=s['score']-competitor,
        cluster=root,ocr_used=ex.used_ocr,characters=len(ex.text),input_sha256=c['input_sha256'])

def main():
    from benchmarks.round4_common import runtime_hash
    if (ROOT/'benchmarks/results/round7/decision_audit_before.json').exists():raise ValueError('Immutable baseline audit already exists')
    if runtime_hash()!=read('benchmarks/results/round6/robustness_v2.json')['identity']['runtime_sha256']:raise ValueError('Round6 audit requires original Round6 runtime and bundle')
    os.environ.setdefault('OMP_THREAD_LIMIT','1')
    cases=[c for c in read('benchmarks/results/round6/robustness_v2.json')['cases'] if not c['correct']]
    rows=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(one,c) for c in cases]):rows.append(f.result())
    rows.sort(key=lambda r:r['case_id']);p=ROOT/'benchmarks/results/round6/decision_rejections.csv'
    with p.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    counts=dict(Counter(r['cluster'] for r in rows));vetoes=dict(Counter(r['veto'] for r in rows))
    write('benchmarks/results/round7/decision_audit_before.json',dict(cases=rows,clusters=counts,vetoes=vetoes,scope='Round6 is development. Reconstructed bytes SHA-checked; no extracted text persisted.'))
    (ROOT/'docs/ROUND7_DECISION_AUDIT.md').write_bytes(('# Round 7 — decision audit\n\nRound6 evaluation è ora development. Tutti i 42 rifiuti rank 1 sono ricostruiti da byte verificati.\n\nCluster: `'+json.dumps(counts)+'`.\n\nVeto: `'+json.dumps(vetoes)+'`.\n\nScore per canale, evidenza ente/versione, margine e soglie nel CSV `benchmarks/results/round6/decision_rejections.csv`. Nessun testo OCR personale conservato.\n').encode())
    print('Rejections',len(rows),'clusters',counts,'vetoes',vetoes,flush=True)

if __name__=='__main__':main()
