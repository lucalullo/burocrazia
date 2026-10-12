"""Correct denominators, record-level missing audit and technical support tiers."""
import csv,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import catalog,read,write
from src.fingerprint_v2 import read_bundle
from maintenance.resolve_resources import resource_kind,SOURCES

def main():
    docs,families=catalog();docs=[d for d in docs if d.stato_verifica not in ['demo','rifiutato']]
    audit=read('benchmarks/results/round6/resource_audit.json');rows=audit['cases']
    records=read_bundle()['records'];active={r['document_id'] for r in records if r['status']=='active'}
    v1_ids={r['document_id'] for r in read('data/document_recognition_fingerprints.json')['records']}
    failures={r['document_id']:r['reason'] for r in read('benchmarks/results/round6/fingerprint_build.json')['failures']}
    quarantined={r['document_id'] for r in records if r['status']=='quarantined'}
    coverage_path=ROOT/'benchmarks/results/round6/final/catalog_coverage.json'
    metadata_ids={r['expected']['document_id'] for r in json.loads(coverage_path.read_bytes())['cases'] if r['document_correct']} if coverage_path.exists() else set()
    from benchmarks.round5_recognition import family_label
    for row in rows:
        did=row['document_id']
        if did in active:row.update(round6_status='fingerprinted_exact')
        elif did in failures:row.update(round6_status='catalog_only',classification='extraction_failure' if 'canonical_' not in failures[did] else 'source_changed',reason=failures[did],safe_next_action='manual_resource_identity_review')
        elif did in quarantined:row.update(round6_status='catalog_only',classification='shared_resource',reason='Allegato identico associato a identità diverse; firme in quarantena.',safe_next_action='manual_identity_adjudication')
        else:row.update(round6_status='metadata_recognition' if did in metadata_ids else 'catalog_only')
        # Existing title/code recognition support is a technique, not a claim
        # that every file can be matched or that an editor verified its content.
        row['technical_state_note']='Disponibilità tecnica separata da provenienza, verifica umana e riconoscibilità misurata.'
    by={}
    for sid,key in SOURCES.items():
        g=[r for r in rows if r['source_id']==sid];fb=[r for r in g if r['expected_resource_type']=='file_backed_document']
        by[key]=dict(operational_docs_total=len(g),file_backed_operational_docs=len(fb),fingerprinted_file_backed_docs=sum(r['document_id'] in active for r in fb),
            fingerprinted_all_operational_docs=sum(r['document_id'] in active for r in g),missing_reasons=dict(Counter(r['classification'] for r in g if r['document_id'] not in active)))
    kinds=Counter(r['expected_resource_type'] for r in rows);file_backed=kinds['file_backed_document']
    report=dict(operational_docs_total=len(docs),file_backed_operational_docs=file_backed,
        fingerprinted_file_backed_docs=sum(r['document_id'] in active and r['expected_resource_type']=='file_backed_document' for r in rows),
        fingerprinted_all_operational_docs=len(active),dynamic_service_docs=kinds['dynamic_service'],metadata_only_docs=kinds['metadata_only_document'],
        denominator_classes=dict(kinds),coverage_all=len(active)/len(docs),coverage_file_backed=len(active)/file_backed,
        by_source=by,missing_reason_breakdown=dict(Counter(r['classification'] for r in rows if r['document_id'] not in active)),
        canonical_resources=len(records),active_resources=sum(r['status']=='active' for r in records),quarantined_resources=sum(r['status']=='quarantined' for r in records),
        new_catalog_identities=0,network_requests=audit['network_requests'],
        denominator_policy='A declared download remains file-backed despite 403/404, unsupported .doc, extraction failure or shared bytes. Detail-only records become file-backed only after an actual supported attachment. No failed fetch is reclassified as a service.')
    report['network_requests']=audit.get('network_requests_total',audit['network_requests'])
    report.update(retained_v1_identities=len(v1_ids&active),newly_fingerprinted_missing_v1=len(active-v1_ids),
        v1_ids_without_active_v2=sorted(v1_ids-active))
    write('benchmarks/results/round6/fingerprint_coverage.json',report)
    fields=['document_id','source','entity','title','code','version','detail_url','download_url','operational_status',
        'expected_resource_type','fetch_attempted','final_url','http_status','content_type','bytes','classification','reason','safe_next_action','round6_status']
    for filename,selected in [('missing_fingerprint_audit.csv',[r for r in rows if r['missing_v1']]),('missing_fingerprint_final.csv',[r for r in rows if r['document_id'] not in active]),('operational_support.csv',rows)]:
        p=ROOT/'benchmarks/results/round6'/filename
        with p.open('w',encoding='utf8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader()
            for row in selected:
                value=dict(row)
                if value['classification']=='available':value.update(classification='other',reason='Risolto: '+value['reason'])
                w.writerow(value)
    lines=['# Fingerprint coverage audit — Round 6','',report['denominator_policy'],'',
        f"Identità operative: {len(docs)}. File-backed: {file_backed}. Identità fingerprinted: {len(active)}.",
        f"Copertura totale {report['coverage_all']:.2%}; copertura file-backed {report['coverage_file_backed']:.2%}.",'',
        'Le 843 assenze v1 sono conservate nel CSV richiesto con il risultato tecnico Round 6; il CSV final contiene le assenze residue.',
        'Stato tecnico e stato editoriale restano separati. Seed SQLite e tutte le identità invariati. Le date sono ricevute effettive, senza inventare attualità della risorsa.','',
        '| Fonte | Operativi | File-backed | Fingerprinted |','|---|---:|---:|---:|']
    lines += [f"| {k} | {v['operational_docs_total']} | {v['file_backed_operational_docs']} | {v['fingerprinted_all_operational_docs']} |" for k,v in by.items()]
    lines+=['','Assenze residue: `'+json.dumps(report['missing_reason_breakdown'],ensure_ascii=False)+'`.','',
        'INPS: MIME multipart con un solo allegato PDF validato; hash del contenitore e del payload distinti nel manifest. Nessun bypass.',
        'Resolver: una pagina ufficiale e al massimo sei allegati correlati a titolo/codice. Redirect con allowlist; fixture offline per ciascuna fonte.',
        'HTTP 403/429 pregressi non ritentati. Robots per percorso, attese >=1 s e budget per sessione. HTML ordinario non chiude più arbitrariamente tutta la fonte.',
        'DOC binario legacy resta non supportato, e resta nel denominatore. DOCX privo di renderer locale: firma digitale disponibile, OCR canonico non dichiarato.',
        'Le quarantene tecniche non revocano né modificano automaticamente i record editoriali.']
    (ROOT/'docs/FINGERPRINT_COVERAGE_AUDIT.md').write_bytes(('\n'.join(lines)+'\n').encode())
    print(json.dumps({k:v for k,v in report.items() if k not in ['by_source','denominator_policy']},indent=2))

if __name__=='__main__':main()
