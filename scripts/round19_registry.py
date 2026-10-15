"""Granular exposure audit: no recognition, no network, no source holdout."""
import copy,csv,sqlite3
from collections import Counter,defaultdict
from rapidfuzz.fuzz import ratio
from scripts.round19_common import *
from benchmarks.round3_audit import catalog
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding
from src.recognize import normalize_text

def expected_ids(value):
    if isinstance(value,list):
        return set().union(*(expected_ids(c) for c in value)) if value else set()
    if not isinstance(value,dict):return set()
    e=value.get('expected',{});ids={e['document_id']} if isinstance(e,dict) and type(e.get('document_id')) is int else set()
    for c in value.values():ids.update(expected_ids(c))
    return ids

def main():
    sealed()
    if (ROOT/REGISTRY).exists():
        assert sys.argv[1:]==['--revise-cross-source-title']
        assert not (OUT/'evaluation_v5_plan.json').exists() and not (OUT/'evaluation_v5_started.json').exists()
        assert not (OUT/'eligibility_initial_diagnostics.json').exists()
        save('eligibility_initial_diagnostics',dict(registry_sha256=sha(REGISTRY),audit_sha256=sha(OUT/'v5_identity_eligibility_audit.csv'),
             preflight=read(OUT/'evaluation_v5_preflight.json'),diagnostics=read(OUT/'round18_pool_diagnostics.json'),
             correction='Generic cross-agency title similarity is not identity/template proof. Unioncamere616 vs ANAC611 share a generic title but different issuer/source and resource. Retain same-issuer near titles and actual resource/field/aggregate checks. No predictions or selection existed.'))
    assert (ROOT/'docs/ROUND19_CONTAMINATION_AUDIT.md').exists()
    docs,_=catalog();by={d.id:d for d in docs};records=read_bundle()['records']
    previous=read('benchmarks/reference/benchmark_contamination_registry_v3.json')
    v=copy.deepcopy(previous)
    # These actual calibration outputs informed runtime/profile development.
    paths=['benchmarks/results/round8/calibration_observations_v4.json',
           'benchmarks/results/round9/calibration_observations_v5.json',
           'benchmarks/results/round9/calibration_strict_veto_observations.json']
    tuning=defaultdict(list)
    for p in paths:
        for did in expected_ids(read(p)):tuning[did].append(p)
    from benchmarks.round8_calibrate import calibration_ids
    for did in calibration_ids():tuning[did].append('benchmarks/round8_calibrate.py:calibration_ids')
    seen_sources={r['source'] for r in previous['known_identities'] if r['development'] or r['calibration']}
    with sqlite3.connect(ROOT/'data/catalog_seed.sqlite3') as db:
        names={r[0]:r[1] for r in db.execute('SELECT id,nome_fonte FROM sources')}
    # Source-specific safety profiles are explicit product configuration;
    # retain correlation without extending tuning to unseen identities.
    profile=read('data/recognition_profiles/safety_v1.json')
    source_profiles=profile.get('sources',profile.get('profiles',{}))
    profile_text=json.dumps(source_profiles,ensure_ascii=False).casefold()
    from src.recognize import DISTINCT_ENTITY_NAMES,ENTITY_ALIASES
    explicit_entities=set(DISTINCT_ENTITY_NAMES)|set(ENTITY_ALIASES.values())
    def profile_flag(s):
        entities={d.ente for d in docs if d.source_id==s}
        return bool(s in seen_sources and any(e.casefold() in {x.casefold() for x in explicit_entities} for e in entities))
    verified={c['expected']['document_id'] for n in ['canonical','canonical_legacy'] for c in read('benchmarks/results/round18/'+n+'.json')['cases'] if c['correct']}
    regroup=defaultdict(list)
    for r in records:regroup[r['document_id']].append(r)
    for k in v['known_identities']:
        did=k['document_id'];legacy=copy.deepcopy(k)
        devpaths=[p for p in k['evidence'].get('development',[]) if 'legacy_' not in p and 'official_holdout' not in p]
        confirmed=bool(tuning[did] or k['calibration'] or devpaths)
        # A historical plan/evaluation alone never proves tuning. Legacy
        # qualification and original holdout exposure with unresolved feedback
        # history are not silently promoted to fresh identities.
        uncertain=bool(k['development'] and not confirmed)
        historical=bool(k['historical_holdout'] or k['prior_evaluation_seen'] or any(k['robustness_round'+str(i)] for i in range(5,9)))
        k.update(legacy_v3=legacy,identity_seen_in_tuning=confirmed,tuning_history_unresolved=uncertain,
                 historical_evaluation_seen=historical,historical_result_used_for_tuning=bool(tuning[did]),
                 evaluation_seen_but_not_used_for_tuning=historical and not confirmed and not uncertain,
                 source_seen=k['source'] in seen_sources,source_specific_rule_tuned=profile_flag(k['source']),
                 exact_identity_feature_built=did in regroup,
                 tuning_provenance=sorted(set(tuning[did]+k['evidence'].get('calibration',[])+devpaths)),
                 benchmark_provenance=copy.deepcopy(k['evidence']),
                 representations_seen=bool(historical or confirmed or uncertain),
                 representation_policy='All historical SHA and equivalent transformations excluded; canonical derivatives must be fresh. Canonical verification alone is not tuning.')
    known={k['document_id']:k for k in v['known_identities']}
    excluded={did for did,k in known.items() if k['identity_seen_in_tuning'] or k['tuning_history_unresolved']}
    old=[r for r in records if r['document_id'] in excluded];old_docs=[by[i] for i in excluded]
    oldsha={r['canonical_file_sha256'] for r in old};oldurls={u for r in old for u in [r['url'],r['final_url']]}
    fields=[set(r['field_set']) for r in old if len(r['field_set'])>=8];aggregates=[set(r['aggregate']) for r in old if len(r['aggregate'])>=24]
    def reason(r):
        d=by[r['document_id']];k=known[d.id]
        if k['identity_seen_in_tuning']:return 'identity_seen_in_tuning'
        if k['tuning_history_unresolved']:return 'tuning_history_unresolved'
        if d.stato_verifica in ['demo','rifiutato']:return 'not_operational'
        if d.id not in verified:return 'not_current_canonical_verified'
        if r['status']!='active' or r['catalog_binding_sha256']!=binding(d):return 'stale_or_unsupported_binding'
        if r['mime_type'] not in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:return 'unsupported_native_format'
        if r['canonical_file_sha256'] in oldsha:return 'tuned_identity_resource_sha_overlap'
        if r['url'] in oldurls or r['final_url'] in oldurls:return 'tuned_identity_url_overlap'
        title=normalize_text(d.titolo_ufficiale);code=normalize_text(d.codice or '')
        if any(d.ente==c.ente and ((code and code==normalize_text(c.codice or '')) or (d.versione==c.versione and (not code or not c.codice or code==normalize_text(c.codice)) and ratio(title,normalize_text(c.titolo_ufficiale))>=92)) for c in old_docs):return 'near_tuned_title_code_version'
        fs=set(r['field_set']);ag=set(r['aggregate'])
        if len(fs)>=8 and any(len(fs&s)/max(1,len(fs|s))>=.90 for s in fields):return 'near_tuned_field_template'
        if len(ag)>=24 and any(len(ag&s)/max(1,len(ag|s))>=.85 for s in aggregates):return 'near_tuned_aggregate_template'
        return ''
    audit=[];pool=[]
    for did,rs in sorted(regroup.items()):
        d=by[did];k=known[did];rr=sorted(rs,key=lambda r:(bool(reason(r)),r['canonical_file_sha256']))[0];why=reason(rr)
        row=dict(document_id=did,source_id=d.source_id,source_name=names[d.source_id],entity=d.ente,
                 operational=d.stato_verifica not in ['demo','rifiutato'],rejected=d.stato_verifica=='rifiutato',stale=rr['catalog_binding_sha256']!=binding(d),canonical_verified=did in verified,
                 fingerprint_supported=rr['status']=='active' and rr['catalog_binding_sha256']==binding(d),identity_seen_in_tuning=k['identity_seen_in_tuning'],representations_seen=k['representations_seen'],
                 historical_evaluation_seen=k['historical_evaluation_seen'],historical_result_used_for_tuning=k['historical_result_used_for_tuning'],source_seen=k['source_seen'],source_specific_rule_tuned=k['source_specific_rule_tuned'],eligible_v5=not why,exclusion_reason=why)
        audit.append(row);k.update(eligible_v5=not why,exclusion_reason=why)
        if not why:pool.append(dict(document_id=did,source_id=d.source_id,sha256=rr['canonical_file_sha256'],mime_type=rr['mime_type'],pages=len(rr['pages']),field_count=len(rr['field_set'])))
    with (OUT/'v5_identity_eligibility_audit.csv').open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(audit[0]),lineterminator='\n');writer.writeheader();writer.writerows(audit)
    ledger=read('benchmarks/results/round18/post_evaluation_exposures.json')
    def hashes(node):
        if isinstance(node,str):return {node} if len(node)==64 and all(c in '0123456789abcdef' for c in node) else set()
        if isinstance(node,list):return set().union(*(hashes(x) for x in node)) if node else set()
        if isinstance(node,dict):return hashes(list(node.values()))
        return set()
    v.update(schema_version=4,registry_id='benchmark-contamination-registry-v4-round19',parent_registry_sha256=sha('benchmarks/reference/benchmark_contamination_registry_v3.json'),created_at=now(),
             legacy_registry_preserved=True,legacy_policy=previous['policy'],policy='Round19 identity tuning excludes; historical evaluation alone and source exposure do not. Unresolved direct development history remains excluded. Exact canonical features are product data, not decision tuning.',
             observed_resource_sha256=sorted(set(previous['observed_resource_sha256'])|hashes(ledger)),post_evaluation_exposures=ledger,
             sources=[dict(source_id=s,source_name=names[s],source_seen=s in seen_sources,source_specific_rule_tuned=profile_flag(s)) for s in sorted(names)],
             audit_policy_sha256=sha('docs/ROUND19_CONTAMINATION_AUDIT.md'),audit_sha256=sha(OUT/'v5_identity_eligibility_audit.csv'))
    v['counts'].update(fingerprint_identities=len(audit),eligible_v5=len(pool),eligible_sources=len({r['source_id'] for r in pool}),identity_seen_in_tuning=sum(k['identity_seen_in_tuning'] for k in v['known_identities']),tuning_history_unresolved=sum(k['tuning_history_unresolved'] for k in v['known_identities']))
    atomic_json(ROOT/REGISTRY,v)
    atomic_json(ROOT/'benchmarks/reference/v5_source_counting_policy_v1.json',dict(schema_version=1,source_field='catalog.source_id = fingerprint.source_id',source_semantics='Existing provenance source ID; same semantics as historical known-document gate. No hostname/entity/page/subsection splitting.',minimum_sources=6,minimum_identities=30,sampling_max_concentration=.35,preferred_max_concentration=.30,seed=SEED,source_id_names=names,created_before_predictions=True))
    oldrows=list(csv.DictReader((ROOT/'benchmarks/results/round18/evaluation_v5_pool_audit.csv').open(encoding='utf8')))
    oldpool={int(r['document_id']):r for r in oldrows if r['eligible']=='True'}
    diagnostic=dict(round18_identities=len(oldpool),round18_records=sum(r['eligible']=='True' for r in oldrows),round18_source_counts=dict(Counter(r['source'] for r in oldpool.values())),round18_entity_counts=dict(Counter(by[i].ente for i in oldpool)),
         round18_exclusions_per_source={str(s):dict(Counter(r['exclusion'] for r in oldrows if int(r['source'])==s and r['eligible']!='True')) for s in sorted({int(r['source']) for r in oldrows})},
         supported_sources=[dict(source_id=s,source_name=names[s],identities=sum(r['source_id']==s for r in audit),eligible_v5=sum(r['source_id']==s for r in pool),exclusions=dict(Counter(r['exclusion_reason'] for r in audit if r['source_id']==s and not r['eligible_v5']))) for s in sorted({r['source_id'] for r in audit})],
         source_level_exclusion=False,legacy_overconservatism='Historical evaluation/plan flags were labelled tuning; no direct blanket source filter. V4 resolves this at identity level.',
         recovered_ids=[r['document_id'] for r in pool if r['document_id'] not in oldpool],pool=pool,unknown_v3_available=116,recognition_calls=0)
    save('round18_pool_diagnostics',diagnostic)
    counts=Counter(r['source_id'] for r in pool);pdf=sum(r['mime_type']=='application/pdf' for r in pool)
    capacity=dict(eligible_identities_total=len(pool),sources_total=len(counts),identities_per_source=dict(counts),max_source_concentration=max(counts.values())/len(pool) if pool else None,
                  representation_capacity=2*len(pool)+14*pdf+60,scan_capacity=14*pdf,fill_capacity=5*min(12,pdf),unknown_v3_available=116)
    requirements={k:dict(actual=a,minimum=m,passed=a>=m) for k,a,m in [('identities',len(pool),30),('sources',len(counts),6),('representations',capacity['representation_capacity'],400),('scans',capacity['scan_capacity'],200),('fills',capacity['fill_capacity'],50),('unknown',116,30)]}
    save('evaluation_v5_preflight',dict(**capacity,requirements=requirements,passed=all(x['passed'] for x in requirements.values()),capacity_basis='Available existing native resources; fill capacity theoretical until generation/reopening/field verification. Actual generated adequacy is a second mandatory barrier before predictions.',recognition_calls=0,registry_sha256=sha(REGISTRY),source_policy_sha256=sha('benchmarks/reference/v5_source_counting_policy_v1.json')))
    print('R19 identity audit',len(audit),'eligible',len(pool),'sources',dict(counts),'recovered',diagnostic['recovered_ids'],flush=True)

if __name__=='__main__':main()
