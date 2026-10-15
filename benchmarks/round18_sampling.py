"""Prospective metadata-only unknown sampling; no recognition imports."""
import math,random
from collections import Counter,defaultdict,deque
from scripts.round18_common import *
from benchmarks.unknown_release import balance
from maintenance.policy import canonical_url,validate_url

SAMPLING='benchmarks/reference/unknown_release_sampling_policy_v1.json'
MANIFEST='benchmarks/manifests/official_unknown_release_v3.json'

def feasible_size(counts):
    return next((n for n in range(sum(counts.values()),99,-1) if sum(min(v,n//4) for v in counts.values())>=n and len(counts)>=8),None)

def sample(cases,seed):
    counts=Counter(c['source'] for c in cases);n=feasible_size(counts)
    if n is None:raise ValueError('Insufficient capped capacity or sources')
    grouped=defaultdict(list)
    for c in sorted(cases,key=lambda c:c['case_id']):grouped[c['source']].append(c)
    queues={}
    for source,rows in sorted(grouped.items()):
        rng=random.Random(int(hashlib.sha256(f'{seed}:{source}'.encode()).hexdigest(),16));strata=defaultdict(list)
        for c in rows:strata[(c['document_type'],c['entity'],bool(c['code']),bool(c['version']))].append(c)
        keys=sorted(strata);rng.shuffle(keys)
        for values in strata.values():rng.shuffle(values)
        ordered=[]
        while any(strata.values()):
            for k in keys:
                if strata[k]:ordered.append(strata[k].pop())
        queues[source]=deque(ordered)
    selected=[];used=Counter()
    while len(selected)<n:
        progress=False
        for source in sorted(queues):
            if queues[source] and used[source]<n//4:
                selected.append(queues[source].popleft());used[source]+=1;progress=True
                if len(selected)==n:break
        if not progress:raise ValueError('Capped round robin cannot fill planned subset')
    return sorted(selected,key=lambda c:c['case_id'])

def exposures(cases):
    registry=read(REGISTRY);seen=set(registry['observed_resource_sha256'])
    urls={canonical_url(u) for c in registry['unknown_resources'] if c.get('prediction_observed') or c.get('release_v1') or c.get('unknown_development') for u in [c.get('official_url'),c.get('url'),c.get('receipt',{}).get('final_url')] if u}
    return [c['case_id'] for c in cases if c['SHA256'] in seen or canonical_url(c['receipt']['final_url']) in urls or c['previously_seen'] or c['historically_seen']]

def main():
    invariant();assert not (ROOT/MANIFEST).exists()
    master=read('benchmarks/results/round17/unknown_v3_truth_audit.json')['confirmed_cases'];counts=Counter(c['source'] for c in master)
    contaminated=exposures(master);eligible=[c for c in master if c['case_id'] not in contaminated]
    assert not contaminated, 'Previously predicted cases must receive additive contamination audit before selection'
    for round in [16,17,18]:
        for name in ['unknown_v3_started.json','evaluation_v5_started.json']:assert not (ROOT/f'benchmarks/results/round{round}'/name).exists()
        for name in ['unknown-release-v3.sqlite','evaluation-v5/evaluation.sqlite']:assert not (ROOT/f'benchmarks/work/round{round}'/name).exists()
    save('unknown_master_pool',dict(cases=master,eligible_cases=eligible,contaminated_case_ids=contaminated,counts=balance(master),inherited_truth_audit_sha256=sha('benchmarks/results/round17/unknown_v3_truth_audit.json'),recognition_calls=0))
    size=feasible_size(counts);capacity=sum(min(n,25) for n in counts.values())
    save('unknown_subset_feasibility',dict(master_total=len(master),source_counts=dict(counts),max_source=max(counts,key=counts.get),max_source_count=max(counts.values()),capacity_at_100=capacity,available_sources=len(counts),subset_100_feasible=capacity>=100 and len(counts)>=8,largest_feasible_size=size,extra_acquisition_needed=0 if size else max(0,100-capacity),reason='Master may be imbalanced; capped subset capacity at100 is112 and maximal feasible N116 has cap29. No network acquisition.',capacities=[dict(n=n,max_per_source=n//4,capacity=sum(min(v,n//4) for v in counts.values())) for n in range(100,len(master)+1)]))
    assert size is not None, 'Acquisition branch requires a separate minimal-deficit plan'
    policy=dict(schema_version=1,policy_id='unknown-release-sampling-v1',seed=SEED,master_may_be_imbalanced=True,release_minimum=100,minimum_sources=8,max_source_fraction=.25,minimum_categories=5,
        size_rule='Largest N>=100 with sum(min(source_count,floor(N/4)))>=N and >=8 available sources.',
        order='Canonical case_id order; source capped round robin; within source secondary type/entity/coded/versioned strata interleaving. Python Random seeded by integer SHA256(global_seed:source), shuffling canonical strata keys/rows.',
        allowed_fields=['case_id','source','entity','document_type','code presence','version presence'],forbidden_fields=['score','prediction','candidate rank','perceived difficulty','fingerprint similarity'],
        independence='Truth/freshness qualification precedes sampling. No recognition result exists for master cases. All DOCUMENT/FAMILY acceptance counts as false acceptance. No post-prediction reselection.',created_at=now())
    assert not (ROOT/SAMPLING).exists();atomic_json(ROOT/SAMPLING,policy)
    chosen=sample(eligible,SEED);b=balance(chosen)
    marker=dict(passed=True,unknown_v3_prediction_calls=0,evaluation_v5_prediction_calls=0,contaminated_case_ids=contaminated,master_sha256=sha(OUT/'unknown_master_pool.json'),registry_sha256=sha(REGISTRY),sampling_code_sha256=sha('benchmarks/round18_sampling.py'),sampling_policy_sha256=sha(SAMPLING),selection_inputs=policy['allowed_fields'],score_or_prediction_used=False,verified_before_manifest_at=now())
    save('no_prediction_before_selection',marker)
    entries=[]
    for c in chosen:
        c=dict(c,truth_status='confirmed_unknown',contamination_status='fresh',category=c['document_type'],selection_stratum=dict(source=c['source'],entity=c['entity'],type=c['document_type'],coded=bool(c['code']),versioned=bool(c['version'])),selected_by_seed=SEED)
        validate_url(c['official_url'],c['source']);validate_url(c['receipt']['final_url'],c['source'])
        raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['SHA256'] and len(raw)<=20*1024*1024
        if c['mime']=='application/pdf':
            import pymupdf
            with pymupdf.open(stream=raw,filetype='pdf') as pdf:assert not pdf.needs_pass and 1<=len(pdf)<=100
        else:
            from src.extract import extract_document
            extract_document(raw,'official.docx')
        entries.append(c)
    assert len({c['SHA256'] for c in entries})==len(entries) and len({canonical_url(c['receipt']['final_url']) for c in entries})==len(entries)
    passed=b['total']>=100 and b['sources']>=8 and b['max_concentration']<=.25 and b['type_groups']>=5 and not exposures(entries)
    manifest=dict(schema_version=2,manifest_id='official-unknown-release-v3',selection_seed=SEED,cases=entries,created_at=now(),registry_sha256=sha(REGISTRY),truth_audit_sha256=sha(OUT/'unknown_master_pool.json'),sampling_policy_sha256=sha(SAMPLING),no_prediction_evidence_sha256=sha(OUT/'no_prediction_before_selection.json'),freeze_binding='Immutable manifest selected before dedicated Round18 freeze; freeze_manifest records its SHA256.')
    assert passed;atomic_json(ROOT/MANIFEST,manifest)
    save('unknown_release_v3_preflight',dict(**b,passed=passed,seed=SEED,input_supported_count=len(entries),all_confirmed=True,all_fresh=True,sha_duplicates=0,canonical_url_duplicates=0,v1_v2_overlap=0,diagnostic_overlap=0,manifest_sha256=sha(MANIFEST),sampling_policy_sha256=sha(SAMPLING),master_total=129,excluded_by_metadata_quota=len(master)-len(entries),recognition_calls=0,created_at=now()))
    (ROOT/'docs/UNKNOWN_RELEASE_SAMPLING_POLICY.md').write_text('''# Unknown release sampling policy v1

Il master contiene tutti gli unknown confermati, freschi e indipendenti, anche se sbilanciati. Solo il subset release deve rispettare N>=100,8 fonti,concentrazione<=25%,5 categorie. La qualifica di truth/freshness precede il sampling.

Seed20261014. Si cerca il più grande N sostenibile con cap floor(N/4); ordinamento iniziale per case_id, round-robin delle fonti e interleaving secondario tipo/ente/codificato/versionato. PRNG per fonte derivato da SHA256(seed:source), senza dipendenza dall'ordine dei file. Vietati score, predizioni, ranking, difficoltà o fingerprint similarity per la scelta. Il codice e la policy sono sigillati prima delle predizioni.

Master129, capacità per N100=112; massimo116 con cap29,13 fonti. Nessuna acquisizione aggiuntiva. I13 casi esclusi rimangono confirmed fresh nel master: esclusione per quota, nessuna reinterpretazione di truth o difficoltà. Il manifest è scritto prima del freeze, che ne registra l'hash; non contiene risultati di recognition. Il precedente preflight fallito Round17 è conservato. V3 single-shot sul freeze, nessuna riselezione/tuning dopo il primo risultato; v5 condizionale al PASS v3.
''',encoding='utf8',newline='\n')
    print('R18 release subset',b,'maximal',size,flush=True)

if __name__=='__main__':main()
