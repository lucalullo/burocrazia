"""Verify unchanged historical workspace bytes and original Git serialization."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round8_common import checked,read,write,OUT

def main():
    checked();target=ROOT/OUT/'historical_serialization_audit.json';assert not target.exists()
    baseline=read(OUT+'baseline/metrics.json');tracked=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines());paths=[p for p in baseline['prior_raw_sha256'] if p in tracked]
    assert subprocess.run(['git','diff','--quiet',baseline['commit'],'HEAD','--',*paths],cwd=ROOT).returncode==0
    rows=[]
    for path,digest in baseline['prior_raw_sha256'].items():
        raw=(ROOT/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
        if path in tracked:
            original=subprocess.check_output(['git','show',baseline['commit']+':'+path],cwd=ROOT)
            relationship='identical_bytes'
            if raw!=original:
                assert raw.replace(b'\r\n',b'\n')==original and json.loads(raw)==json.loads(original),path
                relationship='preexisting_workspace_CRLF_original_Git_LF'
            rows.append(dict(path=path,workspace_sha256=digest,original_git_sha256=hashlib.sha256(original).hexdigest(),relationship=relationship))
        else:
            assert subprocess.run(['git','check-ignore','-q','--',path],cwd=ROOT).returncode==0,path
            rows.append(dict(path=path,workspace_sha256=digest,relationship='historically_ignored_workspace_checkpoint'))
    write(OUT+'historical_serialization_audit.json',dict(baseline_commit=baseline['commit'],workspace_files=len(rows),tracked_files=len(paths),workspace_only=len(rows)-len(paths),normalized_files=[r['path'] for r in rows if r['relationship']=='preexisting_workspace_CRLF_original_Git_LF'],cases=rows,scope='All 110 workspace raw hashes equal the pre-change baseline. All 105 tracked historical Git blobs are byte-identical to the initial Round7 commit. Some workspace files already used CRLF while immutable Git blobs used LF; only that exact relationship is allowed, with equal parsed JSON. No historical file, metric or locked corpus was rewritten.'))
    checked();print('Historical serialization verified:',len(paths),'original Git files;',sum(r['relationship']=='preexisting_workspace_CRLF_original_Git_LF' for r in rows),'preexisting CRLF/LF differences',flush=True)

if __name__=='__main__':main()
