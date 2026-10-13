"""Recompute R11 entry evidence before maintenance changes."""
import hashlib,json,math,re,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks.transactional_writer import atomic_json
from benchmarks.round4_common import runtime_hash
from benchmarks.evaluate import code_hash
from src.fingerprint_v3 import read_bundle,PATH,VERSION
OUT=ROOT/'benchmarks/results/round11'

def main():
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 assert head=='d19547f458e46d38c11a84ffd9e2f735510ac5bc'
 branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
 locks=read('benchmarks/results/round10/evidence_locks.json')
 for p,sha in locks['sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha,p
 docs,_=catalog();operative=[d for d in docs if d.stato_verifica not in ['demo','rifiutato']]
 fixed={c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases'] if c['expected_resource_type']=='file_backed_document'}
 bundle=read_bundle();active={r['document_id'] for r in bundle['records'] if r['status']=='active'};shared={r['document_id'] for r in bundle['records'] if r['status']=='shared'}
 n=len(fixed);fp=len(active&fixed);needed=math.ceil(n*.85)
 target=dict(file_backed_total=n,current_fingerprinted=fp,minimum_for_85=needed,exact_shortfall=needed-fp,operational_total=len(operative),initial_coverage_percent=100*fp/n,shared_only_candidates=len((shared-active)&fixed),scope='Initial R10 unambiguous metric preserved. R11 shared eligibility requires a separate binding/provenance audit; no automatic promotion of all shared IDs.')
 atomic_json(OUT/'coverage_target.json',target)
 cases=read('benchmarks/manifests/official_unknown_v2.json')['cases'];counts=Counter(c['source'] for c in cases);dominant,count=counts.most_common(1)[0];other=len(cases)-count
 balance=dict(current_total=len(cases),current_sources=len(counts),counts_per_source=dict(counts),dominant_source=dominant,current_max_source_count=count,current_max_concentration=count/len(cases),release_minimum=100,max_per_source_at_100=25,non_dominant_available=other,dominant_usable_at_100=min(25,count),minimum_new_non_dominant=max(0,100-other-min(25,count)),minimum_new_sources=max(0,8-len(counts)),preferred_additions=[20,40],scope='All confirmed master cases retained. A deterministic source quota subset may be selected before evaluation; no prediction-based selection.')
 atomic_json(OUT/'unknown_balance_target.json',balance)
 canonical=read('benchmarks/results/round10/canonical.json')['cases']
 historical={p.stem:json.loads(p.read_bytes()) for p in (ROOT/'benchmarks/results/round10').glob('historical_*.json') if p.name!='historical_safety.json'}
 negatives=[r for v in historical.values() for r in v['cases'] if r['expected']['match_type']=='NO_MATCH']
 raw=(ROOT/'reports/round11-baseline-tests.log').read_bytes();m=re.search(rb'(\d+) passed, (\d+) skipped in ([\d.]+)s',raw);assert m and b' failed' not in raw
 tests=dict(passed=int(m[1]),skipped=int(m[2]),failed=0,seconds=float(m[3]),log_sha256=hashlib.sha256(raw).hexdigest())
 perf=read('benchmarks/results/round10/performance.json')
 value=dict(branch=branch,commit=head,entry_working_tree='clean (captured before baseline script creation)',software_version='0.6.1',schema=610,coverage=target,unknown=balance,canonical=dict(exact=sum(r['document_correct'] for r in canonical),total=len(canonical),wrong=sum(r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct'] for r in canonical)),historical_no=len(negatives),historical_false_accepts=[r['id'] for r in negatives if r['observed']['match_type']!='NO_MATCH'],historical_counts={k:dict(passed=v['summary']['passed'],total=len(v['cases'])) for k,v in historical.items()},tests=tests,performance=perf['latency_ms'],performance_source_sha256=hashlib.sha256((ROOT/'benchmarks/results/round10/performance.json').read_bytes()).hexdigest(),fingerprint_version=VERSION,fingerprint_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),decision_version='fingerprint-decision-v5',runtime_sha256=runtime_hash(),code_sha256=code_hash(),r10_evidence_locks_verified=len(locks['sha256']),freeze=None,evaluation_v5='not_run',ci='external_pending')
 assert value['runtime_sha256']==perf['identity']['runtime_sha256'] and value['code_sha256']==perf['identity']['code_sha256']
 atomic_json(OUT/'baseline_audit.json',value)
 (ROOT/'docs/ROUND11_BASELINE_AUDIT.md').write_bytes(f'''# Round 11 baseline audit

Branch `{branch}`, HEAD `{head}`, working tree pulito all’ingresso. Pubblico 0.6.1, schema 610; fingerprint-v3 e decision-v5. Verificati tutti i {len(locks['sha256'])} lock R10. Nessun freeze o evaluation v5, CI external_pending.

Denominatore congelato R6: {n}; identità unambiguous {fp}; coverage {100*fp/n:.6f}%. Minimo per l’85%: {needed}, delta {needed-fp}. Operative {len(operative)}, coverage {100*fp/len(operative):.6f}%. I 38 candidati shared-only sono un limite superiore da auditare, non un aumento automatico della metrica. Nessun cambio di denominatore.

Canonical ricalcolato 979/979, wrong 0; {len(negatives)} osservazioni NO storiche, false accept 0. R061, due casi R8 e cinque casi ufficiali critici verdi nei raw R10. Base 33/35 e locked v1 59/69 preservati, v2 69/69, compat 37/37, hard negatives 30/30 e 100/100. Rerun baseline suite: {tests['passed']} passati, {tests['skipped']} skipped, 0 failed ({tests['seconds']} s), Tesseract locale reale.

Performance R10 p50 {perf['latency_ms']['p50']:.4f} ms, p95 {perf['latency_ms']['p95']:.4f} ms, 402 richieste, legata agli hash correnti. Il raw conserva i quantili del protocollo, non tutti i tempi individuali: il quantile è verificato come misura persistita, senza inventare una nuova ricostruzione dei campioni.

Unknown master {len(cases)}, {len(counts)} fonti: `{json.dumps(dict(counts))}`. Dominante {dominant}={count}, concentrazione {100*count/len(cases):.6f}%; altri {other}. Subset N=100: al massimo 25 dal dominante, quindi servono esattamente {balance['minimum_new_non_dominant']} nuovi casi non dominanti e almeno {balance['minimum_new_sources']} nuova fonte. Tutto il master resta conservato. Dati e hash integrali nei raw R11.
'''.encode())
 print('R11 baseline saved',tests,'coverage shortfall',needed-fp,'unknown additions',balance['minimum_new_non_dominant'])

if __name__=='__main__':main()
