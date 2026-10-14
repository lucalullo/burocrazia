"""Identity-level source feasibility; canonical/candidate exposure is not tuning."""
import argparse,copy,csv,sqlite3
from collections import Counter,defaultdict
from scripts.round21_common import *
from scripts.round19_registry import expected_ids
from benchmarks.round3_audit import catalog
from src.fingerprint_v3 import read_bundle
from src.document_fingerprints import binding
from src.recognize import normalize_text
from rapidfuzz.fuzz import ratio

def audit():
    preserved();v=read('benchmarks/reference/benchmark_contamination_registry_v6.json');docs,_=catalog();by={d.id:d for d in docs};known={k['document_id']:k for k in v['known_identities']};records=read_bundle()['records'];regroup=defaultdict(list)
    for r in records:regroup[r['document_id']].append(r)
    verified={c['expected']['document_id'] for n in ['canonical','canonical_legacy'] for c in read('benchmarks/results/round19/'+n+'.json')['cases'] if c['correct']}
    legacy_paths=['benchmarks/results/round13/legacy_supported_observations.json','benchmarks/results/round13/legacy_adjudication_observations.json']
    legacy_inputs=set().union(*(expected_ids(read(p)) for p in legacy_paths))
    cal=set(v['round20']['calibration_identity_ids'])
    for p in OUT.glob('calibration_v7*.json'):cal.update(read(p).get('identity_ids',[]))
    for p in [*ROOT.glob('benchmarks/results/round20/development_observations_*.json'),*OUT.glob('development_observations_*.json')]:
        cal.update(c['observed']['document_id'] for c in read(p)['cases'] if c['group']!='canonical' and c['observed'].get('document_id'))
    def product_or_evaluation(p):return 'official_holdout' in p or 'official_legacy_fingerprints' in p or p in legacy_paths
    resolved={i for i,k in known.items() if k['tuning_history_unresolved'] and not k['identity_seen_in_tuning'] and not k['tuning_provenance'] and i not in legacy_inputs and all(product_or_evaluation(p) for p in k['benchmark_provenance'].get('development',[]))}
    # Keep actual legacy qualification inputs excluded conservatively; the
    # hundreds of other IDs were merely candidates in those 40 observations.
    tuned={i for i,k in known.items() if k['identity_seen_in_tuning']}|cal
    uncertain={i for i,k in known.items() if k['tuning_history_unresolved']} - resolved
    excluded=tuned|uncertain|legacy_inputs;old=[r for r in records if r['document_id'] in excluded];old_docs=[by[i] for i in excluded]
    oldsha={r['canonical_file_sha256'] for r in old};oldurl={u for r in old for u in [r['url'],r['final_url']]}
    fields=[set(r['field_set']) for r in old if len(r['field_set'])>=8];aggs=[set(r['aggregate']) for r in old if len(r['aggregate'])>=24]
    rows=[];pool=[]
    for did,rs in sorted(regroup.items()):
        d=by[did];k=known[did];native=[r for r in rs if r['status']=='active' and r['mime_type'] in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'] and r['catalog_binding_sha256']==binding(d)];r=native[0] if native else rs[0];why=''
        if k.get('V5_seen'):why='V5_identity_seen'
        elif did in cal:why='Round20_21_development_identity'
        elif did in tuned:why='historical_tuning_identity'
        elif did in legacy_inputs:why='canonical_qualification_conservative_guard_not_claimed_tuning'
        elif did in uncertain:why='unresolved_direct_tuning_history'
        elif d.stato_verifica in ['demo','rifiutato'] or not native:why='unsupported_or_stale_or_nonoperational'
        elif did not in verified:why='canonical_not_verified'
        elif r['canonical_file_sha256'] in oldsha or r['url'] in oldurl or r['final_url'] in oldurl:why='actual_resource_overlap'
        elif any(d.ente==x.ente and ((d.codice and normalize_text(d.codice)==normalize_text(x.codice or '')) or (d.versione==x.versione and ratio(normalize_text(d.titolo_ufficiale),normalize_text(x.titolo_ufficiale))>=92)) for x in old_docs):why='same_issuer_near_identity'
        elif len(r['field_set'])>=8 and any(len(set(r['field_set'])&s)/max(1,len(set(r['field_set'])|s))>=.9 for s in fields):why='near_tuned_field_template'
        elif len(r['aggregate'])>=24 and any(len(set(r['aggregate'])&s)/max(1,len(set(r['aggregate'])|s))>=.85 for s in aggs):why='near_tuned_aggregate'
        row=dict(document_id=did,source_id=d.source_id,fingerprint_supported=bool(native),canonical_verified=did in verified,prior_tuning_seen=did in tuned,tuning_history_unresolved=did in uncertain,canonical_qualification_guard=did in legacy_inputs,V5_seen=k.get('V5_seen',False),round20_dev_seen=did in cal,prior_eval_seen=k['historical_evaluation_seen'],source_profile_tuned=k['source_specific_rule_tuned'],old_uncertainty_resolved=did in resolved,eligible_v6=not why,exclusion_reason=why)
        rows.append(row)
        if not why:pool.append(dict(document_id=did,source_id=d.source_id,canonical_sha=r['canonical_file_sha256'],fingerprint_supported=True,prior_tuning_seen=False,prior_eval_seen=k['historical_evaluation_seen'],reserved_for_v6=False,reservation_reason='Metadata-only prospect; final reservation only after development/canonical/performance checks. Historical canonical/candidate/evaluation exposure is not identity tuning.',mime_type=r['mime_type'],pages=len(r['pages']),field_count=len(r['field_set'])))
    with sqlite3.connect(ROOT/'data/catalog_seed.sqlite3') as db:names=dict(db.execute('SELECT id,nome_fonte FROM sources'))
    sources=[]
    for s in sorted(names):
        relevant=[r for r in rows if r['source_id']==s];fresh=[r for r in pool if r['source_id']==s]
        sources.append(dict(source_id=s,source_name=names[s],total_identities=sum(d.source_id==s and d.stato_verifica not in ['demo','rifiutato'] for d in docs),fingerprinted_identities=len(relevant),tuning_contaminated_identities=sum(r['prior_tuning_seen'] for r in relevant),V5_seen_identities=sum(r['V5_seen'] for r in relevant),round20_dev_seen_identities=sum(r['round20_dev_seen'] for r in relevant),fresh_eligible_identities=len(fresh),source_profile_tuned=any(r['source_profile_tuned'] for r in relevant),eligible_for_v6_diversity=bool(fresh),exclusion_reason='' if fresh else json.dumps(dict(Counter(r['exclusion_reason'] for r in relevant)),sort_keys=True) if relevant else 'No supported canonical fingerprint; official resources would require separate identity/provenance qualification.'))
    for name,values in [('v6_source_eligibility',sources),('v6_identity_eligibility',rows)]:
        with (OUT/(name+'.csv')).open('w',encoding='utf8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(values[0]),lineterminator='\n');w.writeheader();w.writerows(values)
    counts=Counter(c['source_id'] for c in pool);pdf=sum(c['mime_type']=='application/pdf' for c in pool)
    save('v6_pool_prospects',dict(cases=pool,counts_per_source=dict(counts),recognition_calls=0,transform_calls=0,resolved_candidate_only_or_evaluation_ids=sorted(resolved),legacy_actual_inputs_excluded=sorted(legacy_inputs),proof_sha256={p:sha(p) for p in legacy_paths},parent_registry_sha256=sha('benchmarks/reference/benchmark_contamination_registry_v6.json'),scope='No reservation or selection yet. All actual calibration/V5 identities stay excluded. No source-level exclusion.'))
    requirements={k:dict(actual=a,minimum=m,passed=a>=m) for k,a,m in [('identities',len(pool),30),('sources',len(counts),6),('representations',2*len(pool)+14*pdf+60,400),('scans',14*pdf,200),('fills',5*min(12,pdf),50)]}
    save('v6_preflight',dict(identities=len(pool),sources=len(counts),counts_per_source=dict(counts),representation_capacity=2*len(pool)+14*pdf+60,scan_capacity=14*pdf,filled_capacity=5*min(12,pdf),max_concentration=max(counts.values())/len(pool) if pool else None,requirements=requirements,passed=all(r['passed'] for r in requirements.values()),valid_filled_generated=0,recognition_calls=0,transform_calls=0,capacity_only=True,reserved_manifest_created=False))
    table='\n'.join(f"| {s['source_id']} | {s['source_name']} | {s['fingerprinted_identities']} | {s['fresh_eligible_identities']} | {s['exclusion_reason']} |" for s in sources)
    (ROOT/'docs/ROUND21_V6_SOURCE_AUDIT.md').write_text(f'''# Round 21 — audit fonti V6

Audit di tutte le19 fonti catalogate e1.019 identità con fingerprint, senza predizioni o trasformazioni. Il pool passa da316/4 del Round20 a **{len(pool)}/{len(counts)}**, conteggi `{dict(counts)}`. Fonte è sempre il source_id storico: nessuna divisione artificiale.

La precedente incertezza includeva centinaia di ID presenti come candidati nei diagnostici legacy Round13: ciascuno dei due file contiene soltanto40 identità input effettive. L'audit distingue questi input, che restano esclusi conservativamente, dai candidati del catalogo. La restante esposizione a holdout storico/costruzione canonica non dimostra tuning secondo la regola esplicita Round21. Nessuna identità con identity_seen_in_tuning, provenienza diretta di calibrazione, V5 o development Round20/21 viene recuperata. V6 deve comunque usare rappresentazioni/seed/SHA nuovi. Tutti i flag e registry precedenti restano immutati; gli ID riclassificati e i file di prova/hash sono in v6_pool_prospects.json.

Controlli aggiuntivi preservati: binding, formato, canonical verificato, risorsa/URL effettivamente condivisi, titolo/codice/versione dello stesso emittente, campi e aggregate vicini a identità contaminate. Un profilo di fonte e la costruzione di una fingerprint non contaminano automaticamente tutte le sue identità. Le fonti senza risorse qualificate restano escluse con ragione esplicita; non serve costruire nuove fingerprint se il gate viene già dimostrato con quelle esistenti.

| Fonte | Nome | Fingerprint ID | Fresh ID | Motivo esclusione |
| --- | --- | --- | --- | --- |
{table}

Capacità teoriche: `{requirements}`. Non si rivendicano compilati validi prima della generazione. La prenotazione finale sarà fissata dopo il tuning, prima del freeze; nessuna trasformazione/predizione sulle identità riservate prima del freeze. Le verifiche canoniche del prodotto avvengono prima della prenotazione e non guidano soglie sulle future identità.
''',encoding='utf8',newline='\n')
    print('R21 source audit',len(pool),'identities',dict(counts),'resolved',len(resolved),flush=True)
if __name__=='__main__':audit()
