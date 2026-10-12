"""Reconcile actual recovery and immutable operational denominators."""
import csv,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,write
from src.fingerprint_v2 import read_bundle

def main():
    out='benchmarks/results/round7/'
    previous=list(csv.DictReader((ROOT/'benchmarks/results/round6/operational_support.csv').open(encoding='utf8')))
    records=read_bundle()['records'];active={r['document_id'] for r in records if r['status']=='active'}
    old=read('benchmarks/results/round6/fingerprint_coverage.json')
    old_ids={int(r['document_id']) for r in previous if r['round6_status']=='fingerprinted_exact'}
    by=defaultdict(list)
    for r in records:by[r['document_id']].append(r)
    failures=defaultdict(list)
    for r in read(out+'fingerprint_build.json')['failures']:failures[r['document_id']].append(r['reason'])
    resources=read('benchmarks/manifests/official_fingerprint_cache_v3.json')['files']
    supported={r['document_id'] for r in resources if r['mime'] in ('application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    reasons={};sources={};full=[]
    for r in previous:
        did=int(r['document_id']);r=dict(r);r['round7_status']='fingerprinted_exact' if did in active else 'not_fingerprinted'
        if did not in active:
            reason='shared_resource' if any(x['status']=='quarantined' for x in by[did]) else 'source_changed' if any(x['status']=='stale' for x in by[did]) else r['classification']
            if failures[did]:reason='unsupported_mime' if all(x.startswith('unsupported_actual_format') for x in failures[did]) else 'canonical_identity_or_extraction_failure'
            reasons[did]=reason;r['round7_reason']=reason+': '+'; '.join(sorted(set(failures[did])))
        else:r['round7_reason']='active_hash_only_signature'
        # Original file-backed identities never leave the denominator. Newly
        # obtained supported files can only add to it.
        r['expected_resource_type']='file_backed_document' if r['expected_resource_type']=='file_backed_document' or did in supported else r['expected_resource_type']
        full.append(r)
    file_ids={int(r['document_id']) for r in full if r['expected_resource_type']=='file_backed_document'}
    assert len(full)==1212 and len(file_ids)>=1158
    for source in sorted({r['source'] for r in full}):
        rr=[r for r in full if r['source']==source];ids={int(r['document_id']) for r in rr}
        sources[source]=dict(operational_docs_total=len(rr),file_backed_operational_docs=len(ids&file_ids),fingerprinted_all_operational_docs=len(ids&active),fingerprinted_file_backed_docs=len(ids&active&file_ids),missing_reasons=dict(Counter(reasons[i] for i in ids-active)))
    value=dict(operational_docs_total=1212,file_backed_operational_docs=len(file_ids),fingerprinted_all_operational_docs=len(active),fingerprinted_file_backed_docs=len(active&file_ids),metadata_only_docs=1212-len(file_ids),dynamic_service_docs=0,coverage_all=len(active)/1212,coverage_file_backed=len(active&file_ids)/len(file_ids),by_source=sources,baseline_round6=old,added_active_identities=sorted(active-old_ids),lost_active_identities=sorted(old_ids-active),missing_reasons=dict(Counter(reasons.values())),denominator_policy='Round6 file-backed classification preserved; new supported actual files only add. No failed/blocked file removed.',future_retrievable_gate_applied=False)
    write(out+'fingerprint_coverage.json',value)
    recovered=read(out+'recovery_attempts.json')['cases']
    for r in recovered:r['fingerprinted']=r['document_id'] in active;r['final_reason']='active_hash_only_signature' if r['fingerprinted'] else reasons[r['document_id']]+': '+'; '.join(sorted(set(failures[r['document_id']])))
    for did in sorted(old_ids-active):
        p=next(r for r in full if int(r['document_id'])==did)
        recovered.append(dict(document_id=did,source=p['source'],previous_reason='fingerprinted_exact',action='new_resource_alias_collision_audit',recovered=False,fingerprinted=False,final_reason=p['round7_reason']))
    for name,rows in [('fingerprint_recovery.csv',recovered),('operational_support.csv',full)]:
        with (ROOT/out/name).open('w',encoding='utf8',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print('Active',len(active),'file-backed',len(file_ids),'coverage',value['coverage_file_backed'])

if __name__=='__main__':main()
