"""Baseline and source-based adjudication, completed before an engine edit."""
import argparse,subprocess
from collections import Counter
from scripts.round15_common import *
from scripts.round14_baseline import tests

def baseline():
    from scripts.round14_common import sealed as old_sealed
    f=old_sealed();assert head()==BASE
    locks=read('benchmarks/results/round14/evidence_locks.json')
    for p,h in locks['sha256'].items():assert sha(p)==h,p
    h=historical();t=tests('reports/round15-baseline-tests.log');save('baseline_tests',t)
    m=read('benchmarks/manifests/official_unknown_release_v2.json');u=read('benchmarks/results/round14/unknown_release_v2.json');obs=read('benchmarks/results/round14/unknown_release_v2_observations.json')
    accepted=[r for r in obs['cases'] if r['observed']['match_type']=='DOCUMENT_MATCH'];failed=[r for r in obs['cases'] if r['extraction_failed']]
    assert len(accepted)==3 and len(failed)==4 and u['correct_no_match']==107 and u['n']==114
    assert sha('benchmarks/manifests/official_unknown_release_v2.json')==u['manifest_sha256'] and sha('benchmarks/results/round14/unknown_release_v2_observations.json')==u['observations_sha256']
    first=subprocess.check_output(['git','log','--all','--format=%H %ad %s','--date=iso-strict','-S','MAX_PDF_PAGES','--','src/extract.py'],cwd=ROOT,text=True).strip()
    initial=first.split()[0];old=subprocess.check_output(['git','show',initial+':src/extract.py'],cwd=ROOT)
    assert b'MAX_PDF_PAGES = 100' in old
    subprocess.run(['git','merge-base','--is-ancestor',initial,f['freeze_git_commit']],cwd=ROOT,check=True)
    page=dict(limit_pages=100,first_commit_or_evidence=first,existed_before_round14_selection=True,
        runtime_behavior='ExtractionError before page extraction/OCR/recognition when page_count>100; readable error, no document result.',
        benchmark_contract_before_round14=dict(product_limit=True,documented_paths=['README.md','docs/ESTRAZIONE.md'],round14_classification_preflight_missing=True,round14_denominator_remains=114),
        conclusion='Preexisting product limit. Future unknown classification admits supported input only; separate input-safety benchmark covers unsupported limits. Historical107/114 is unchanged.',
        other_preexisting_limits=dict(upload_bytes=20*1024*1024,extracted_text_characters=1000000,docx_members=2000,docx_member_bytes=10*1024*1024,docx_total_bytes=50*1024*1024,docx_compression_ratio=200),
        round14_oversized_cases=read('benchmarks/results/round14/failure_audit.json')['extraction_errors'],audited_at=now())
    save('page_limit_audit',page)
    save('baseline_audit',dict(entry_branch='codex/coverage-benchmark-v0.7.0',entry_commit=BASE,entry_working_tree='clean',entry_modified=0,entry_untracked=0,
         software='0.6.1',schema=610,round14_freeze=f['freeze_git_commit'],round14_semantic_engine_unchanged=True,engine_files_sha256=engine_files(),
         historical_status='historical_unknown_release_v2_round14',manifest_sha256=u['manifest_sha256'],observations_sha256=u['observations_sha256'],result_sha256=sha('benchmarks/results/round14/unknown_release_v2.json'),
         historical_metrics={k:u[k] for k in ['n','correct_no_match','wrong_document_match','wrong_family_match','extraction_failed','rejection_rate']},
         accepted_cases=[dict(case_id=r['id'],observed=r['observed']) for r in accepted],inail_disputes=[r['id'] for r in accepted if r['provenance']['source']=='inail'],
         unsupported_cases=[r['id'] for r in failed],baseline_tests=t,historical_git_blobs_verified=len(h),round14_locks_verified=len(locks['sha256']),audited_at=now()))
    (ROOT/'docs/ROUND15_BASELINE_AUDIT.md').write_text(f'''# Round15 — baseline

Branch `codex/coverage-benchmark-v0.7.0`; HEAD `{BASE}`; working tree pulito all'ingresso, 0 modificati e 0 non tracciati. Software pubblico 0.6.1, schema610. Freeze Round14 `{f['freeze_git_commit']}` verificato: byte motore/profili/dataset/catalogo e truth storiche invariati, incluso il precedente dettaglio di serializzazione del manifest.

Verificati {len(locks['sha256'])} lock Round14 e {len(h)} blob storici. Baseline pytest: **{t['passed']} passed, 0 failed, {t['skipped']} skipped**, {t['seconds']}s; hash del log nel JSON.

Unknown v2 è `historical_unknown_release_v2_round14`: **107/114**, 3 DOCUMENT_MATCH, 0 FAMILY_MATCH e 4 errori di estrazione. Accettazioni: U14-5f0c017c3d56e6c5 e U14-c1fc4765c01dcd62 (INAIL, record1147); U14-d6e51fa8e7f88431 (ANAC, record615). I due INAIL sono compresi nei tre, non cinque casi distinti. I quattro PDF oltre limite sono elencati in page_limit_audit.json; restano nel denominatore114.

Il limite100 pagine esiste da `{first}` ed è antenato del freeze. README ed ESTRAZIONE lo documentavano. L'audit Round14 non lo aveva separato in preflight: questo difetto metodologico non viene cancellato. Soltanto i futuri gate separano classificazione e input-safety.

Stato ereditato: coverage1002/1158=86.528497%, canonici980/980+27/27, historicalNO241 senza accettazioni, mediana warm p95 247.1435ms, pytest777/0/3. Nessuno di questi esiti sostituisce le nuove verifiche dopo l'eventuale fix. Prossima attività: adjudication ufficiale completata prima di qualsiasi modifica al motore.
''',encoding='utf8',newline='\n')
    print('Round15 baseline verified',t,flush=True)

