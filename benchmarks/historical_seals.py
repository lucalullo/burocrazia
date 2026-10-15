"""Historical freeze tests inspect the original Git tree after later tuning."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def verify_engine_at(commit,expected):
    if not (ROOT/'.git').exists():
        import pytest
        pytest.skip('Historical source Git tree required')
    for p,h in expected.items():
        raw=subprocess.check_output(['git','show',commit+':'+p],cwd=ROOT)
        if p=='data/catalog_manifest.json':
            physical=(ROOT/p).read_bytes()
            assert hashlib.sha256(physical).hexdigest()==h and physical.replace(b'\r\n',b'\n')==raw
        else:assert hashlib.sha256(raw).hexdigest()==h,p
    return True
