"""Development-only representation probe; does not persist input features."""
import sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.transactional_writer import atomic_json
from benchmarks.round5_performance import deep_size
from benchmarks.evaluate import quantile
from src.fingerprint_v3 import public_index,features

def main():
    ix=public_index();cases=read('benchmarks/corpora/development_regression.json')['cases'];queries=[features(c['text']) for c in cases]
    # Include dense official page-hash queries, never synthetic recognition truth.
    for p in ix.pages[::200]:queries.append(dict(tokens=frozenset(p['digital'])|frozenset(p['ocr']),chars={n:frozenset(p['chars'][n]) for n in ['3','4','5']},anchors=frozenset(p['anchors'])))
    ids=[ix.candidates(q) for q in queries];baseline=[ix.page_scores_reference(q,ii,'3') for q,ii in zip(queries,ids)]
    def measure(fn):
        values=[]
        for _ in range(3):
            for q,ii in zip(queries,ids):
                t=time.perf_counter();rows=fn(q,ii,'3');values.append((time.perf_counter()-t)*1000)
        return dict(p50=quantile(values,.5),p95=quantile(values,.95))
    original_bytes=deep_size(ix.__dict__);original=measure(ix.page_scores_reference);intersection_arrays=measure(ix.page_scores)
    for p in ix.pages:
        for k in ['digital','ocr','anchors']:p[k]=tuple(p[k])
        p['chars']={n:tuple(v) for n,v in p['chars'].items()}
    size=deep_size(ix.__dict__);tuples=measure(ix.page_scores)
    equality=all(ix.page_scores(q,ii,'3')==r for q,ii,r in zip(queries,ids,baseline))
    atomic_json(ROOT/'benchmarks/results/round9/optimization_probe.json',dict(reference_arrays=original,intersection_arrays=intersection_arrays,intersection_tuples=tuples,reference_bytes=original_bytes,tuple_bytes=size,exact_equivalence=equality,query_count=len(queries),scope='Development page-scoring microbenchmark only, not the warm recognition gate. Dense canonical hash queries plus historical synthetic inputs; no persisted query features.'))
    print(original,intersection_arrays,tuples,'bytes',original_bytes,size,'equal',equality)
if __name__=='__main__':main()
