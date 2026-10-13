"""Add Round14/15 exposure to the immutable v1 contamination registry."""
import copy,re
from scripts.round15_common import *

def main():
    old=read('benchmarks/reference/benchmark_contamination_registry_v1.json');v=copy.deepcopy(old)
    known={r['document_id']:r for r in v['known_identities']};unknown={r['sha256']:r for r in v['unknown_resources']};observed=set(v['observed_resource_sha256'])
    paths=[*sorted((ROOT/'benchmarks/results/round14').glob('*.json')),*sorted(OUT.glob('*.json')),ROOT/'benchmarks/manifests/official_unknown_release_v2.json',ROOT/'benchmarks/manifests/input_safety_v1.json',ROOT/'tests/fixtures/round15_confirmed_false_accept.json']
    # No future evaluation selection or prediction can be folded back into this seal.
    finalization={'freeze_manifest.json','baseline_audit.json','pre_freeze_gate.json','evidence_locks.json','historical_locks.json','prepackage_audit.json','final_checks.json','tests.json','baseline_tests.json','freeze_not_created.json','evaluation_not_run.json','summary_ui.json','initial_validation_failure.json','scope_validation_environment.json'}
    paths=[p for p in paths if p.name not in finalization and not p.name.startswith(('unknown_v3','unknown_release_v3','evaluation_v5'))]
    for p in paths:
        if not p.exists():continue
        rel=p.relative_to(ROOT).as_posix();value=read(p);v['input_sha256'][rel]=sha(p)
        canonical='canonical' in p.name or 'catalog_coverage' in p.name
        diagnostic=not canonical and any(s in p.name for s in ['development','historical','verification','performance','false_accept'])
        def mark(did):
            if type(did) is int and did in known and diagnostic:
                r=known[did];r['tuning']=True;r['prior_evaluation_seen']=True
                for flag in ['tuning','prior_evaluation_seen']:
                    r['evidence'][flag]=sorted(set(r['evidence'].get(flag,[])+[rel]))
                r['contamination_reason']=sorted(set(r['contamination_reason']+['tuning','prior_evaluation_seen']));r['eligible_v5']=False
        def walk(node):
            if isinstance(node,list):
                for child in node:walk(child)
            elif isinstance(node,dict):
                expectation=node.get('expected',{});prediction=node.get('observed',{});provenance=node.get('provenance',{})
                if not isinstance(expectation,dict):expectation={}
                if not isinstance(prediction,dict):prediction={}
                if not isinstance(provenance,dict):provenance={}
                mark(expectation.get('document_id',provenance.get('document_id')))
                if prediction:mark(prediction.get('document_id'))
                h=node.get('input_sha256',node.get('SHA256',node.get('sha256',node.get('official_sha256'))))
                # A nested listing receipt or a result-file digest is not an
                # input prediction. Require a case/resource identifier here.
                if ('id' in node or 'case_id' in node) and isinstance(h,str) and re.fullmatch('[a-f0-9]{64}',h):
                    release='official_unknown_release_v2.json' in rel or '/round14/unknown_release' in rel
                    isunknown=release or expectation.get('match_type')=='NO_MATCH' or 'unknown' in p.name or 'input_safety' in p.name or 'confirmed_false_accept' in p.name
                    if prediction or release or 'input_safety' in p.name or 'confirmed_false_accept' in p.name:observed.add(h)
                    if isunknown:
                        r=unknown.setdefault(h,dict(sha256=h,case_ids=[],unknown_resource=True,unknown_development=False,release_v1=False,prediction_observed=False,used_bugfix=False,evidence=[]))
                        r['evidence']=sorted(set(r['evidence']+[rel]));ident=node.get('id',node.get('case_id'))
                        if ident:r['case_ids']=sorted(set(r['case_ids']+[str(ident)]))
                        r['release_v2']=r.get('release_v2',False) or release;r['prediction_observed']|=bool(prediction or release)
                        r['unknown_development']|='/round15/' in rel and diagnostic;r['used_bugfix']|='confirmed_false_accept' in p.name
                        if r['release_v2']:r['classification']='historical_unknown_release_v2_round14'
                for child in node.values():walk(child)
        walk(value)
    # The official critical resource has a receipt-backed SHA even if a diagnosis
    # stores only its case id; explicitly bind these to adjudication evidence.
    for c in read('benchmarks/reference/round15_truth_adjudication.json')['cases']:
        h=c['official_evidence']['download_receipt']['sha256'];observed.add(h)
        unknown[h]['round15_diagnostic']=True;unknown[h]['unknown_development']=True
    release_shas={c['SHA256'] for c in read('benchmarks/manifests/official_unknown_release_v2.json')['cases']}
    assert {h for h,r in unknown.items() if r.get('release_v2')}==release_shas
    assert release_shas<=observed and set(old['observed_resource_sha256'])<=observed
    v.update(schema_version=2,registry_id='benchmark-contamination-registry-v2',baseline_commit=BASE,created_at=now(),parent_registry_sha256=sha('benchmarks/reference/benchmark_contamination_registry_v1.json'),
        known_identities=[known[k] for k in sorted(known)],unknown_resources=[unknown[k] for k in sorted(unknown)],observed_resource_sha256=sorted(observed),
        policy='Immutable v1 union plus all Round14 release-v2 resources and Round15 pre-freeze diagnostic inputs. Known historical calibration/tuning/evaluation identities excluded. Canonical-only verification does not tune representation selection. Unknown freshness requires both SHA exclusion and a separate semantic/technical near-resource audit. No future release predictions may be inserted retroactively into this frozen registry.')
    v['counts'].update(known_contaminated=sum(bool(r['contamination_reason']) for r in known.values()),known_eligible=sum(r['eligible_v5'] for r in known.values()),unknown_resources=len(unknown),unknown_previously_seen=sum(r['prediction_observed'] for r in unknown.values()),unknown_release_v2=sum(r.get('release_v2',False) for r in unknown.values()),all_previously_observed_resource_shas=len(observed))
    atomic_json(ROOT/REGISTRY,v);print('Round15 registry',v['counts'],flush=True)

if __name__=='__main__':main()
