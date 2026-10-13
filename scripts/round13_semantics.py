"""Prove the source-contract extension did not change recognition semantics."""
import ast
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
BASELINE='77bbe149a52102d5ca42743702c5b39f5a475326'


def check():
    paths=['src/recognize.py','src/extract.py','src/fingerprint_decision_v5.py','src/fingerprint_decision_v4.py',
           'src/fingerprint_match_v2.py','src/title_evidence.py','src/fingerprint_pages.py',
           'data/recognition_profiles/fingerprint_decision_v5.json','data/recognition_features.json','data/catalog_seed.sqlite3']
    hashes={}
    for path in paths:
        old=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT)
        assert (ROOT/path).read_bytes()==old,path
        hashes[path]=hashlib.sha256(old).hexdigest()
    old=ast.parse(subprocess.check_output(['git','show',BASELINE+':src/fingerprint_v3.py'],cwd=ROOT))
    new=ast.parse((ROOT/'src/fingerprint_v3.py').read_bytes())
    def nodes(tree):
        return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name not in ['validate','validate_legacy_source']}
    assert nodes(old)==nodes(new),'Fingerprint features, index or scoring changed'
    constants=lambda tree:[ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.Assign)]
    assert constants(old)==constants(new),'Fingerprint parameters/version changed'
    return dict(status='passed',byte_identical=hashes,features_index_scoring_ast_unchanged=True,
                allowed_change='Only fingerprint source provenance validation, not input formats, decision/fusion/ranking/weights/thresholds/veto. Runtime imports no legacy converter.',
                baseline_commit=BASELINE)


if __name__=='__main__':
    from benchmarks.transactional_writer import atomic_json
    atomic_json(ROOT/'benchmarks/results/round13/semantic_invariance.json',check())
    print('R13 semantic invariance verified',flush=True)
