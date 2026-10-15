"""Audit real identity support for all 16 families, without inventing labels."""
import csv,time
from collections import defaultdict
from benchmarks.round3_audit import ROOT,catalog,read,write
from benchmarks.round5_recognition import family_label,split_identities,raw_record
from benchmarks.round6_recognition import OUT,save,active_records
from benchmarks.evaluate import summary
from scripts.benchmark import evaluate_case
from src.extract import extract_document
from src.recognize import recognize_document_family
from src.models import CatalogRecognitionResult

def main():
    docs,families=catalog();real=[d for d in docs if d.stato_verifica not in ['demo','rifiutato']]
    resources=read('benchmarks/manifests/official_fingerprint_cache_v2.json')['files'];active=active_records()
    available={r['document_id'] for r in resources};fingerprinted={r['document_id'] for r in active}
    byid={r['document_id']:r for r in active};audit=[];rows=[];splits={}
    for f in families:
        identities=[d for d in real if family_label(d)==f.id]
        usable=[d for d in identities if d.id in fingerprinted]
        items=[dict(document_id=d.id,sha256=byid[d.id]['canonical_file_sha256']) for d in usable]
        development,held=split_identities(items)
        evaluable=len(held)>=3 and len(development)>=2
        status='evaluable' if evaluable else 'territorial_template' if f.id in [15,16] else 'insufficient_identities' if len(identities)<5 else 'insufficient_files'
        audit.append(dict(family_id=f.id,family_name=f.nome,real_identities=len(identities),
            official_files_available=sum(d.id in available for d in identities),fingerprinted_identities=len(usable),
            held_out_identities_possible=len(held),status=status,
            label_basis='Conservative existing catalog identity/family mapping, not recognition-derived; absent mappings do not establish coverage.'))
        splits[str(f.id)]=dict(development_identities=[i['document_id'] for i in development],held_out_identities=[i['document_id'] for i in held],evaluable=evaluable)
        # Exploratory below-sample observations remain explicitly separate.
        for item in held:
            r=byid[item['document_id']];raw=raw_record(r);ext='.pdf' if r['mime_type']=='application/pdf' else '.docx'
            ex=extract_document(raw,'family'+ext);begin=time.perf_counter()
            result=recognize_document_family(ex.text,families,known_entities=[d.ente for d in docs])
            model=CatalogRecognitionResult('FAMILY_MATCH' if result.recognized else 'NO_MATCH',0,result.confidence,family=result.family)
            row=evaluate_case(dict(id='FH6-'+str(item['document_id']),group='document:'+str(item['document_id']),category='family_identity_holdout',expected=dict(match_type='FAMILY_MATCH',family_id=f.id)),model,(time.perf_counter()-begin)*1000)
            row.update(provenance=dict(document_id=item['document_id'],sha256=item['sha256']),representation='official_original',family_evaluable=evaluable)
            rows.append(row)
    path=ROOT/OUT/'family_evaluability.csv'
    with path.open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(audit[0]),lineterminator='\n');writer.writeheader();writer.writerows(audit)
    evaluated=[r for r in rows if r['family_evaluable']]
    per={str(f.id):summary([r for r in evaluated if r['expected']['family_id']==f.id]) for f in families if any(r['expected']['family_id']==f.id for r in evaluated)}
    macro={key:sum(v['metrics'][key]['value'] for v in per.values() if v['metrics'][key]['value'] is not None)/sum(v['metrics'][key]['value'] is not None for v in per.values()) if any(v['metrics'][key]['value'] is not None for v in per.values()) else None for key in ['family_precision','family_recall','family_f1']}
    save('family_release',evaluated,families_total=len(families),families_evaluable=sum(r['status']=='evaluable' for r in audit),
        splits=splits,per_family=per,macro=macro,exploratory_cases=rows,exploratory_summary=summary(rows),
        false_accepts=sum(r['observed']['match_type']=='FAMILY_MATCH' and not r['family_correct'] for r in evaluated),
        capability_status='not_sufficiently_validated' if len(per)<5 else 'evaluated',
        limitations='Retrospective split; no new family phrases, no exact fingerprints in family scoring. Fewer than five evaluable families does not block known-document RC; family capability remains unvalidated. Historical synthetic hard negatives reported separately.')
    print('Families evaluable',len(per),'exploratory cases',len(rows),flush=True)

if __name__=='__main__':main()
