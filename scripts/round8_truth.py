"""Explicit, evidence-backed reconciliation; never edits historical labels."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import catalog,read,write
from benchmarks.round6_recognition import raw_record
from src.extract import extract_document

def main():
    target=ROOT/'benchmarks/reference/reference_truth_v1.json'
    if target.exists():raise ValueError('Truth v1 already exists; new evidence needs a new registry version')
    docs,families=catalog();by={d.id:d for d in docs}
    bundle=read('data/document_recognition_fingerprints_v2.json');inventory=read('benchmarks/results/round8/baseline/contradictions.json')
    entries=[];groups=[]
    for gi,group in enumerate(inventory['exact_text_conflicts'],1):
        cases=group['cases'];first=cases[0];ids=sorted({c['expected'].get('document_id') for c in cases if c['expected'].get('document_id')})
        if first['case_id']=='EX02':ids=[13]
        if first['case_id']=='EX03':ids=[12]
        if first['case_id']=='R066':ids=[143]
        if first['case_id']=='R068':ids=[167]
        evidence=[]
        for did in ids:
            d=by[did]
            resources=[r for r in bundle['records'] if r['document_id']==did]
            for r in resources[:1]:
                raw=raw_record(r);assert hashlib.sha256(raw).hexdigest()==r['canonical_file_sha256']
                ex=extract_document(raw,'evidence'+('.pdf' if r['mime_type']=='application/pdf' else '.docx'))
                evidence.append(dict(document_id=did,url=r['url'],final_url=r['final_url'],acquired_at=r['acquisition_date'],sha256=r['canonical_file_sha256'],catalog_title=d.titolo_ufficiale,code=d.codice,entity=d.ente,version=d.versione,opening_text_sha256=hashlib.sha256(ex.text[:2000].encode()).hexdigest(),scope='Official local bytes inspected; no full text redistributed.'))
            if not resources:evidence.append(dict(document_id=did,url=d.detail_url,scope='Catalog provenance only; official bytes unavailable, insufficient for confirmation.'))
        chosen=None;note=''
        if first['case_id'] in ['R066','R068']:
            did=ids[0];d=by[did]
            assert any(e.get('sha256') for e in evidence)
            chosen=dict(match_type='DOCUMENT_MATCH',document_id=did,entity=d.ente,version=d.versione)
            note='Full official heading and compatible issuing authority are present. R066 additionally states INL 31. Official local PDF/DOCX confirms a specific catalog identity; old family-only label was less specific.'
        elif first['case_id'] in ['EX02','EX03']:
            note='Official bytes confirm code/title and version 1.1, but the synthetic input omits the revision. It cannot establish that revision independently of catalog uniqueness. Both historical expectations are preserved; release truth is ambiguous.'
        elif first['case_id'] in ['R060','R061']:
            fid=first['expected'].get('family_id') or (3 if first['case_id']=='R060' else 4)
            f=next(f for f in families if f.id==fid)
            evidence.append(dict(family_id=fid,url=f.official_url,scope='Historical family source URL only. No independently inspected official source bytes proving this input label; excluded from primary release truth.'))
            note='Issuer/function conflict was intentionally corrected in locked v2. Runtime safety keeps NO, but absent official source bytes this registry does not certify the label as official truth.'
        else:
            note='Bare category or profession label is insufficient to establish a unique form/version. Official evidence distinguishes a full form heading or informational shared attachment; the short synthetic input remains ambiguous.'
        for c in cases:
            official=chosen is not None and c['expected'].get('match_type')==chosen['match_type'] and c['expected'].get('document_id')==chosen.get('document_id')
            status='official_truth_confirmed' if official else 'historical_fixture_error' if chosen else 'ambiguous'
            entries.append(dict(group_id=f'TRUTH-{gi:02}',case_id=c['case_id'],corpus=c['corpus'],input_sha256=c['text_sha256'],historical_expected=c['expected'],alternative_expected=[x['expected'] for x in cases if x['expected']!=c['expected']],reconciled_expected=chosen,document_id=chosen.get('document_id') if chosen else ids[0] if len(ids)==1 else None,family_id=c['expected'].get('family_id'),entity=chosen.get('entity') if chosen else c['expected'].get('entity'),version_year=chosen.get('version') if chosen else c['expected'].get('version'),official_evidence=evidence,status=status,label_status='confirmed' if official else 'excluded_from_release_gate' if chosen else 'ambiguous',notes=note))
        groups.append(dict(group_id=f'TRUTH-{gi:02}',case_ids=sorted({c['case_id'] for c in cases}),status='official_truth_confirmed' if chosen else 'ambiguous',notes=note))
    classified={(e['case_id'],e['corpus']) for e in entries}
    unclassified=[c for g in inventory['case_id_label_changes'] for c in g['cases'] if (c['case_id'],c['corpus']) not in classified]
    assert not unclassified,unclassified
    result=dict(schema_version=1,registry_id='reference-truth-v1',catalog_sha256='790b690123c82e1cb7bdfa67a10216284022987d50b0abbcc4a1a245785e3e99',scope='Explicit adjudication of all baseline contradictions before Round8 tuning. Historical corpus bytes remain locked. Only official_truth_confirmed + confirmed entries may enter reconciled primary release gates.',groups=groups,cases=entries,counts=dict(Counter(e['status'] for e in entries)),unclassified_contradictions=0,corpus_sha256=read('benchmarks/results/round8/baseline/metrics.json')['corpus_sha256'])
    write('benchmarks/reference/reference_truth_v1.json',result)
    rows='\n'.join(f"| {g['group_id']} | {', '.join(g['case_ids'])} | {g['status']} | {g['notes']} |" for g in groups)
    text=f"""# Reference truth audit v1

Audit precedente al tuning Round 8. I corpus locked e tutte le etichette storiche restano invariati. R6/R7 sono development. Le contraddizioni sono classificate per input normalizzato, senza scegliere l'expected in funzione del riconoscitore.

9 gruppi contraddittori, {len(entries)} occorrenze, 0 non classificati. Stati: `{json.dumps(result['counts'],sort_keys=True)}`. Soltanto `official_truth_confirmed` con `label_status=confirmed` entra nei gate riconciliati. I casi ambigui restano esclusi; le regressioni storiche di sicurezza sono comunque riportate separatamente, senza sostituire v1 con v2.

| Gruppo | Casi | Stato riconciliato | Motivazione |
|---|---|---|---|
{rows}

Le prove registrano URL, ricevuta effettiva, SHA dei byte ufficiali, identità e hash dell'intestazione ispezionata. Nessun evento pregresso inventato e nessuna nuova verifica editoriale attribuita. I PDF/DOCX ufficiali restano nella cache ignorata. La mancanza di byte ufficiali è dichiarata, non sostituita con un URL come prova di contenuto.

I nuovi casi canonical/evaluation ereditano `confirmed` soltanto da una risorsa ufficiale SHA-verificata, binding catalogo valido e identità non ambigua. Le risorse condivise sono escluse dall'identità exact se metadata/code/ente non disambiguano. Gli unknown storici mantengono `historical_only`; nessuna indipendenza nuova rivendicata.

Registro: `benchmarks/reference/reference_truth_v1.json`. Una revisione richiede un nuovo registro/versione con motivazione, non la sovrascrittura di v1.
"""
    (ROOT/'docs/REFERENCE_TRUTH_AUDIT.md').write_bytes(text.encode());print(result['counts'])

if __name__=='__main__':main()
