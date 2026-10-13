"""Preserve all source/data versions and verify single-shot/context integrity."""
import csv,hashlib,json,re,statistics,subprocess,sys,zipfile
from io import BytesIO
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_release import validate,select
from benchmarks.evaluate import code_hash
from benchmarks.round9_performance import describe
from src.benchmark_display import load_summary
from scripts.round13_semantics import check

OUT=ROOT/'benchmarks/results/round13';BASELINE='77bbe149a52102d5ca42743702c5b39f5a475326'


def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()


def main():
    check()
    fp=read('data/document_recognition_fingerprints_v3.json')
    old_raw=subprocess.check_output(['git','show',BASELINE+':data/document_recognition_fingerprints_v3.json'],cwd=ROOT)
    old=json.loads(old_raw);assert fp['records'][:1028]==old['records']
    restored_prefix=(json.dumps(dict(fp,records=fp['records'][:1028]),ensure_ascii=False,indent=2)+'\n').encode()
    assert restored_prefix==old_raw
    restore=read('benchmarks/results/round13/pre_adjudication_bundle_restore.json')
    previous=json.loads(json.dumps(fp))
    for change in restore['records']:
        for i,r in enumerate(previous['records']):
            if r['document_id']==change['document_id'] and r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy':
                previous['records'][i]=json.loads(change['record_json_before']);break
    previous_bytes=(json.dumps(previous,ensure_ascii=False,indent=2)+'\n').encode()
    assert hashlib.sha256(previous_bytes).hexdigest()==restore['bundle_sha256_before']
    assert digest('data/document_recognition_fingerprints_v3.json')==restore['bundle_sha256_after']
    unknown=read('benchmarks/results/round13/unknown_release_v1.json')
    assert unknown['identity']['fingerprint_sha256']==restore['bundle_sha256_before']
    files=sorted([*ROOT.glob('src/**/*.py'),*ROOT.glob('maintenance/*.py'),*ROOT.glob('benchmarks/*.py'),ROOT/'scripts/benchmark.py',ROOT/'app.py',ROOT/'run.py',ROOT/'data/recognition_features.json',*ROOT.glob('data/recognition_profiles/*.json'),*ROOT.glob('data/document_recognition_fingerprints*.json')])
    code_before=hashlib.sha256(b''.join(p.relative_to(ROOT).as_posix().encode()+b'\0'+(previous_bytes if p==ROOT/'data/document_recognition_fingerprints_v3.json' else p.read_bytes())+b'\0' for p in files)).hexdigest()
    assert code_before==unknown['identity']['code_sha256'],'The earlier single-shot code/data context is not exactly restorable'
    assert unknown['observations_sha256']==digest('benchmarks/results/round13/unknown_release_observations.json')
    observed=read('benchmarks/results/round13/unknown_release_observations.json')
    assert observed['complete'] and observed['expected_count']==observed['completed']==len(observed['cases'])==105
    assert len({r['id'] for r in observed['cases']})==105
    master=validate(read('benchmarks/manifests/official_unknown_master_v1.json'));release=validate(read('benchmarks/manifests/official_unknown_release_v1.json'))
    assert [c['case_id'] for c in select(master['cases'])]==[c['case_id'] for c in release['cases']]
    assert {c['case_id'] for c in release['cases']}=={c['id'] for c in observed['cases']}
    assert digest('benchmarks/manifests/official_unknown_release_v1.json')==unknown['manifest_sha256']
    for c in master['cases']:assert digest('benchmarks/cache/'+c['SHA256']+'.body')==c['SHA256']
    manifest=read('benchmarks/manifests/official_legacy_fingerprints_v1.json')
    for item in manifest['files']:
        raw=(ROOT/'benchmarks/cache'/(item['original_sha256']+'.body')).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['original_sha256']==item['receipt']['sha256']
        fmt=item['original_format']
        if fmt=='.doc':assert 'WordDocument'.encode('utf-16le') in raw
        elif fmt=='.xls':assert any(s.encode('utf-16le') in raw for s in ['Workbook','Book'])
        elif fmt=='.rtf':assert raw.lstrip().startswith(b'{\\rtf')
        elif fmt=='.xlsx':
            with zipfile.ZipFile(BytesIO(raw)) as z:assert 'xl/workbook.xml' in z.namelist()
    for folder in ['round13-legacy','round13-adjudication','round13-canonical','round13-converter-probe']:
        p=ROOT/'benchmarks/work'/folder
        assert not p.exists() or not list(p.iterdir()),folder
    definition=digest('benchmarks/reference/fingerprint_support_definition_v1.json')
    assert definition==read('benchmarks/results/round13/support_definition_lock.json')['sha256']
    rows=list(csv.DictReader((OUT/'legacy_fingerprint_audit.csv').open(encoding='utf8')))
    assert len(rows)==40 and sum(r['eligible_for_fingerprint_coverage']=='True' for r in rows)==27
    assert not read('benchmarks/results/round13/legacy_adjudication_observations.json')['wrong_document_accepts']
    perf=read('benchmarks/results/round13/performance_confirmation.json')
    assert len(perf['runs'])==5 and perf['identity']['code_sha256']==code_hash()
    for run in perf['runs']:assert len(run['samples'])==402 and describe([r['milliseconds'] for r in run['samples']])==run['latency_ms']
    assert statistics.median(r['latency_ms']['p95'] for r in perf['runs'])==perf['median_p95']
    archives={}
    for number in [8,9,10,11,12]:
        previous_archive=read(f'dist/package-verification-round{number}.json')
        assert digest('dist/'+previous_archive['archive'])==previous_archive['sha256']
        archives[previous_archive['archive']]=previous_archive['sha256']
    latest=load_summary(ROOT/'benchmarks/latest_summary.json');assert latest['round']==13 and latest['status']=='NOT READY'
    assert latest['unknown_official']['status']=='not_run' and not latest['unknown_official']['summary']['metrics']
    for path,sha in read('benchmarks/results/round8/baseline/metrics.json')['prior_raw_sha256'].items():assert digest(path)==sha
    for p in OUT.iterdir():
        if p.suffix in {'.json','.csv','.md'}:assert not re.search(rb'C:\\+(?:Users|users)\\',p.read_bytes()),p.name
    atomic_json(OUT/'prepackage_audit.json',dict(status='verified',old_fingerprint_records_preserved=1028,prior_bundle_sha256=hashlib.sha256(old_raw).hexdigest(),
                single_shot_original_context_byte_restorable=True,unknown_release_calls=105,unknown_release_replays=0,
                earlier_unknown_code_sha256=code_before,current_code_sha256=code_hash(),definition_sha256=definition,
                prior_archives_sha256=archives,official_unknown_hashes_verified=125,legacy_original_hashes_verified=40,
                converted_outputs_deleted=True,summary_contract='valid'))
    historical={}
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,*[f'benchmarks/results/round{n}' for n in range(6,13)]],cwd=ROOT,text=True).splitlines()
    paths+=['benchmarks/manifests/official_unknown_v1.json','benchmarks/manifests/official_unknown_v2.json','benchmarks/manifests/official_unknown_master_v1.json','benchmarks/manifests/official_unknown_release_v1.json','benchmarks/reference/reference_truth_v2.json','benchmarks/reference/reference_truth_v2_round10_addendum.json','benchmarks/reference/reference_truth_v2_round11_addendum.json','docs/ROUND12_REPORT.md','docs/ROUND12_BASELINE_AUDIT.md']
    for p in paths:
        original=subprocess.check_output(['git','show',BASELINE+':'+p],cwd=ROOT);current=(ROOT/p).read_bytes()
        assert current==original or current.replace(b'\r\n',b'\n')==original,p
        historical[p]=hashlib.sha256(original).hexdigest()
    current=[p for p in OUT.iterdir() if p.suffix in {'.json','.csv','.md'} and p.name!='evidence_locks.json']
    current.extend(ROOT/p for p in ['benchmarks/reference/fingerprint_support_definition_v1.json','benchmarks/manifests/official_legacy_fingerprints_v1.json','docs/ROUND13_BASELINE_AUDIT.md','docs/FINGERPRINT_COVERAGE_SEMANTICS.md','docs/ROUND13_REPORT.md','docs/BENCHMARK.md','docs/FINGERPRINT_COVERAGE_AUDIT.md','docs/release_gates.json','benchmarks/latest_summary.json'])
    atomic_json(OUT/'evidence_locks.json',dict(schema_version=1,status='NOT READY',baseline_commit=BASELINE,
                sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(current)},historical_original_git_sha256=historical,
                scope='Evidence locks, not a freeze. R6-R12 raw/corpora preserved. Initial and corrected R13 contexts preserved, no unknown replay or v5.'))
    print('R13 evidence verified',len(current),'historical',len(historical),flush=True)


if __name__=='__main__':main()
