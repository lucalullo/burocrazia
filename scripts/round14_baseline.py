"""Audit the entry candidate and finish the pre-freeze prerequisite gate."""
import argparse,copy,hashlib,json,re,statistics,subprocess
from scripts.round14_common import *
from benchmarks.round3_audit import catalog
from benchmarks.round9_performance import describe
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding

def tests(path):
    raw=(ROOT/path).read_bytes();m=re.search(rb'(\d+) passed, (\d+) skipped in ([\d.]+)s',raw)
    assert m and b' failed' not in raw and b' error' not in raw
    return dict(passed=int(m[1]),failed=0,skipped=int(m[2]),seconds=float(m[3]),log_sha256=hashlib.sha256(raw).hexdigest())

def perf_check(p):
    assert len(p['runs'])==5 and p['status']=='complete'
    for r in p['runs']:assert len(r['samples'])==402 and describe([v['milliseconds'] for v in r['samples']])==r['latency_ms']
    assert statistics.median(r['latency_ms']['p95'] for r in p['runs'])==p['median_p95']
    return dict(p50=[r['latency_ms']['p50'] for r in p['runs']],p95=[r['latency_ms']['p95'] for r in p['runs']],median_p95=p['median_p95'],pass_count=p['pass_count'],
                preferred_four_of_five=p['pass_count']>=4,prudent_fragile=p.get('prudent_fragile'),mandatory_gate='Median p95 <=250ms; four of five preferred only',passed=p['median_p95']<=250)

