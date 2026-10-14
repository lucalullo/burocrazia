"""Additive tuning/representation exposure and prospective V6 feasibility."""
import copy,csv
from collections import Counter
from scripts.round20_common import *
from scripts.round19_registry import expected_ids
from benchmarks.round3_audit import catalog
from src.fingerprint_v3 import read_bundle
from src.recognize import normalize_text
from rapidfuzz.fuzz import ratio

def main(final=False):
    preserved();old='benchmarks/reference/benchmark_contamination_registry_v4.json' if not final else 'benchmarks/reference/benchmark_contamination_registry_v5.json'
    target='benchmarks/reference/benchmark_contamination_registry_v6.json' if final else 'benchmarks/reference/benchmark_contamination_registry_v5.json'
    assert not (ROOT/target).exists()
    v=copy.deepcopy(read(old));rows=read('benchmarks/results/round19/evaluation_v5_observations.json')['cases']
    v5ids={c['expected']['document_id'] for c in rows if not c['unknown']}
    calibration=set(read('benchmarks/results/round9/calibration_v5.json')['identity_ids'])|v5ids
    calibration|={c['observed']['document_id'] for c in rows if c['observed']['document_id'] is not None and not c['correct']}
    if (OUT/'development_inputs_manifest.json').exists():
        calibration|={c['expected']['document_id'] for c in read(OUT/'development_inputs_manifest.json')['cases'] if c['group']!='canonical' and (c.get('expected') or {}).get('document_id')}
    for p in OUT.glob('calibration_v6*.json'):calibration.update(read(p).get('identity_ids',[]))
    unknowns=[]
    for name in ['official_unknown_v1','official_unknown_v2','official_unknown_release_v1','official_unknown_release_v2','official_unknown_release_v3']:
        p='benchmarks/manifests/'+name+'.json'
        if (ROOT/p).exists():
            for c in read(p)['cases']:
                h=c.get('SHA256',c.get('sha256'))
                if h:unknowns.append(h)
    seen=set(v['observed_resource_sha256'])|set(unknowns)|{r['input_sha256'] for r in rows}
    for k in v['known_identities']:
        did=k['document_id'];k.setdefault('round19_eligible_v5',k['eligible_v5'])
        k.update(V5_seen=did in v5ids,round20_development_seen=did in calibration)
        if did in calibration:
            k.update(identity_seen_in_tuning=True,historical_result_used_for_tuning=True,eligible_v5=False)
            k['tuning_provenance']=sorted(set(k['tuning_provenance']+['benchmarks/results/round20/development_inputs_manifest.json' if final else 'benchmarks/results/round19/evaluation_v5_observations.json']))
        k['eligible_v6']=bool(k['round19_eligible_v5'] and not k['identity_seen_in_tuning'] and not k['tuning_history_unresolved'] and not k['V5_seen'])
    version=6 if final else 5
    v.update(schema_version=version,registry_id=f'benchmark-contamination-registry-v{version}-round20',parent_registry_sha256=sha(old),created_at=now(),observed_resource_sha256=sorted(seen),
         round20=dict(V5_identity_ids=sorted(v5ids),calibration_identity_ids=sorted(calibration),V5_representation_sha256=sorted({c['input_sha256'] for c in rows}),unknown_v1_v2_v3_sha256=sorted(set(unknowns)),
              future_V6_eligibility='V5 and all calibration/historical tuning identities excluded. Source seen/profile flags alone do not exclude. Fresh representation cannot rescue a tuned identity.',phase='post_calibration' if final else 'before_engine_changes'))
    v['counts'].update(round20_tuning_identities=len(calibration),V5_seen_identities=len(v5ids),unknown_v1_v2_v3_resources=len(set(unknowns)))
    if final:
        docs,_=catalog();by={d.id:d for d in docs};records=read_bundle()['records'];known={k['document_id']:k for k in v['known_identities']}
        contaminated={i for i,k in known.items() if k['identity_seen_in_tuning'] or k['tuning_history_unresolved']}
        oldrecords=[r for r in records if r['document_id'] in contaminated];old_docs=[by[i] for i in contaminated]
        oldsha={r['canonical_file_sha256'] for r in oldrecords};oldurl={u for r in oldrecords for u in [r['url'],r['final_url']]}
        fields=[set(r['field_set']) for r in oldrecords if len(r['field_set'])>=8];agg=[set(r['aggregate']) for r in oldrecords if len(r['aggregate'])>=24]
        oldaudit=list(csv.DictReader((ROOT/'benchmarks/results/round19/v5_identity_eligibility_audit.csv').open(encoding='utf8')));audit=[]
        for a in oldaudit:
            did=int(a['document_id']);d=by[did];k=known[did];reason=''
            if k['V5_seen']:reason='V5_identity_seen'
            elif did in calibration:reason='Round20_calibration_identity'
            elif a['eligible_v5']!='True':reason='historical_'+a['exclusion_reason']
            else:
                rs=[r for r in records if r['document_id']==did and r['status']=='active'];r=rs[0]
                title=normalize_text(d.titolo_ufficiale);code=normalize_text(d.codice or '')
                if r['canonical_file_sha256'] in oldsha or r['url'] in oldurl or r['final_url'] in oldurl:reason='tuned_resource_overlap'
                elif any(d.ente==c.ente and ((code and code==normalize_text(c.codice or '')) or (d.versione==c.versione and (not code or not c.codice or code==normalize_text(c.codice)) and ratio(title,normalize_text(c.titolo_ufficiale))>=92)) for c in old_docs):reason='near_tuned_identity_title_code_version'
                elif len(r['field_set'])>=8 and any(len(set(r['field_set'])&s)/max(1,len(set(r['field_set'])|s))>=.9 for s in fields):reason='near_tuned_field_template'
                elif len(r['aggregate'])>=24 and any(len(set(r['aggregate'])&s)/max(1,len(set(r['aggregate'])|s))>=.85 for s in agg):reason='near_tuned_aggregate'
            k['eligible_v6']=not reason;k['v6_exclusion_reason']=reason
            audit.append(dict(document_id=did,source=d.source_id,entity=d.ente,fingerprint_supported=a['fingerprint_supported'],canonical_verified=a['canonical_verified'],tuning_seen=k['identity_seen_in_tuning'],V5_seen=k['V5_seen'],development_seen=did in calibration,source_profile_tuned=k['source_specific_rule_tuned'],eligible_v6=not reason,exclusion_reason=reason))
        with (OUT/'v6_pool_audit.csv').open('w',encoding='utf8',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=list(audit[0]),lineterminator='\n');w.writeheader();w.writerows(audit)
        eligible=[a for a in audit if a['eligible_v6']];counts=Counter(a['source'] for a in eligible);pdf=sum(any(r['mime_type']=='application/pdf' and r['status']=='active' for r in records if r['document_id']==a['document_id']) for a in eligible)
        capacities=dict(identities=len(eligible),sources=len(counts),counts_per_source=dict(counts),max_concentration=max(counts.values())/len(eligible) if eligible else None,representation_capacity=2*len(eligible)+14*pdf+60,scan_capacity=14*pdf,fill_capacity=5*min(12,pdf),valid_filled_generated=0)
        save('v6_preflight',dict(**capacities,passed=len(eligible)>=30 and len(counts)>=6,exclusion_counts=dict(Counter(a['exclusion_reason'] for a in audit if not a['eligible_v6'])),capacity_status='Theoretical only; source gate failed before any fresh generation or predictions. No V6 identity selection.',source_semantics='Historical catalog source_id, unchanged',recognition_calls=0))
        v['counts'].update(eligible_v6=len(eligible),eligible_v6_sources=len(counts))
    atomic_json(ROOT/target,v)
    print('R20 registry',version,'V5IDs',len(v5ids),'calibrationIDs',len(calibration),'V6',v['counts'].get('eligible_v6'),v['counts'].get('eligible_v6_sources'),flush=True)

if __name__=='__main__':main('--final' in sys.argv)
