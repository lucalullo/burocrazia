"""Correct known-source common-page ambiguity, preserving the prior single-shot."""
import csv
from datetime import UTC,datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks.transactional_writer import atomic_json
from benchmarks.round8_common import case_result
from maintenance.build_fingerprints_v3 import atomic
from maintenance.legacy_convert import convert_official
from maintenance.round13_legacy import normalize_pdf
from src.fingerprint_v3 import read_bundle,PATH,public_index,revision
from maintenance.round13_audit import FIELDS
from scripts.round13_validation import coverage

OUT=ROOT/'benchmarks/results/round13'


def main():
    assert not (OUT/'ambiguity_adjudication.json').exists(),'Adjudication already completed'
    bundle=read_bundle();before=hashlib.sha256(PATH.read_bytes()).hexdigest()
    unknown=read('benchmarks/results/round13/unknown_release_v1.json')
    assert before==unknown['identity']['fingerprint_sha256']
    originals=[];pages=[];group={617,618,619}
    for r in bundle['records']:
        if r['document_id'] not in group or r['ocr_metadata'].get('source_kind')!='maintenance_derived_legacy':continue
        originals.append(dict(document_id=r['document_id'],record_json_before=json.dumps(r,ensure_ascii=False)))
        p=next(p for p in r['pages'] if p['number']==2)
        pages.append(dict(document_id=r['document_id'],common_page=2,signature_sha256=hashlib.sha256(json.dumps({k:p[k] for k in ['digital','chars','anchors']},sort_keys=True).encode()).hexdigest()))
        r['status']='shared';r['shared_kind']='ambiguous'
        r['ocr_metadata'].update(ambiguity_group='UNIONCAMERE-617-618-619-COMMON-PAGE2',
                                  adjudication='Common page2 does not establish which access request was uploaded.')
    assert len(originals)==3
    previous=read('benchmarks/results/round13/legacy_supported_observations.json')['final_cases']
    for did in [617,619]:
        evidence=next(c for c in previous if c['provenance']['document_id']==did)
        assert evidence['observed']['document_id']==618 and 'canonical_page:2' in evidence['signals']
        assert all(signal in evidence['signals'] for signal in ['digital:1.0000','chars:1.0000','anchors:1.0000'])
    atomic(bundle);public_index.cache_clear();revision.cache_clear()
    after=hashlib.sha256(PATH.read_bytes()).hexdigest()
    restored=json.loads(json.dumps(bundle))
    for original in originals:
        for i,r in enumerate(restored['records']):
            if r['document_id']==original['document_id'] and r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy':
                restored['records'][i]=json.loads(original['record_json_before']);break
    assert hashlib.sha256((json.dumps(restored,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()==before
    atomic_json(OUT/'pre_adjudication_bundle_restore.json',dict(bundle_sha256_before=before,bundle_sha256_after=after,records=originals,
                recipe='Replace these three complete record objects using the JSON strings, preserve all other records/root order, serialize UTF8 ensure_ascii=False indent2 trailing LF; exact prior byte SHA verified.'))
    path=OUT/'legacy_fingerprint_audit.csv'
    (OUT/'legacy_fingerprint_audit_initial.csv').write_bytes(path.read_bytes())
    (OUT/'coverage_final_initial.json').write_bytes((OUT/'coverage_final.json').read_bytes())
    rows={int(r['document_id']):r for r in csv.DictReader(path.open(encoding='utf8'))}
    docs,families=catalog();observed=[]
    for r in bundle['records']:
        if r['ocr_metadata'].get('source_kind')!='maintenance_derived_legacy':continue
        did=r['document_id'];meta=r['ocr_metadata']
        raw=(ROOT/'benchmarks/cache'/(r['canonical_file_sha256']+'.body')).read_bytes()
        pdf=normalize_pdf(convert_official(raw,meta['original_format'],ROOT/'benchmarks/work/round13-adjudication')[0])
        assert hashlib.sha256(pdf).hexdigest()==meta['derived_sha256']
        cc=dict(id='L13-ADJ-'+str(did),group='document:'+str(did),category='legacy_qualification_after_adjudication',
                expected=dict(match_type='DOCUMENT_MATCH',document_id=did),label_status='source_association_audited',
                representation='deterministic_derived_pdf',provenance=dict(document_id=did,original_sha256=r['canonical_file_sha256'],derived_sha256=meta['derived_sha256']))
        result=case_result(cc,pdf,'legacy-derived.pdf',docs,families)
        usable=r['status']=='active' and result['document_correct'] and 'content_fingerprint_match' in result['signals'] and 'fingerprint_v3' in result['signals']
        result['eligible']=usable;observed.append(result)
        rows[did].update(runtime_indexed=r['status'] in ['active','shared'],rejected=r['status']=='quarantined',
                         shared_resource=r['status']=='shared',ambiguity_group=meta.get('ambiguity_group',''),
                         supported_representation_result=result['observed']['match_type']+':'+str(result['observed'].get('document_id')),
                         eligible_for_fingerprint_coverage=usable)
        if did in group:rows[did]['exclusion_reason']='unresolved_common_page2_ambiguity; resource-level only, no exact fingerprint identity'
        if did%5==0:print('R13 adjudication verified ID',did,flush=True)
    wrong=[r['id'] for r in observed if r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct']]
    with path.open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(rows.values())
    atomic_json(OUT/'legacy_adjudication_observations.json',dict(cases=observed,wrong_document_accepts=wrong,
                bundle_sha256=after,scope='Known-source technical ambiguity adjudication, no release replay. Expected identities unchanged; source records shared, decision rules unchanged.'))
    atomic_json(OUT/'ambiguity_adjudication.json',dict(author='Codex technical audit',observed_at=datetime.now(UTC).isoformat(),
                document_ids=sorted(group),common_page_evidence=pages,prior_cross_wrong={'617':618,'619':618},
                dataset_sha256_before=before,dataset_sha256_after=after,wrong_after=wrong,
                definition_sha256=hashlib.sha256((ROOT/'benchmarks/reference/fingerprint_support_definition_v1.json').read_bytes()).hexdigest(),
                reason='Three different request forms share page2 fingerprint statistics; that page cannot prove an exact request identity. All three bindings explicitly shared/ambiguous. Prior observations preserved.'))
    atomic_json(OUT/'unknown_binding_invalidation.json',dict(status='current_candidate_unmeasured',release_replay=False,
                measured_rejection_rate=unknown['rejection_rate'],measured_cases=unknown['actual_count'],
                measured_bundle_sha256=before,current_bundle_sha256=after,
                reason='Unknown single-shot was started prematurely before final cross-identity adjudication. Its valid observations are retained for the earlier bundle and cannot establish the prerequisite for the corrected candidate. No replay or tuning on this subset.'))
    coverage()
    print('R13 ambiguity adjudicated; wrong exact after',wrong,flush=True)


if __name__=='__main__':main()
