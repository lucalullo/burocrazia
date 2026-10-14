"""Restore the single historical catalog-manifest physical representation.

Git historically serializes this JSON as LF, while frozen local receipts bind
its CRLF bytes. Both hashes were proved in Round 22. No content is changed.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def restore():
    path = 'data/catalog_manifest.json'
    proofs = json.loads((ROOT / 'benchmarks/results/round22/archive_serialization_audit.json').read_bytes())
    proof = next(c for c in proofs['differences'] if c['path'] == path)
    target = ROOT / path
    raw = target.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest == proof['workspace_sha256']:
        return False
    assert digest == proof['archive_sha256'] == proof['prior_Round21_archive_sha256']
    restored = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    assert hashlib.sha256(restored).hexdigest() == proof['workspace_sha256']
    target.write_bytes(restored)
    return True

if __name__ == '__main__':
    print('Historical catalog-manifest bytes restored:', restore())
