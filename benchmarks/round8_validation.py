"""Frozen historical contracts and public canonical resources; no fresh tuning."""
import argparse,hashlib,time,csv
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from benchmarks.round8_common import *
from benchmarks.evaluate import canonical_cases
from benchmarks.reference_truth import load,confirmed
from scripts.benchmark import load_corpus
from src.recognize import recognize_document_family

def historical():
    docs,families=catalog();truth=load();lookup={(c['corpus'],c['case_id']):c for c in truth['cases']};allrows=[]
    names=['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2','family_release_v3']
    for name in names+['development_compat_v2','catalog_coverage']:
        path='tests/fixtures/benchmark_v2.json' if name=='development_compat_v2' else 'benchmarks/corpora/'+name+'.json'
        cases=canonical_cases(docs) if name=='catalog_coverage' else load_corpus(ROOT/path)[0]['cases'];rows=[]
        for cc in cases:
            t=time.perf_counter()
            if name=='family_release_v3':
                r=recognize_document_family(cc['text'],families,known_entities=[d.ente for d in docs]);result=CatalogRecognitionResult('FAMILY_MATCH' if r.recognized else 'NO_MATCH',0,r.confidence,family=r.family)
            else:result=recognize_catalog(cc['text'],docs,families)
            row=evaluate_case(cc,result,(time.perf_counter()-t)*1000);ref=lookup.get((path,cc['id']))
            row.update(label_status=ref['label_status'] if ref else 'historical_only',truth_status=ref['status'] if ref else 'historical_expected_preserved',representation='synthetic_historical')
            rows.append(row)
        save('historical_'+name,rows,scope='Original locked expectations unchanged, historical diagnostic and safety contract; no unsupported labels promoted to confirmed.')
        allrows.extend(rows);print('Historical',name,sum(r['correct'] for r in rows),'/',len(rows),flush=True)
    reconciled=[]
    for ref in confirmed():
        cc=next(c for c in read(ref['corpus'])['cases'] if c['id']==ref['case_id']);cc=dict(cc,expected=ref['reconciled_expected'])
        row=evaluate_case(cc,recognize_catalog(cc['text'],docs,families));row.update(label_status='confirmed',representation='reconciled_historical');reconciled.append(row)
    save('reconciled_truth',reconciled,scope='Only official_truth_confirmed registry rows enter this truth gate.')

def canonical():
    docs,families=catalog();rows=[];records=active_records()
    for i,r in enumerate(records):
        rows.append(case_result(case(r,'canonical_'+r['canonical_file_sha256'][:12]),raw_record(r),'canonical'+('.pdf' if r['mime_type']=='application/pdf' else '.docx'),docs,families))
        if (i+1)%100==0:print('Canonical',i+1,'/',len(records),flush=True)
    save('canonical',rows,scope='Unambiguous active canonical resources; exact SHA identity plus unchanged entity/version/operational checks.')
    old=read('benchmarks/results/round7/fingerprint_coverage.json');ids={r['document_id'] for r in records}
    cov=dict(old,fingerprinted_all_operational_docs=len(ids),fingerprinted_file_backed_docs=len(ids),coverage_all=len(ids)/1212,coverage_file_backed=len(ids)/1158,recovered=len(ids)-941,denominator_scope='Fixed Round7 1212 operational / 1158 file-backed; no denominator redefinition.')
    write(OUT+'fingerprint_coverage.json',cov)
    groups=defaultdict(list)
    for r in read_bundle()['records']:groups[r['canonical_file_sha256']].append(r)
    audit=[]
    for sha,rs in groups.items():
        if len(rs)<2:continue
        dids=sorted({r['document_id'] for r in rs});ds=[d for d in docs if d.id in dids]
        same=len(dids)==1;common=len({(d.ente,d.codice) for d in ds})==1 and bool(ds[0].codice)
        kind='same_identity_duplicate' if same else 'common_form' if common else 'shared_attachment' if len({d.ente for d in ds})==1 else 'ambiguous'
        audit.append(dict(sha256=sha,document_ids=dids,resource_bindings=len(rs),classification=kind,identity_decision='Explicit unique code and compatible entity required; otherwise conservative refusal.'))
    write(OUT+'shared_resource_audit.json',dict(groups=audit,counts=dict(Counter(r['classification'] for r in audit)),shared_bindings=sum(len(rs) for rs in groups.values() if len({r['document_id'] for r in rs})>1),unambiguous_canonical_files=len(records),exact_resource_bindings=len(read_bundle()['records']),scope='Classification derived from existing catalog metadata; shared bytes alone never establish identity.'))