def adjudicate():
    assert read(OUT/'baseline_audit.json')['entry_commit']==BASE
    assert engine_files()==read(OUT/'baseline_audit.json')['engine_files_sha256'],'Engine changed before adjudication'
    e=read(OUT/'official_truth_evidence.json');m=read('benchmarks/manifests/official_unknown_release_v2.json');by={c['case_id']:c for c in m['cases']}
    canonical={c['document_id']:c for c in e['files'] if 'document_id' in c};cases=[]
    for c in e['files']:
        if 'case_id' not in c:continue
        case=by[c['case_id']];inail=case['source']=='inail';did=1147 if inail else 615;ref=canonical[did]
        status='ambiguous_truth' if inail else 'confirmed_unknown'
        reason=('The official2024/2025 form has the same issuer, beneficiary subtype and fund as record1147, but a different annual heading and attachment number from canonical2023/circular58-2023. Catalog version is null. Official evidence establishes a related annual variant, not identity equivalence across years. Neither correct exact match nor false acceptance is confirmed. Shared textual page is diagnostic, not a truth oracle.' if inail else 'The official listing links a draft normative regulation and the A.7 individual access application as distinct resources. Literal PDF headings and purposes differ. No catalog record or supported family represents this draft regulation; legal references to access and law241/1990 do not establish form identity.')
        listing=next(x for x in e['listings'] if x['url']==case['audit_evidence']['source_evidence']['listing_url'])
        evidence=dict(official_page=listing['url'],listing_receipt=listing['receipt'],official_title=('Modulo per Società partecipata pubblica' if inail else 'Bozza di Regolamento disciplinante i procedimenti relativi all’accesso civico, all’accesso civico generalizzato e all’accesso ai documenti amministrativi'),
            code=None,attachment=('Allegato8' if case['version']=='2025' else 'Allegato5') if inail else 'Documento in consultazione',entity=case['entity'],version=case['version'] or None,
            download_url=case['official_url'],download_receipt=case['receipt'],opening_sha256=__import__('hashlib').sha256(c['opening'].encode()).hexdigest(),canonical_sha256=ref['canonical_sha256'],canonical_title=ref['catalog']['titolo_ufficiale'],canonical_version_field=ref['catalog']['versione'],
            canonical_literal_annual_heading='2023' if inail else None,canonical_detail_url=ref['catalog']['detail_url'],canonical_download_url=ref['official_url'],
            replacement='No official replacement/equivalence assertion established; no event invented.',family='No supported catalog family for this official resource.',access_date=listing['receipt']['acquired_at'],inspected_at=c['inspected_at'])
        cases.append(dict(case_id=c['case_id'],historical_expected='NO_MATCH',adjudicated_status=status,expected_document_id=None,expected_family_id=None,
             official_evidence=evidence,evidence_date=evidence['access_date'],confidence='ambiguous' if inail else 'confirmed',release_gate_eligible=False,
             notes=reason,historical_truth_error_confirmed=False,historical_truth_qualification_error=inail,relation_to_catalog_document=did,decision_basis='Official content and listing only; prediction excluded from adjudication criteria.'))
    for c in read(OUT/'page_limit_audit.json')['round14_oversized_cases']:
        original=by[c['case_id']]
        cases.append(dict(case_id=c['case_id'],historical_expected='NO_MATCH',adjudicated_status='insufficient_official_evidence',expected_document_id=None,expected_family_id=None,
            official_evidence=dict(download_url=c['official_url'],download_receipt=original['receipt'],page_count=c['pages']),evidence_date=original['acquisition_date'],confidence='insufficient',release_gate_eligible=False,
            notes='Unsupported input for classification; confirmed page count and preexisting safe-rejection contract. Not an adjudicated recognition NO_MATCH. Historical denominator114 retained.'))
    value=dict(schema_version=3,registry_id='reference-truth-v3-round15',created_at=now(),historical_status='historical_unknown_release_v2_round14',cases=cases,
        policy='Additive adjudication. Historical labels/raw/metrics unchanged. Ambiguous cases cannot enter release gates. All critical resources are observed and excluded from future fresh benchmarks.')
    atomic_json(ROOT/'benchmarks/reference/reference_truth_v3.json',value)
    atomic_json(ROOT/'benchmarks/reference/round15_truth_adjudication.json',dict(schema_version=1,completed_at=now(),evidence_sha256=sha(OUT/'official_truth_evidence.json'),recognition_calls=0,
        decisions_completed_before_engine_change=True,engine_runtime_at_adjudication=read(OUT/'baseline_audit.json')['engine_files_sha256'],counts=dict(Counter(c['adjudicated_status'] for c in cases[:3])),cases=cases[:3]))
    accepted=[]
    for c in cases[:3]:
        false=c['adjudicated_status']=='confirmed_unknown'
        accepted.append(dict(case_id=c['case_id'],predicted_document=c['relation_to_catalog_document'],adjudicated_truth=c['adjudicated_status'],is_confirmed_false_accept=false,is_truth_error=False,is_ambiguous=not false,
           root_cause_if_false='Metadata fallback informational-heading gate recognizes Regolamento only at line start; Bozza di Regolamento bypasses it and shared legal title tokens become identity evidence.' if false else None,
           action='Generalize explicit heading wrappers before informational-resource rejection; add regression without case-specific IDs/URLs.' if false else 'No engine tuning from unresolved annual identity; retain ambiguity and exclude from release gates.'))
    save('confirmed_false_accepts',dict(schema_version=1,adjudication_sha256=sha('benchmarks/reference/round15_truth_adjudication.json'),confirmed_false_accepts=sum(c['is_confirmed_false_accept'] for c in accepted),cases=accepted,completed_at=now()))
    (ROOT/'docs/ROUND15_TRUTH_ADJUDICATION.md').write_text('''# Round15 — adjudication indipendente

Tre risorse distinte; i due dubbi INAIL sono inclusi nelle tre accettazioni. Decisioni basate sui contenuti e sui collegamenti ufficiali, completate prima di cambiare il motore. I segnali del riconoscitore servono soltanto alla successiva diagnosi.

| Caso | Esito | Motivo |
|---|---|---|
| U14-5f0c017c3d56e6c5 | ambiguous_truth | Modulo società partecipata pubblica, Anno2025, Allegato8 alla circolare36/2026; relazione annuale con record1147, versione catalogo nulla, canonico Anno2023. |
| U14-c1fc4765c01dcd62 | ambiguous_truth | Stesso sottotipo, Anno2024, Allegato5 alla circolare36/2026; l'equivalenza di identità tra annualità non è dimostrata. |
| U14-d6e51fa8e7f88431 | confirmed_unknown | Bozza di regolamento ANAC di17 pagine distinta dal modulo individuale A.7; non è un documento o una famiglia supportati dal catalogo. |

Fonti: [circolare INAIL36/2026](https://www.inail.it/portale/it/atti-e-documenti/note-provvedimenti-e-istruzioni-operative/normativa-circolari-inail/dettaglio.2026.08.circolare-n-36-del-7-ago-2026.html), [moduli INAIL del fondo](https://www.inail.it/portale/it/atti-e-documenti/moduli-e-modelli/assicurazione/moduli-prestazioni/prestazioni-economiche/fondo-vittime-amianto-lavoratori-di-societa-partecipate-pubblich.html), [pagina ANAC con allegati distinti](https://www.anticorruzione.it/-/accesso-civico-e-accesso-civico-generalizzato). Download, hash, titoli, ricevute e date effettive sono nei due JSON reference e official_truth_evidence.json. Le ricevute cache ANAC del12 ottobre restano tali: il403 del consultatore web non è aggirato e l'ispezione odierna non inventa un nuovo download.

**1 falso positivo confermato, 0 match esatti confermati, 2 ambigui.** Nessun errore di truth esatta è dichiarato dimostrato per INAIL; è dimostrato l'errore di qualificazione come confirmed_unknown senza risolvere la relazione annuale. Non si forza il motore a rifiutarli. La pagina testuale condivisa spiega tecnicamente il match ma non prova equivalenza tra annualità. Nessun evento di sostituzione o verifica editoriale aggiunto.

Reference truth v3 è aggiuntiva. Tutti i casi sono esclusi dai futuri gate indipendenti perché già osservati; i quattro oltre limite sono esclusi anche dal dominio di classificazione, con stato insufficiente per una decisione di riconoscimento. Il Round14 resta107/114, 3 DOCUMENT_MATCH, 0 FAMILY_MATCH, 4 errori: manifest, raw, label e metriche intatti. Il solo caso ANAC autorizza il fix generalizzabile dell'intestazione informativa.
''',encoding='utf8',newline='\n')
    print('Adjudication complete: 1 confirmed false accept, 2 ambiguous; no engine change yet',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['baseline','adjudicate']);a=p.parse_args();globals()[a.mode]()
