"""Archive tracked HEAD and verify release hygiene and frozen bytes."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    gates=json.loads((ROOT/'docs/release_gates.json').read_text(encoding='utf-8'))
    round_number=gates.get('round',5)
    name=f'BurOCRazia-v0.7.0-RC1-round{round_number}.zip' if gates.get('local_gates_passed') else f'BurOCRazia-v0.7.0-candidate-NOT-READY-round{round_number}.zip'
    output=ROOT/'dist'/name;output.parent.mkdir(exist_ok=True)
    subprocess.run(['git','archive','--format=zip','--prefix=BurOCRazia/','-o',str(output),'HEAD'],cwd=ROOT,check=True)
    forbidden={'.git','.venv','__pycache__','.pytest_cache','cache','staging','tmp-build','work','node_modules'}
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        names=archive.namelist();violations=[]
        for name in names:
            parts=Path(name).parts
            if forbidden.intersection(parts) or re.search(r'\.(?:pdf|docx|exe|traineddata|db|db-wal|db-shm|pyc)$',name,re.I):violations.append(name)
            if name.endswith(('.py','.md','.json','.toml','.yml','.txt','.ps1')):
                raw=archive.read(name)
                if re.search(rb'C:\\+(?:Users|users)\\',raw,re.I) or re.search(rb'\b'+b'Chi'+b'arIA'+rb'\b',raw,re.I):violations.append(name+': user path/old name')
                if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{32,}',raw):violations.append(name+': secret pattern')
        assert not violations,violations
        manifest=json.loads(archive.read('BurOCRazia/data/catalog_manifest.json'))
        assert hashlib.sha256(archive.read('BurOCRazia/data/catalog_seed.sqlite3')).hexdigest()==manifest['sha256']
        for locks in ['corpus_locks_v1.json','corpus_locks_v2.json','file_corpus_locks_v1.json','file_corpus_locks_v2.json','family_release_locks_v1.json','family_release_locks_v2.json','family_release_locks_v3.json','development_compat_locks_v2.json']:
            values=json.loads(archive.read('BurOCRazia/benchmarks/manifests/'+locks))['sha256']
            for key,digest in values.items():
                path=key if '/' in key else 'benchmarks/corpora/'+key
                assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
        frozen=json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_holdout_locks_v1.json'))
        for path,digest in frozen['sha256'].items():
            assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
        frozen2=json.loads(archive.read('BurOCRazia/benchmarks/manifests/official_holdout_locks_v2.json'))
        for path,digest in frozen2['sha256'].items():
            assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
        package=json.loads(archive.read('BurOCRazia/maintenance/releases/2026-10-11/manifest.json'))
        for item in package['files']:
            raw=archive.read('BurOCRazia/maintenance/releases/2026-10-11/'+item['path'])
            assert len(raw)==item['size_bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        from benchmarks.evaluate import code_hash
        relevant=sorted([*ROOT.glob('src/**/*.py'),*ROOT.glob('maintenance/*.py'),*ROOT.glob('benchmarks/*.py'),*ROOT.glob('data/recognition_profiles/*.json'),*ROOT.glob('data/document_recognition_fingerprints*.json'),ROOT/'scripts/benchmark.py',ROOT/'app.py',ROOT/'run.py',ROOT/'data/recognition_features.json'])
        for file in relevant:assert archive.read('BurOCRazia/'+file.relative_to(ROOT).as_posix())==file.read_bytes(),file.relative_to(ROOT)
        assert gates['identity']['code_sha256']==code_hash()
        from benchmarks.round4_common import runtime_hash
        assert gates['identity']['runtime_sha256']==runtime_hash()
        from src.document_fingerprints import validate
        fp=archive.read('BurOCRazia/data/document_recognition_fingerprints.json')
        validate(json.loads(fp))
        if round_number<6:assert hashlib.sha256(fp).hexdigest()==gates['identity']['fingerprint_sha256']
        if round_number>=6:
            from src.fingerprint_v2 import validate as validate_v2
            fp2=archive.read('BurOCRazia/data/document_recognition_fingerprints_v2.json')
            validate_v2(json.loads(fp2))
            assert hashlib.sha256(fp2).hexdigest()==gates['identity']['fingerprint_sha256']
        if round_number==7:
            freeze=json.loads(archive.read('BurOCRazia/benchmarks/results/round7/freeze.json'))
            for key in ['runtime_sha256','code_sha256','fingerprint_sha256']:assert freeze[key]==gates['identity'][key]
            assert hashlib.sha256(archive.read('BurOCRazia/benchmarks/results/round7/decision_calibration.json')).hexdigest()==freeze['calibration_sha256']
            if freeze.get('calibration_reference_fix_sha256'):assert hashlib.sha256(archive.read('BurOCRazia/benchmarks/results/round7/decision_calibration_reference_fix.json')).hexdigest()==freeze['calibration_reference_fix_sha256']
            assert hashlib.sha256(archive.read('BurOCRazia/data/recognition_profiles/fingerprint_decision_v3.json')).hexdigest()==freeze['profile_sha256']
            leakage=json.loads(archive.read('BurOCRazia/benchmarks/results/round7/evaluation_v3_leakage.json'))
            assert leakage['prohibited_leakage']==0 and not any(leakage[k] for k in ['identity_overlap','resource_sha_overlap','canonical_url_overlap','title_code_version_overlap'])
            plan=json.loads(archive.read('BurOCRazia/benchmarks/results/round7/robustness_v3_evaluation_plan.json'))
            assert not set(plan['calibration_identities'])&set(plan['evaluation_identities'])
            locks=json.loads(archive.read('BurOCRazia/benchmarks/results/round7/evaluation_locks.json'))
            for path,digest in locks['sha256'].items():
                assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
        if round_number==6:
            calibration=json.loads(archive.read('BurOCRazia/benchmarks/results/round6/fingerprint_calibration.json'))
            assert hashlib.sha256(archive.read('BurOCRazia/data/recognition_profiles/fingerprint_v2.json')).hexdigest()==calibration['profile_sha256']
            assert not set(calibration['calibration_identities'])&set(calibration['evaluation_identities'])
            locks=json.loads(archive.read('BurOCRazia/benchmarks/results/round6/evaluation_locks.json'))
            for path,digest in locks['sha256'].items():
                assert hashlib.sha256(archive.read('BurOCRazia/'+path)).hexdigest()==digest,path
            assert locks['runtime_sha256']==gates['identity']['runtime_sha256']
        assert archive.read('BurOCRazia/docs/release_gates.json')==(ROOT/'docs/release_gates.json').read_bytes()
    report=dict(schema_version=1,commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),archive=output.name,bytes=output.stat().st_size,members=len(names),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),catalog_sha256=manifest['sha256'],frozen_locks_verified=True,code_bytes_match_measurements=True,hygiene_violations=[])
    (output.parent/'package-verification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    output.with_suffix('.zip.sha256').write_bytes((report['sha256']+'  '+output.name+'\n').encode())
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
