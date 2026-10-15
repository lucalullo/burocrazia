"""Versioned release-fast contracts, preserving every historical truth file."""
from scripts.round16_common import *
from benchmarks.release_truth import select_release
from collections import Counter

def main():
    assert not (ROOT/POLICY).exists(),'Truth policy already fixed'
    prepared=read('benchmarks/work/round16/semantic-inputs.json')['rows'];cases=[]
    sources={TRUTH:sha(TRUTH),'benchmarks/reference/reference_truth_v2.json':sha('benchmarks/reference/reference_truth_v2.json')}
    for c in prepared:
        if c['category'] in ['canonical','canonical_legacy']:
            cases.append(dict(case_id=c['id'],confidence='confirmed',release_gate_eligible=True,expected=c['expected'],truth_domain='technical_canonical_binding',input_key=c['id'],evidence=dict(input_sha256=c['sha256'],catalog_sha256=sha('data/catalog_seed.sqlite3'),fingerprint_sha256=sha('data/document_recognition_fingerprints_v3.json')),notes='Technical association of the current canonical/qualified derived resource to its immutable catalog binding; not editorial verification.'))
    names=['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3']
    for name in names:
        path='benchmarks/corpora/'+name+'.json';sources[path]=sha(path)
        for c in read(path)['cases']:
            if c['expected']['match_type']=='NO_MATCH':
                cases.append(dict(case_id=name+':'+c['id'],confidence='confirmed',release_gate_eligible=True,expected=c['expected'],truth_domain='synthetic_safety_contract',input_key=name+':'+c['id'],evidence=dict(corpus=path,corpus_sha256=sha(path),case_id=c['id']),notes='Locked negative product contract, including prudent abstention on insufficient issuer/version evidence. Does not certify an official unknown identity or independent unknown precision.'))
    path='tests/fixtures/benchmark_v2.json';sources[path]=sha(path)
    for c in read(path)['cases']:
        if c['expected']['match_type']=='NO_MATCH':
            cases.append(dict(case_id='development_compat_v2:'+c['id'],confidence='confirmed',release_gate_eligible=True,expected=c['expected'],truth_domain='synthetic_safety_contract',input_key='development_compat_v2:'+c['id'],evidence=dict(corpus=path,corpus_sha256=sha(path),case_id=c['id']),notes='Explicit locked abstention/issuer/revision safety contract; separate from ambiguous historical expectations requesting an exact revision.'))
    base=read(TRUTH)
    for c in base['cases']:
        is_anac=c['adjudicated_status']=='confirmed_unknown';key='ANAC:'+c['case_id'] if is_anac else 'historical_v2:'+c['case_id']
        cases.append(dict(case_id=key,confidence=c['confidence'],release_gate_eligible=is_anac,expected=dict(match_type='NO_MATCH') if is_anac else None,truth_domain='official_adjudication' if is_anac else 'historical_dispute',input_key=key if is_anac else None,
             evidence=c['official_evidence'],notes='Observed ANAC is eligible only for confirmed diagnostic regression, never for fresh unknown release. Original v3 fresh-release exclusion is preserved under independent_evaluation_eligible=false.' if is_anac else c['notes'],independent_evaluation_eligible=False))
    # EX02/EX03 are INPS, not the two INAIL resources. Their original labels
    # remain visible; this addendum links the existing v2 ambiguity explicitly.
    for c in read('benchmarks/reference/reference_truth_v2.json')['cases']:
        if c['corpus']=='benchmarks/corpora/development_regression.json' and c['case_id'] in ['EX02','EX03']:
            cases.append(dict(case_id='development_regression:'+c['case_id'],confidence='ambiguous',release_gate_eligible=False,expected=None,truth_domain='official_identity_dispute',input_key=None,evidence=c['source_evidence'],notes=c['notes'],historical_expected=dict(match_type=c['expected_status'],document_id=c['expected_document_id'])))
    # Parser limits are a separate safe rejection contract, not NO_MATCH truth.
    path='benchmarks/manifests/input_safety_v1.json';sources[path]=sha(path)
    for c in read(path)['cases']:
        cases.append(dict(case_id='input_safety:'+c['case_id'],confidence='confirmed',release_gate_eligible=True,expected=dict(match_type='SAFE_REJECTION'),truth_domain='parser_limit_contract',input_key=c['case_id'],evidence=dict(manifest=path,manifest_sha256=sha(path),input_sha256=c['SHA256']),notes='Unsupported-input rejection, no document/family result, no crash or temporary residue. Separate from classification accuracy.'))
    registry=dict(schema_version=3,registry_id='reference-truth-v3-round16-release-fast-addendum',base_reference_truth_v3_sha256=sha(TRUTH),cases=cases,source_sha256=sources,created_at=now(),
        rationale='Round15 v3 covered seven disputed/unsupported observed resources and excluded them from fresh release. Round16 adds explicit confirmed diagnostic contracts with distinct truth domains. No historical label, official adjudication or independence claim is changed.')
    selected=select_release(cases);assert len([c for c in selected if c['truth_domain']=='technical_canonical_binding'])==1007
    assert len([c for c in selected if c['truth_domain']=='synthetic_safety_contract'])==241
    atomic_json(ROOT/ADDENDUM,registry)
    policy=dict(schema_version=1,policy_id='release-truth-policy-v1',base_reference_truth_v3_sha256=sha(TRUTH),registry_sha256=sha(ADDENDUM),registry=ADDENDUM,
        confidence_policy=dict(confirmed='included_in_release_gate; exclusion is an error',ambiguous='excluded_from_release_gate; historical mismatch always visible',insufficient='excluded_from_release_gate',historical_only='historical_report_only',obsolete='excluded until independently requalified with a new version and actual evidence; historical results retained'),
        domains=['official_adjudication','technical_canonical_binding','synthetic_safety_contract','parser_limit_contract'],
        gate_scope='Confirmed diagnostic release-fast regression; not independent unknown/known robustness evaluation. Freshness governed separately by contamination registry.',
        historical_policy='Compare every frozen original expectation, retain all mismatches including EX02/EX03 and locked-v1 contradictions. Never rewrite historical expected.',created_at=now())
    atomic_json(ROOT/POLICY,policy)
    (ROOT/'docs/RELEASE_TRUTH_POLICY.md').write_text(f'''# Release truth policy v1

La regressione storica confronta gli expected originali e mostra tutti i mismatch. Il release-gate-fast usa reference truth v3 più l'addendum Round16 motivato: **{len(selected)} contratti confermati**, senza cambiare alcun corpus o reference storica. Hash di v3, addendum, policy e input sono registrati.

Confirmed entra sempre; tentare di escluderlo è errore. Ambiguous e insufficient sono esclusi; historical_only resta nel report storico. Obsolete resta escluso finché una nuova versione con evidenza effettiva ne dimostra la riqualificazione. Nessuna scadenza o sostituzione viene inventata.

I domini sono espliciti: identità ufficiale adjudicata; binding tecnico del file canonico/derivato qualificato; contratto sintetico di rifiuto prudente; limite del parser. Un contratto sintetico confermato non diventa truth ufficiale o prova di precisione sugli sconosciuti. R061 e i negativi hard restano contratti di sicurezza anche quando una vecchia interpretazione dell'identità era ambigua. Le versioni v1/v2 e la v3 Round15 restano byte-identiche.

EX02/EX03 sono **INPS CI543/CI544**, revisione1.1 assente nel testo sintetico, già ambiguous in v2. I due INAIL ambigui sono distinti e restano esclusi. Entrambi i gruppi rimangono visibili; nessuno è usato per tuning. Le varianti compat-v2 con expected NO sono contratti espliciti di astensione, non una conferma della versione omessa negli expected storici.

ANAC, già osservato, entra nella regressione confermata grazie all'adjudication ufficiale precedente al fix. Il vecchio release_gate_eligible=false escludeva le risorse osservate dai futuri corpus indipendenti: non viene riscritto; il nuovo addendum dichiara un gate diagnostico distinto e independent_evaluation_eligible=false. Nessun caso storico/diagnostico può entrare come fresco in unknown v3 o evaluation v5.
''',encoding='utf8',newline='\n')
    save('truth_policy_audit',dict(passed=True,selected=len(selected),by_domain=dict(Counter(c['truth_domain'] for c in selected)),excluded=[dict(case_id=c['case_id'],confidence=c['confidence']) for c in cases if not c['release_gate_eligible']],reference_truth_v3_sha256=sha(TRUTH),addendum_sha256=sha(ADDENDUM),policy_sha256=sha(POLICY),historical_labels_changed=False))
    print('Release truth policy',len(selected),'confirmed contracts',flush=True)
if __name__=='__main__':main()
