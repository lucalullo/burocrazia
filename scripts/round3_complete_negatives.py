"""One bounded negative-only acquisition amendment before ANY holdout evaluation."""
from collections import Counter
from dataclasses import asdict
from datetime import UTC,datetime
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,write
from benchmarks.round3_holdout import require_freeze,development,MANIFEST,RESULT
from benchmarks.holdout_leakage import collision,check
from maintenance.fetch import Fetcher

def main():
    require_freeze()
    assert not (ROOT/RESULT).exists(),'Never amend a manifest after the first evaluation.'
    event_path='benchmarks/results/round3/holdout_negative_amendment.json'
    assert not (ROOT/event_path).exists(),'Only one predefined amendment is allowed.'
    initial=(ROOT/MANIFEST).read_bytes()
    snapshot=ROOT/'benchmarks/results/round3/holdout_manifest_initial.json'
    with snapshot.open('xb') as f:f.write(initial)
    manifest=read(MANIFEST);cases=manifest['cases'];dev=development();hashes={c.get('sha256') for c in cases+dev};attempts=[]
    fetcher=Fetcher(ROOT/'benchmarks/cache',allow_network=True,use_cache=True)
    negatives=sum(c['expected_match_type']=='NO_MATCH' for c in cases)
    # A distinct informational-resource batch, not retries of blocked positives.
    # Preserve Fetcher's 400-request hard ceiling; use a lower 65-request budget.
    for c in read('benchmarks/results/round3/holdout_plan.json')['negative_options']:
        if negatives>=50 or fetcher.requests>=65:break
        try:
            receipt=fetcher.fetch(c['url'],c['source_key']);raw=fetcher.read(receipt)
            fmt='pdf' if raw.startswith(b'%PDF-') else 'docx' if raw.startswith(b'PK') else None
            if not fmt:raise ValueError('Non-document response')
            item=dict(c,id=f'OH1-{len(cases)+1:03}',format=fmt,sha256=receipt.sha256,acquired_at=receipt.acquired_at,cache_key=receipt.sha256+'.body',receipt=asdict(receipt),label_basis='Explicit official informational listing heading, selected before extraction or recognition.',reuse_conditions='Redistribution rights not established; ignored local cache only.')
            if receipt.sha256 in hashes or any(collision(item,x) for x in cases+dev):
                attempts.append(dict(url=c['url'],source_key=c['source_key'],status='duplicate_or_leakage_excluded'));continue
            cases.append(item);hashes.add(receipt.sha256);negatives+=1
            attempts.append(dict(url=c['url'],source_key=c['source_key'],status='downloaded',sha256=receipt.sha256))
        except (ValueError,OSError) as exc:attempts.append(dict(url=c['url'],source_key=c['source_key'],status='failed',reason=str(exc)))
        if len(attempts)%10==0:print('Negative-only batch:',negatives,'negatives',fetcher.requests,'requests',flush=True)
    leakage=check(dev,cases);assert leakage['passed']
    manifest['pre_evaluation_amendment']='One negative-only batch, original metadata/SHA order, lower 65-request budget, no extraction or recognition. Initial manifest preserved in raw results.'
    write(MANIFEST,manifest)
    acquisition=read('benchmarks/results/round3/holdout_acquisition.json')
    acquisition.update(negatives=negatives,attempts=acquisition['attempts']+attempts,complete_target=acquisition['positives']>=150 and negatives>=50,manifest_sha256=hashlib.sha256((ROOT/MANIFEST).read_bytes()).hexdigest(),negative_batch_requests=fetcher.requests,negative_batch_budget=65)
    write('benchmarks/results/round3/holdout_acquisition.json',acquisition)
    write('benchmarks/results/round3/holdout_leakage_check.json',leakage)
    write(event_path,dict(amended_at=datetime.now(UTC).isoformat(),initial_manifest_sha256=hashlib.sha256(initial).hexdigest(),final_manifest_sha256=acquisition['manifest_sha256'],negative_count=negatives,network_requests=fetcher.requests,attempts=attempts,no_holdout_text_read=True,no_recognition_run=True,reason='Initial positive queue exhausted its acquisition budget before reaching the separate negative queue; complete the predefined negative sample before any evaluation. No blocked source is retried.'))
    print('Completed negative batch:',negatives,Counter(c['source_key'] for c in cases if c['expected_match_type']=='NO_MATCH'),flush=True)

if __name__=='__main__':main()
