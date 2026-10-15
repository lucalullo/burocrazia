"""One prospective v3 run on the immutable Round18 subset and freeze."""
import argparse,hashlib
from scripts.round18_common import *
from benchmarks.round18_sampling import MANIFEST,SAMPLING,sample,exposures
from benchmarks.round17_unknown import metrics
from benchmarks.unknown_release import balance
from benchmarks.round3_audit import catalog
from benchmarks.transactional_writer import CaseJournal
from benchmarks.unknown_v2 import validate as validate_old_contract

def validate_observations(value):
    import jsonschema
    jsonschema.validate(value,read('benchmarks/schemas/round18_unknown_observations.schema.json'))
    ids=[r['id'] for r in value['cases']]
    assert len(ids)==len(set(ids))==value['expected_count']==value['completed'] and value['complete']
    assert all(r['input_sha256']==r['provenance']['sha256'] for r in value['cases'])
    return value

def validate_release(m):
    f=sealed();assert sha(MANIFEST)==f['unknown_manifest_sha256']
    assert m['sampling_policy_sha256']==sha(SAMPLING) and m['registry_sha256']==sha(REGISTRY)
    assert m['truth_audit_sha256']==sha(OUT/'unknown_master_pool.json')
    validate_old_contract(dict(m,schema_version=2,manifest_id='official-unknown-v2'))
    master=read(OUT/'unknown_master_pool.json')['eligible_cases']
    assert [c['case_id'] for c in sample(master,SEED)]==[c['case_id'] for c in m['cases']]
    assert not exposures(m['cases'])
    assert all(c['truth_status']=='confirmed_unknown' and c['contamination_status']=='fresh' for c in m['cases'])
    assert read(OUT/'unknown_release_v3_preflight.json')['passed']
    return m

def run():
    freeze=sealed();manifest=validate_release(read(MANIFEST));target=OUT/'unknown_release_v3.json'
    assert not target.exists(),'Release already completed; no replay'
    from benchmarks import round8_common as common
    from benchmarks.evaluate import code_hash
    common.SEED=SEED;ident=common.identity();key=dict(freeze_commit=freeze['freeze_git_commit'],manifest_sha256=sha(MANIFEST),runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],runner_code_sha256=code_hash(),registry_sha256=sha(REGISTRY),infrastructure_sha256=infrastructure_sha256())
    assert ident['runtime_sha256']==freeze['runtime_sha256'] and ident['fingerprint_sha256']==freeze['fingerprint_dataset_sha256']
    journal=CaseJournal(ROOT/'benchmarks/work/round18/unknown-release-v3.sqlite',identity=key,expected_ids=[c['case_id'] for c in manifest['cases']]);pending=set(journal.pending());docs,families=catalog()
    marker=OUT/'unknown_v3_started.json'
    if marker.exists():assert read(marker)['identity']==key
    else:save('unknown_v3_started',dict(identity=key,expected_count=len(manifest['cases']),started_at=now(),single_shot=True))
    for i,c in enumerate(manifest['cases'],1):
        if c['case_id'] not in pending:continue
        raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['SHA256']
        cc=dict(id=c['case_id'],group=c['resource_group'],category=c['document_type'],expected=dict(match_type='NO_MATCH'),label_status='confirmed_unknown',representation='official_original',
                provenance=dict(source=c['source'],entity=c['entity'],document_type=c['document_type'],sha256=c['SHA256'],previously_seen=False,official_url=c['official_url'],truth_version=c['version']))
        journal.append(common.case_result(cc,raw,'unknown.pdf' if c['mime']=='application/pdf' else 'unknown.docx',docs,families))
        if i%10==0:print('R18 unknown persisted',i,'/',len(manifest['cases']),flush=True)
    rows=journal.rows();export=OUT/'unknown_release_v3_observations.json';journal.export(export,complete=True);validate_observations(read(export))
    assert len(rows)==len(manifest['cases'])
    m=metrics(rows);stats=balance(manifest['cases'])
    save('unknown_release_v3',dict(schema_version=1,status='complete',identity=ident,freeze_commit=freeze['freeze_git_commit'],manifest_sha256=sha(MANIFEST),
        expected_count=len(rows),actual_count=len(rows),unique_case_ids=len({r['id'] for r in rows}),recognition_calls=len(rows),**m,selection=stats,
        per_source={s:metrics([r for r in rows if r['provenance']['source']==s]) for s in stats['counts_per_source']},
        per_entity={s:metrics([r for r in rows if r['provenance']['entity']==s]) for s in sorted({c['entity'] for c in manifest['cases']})},
        per_type={s:metrics([r for r in rows if r['category']==s]) for s in stats['document_types']},
        per_category={s:metrics([r for r in rows if r['category']==s]) for s in stats['document_types']},
        wrong_accepts=[dict(id=r['id'],observed=r['observed'],signals=r['signals']) for r in rows if r['observed']['match_type']!='NO_MATCH'],
        observations_sha256=sha(export),passed=m['rejection_rate']>=.99 and m['false_acceptance_rate']<=.01 and m['entity_errors']==0 and m['version_errors']==0,
        error_basis='Entity errors compare an emitted entity to the literal verified issuer, applying only existing public ENTITY_ALIASES. Version errors count explicit contradictory version/year only. Every document/family acceptance is false acceptance even when entity/version are compatible.',
        scope='First single-shot on byte-identical freeze engine. Fresh prediction SHA, no release v1/development/observed resource overlap. Known v5 may run only if this gate passes.'))
    sealed();print('R18 unknown result',m,flush=True)

if __name__=='__main__':run()
