"""Audit every fixed-denominator residual and local legacy capability."""
import csv,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks.transactional_writer import atomic_json
from maintenance.resolve_resources import resource_kind,SOURCES,sniff
from maintenance.legacy_resolver import inspect_legacy
from src.fingerprint_v3 import read_bundle

def main():
    docs,_=catalog();bundle=read_bundle();active={r['document_id'] for r in bundle['records'] if r['status']=='active'}
    prior={int(r['document_id']):r for r in csv.DictReader((ROOT/'benchmarks/results/round6/missing_fingerprint_final.csv').open(encoding='utf8'))}
    fixed={c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases'] if c['expected_resource_type']=='file_backed_document'}
    assert len(fixed)==1158
    r8=read('benchmarks/results/round8/recovery_attempts.json');r9=read('benchmarks/results/round9/recovery_attempts.json');attempts=defaultdict(list);files=defaultdict(list)
    for r in r8['attempts']:attempts[r['document_id']].append(r)
    for r in read('benchmarks/manifests/official_fingerprint_cache_v5.json')['files']:files[r['document_id']].append(r)
    rejected=defaultdict(list)
    for r in read('benchmarks/results/round8/fingerprint_build.json')['additional_resources_rejected']:rejected[r['document_id']].append(r['reason'])
    rows=[];legacy=[]
    for d in docs:
        if d.stato_verifica in ['demo','rifiutato'] or d.id in active or d.id not in fixed:continue
        old=prior.get(d.id,{});new=[r for r in r9['attempts'] if r['document_id']==d.id];probes=[]
        shas={f['sha256'] for f in files[d.id]}|{a['sha256'] for a in attempts[d.id]+new if a.get('sha256')}
        for sha in sorted(shas):
            raw=(ROOT/'benchmarks/cache'/(sha+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
            p=inspect_legacy(raw)
            if p['format']!='not_legacy':probes.append(p);legacy.append(dict(document_id=d.id,sha256=sha,**p))
        reason=';'.join(sorted(set(rejected[d.id]))) or ';'.join(sorted({r.get('reason','') for r in new})) or old.get('reason','no_official_identity_evidence')
        rows.append(dict(document_id=d.id,source=SOURCES[d.source_id],current_reason=old.get('classification','catalog_only'),previous_attempts=len(attempts[d.id]),resolver='bounded official detail/wrapper/multipart/redirect/IRI resolver; local legacy capability probe',alternative_resource_known=bool(files[d.id]),action='recheck existing resource associations and official alternatives; preserve shared ambiguity',result='no newly unambiguous supported resource',fingerprint_status='shared_resource_only' if any(r['document_id']==d.id and r['status']=='shared' for r in bundle['records']) else 'not_fingerprinted',final_reason=reason,legacy_probe=json.dumps(probes)))
    assert len(rows)==1158-len(active),(len(rows),len(active))
    out=ROOT/'benchmarks/results/round9'
    with (out/'fingerprint_recovery_v2.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    atomic_json(out/'legacy_audit.json',dict(cases=legacy,local_converter_available=inspect_legacy(b'{\\rtf1 test}')['converter_available'],converted=0,scope='Capability checked locally. No safe local converter available in this environment; no software installed, no macro execution, no derived bytes committed. Unsupported formats not counted as fingerprints.'))
    atomic_json(out/'fingerprint_coverage.json',dict(operational=1212,file_backed=1158,fingerprinted=len(active),coverage_all=len(active)/1212,coverage_file_backed=len(active)/1158,recovered=len(active)-941,residual_audited=len(rows),network_requests=r9['network_requests'],resource_bindings=len(read_bundle()['records']),unambiguous_resource_bindings=sum(r['status']=='active' for r in read_bundle()['records']),scope='Fixed denominator, shared resource recognition separated from unambiguous identity recognition. No catalog source or identity additions.'))
    print('Coverage',len(active),'/1158; residual',len(rows),'legacy',len(legacy))
if __name__=='__main__':main()
