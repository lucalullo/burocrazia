"""Measure only development unknowns with the R9 transactional writer."""
import hashlib
from concurrent.futures import ProcessPoolExecutor,as_completed
from benchmarks import round8_common as common
from benchmarks.round8_common import ROOT,read,case_result,identity
from benchmarks.transactional_writer import CaseJournal,atomic_json
from benchmarks.unknown_v2 import validate
from benchmarks.evaluate import summary

def worker(c):
 raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['SHA256']
 cc=dict(id=c['case_id'],group=c['resource_group'],category='confirmed_unknown_development',expected=dict(match_type='NO_MATCH'),label_status='confirmed',representation='official_original',provenance=dict(sha256=c['SHA256'],source=c['source'],entity=c['entity'],split=c['split'],historically_seen=c['historically_seen']))
 return case_result(cc,raw,'unknown.'+('pdf' if c['mime']=='application/pdf' else 'docx'))

def main():
 common.SEED=2026101210;manifest=validate(read('benchmarks/manifests/official_unknown_v2.json'));cases=[c for c in manifest['cases'] if c['split']=='unknown_dev'];ident=identity();binding={k:v for k,v in ident.items() if k not in ['commit','executed_at']};binding['manifest_sha256']=hashlib.sha256((ROOT/'benchmarks/manifests/official_unknown_v2.json').read_bytes()).hexdigest()
 journal=CaseJournal(ROOT/'benchmarks/work/round10'/('unknown-dev-'+binding['manifest_sha256'][:12]+'-'+binding['code_sha256'][:12]+'.sqlite'),identity=binding,expected_ids=[c['case_id'] for c in cases]);pending=set(journal.pending())
 with ProcessPoolExecutor(max_workers=3) as pool:
  for f in as_completed([pool.submit(worker,c) for c in cases if c['case_id'] in pending]):journal.append(f.result())
 rows=journal.rows();final=ROOT/'benchmarks/results/round10/unknown_development_observations.json';journal.export(final,complete=True)
 errors=sum(r['extraction_failed'] for r in rows);fa=sum(r['observed']['match_type']!='NO_MATCH' for r in rows)
 atomic_json(ROOT/'benchmarks/results/round10/unknown_development.json',dict(identity=ident,cases=rows,summary=summary(rows),false_accepts=fa,extraction_failed=errors,correct_rejections=sum(not r['extraction_failed'] and r['observed']['match_type']=='NO_MATCH' for r in rows),expected_count=len(cases),actual_count=len(rows),unique_case_ids=len({r['id'] for r in rows}),observations_sha256=hashlib.sha256(final.read_bytes()).hexdigest(),evaluation_recognition_calls=0,scope='Development only; no tuning performed. All R9 inputs remain contaminated. New unknown_eval resources untouched by recognition, no freeze or v5 execution.'))
 print('Unknown development',len(rows),'false accept',fa,'extract errors',errors,flush=True)

if __name__=='__main__':main()
