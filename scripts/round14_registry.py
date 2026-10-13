"""Conservative, evidence-linked exposure registry; never run recognition."""
from collections import Counter
import re,subprocess
from scripts.round14_common import *
from benchmarks.round3_audit import catalog
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding

FLAGS=['calibration','development','robustness_round5','robustness_round6','robustness_round7','robustness_round8','filled','scan','historical_holdout','tuning','prior_evaluation_seen','canonical_verification']

def main():
    assert_baseline_engine();docs,families=catalog();by={d.id:d for d in docs}
    known={d.id:dict(document_id=d.id,source=d.source_id,entity=d.ente,**{k:False for k in FLAGS},evidence={}) for d in docs}
    unknown={};family={str(f.id):dict(family_id=f.id,development=False,historical_held_out=False,negative=False,evidence=[]) for f in families}
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'benchmarks/results','benchmarks/manifests','benchmarks/corpora','tests/fixtures'],cwd=ROOT,text=True).splitlines()
    paths=[p for p in paths if p.endswith('.json')]
    inputs={};manifest_cases={}
    for p in paths:
        if '/manifests/' not in p:continue
        value=read(p)
        for c in value.get('cases',[]):
            if isinstance(c,dict):
                ident=c.get('case_id',c.get('id'));h=c.get('SHA256',c.get('sha256'))
                if ident and isinstance(h,str) and re.fullmatch('[a-f0-9]{64}',h):manifest_cases.setdefault(str(ident),set()).add(h)
    def mark(did,flags,p):
        if type(did) is not int or did not in known:return
        for flag in flags:
            known[did][flag]=True;known[did]['evidence'].setdefault(flag,set()).add(p)
    def resource(h,c,p,flags,observed):
        if not isinstance(h,str) or not re.fullmatch('[a-f0-9]{64}',h):return
        r=unknown.setdefault(h,dict(sha256=h,case_ids=set(),unknown_resource=False,unknown_development=False,release_v1=False,prediction_observed=False,used_bugfix=False,evidence=set()))
        expectation=c.get('expected',{})
        r['unknown_resource']|=('unknown' in p or isinstance(expectation,dict) and expectation.get('match_type')=='NO_MATCH' or c.get('expected_match_type')=='NO_MATCH')
        if c.get('id',c.get('case_id')):r['case_ids'].add(str(c.get('id',c.get('case_id'))))
        r['evidence'].add(p);r['prediction_observed']|=observed
        r['unknown_development']|=('unknown' in p and bool({'development','calibration','tuning'}&set(flags)))
        r['release_v1']|=('official_unknown_release_v1.json' in p or '/round13/unknown_release' in p)
        r['used_bugfix']|=observed and ('calibr' in p or 'before_final_refinement' in p or 'strict_veto' in p)
    for p in paths:
        value=read(p);inputs[p]=sha(p);low=p.lower();rmatch=re.search(r'/round([5-8])/',low)
        canonical=('canonical' in low or 'catalog_coverage' in low)
        flags=set()
        if 'calibr' in low:flags|={'calibration','tuning'}
        if 'develop' in low or 'regression' in low or 'benchmark_v2' in low or 'hard_negative' in low:flags|={'development','tuning'}
        if 'holdout' in low or 'release_locked' in low:flags.add('historical_holdout')
        if 'filled' in low:flags.add('filled')
        if 'scan' in low:flags.add('scan')
        if rmatch and ('robustness' in low or 'filled' in low or 'scan' in low):flags.add('robustness_round'+rmatch[1])
        if any(t in low for t in ['robustness','evaluation_checkpoint','evaluation_started','evaluation_plan']):flags|={'prior_evaluation_seen','tuning'}
        if '/round13/legacy_' in low or '/round13/ambiguity_' in low:flags|={'development','tuning'}
        if canonical:flags={'canonical_verification'}
        def walk(node):
            if isinstance(node,list):
                for child in node:walk(child)
            elif isinstance(node,dict):
                for key,child in node.items():
                    if key in ['calibration_identities','development_identities','evaluation_identities','canonical_document_ids'] and isinstance(child,list):
                        direct={'calibration','tuning'} if key.startswith('calibration') else {'development','tuning'} if key.startswith('development') else {'prior_evaluation_seen','tuning'}
                        for did in child:mark(did,direct|flags,p)
                expected=node.get('expected',{});provenance=node.get('provenance',{})
                if not isinstance(expected,dict):expected={}
                if not isinstance(provenance,dict):provenance={}
                observed=isinstance(node.get('observed'),dict)
                case=isinstance(expected,dict) and bool(expected) or isinstance(provenance,dict) and bool(provenance) and 'id' in node
                if case:
                    did=expected.get('document_id',provenance.get('document_id',node.get('document_id')))
                    mark(did,flags,p)
                    if observed and not canonical and ('calibr' in low or 'develop' in low or 'holdout' in low):mark(node['observed'].get('document_id'),{'tuning'},p)
                    for state in [expected,node['observed'] if observed else {}]:
                        fid=str(state.get('family_id',''))
                        if fid in family:
                            f=family[fid];f['development']|=('development' in flags or 'calibration' in flags)
                            f['historical_held_out']|=('historical_holdout' in flags or 'family_release' in low)
                            f['negative']|=expected.get('match_type')=='NO_MATCH';f['evidence'].append(p)
                    h=node.get('input_sha256',node.get('SHA256',node.get('sha256',provenance.get('sha256',provenance.get('canonical_sha256')))))
                    resource(h,node,p,flags,observed)
                    for h in manifest_cases.get(str(node.get('id',node.get('case_id',''))).removeprefix('UNKNOWN-'),set()):resource(h,node,p,flags,observed)
                # Direct official manifest entries, including unobserved resources.
                if 'SHA256' in node or 'sha256' in node and ('case_id' in node or 'id' in node):
                    resource(node.get('SHA256',node.get('sha256')),node,p,flags,observed or node.get('historically_seen') is True)
                    if node.get('document_id') is not None and 'official_' in low:mark(node['document_id'],{'development','tuning','historical_holdout'},p)
                if 'document_id' in node and any(t in low for t in ['filled_generation','legacy_fingerprint','legacy_supported','legacy_adjudication']):mark(node['document_id'],flags|{'development','tuning'},p)
                for child in node.values():walk(child)
        walk(value)
    bundle=read_bundle();active={r['document_id']:r for r in bundle['records'] if r['status']=='active'}
    for did,row in known.items():
        d=by[did];r=active.get(did);supported=bool(r and r['catalog_binding_sha256']==binding(d))
        row['fingerprint_supported']=supported;row['operational']=d.stato_verifica not in ['demo','rifiutato']
        contaminated=any(row[k] for k in FLAGS if k!='canonical_verification')
        row['contamination_reason']=[k for k in FLAGS if row[k] and k!='canonical_verification']
        row['eligible_v5']=row['operational'] and supported and not contaminated
        row['evidence']={k:sorted(v) for k,v in row['evidence'].items()}
    for row in unknown.values():
        for k in ['case_ids','evidence']:row[k]=sorted(row[k])
        if row['release_v1']:row['classification']='historical_pre_unioncamere_fix'
    for row in family.values():row['evidence']=sorted(set(row['evidence']))
    observed_shas=sorted(k for k,r in unknown.items() if r['prediction_observed'])
    unknown={k:r for k,r in unknown.items() if r['unknown_resource']}
    counts=dict(known_total=len(known),known_contaminated=sum(bool(r['contamination_reason']) for r in known.values()),known_eligible=sum(r['eligible_v5'] for r in known.values()),
                unknown_resources=len(unknown),unknown_previously_seen=sum(r['prediction_observed'] for r in unknown.values()),unknown_release_v1=sum(r['release_v1'] for r in unknown.values()),
                all_previously_observed_resource_shas=len(observed_shas),families=len(family))
    atomic_json(ROOT/REGISTRY,dict(schema_version=1,registry_id='benchmark-contamination-registry-v1',baseline_commit=BASE,created_at=now(),
                policy='Conservative union of all pre-R14 calibration/development, observed historical robustness/filled/scans/holdouts, legacy qualification and explicit plan identities. Catalog-wide canonical SHA/smoke verification recorded separately: these checks neither tune transformations nor establish identity-disjoint evaluation. Any missing/uncertain tuning history excludes rather than promotes. Previously observed resource SHA cannot enter unknown v2.',
                known_identities=[known[k] for k in sorted(known)],unknown_resources=[unknown[k] for k in sorted(unknown)],observed_resource_sha256=observed_shas,family_identities=list(family.values()),
                input_sha256=inputs,counts=counts))
    print('R14 contamination registry',counts,flush=True)

if __name__=='__main__':main()