def unknown():
    docs,families=catalog();rows=[];seen=set();five=[]
    from benchmarks.round6_recognition import cached_texts
    for name in ['official_documents_v2','official_holdout_v1','official_holdout_v2']:
        manifest,values=cached_texts(name)
        for c in manifest['cases']:
            if c['id'] in {'OH1-033','OH1-047','OH1-055','OH1-063','OH1-098'}:
                actual=recognize_catalog(values[c['id']].get('text',''),docs,families,file_sha256=c['sha256']);five.append(dict(id=c['id'],safe=actual.match_type=='NO_MATCH' or bool(actual.document and actual.document.id==c.get('document_id')),observed=actual.match_type))
            if c.get('expected_match_type')!='NO_MATCH' or c['sha256'] in seen:continue
            seen.add(c['sha256']);raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256']
            cc=dict(id=c['id'],group=c['sha256'],category='unknown_official',expected=dict(match_type='NO_MATCH'),label_status='historical_only',representation='official_original',provenance=dict(canonical_sha256=c['sha256'],url=c['url']))
            rows.append(case_result(cc,raw,c['id']+'.'+c['format'],docs,families))
    save('unknown_v4',rows,additional_fresh_unknown=0,confirmed_release_cases=0,release_gate_status='unmeasured_confirmed_unknown',scope='137 historical official unknowns, also seen in development calibration. All historical expectations retained. No independent or officially reconciled unknown set available; historical rejection is reported separately and cannot establish confirmed main-gate precision.')
    write(OUT+'historical_five.json',dict(cases=five,passed=len(five)==5 and all(c['safe'] for c in five)))

def family():
    from benchmarks.round5_recognition import family_label,split_identities
    docs,families=catalog();records=active_records();by={r['document_id']:r for r in records};audit=[];rows=[]
    for f in families:
        ids=[d.id for d in docs if d.stato_verifica not in ['demo','rifiutato'] and family_label(d)==f.id];usable=[dict(document_id=i,sha256=by[i]['canonical_file_sha256']) for i in ids if i in by];development,held=split_identities(usable);evaluable=len(development)>=2 and len(held)>=3
        audit.append(dict(family_id=f.id,real_identities=len(ids),usable=len(usable),development_identities=[r['document_id'] for r in development],holdout_identities=[r['document_id'] for r in held],evaluable=evaluable))
        for item in held:
            r=by[item['document_id']];ex=extract_document(raw_record(r),'family'+('.pdf' if r['mime_type']=='application/pdf' else '.docx'));actual=recognize_document_family(ex.text,families,known_entities=[d.ente for d in docs]);model=CatalogRecognitionResult('FAMILY_MATCH' if actual.recognized else 'NO_MATCH',0,actual.confidence,family=actual.family)
            cc=dict(id='FH8-'+str(item['document_id']),group='document:'+str(item['document_id']),category='family_holdout',expected=dict(match_type='FAMILY_MATCH',family_id=f.id));row=evaluate_case(cc,model);row.update(label_status='confirmed',family_evaluable=evaluable,representation='official_original');rows.append(row)
    evaluated=[r for r in rows if r['family_evaluable']];count=sum(a['evaluable'] for a in audit)
    save('family_release',evaluated,audit=audit,families_total=len(families),families_evaluable=count,exploratory_cases=rows,capability_status='insufficiently_validated' if count<5 else 'evaluated',useful_recall_gate='exact_document_recall' if count<5 else 'validated_family_plus_exact',false_accepts=sum(not r['family_correct'] and r['observed']['match_type']=='FAMILY_MATCH' for r in evaluated),scope='Existing identity/family labels only; no exact fingerprint channel in isolated family recognition. Retrospective split, exploratory cases excluded when insufficient support.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['historical','canonical','unknown','family']);a=p.parse_args();checked();globals()[a.mode]()
