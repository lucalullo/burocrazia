"""Public snapshot using an independent temporary index, never a commit."""
import os
from scripts.round22_common import *

def main():
    boundary();assert head()==BASE;before=sha('.git/index');assert before==read(OUT/'baseline_audit.json')['original_index_sha256']
    names=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    original={p for p in read(OUT/'baseline_audit.json')['protected_sha256']}
    allowed=('benchmarks/results/round22/','benchmarks/round22_','benchmarks/reference/filled_generation_policy_v2.json','docs/ROUND22_','docs/CONTINUITA_OPERATIVA.md','scripts/round22_','tests/test_round22_','README_CANDIDATE_','CHANGELOG_CANDIDATE.md')
    assert all(p in original or p.startswith(allowed) for p in names),[p for p in names if p not in original and not p.startswith(allowed)]
    temp=ROOT/'tmp-build'/('round22-index-'+datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f'));assert not temp.exists();temp.parent.mkdir(exist_ok=True)
    env=dict(os.environ,GIT_INDEX_FILE=str(temp))
    subprocess.run(['git','read-tree','HEAD'],cwd=ROOT,env=env,check=True)
    subprocess.run(['git','add','--all','--','.'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    value=subprocess.check_output(['git','write-tree'],cwd=ROOT,env=env,text=True).strip();assert sha('.git/index')==before and head()==BASE
    atomic_json(ROOT/'.codex-context'/('TREE-'+value+'.json'),dict(round=22,tree=value,head=BASE,original_index_sha256=before,created_at=now(),temporary_index=temp.relative_to(ROOT).as_posix(),new_commit_created=False))
    print(value,flush=True)

if __name__=='__main__':main()
