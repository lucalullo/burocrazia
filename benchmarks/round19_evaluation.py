"""Fresh identity audit, deterministic representations, one transactional v5 run."""
import argparse,csv,re
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from rapidfuzz.fuzz import ratio
from scripts.round19_common import *
from scripts.round19_seal import verify_benchmark_seal
from benchmarks.round3_audit import catalog
from benchmarks.round8_common import case,case_result,raw_record,identity
from benchmarks import round8_common as common
from benchmarks.round8_evaluation import transformed
from benchmarks.round8_fill import generate
from benchmarks.round6_recognition import TRANSFORMS
from benchmarks.transactional_writer import CaseJournal
from benchmarks.evaluate import summary,code_hash
from src.recognize import normalize_text
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding

WORK=ROOT/'benchmarks/work/round19/evaluation-v5'

def worker(item):
    raw=(ROOT/item['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
    r=case_result(item['case'],raw,Path(item['path']).name);r.update(filled=item['filled'],scan_like=item['scan_like'],unknown=item['unknown']);return r

def run():
    common.SEED=SEED
    f=sealed();verify_benchmark_seal();assert read(OUT/'evaluation_v5_generation_preflight.json')['passed'];assert not (OUT/'evaluation_v5_gate.json').exists(),'No completed evaluation replay'
    prepared=read(OUT/'evaluation_v5_prepared.json');items=prepared['representations'];ident=identity();key=dict(freeze_commit=f['freeze_git_commit'],prepared_sha256=sha(OUT/'evaluation_v5_prepared.json'),runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],runner_code_sha256=code_hash(),registry_sha256=sha(REGISTRY),benchmark_seal_sha256=sha(OUT/'benchmark_seal.json'))
    journal=CaseJournal(WORK/'evaluation.sqlite',identity=key,expected_ids=[c['case']['id'] for c in items]);pending=set(journal.pending())
    if not (OUT/'evaluation_v5_started.json').exists():save('evaluation_v5_started',dict(identity=key,expected_count=len(items),single_shot=True,created_at=now()))
    else:assert read(OUT/'evaluation_v5_started.json')['identity']==key
    with ProcessPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(worker,c):c['case']['id'] for c in items if c['case']['id'] in pending}
        for future in as_completed(jobs):
            r=future.result();assert r['id']==jobs[future];journal.append(r)
            if len(journal.rows())%25==0:print('R19 v5 persisted',len(journal.rows()),'/',len(items),flush=True)
    rows=journal.rows();journal.export(OUT/'evaluation_v5_observations.json',complete=True);assert len(rows)==len(items)==len({r['id'] for r in rows})
    import jsonschema
    jsonschema.validate(read(OUT/'evaluation_v5_observations.json'),read('benchmarks/schemas/round19_evaluation_observations.schema.json'))
    assert {r['id']:r['input_sha256'] for r in rows}=={c['case']['id']:c['sha256'] for c in items}
    known=[r for r in rows if not r['unknown']];scans=[r for r in known if r['scan_like']];filled=[r for r in known if r['filled']];unknown=[r for r in rows if r['unknown']]
    for name,group in [('robustness_v5',known),('scan_v5',scans),('filled_v5',filled),('end_to_end_v5',rows)]:save(name,dict(summary=summary(group),cases=group,identity=ident,observations_sha256=sha(OUT/'evaluation_v5_observations.json')))
    retrieval={str(k):sum(r['candidate_recall_at_k'][str(k)] for r in known)/len(known) for k in [1,5,10,25]};save('retrieval_v5',dict(n=len(known),recall_at_k=retrieval,observations_sha256=sha(OUT/'evaluation_v5_observations.json')))
    gates={}
    def g(n,a,passed):gates[n]=dict(actual=a,passed=bool(passed))
    def rate(group):
        tp=sum(r['document_correct'] for r in group);accepted=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in group)
        return tp/accepted if accepted else 0,tp/len(group) if group else 0
    precision,recall=rate(known);sp,sr=rate(scans);fp,fr=rate(filled);generation=read(OUT/'evaluation_v5_generation_preflight.json')['filled_generation_rate'];errors=dict(entity=sum(r['entity_error'] for r in known),version=sum(r['version_error'] for r in known));reject=sum(r['observed']['match_type']=='NO_MATCH' and not r['extraction_failed'] for r in unknown)/len(unknown)
    g('v5_preflight',read(OUT/'evaluation_v5_generation_preflight.json'),True);g('v5_leakage',0,read(OUT/'evaluation_v5_leakage.json')['passed']);g('v5_precision',precision,precision>=.995);g('v5_exact_recall',recall,recall>=.90);g('v5_scan_precision',sp,sp>=.995);g('v5_scan_recall',sr,sr>=.85);g('v5_filled_generation',generation,generation>=.90);g('v5_filled_precision',fp,fp>=.995);g('v5_filled_recall',fr,fr>=.90);g('v5_retrieval_at25',retrieval['25'],retrieval['25']==1);g('v5_retrieval_at1',retrieval['1'],retrieval['1']>=.99);g('v5_entity_version',errors,not any(errors.values()));g('v5_unknown_mix',reject,reject>=.99)
    save('evaluation_v5_gate',dict(passed=all(v['passed'] for v in gates.values()),gates=gates,expected_count=len(items),actual_count=len(rows),unique_case_ids=len(rows),final_observations_sha256=sha(OUT/'evaluation_v5_observations.json'),freeze_commit=f['freeze_git_commit'],identity=ident,single_shot=True))
    sealed();print('R19 v5 final gates',gates,flush=True)

if __name__=='__main__':
    run()
