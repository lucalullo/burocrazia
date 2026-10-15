"""Append proof for a reference-only diagnostic correction; keep calibration bytes."""
import hashlib,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,write
from benchmarks.round4_common import runtime_hash
from src.fingerprint_v2 import revision
from src.fingerprint_decision_v3 import PATH

def main():
    out='benchmarks/results/round7/';cal=read(out+'decision_calibration.json')
    def original(path):return subprocess.check_output(['git','show',cal['commit']+':'+path])
    old=original('src/fingerprint_match_v2.py').decode()
    expected=old.replace('            best=rows[0] if rows else None',"            # Decision reference scans all rows; the user-facing diagnostic\n            # describes the same indexed retrieval view in either mode.\n            diagnostic_rows=index.similarities(query,visual) if reference else rows\n            best=diagnostic_rows[0] if diagnostic_rows else None")
    expected=expected.replace("candidate_ids=tuple(r['document_id'] for r in rows[:25]))","candidate_ids=tuple(r['document_id'] for r in diagnostic_rows[:25]))")
    assert (ROOT/'src/fingerprint_match_v2.py').read_bytes()==expected.encode(),'Unexpected runtime edit'
    files=sorted([*ROOT.glob('src/**/*.py'),*ROOT.glob('data/recognition_profiles/*.json'),ROOT/'app.py',ROOT/'run.py',ROOT/'data/recognition_features.json']);parts=[]
    for p in files:
        name=p.relative_to(ROOT).as_posix();raw=p.read_bytes()
        if name=='src/fingerprint_match_v2.py':raw=old.encode()
        elif p!=PATH:assert raw==original(name),name
        parts.extend([name.encode(),b'\0',raw,b'\0'])
    reconstructed=hashlib.sha256(b''.join(parts)).hexdigest();assert reconstructed==cal['runtime_sha256']
    assert hashlib.sha256(PATH.read_bytes()).hexdigest()==cal['profile_sha256']
    log=(ROOT/'reports/round7-full-tests.log').read_bytes();text=log.decode('utf8',errors='replace')
    m=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',text)
    assert m and int(m[1])>=690 and not re.search(r'\b[1-9]\d* failed\b',text)
    tests=dict(passed=int(m[1]),failed=0,skipped=int(m[2]),seconds=float(m[3]),log_sha256=hashlib.sha256(log).hexdigest())
    value=dict(original_calibration_sha256=hashlib.sha256((ROOT/out/'decision_calibration.json').read_bytes()).hexdigest(),original_runtime_sha256=cal['runtime_sha256'],reconstructed_original_runtime_sha256=reconstructed,runtime_sha256=runtime_hash(),profile_sha256=cal['profile_sha256'],fingerprint_sha256=revision(),production_branch_changed=False,full_tests=tests,source_change='Only diagnostic retrieval view for reference=True normalized to the indexed view. With reference=False the same rows, candidates and reason are used. No thresholds, scores, acceptance, entity/version constraints or input bytes changed.',proof='Exact source replacement verified and every other runtime byte matched calibration commit/profile; complete public-catalog/corpus differential tests compare all result fields including reasons.',original_matcher_sha256=hashlib.sha256(old.encode()).hexdigest(),current_matcher_sha256=hashlib.sha256(expected.encode()).hexdigest())
    destination=ROOT/out/'decision_calibration_reference_fix.json'
    assert not destination.exists(),'Append-only proof already exists'
    write(out+'decision_calibration_reference_fix.json',value);print('Reference diagnostic equivalence proof appended; original calibration/profile unchanged')

if __name__=='__main__':main()
