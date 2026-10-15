"""Contaminated development replay; never label it independent V5/V6."""
import argparse,time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict
from scripts.round20_common import *
from benchmarks.round3_audit import catalog
from benchmarks.transactional_writer import CaseJournal
from benchmarks.evaluate import summary,code_hash
from benchmarks.round4_common import runtime_hash
from benchmarks.release_truth import load_release
from src.fingerprint_pages import RequestPages
from src.recognize import recognize_catalog,recognize_document_family
from src.models import CatalogRecognitionResult
from src.fingerprint_decision_v6 import profile,revision
from scripts.benchmark import evaluate_case

def worker(c):
    docs,families=catalog();raw=(ROOT/c['raw_file']).read_bytes() if c.get('raw_file') else b''
    if raw:assert hashlib.sha256(raw).hexdigest()==c['sha256']
    ctx=RequestPages(tuple(c['texts']),c['representation'],tuple(c['field_set']),tuple(c['numbers']),raw,c['filename']);diag={'expected_id':(c.get('expected') or {}).get('document_id')};start=time.perf_counter()
    if c.get('extraction_failed'):
        result=CatalogRecognitionResult('NO_MATCH',0,0,reason='Historical unsupported parser input safely rejected.')
    elif c.get('recognition')=='family':
        f=recognize_document_family(c['text'],families,known_entities=[d.ente for d in docs]);result=CatalogRecognitionResult('FAMILY_MATCH' if f.recognized else 'NO_MATCH',0,f.confidence,family=f.family)
    else:result=recognize_catalog(c['text'],docs,families,page_context=ctx,file_sha256=c['sha256'],fingerprint_diagnostics=diag)
    if c.get('expected'):
        cc=dict(id=c['id'],group=c['group'],category=c['category'],expected=c['expected']);row=evaluate_case(cc,result,(time.perf_counter()-start)*1000)
    else:
        row=dict(id=c['id'],expected=None,observed=dict(match_type=result.match_type,document_id=result.document.id if result.document else None,family_id=result.family.id if result.family else None),labelled=False)
    row.update(group=c['group'],category=c['category'],original_id=c['id'].removeprefix('HIST:'),input_sha256=c['sha256'],representation=c['representation'],transform=c.get('transform'),filled=c.get('filled',False),scan_like=c.get('scan_like',False),
        extraction_failed=c.get('extraction_failed',False),extraction_error=c.get('extraction_error'),signals=list(result.document_signals),reason=result.reason,recognition_calls=0 if c.get('extraction_failed') else 1,
        decision_diagnostics={k:v for k,v in diag.items() if k not in ['candidate_ids','candidates']},candidate_ids=diag.get('candidate_ids',[])[:25],top_candidates=diag.get('candidates',[])[:5])
    return row

def run(attempt):
    preserved();prepared=read(WORK/'development-inputs.json');rows=prepared['rows']
    ident=dict(runtime_sha256=runtime_hash(),fingerprint_sha256=sha('data/document_recognition_fingerprints_v3.json'),profile_sha256=revision(),prepared_sha256=sha(WORK/'development-inputs.json'),runner_code_sha256=code_hash(),attempt=attempt)
    target=OUT/('development_observations_'+attempt+'.json');assert not target.exists()
    journal=CaseJournal(WORK/('development-'+attempt+'-'+ident['runtime_sha256'][:12]+'.sqlite'),identity=ident,expected_ids=[c['id'] for c in rows]);pending=set(journal.pending())
    with ProcessPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(worker,c):c['id'] for c in rows if c['id'] in pending}
        for f in as_completed(jobs):
            r=f.result();assert r['id']==jobs[f];journal.append(r)
            if len(journal.rows())%100==0:print('R20 development',attempt,len(journal.rows()),'/',len(rows),flush=True)
    actual=journal.rows();journal.export(target,complete=True);assert len(actual)==len(rows)
    _,_,contracts=load_release();qualified={c['input_key'] for c in contracts if c['truth_domain']!='parser_limit_contract'}
    certain=[r for r in actual if r.get('expected') and (r['group']!='historical' or r['original_id'] in qualified)]
    known=[r for r in certain if r['expected']['match_type']=='DOCUMENT_MATCH'];negative=[r for r in certain if r['expected']['match_type']=='NO_MATCH' and not r['extraction_failed']]
    v5=[r for r in actual if r['group']=='v5'];scans=[r for r in v5 if r['scan_like']];fills=[r for r in v5 if r['filled']]
    fa=[r['id'] for r in negative if r['observed']['match_type']!='NO_MATCH']+[r['id'] for r in known if r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct']]
    def rate(rs):
        tp=sum(r['document_correct'] for r in rs);accepted=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in rs)
        return dict(n=len(rs),exact=tp,accepted=accepted,wrong=accepted-tp,precision=tp/accepted if accepted else 0,recall=tp/len(rs) if rs else 0)
    m=rate(v5);s=rate(scans);fill=rate(fills);global_known=rate(known)
    canonical=[r for r in actual if r['group']=='canonical'];canonpass=len(canonical)==1007 and all(r['document_correct'] for r in canonical)
    gates=dict(dev_precision_pass=m['precision']>=.995 and global_known['precision']>=.995,dev_recall_pass=m['recall']>=.9,dev_scan_pass=s['recall']>=.85,dev_filled_pass=fill['recall']>=.9,confirmed_safety_pass=not fa,canonical_pass=canonpass)
    save('development_regression_v5_after_fix_'+attempt,dict(classification='development_regression_v5_after_fix',identity=ident,metrics=m,scan=s,filled=fill,cases=v5,observations_sha256=sha(target),historical_original_unchanged=True))
    used_ids={c['expected']['document_id'] for c in rows if c['group']!='canonical' and c.get('expected') and type(c['expected'].get('document_id')) is int}
    used_ids|={r['observed']['document_id'] for r in certain if r['observed'].get('document_id') and not r['correct']}
    save('calibration_'+attempt,dict(identity=ident,parameters=profile(),thresholds=profile()['thresholds'],weights=dict(content=.5,chars=.35,anchors=.15),rules=['respect fingerprint ambiguity in metadata fallback','weak subordinate/OCR-prefix entity evidence is not contradictory issuer','strong char+OCR+anchor+visual scan tier','two aligned pages corroborate identity over shared attachment'],
        objective='Zero confirmed false accepts first; improve recall only with corroborated independent channels. No future V6 identity selection or tuning.',identity_ids=sorted(used_ids),
        combined_known=global_known,V5_development=m,scan=s,filled=fill,confirmed_negative_count=len(negative),negative_false_accept_ids=[r['id'] for r in negative if r['observed']['match_type']!='NO_MATCH'],confirmed_false_accept_ids=fa,canonical_exact=sum(r['document_correct'] for r in canonical),gates=gates,passed=all(gates.values()),
        actual_count=len(actual),recognition_calls=sum(r['recognition_calls'] for r in actual),observations_sha256=sha(target),scope='Contaminated development diagnostics only. Original independent V5 P98.2456/R70.5512/scan63.2937 preserved. Unsupported parser-limit cases are reported separately, never credited as unknown classification.'))
    print('R20 development complete',attempt,m,s,fill,'falseaccepts',fa,'gates',gates,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('attempt');run(p.parse_args().attempt)