def initial():
    serialization=assert_baseline_engine()
    locks=read('benchmarks/results/round13/evidence_locks.json')
    for p,h in locks['sha256'].items():assert sha(p)==h,p
    docs,_=catalog();by={d.id:d for d in docs};bundle=read_bundle()
    fixed={c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases'] if c['expected_resource_type']=='file_backed_document'}
    native={r['document_id'] for r in bundle['records'] if r['status']=='active' and r['mime_type'] in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
    shared={c['document_id'] for c in read('benchmarks/results/round12/shared_eligibility_audit.json')['cases'] if c['eligible']}
    legacy={r['document_id'] for r in bundle['records'] if r['status']=='active' and r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy'}
    for r in bundle['records']:
        if r['status']=='active':assert r['catalog_binding_sha256']==binding(by[r['document_id']])
    supported=(native|shared|legacy)&fixed
    assert len(native&fixed)==942 and len(shared-native)==33 and len(legacy)==27 and len(supported)==1002
    coverage=dict(file_backed_total=len(fixed),operational_total=1212,native_supported=len((native|shared)&fixed),legacy_qualified=len(legacy),
                  runtime_usable_supported=len(supported),file_backed_percent=100*len(supported)/len(fixed),all_operational_percent=100*len(supported)/1212,
                  shared_resource_only=33,definition_sha256=sha('benchmarks/reference/fingerprint_support_definition_v1.json'),eligible_ids=sorted(supported),
                  legacy_ids=sorted(legacy),passed=len(supported)/len(fixed)>=.85 and len(supported)/1212>=.70)
    save('coverage',coverage)
    restore=read('benchmarks/results/round13/pre_adjudication_bundle_restore.json');prior=copy.deepcopy(bundle);delta=[]
    for ch in restore['records']:
        i=next(i for i,r in enumerate(prior['records']) if r['document_id']==ch['document_id'] and r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy')
        old=json.loads(ch['record_json_before']);new=prior['records'][i]
        delta.append(dict(document_id=ch['document_id'],changed_fields=[k for k in new if new[k]!=old[k]],
                          before_status=old['status'],after_status=new['status'],before_shared_kind=old['shared_kind'],after_shared_kind=new['shared_kind']))
        prior['records'][i]=old
    assert hashlib.sha256((json.dumps(prior,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()==restore['bundle_sha256_before']
    unknown=read('benchmarks/results/round13/unknown_release_v1.json')
    assert unknown['identity']['fingerprint_sha256']==restore['bundle_sha256_before']!=sha('data/document_recognition_fingerprints_v3.json')
    native_c=read('benchmarks/results/round14/canonical.json');legacy_c=read('benchmarks/results/round14/canonical_legacy.json')
    assert native_c['counts']['exact']==980 and legacy_c['counts']['exact']==27
    prior_tests=read('benchmarks/results/round13/tests.json')
    assert tests('reports/round13-full-tests.log')['log_sha256']==prior_tests['log_sha256']
    value=dict(entry_commit=BASE,entry_branch='codex/coverage-benchmark-v0.7.0',entry_working_tree='clean',software_version='0.6.1',schema=610,
               coverage=coverage,canonical_native=native_c['counts'],canonical_legacy=legacy_c['counts'],
               unknown_v1=dict(status='historical_pre_unioncamere_fix',correct_no_match=105,total=105,valid_for_current_bundle=False,
                               measured_commit=unknown['identity']['commit'],measured_bundle=unknown['identity']['fingerprint_sha256'],final_r13_bundle=sha('data/document_recognition_fingerprints_v3.json'),exact_delta=delta,replayed=False),
               prior_performance=perf_check(read('benchmarks/results/round13/performance_confirmation.json')),prior_tests=prior_tests,
               round13_locks_verified=len(locks['sha256']),engine_files_sha256=engine_files(),preexisting_serialization_differences=serialization,audited_at=now())
    save('baseline_audit',value)
    (ROOT/'docs/ROUND14_BASELINE_AUDIT.md').write_text(f'''# Round 14 — audit iniziale

Branch `codex/coverage-benchmark-v0.7.0`, HEAD `{BASE}`, working tree pulito all'ingresso. Software pubblico 0.6.1, schema 610. Nessun byte del motore, profilo, fingerprint, catalogo o truth è cambiato. Verificati tutti i {len(locks['sha256'])} lock Round 13 prima di modificare file di infrastruttura.

Coverage ricalcolata dal bundle e dai binding correnti: 942 identità native attive, 33 associazioni shared storiche di supporto risorsa, 27 legacy qualificate. Totale **1002/1158 = 86.528497%**, sul totale operativo **1002/1212 = 82.673267%**. Definizione congelata SHA `{coverage['definition_sha256']}`. Canonici rieseguiti: **980/980 nativi, 27/27 legacy**, zero errori di estrazione o identità. Safety storica e cinque critici rieseguiti nei raw Round 14.

Unknown v1 conserva 105/105 ed è classificato in questo round **historical_pre_unioncamere_fix**. Il commit annotato durante la misura era `{unknown['identity']['commit']}` con working tree Round 13; il digest effettivo del bundle misurato è `{unknown['identity']['fingerprint_sha256']}`. Il commit finale Round 13 contiene invece `{sha('data/document_recognition_fingerprints_v3.json')}`. Ricostruito byte per byte il primo bundle dai tre record preservati. Il delta esatto riguarda soltanto status, shared_kind e ocr_metadata dei documenti 617, 618, 619; statistiche delle pagine, originali, soglie, scoring e veti invariati. V1 non valida il bundle finale e non sarà rieseguito.

Baseline performance Round 13 verificata sui 2010 tempi grezzi: mediana p95 215.5789 ms, 5/5 sotto 250 ms. Rapporto pytest precedente verificato con il suo hash: 772 passed, 0 failed, 3 skipped, 395.9 s. Il pre-freeze Round 14 richiede inoltre cinque nuove misure warm e un nuovo pytest completo, salvati separatamente; non si presume il loro esito. Registro di contaminazione prima del freeze; nuovi benchmark soltanto dopo il commit freeze e il PASS dei prerequisiti.
''',encoding='utf8',newline='\n')
    print('R14 entry audit complete',flush=True)

def gate():
    assert_baseline_engine();cov=read('benchmarks/results/round14/coverage.json')
    native=read('benchmarks/results/round14/canonical.json');legacy=read('benchmarks/results/round14/canonical_legacy.json')
    hist={p.stem:json.loads(p.read_bytes()) for p in OUT.glob('historical_*.json') if isinstance(json.loads(p.read_bytes()).get('cases'),list)}
    no=[c for v in hist.values() for c in v['cases'] if c['expected']['match_type']=='NO_MATCH'];wrong=[c['id'] for c in no if c['observed']['match_type']!='NO_MATCH']
    five=read('benchmarks/results/round14/verification.json')['historical_five_passed']
    r061=next(c for c in hist['historical_release_locked_v2']['cases'] if c['id']=='R061')
    two=[c for c in hist['historical_development_compat_v2']['cases'] if c['id'] in ['EX02MISSINGREV','EX03MISSINGREV']]
    safety=dict(n=len(no),false_accepts=wrong,r061=r061['observed'],round8_two=[c['observed'] for c in two],historical_five_passed=five,
                passed=len(no)==241 and not wrong and five and r061['observed']['match_type']=='NO_MATCH' and len(two)==2 and all(c['observed']['match_type']=='NO_MATCH' for c in two))
    save('historical_safety',safety)
    perf=perf_check(read('benchmarks/results/round14/performance_pre_freeze.json'));test=tests('reports/round14-baseline-tests.log');save('baseline_tests',test)
    checks=dict(coverage_pass=cov['passed'],canonical_native_pass=native['counts']['exact']==len(native['cases'])==980,
                canonical_legacy_pass=legacy['counts']['exact']==len(legacy['cases'])==27,historical_safety_pass=safety['passed'],performance_pass=perf['passed'],tests_pass=test['failed']==0)
    save('pre_freeze_gate',dict(**checks,passed=all(checks.values()),coverage=cov,performance=perf,tests=test,registry_sha256=sha(REGISTRY),created_at=now(),engine_files_sha256=engine_files()))
    print('R14 pre-freeze gate',checks,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['initial','gate']);a=p.parse_args();globals()[a.mode]()
