"""Serialize saved partial evidence only; never repeat any recognition."""
import hashlib,sys
from collections import Counter
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round8_common import checked,read,write,save,OUT
from benchmarks.round8_evaluation import generation_csv

def main():
    frozen=checked();out=ROOT/OUT
    assert (out/'evaluation_started.json').exists()
    assert not (out/'robustness_v4.json').exists(), 'Do not replace published observations'
    raw=(out/'evaluation_checkpoint.json').read_bytes();sha=hashlib.sha256(raw).hexdigest()
    checkpoint=read(OUT+'evaluation_checkpoint.json');rows=sorted(checkpoint['cases'],key=lambda r:r['id'])
    assert len(rows)==checkpoint['completed'] and len({r['id'] for r in rows})==len(rows)
    prepared=read(OUT+'evaluation_prepared.json');planned={r['case']['id']:r for r in prepared['representations']}
    for r in rows:assert planned[r['id']]['sha256']==r['input_sha256']
    (out/'evaluation_checkpoint_preserved.json').write_bytes(raw)
    log=(ROOT/'reports/round8-evaluation-single-shot.log').read_bytes()
    assert b'OSError: [Errno 22] Invalid argument' in log
    counts=Counter(str(r['provenance']['source_id']) for r in rows)
    status=dict(complete=False,planned=len(planned),persisted=len(rows),unavailable=len(planned)-len(rows),persisted_identity_ids=sorted({r['expected']['document_id'] for r in rows}),persisted_source_counts=dict(counts),persisted_source_concentration=max(counts.values())/len(rows),error_type='OSError',errno=22,failure_stage='Writing evaluation_checkpoint.json',checkpoint_sha256=sha,log_sha256=hashlib.sha256(log).hexdigest(),recorded_at=datetime.now(UTC).isoformat(),rerun=False,recognition_calls_during_preservation=0,scope='The single-shot runner terminated after a checkpoint write error. Its ProcessPool context awaited submitted work before exit, but results not in the saved checkpoint are unavailable. They are neither inferred nor counted as recognition failures. Saved rows are a completion-order subset and cannot represent the intended evaluation population. No rerun or post-freeze tuning performed.')
    write(OUT+'evaluation_interruption.json',dict(**status,freeze=frozen,unavailable_case_ids=sorted(set(planned)-{r['id'] for r in rows})))
    plan=read(OUT+'robustness_v4_evaluation_plan.json')
    for name,subset in [('robustness_v4',rows),('scan_v4',[r for r in rows if r['scan_like']]),('filled_v4',[r for r in rows if r['filled']]),('retrieval_v4',rows)]:
        save(name,subset,plan=plan,completion=status,status='incomplete',scope='INCOMPLETE: saved partial rows from the sole evaluation invocation. Descriptive metrics only; insufficient and not representative. Generation failures remain separate. No recognition executed by preservation script.')
    observed={r['id']:r for r in rows}
    for a in prepared['generation_audit']:
        a['recognition_result']=observed[a['case_id']]['observed']['match_type'] if a['case_id'] in observed else 'unavailable_after_run_interruption' if a['generated'] else 'not_run_generation_failed'
    generation_csv(prepared['generation_audit']);checked()
    print('Preserved',len(rows),'/',len(planned),'single-shot rows; NO recognition repeated',flush=True)

if __name__=='__main__':main()
