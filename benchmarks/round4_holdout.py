"""Fresh holdout v2 protocol. Network acquisition lives in maintenance only."""
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC,datetime
import hashlib
import json
import subprocess
import time
from benchmarks.round4_common import ROOT,OUT,read,write,catalog,runtime_hash
from benchmarks.round3_holdout import development,plan as old_plan
from benchmarks.holdout_leakage import check,collision
from benchmarks.evaluate import summary,bootstrap,code_hash
from maintenance.fetch import Fetcher,Fetched
from src.extract import extract_document,ExtractionError
from src.recognize import recognize_catalog,catalog_revision
from src.text_quality import text_quality
from scripts.benchmark import evaluate_case

MANIFEST='benchmarks/manifests/official_holdout_v2.json'
RESULT=OUT+'official_holdout_v2.json'
FREEZE=OUT+'engine_freeze.json'

def previous():
    docs,_=catalog();by_id={d.id:d for d in docs};prior=development()
    for c in read('benchmarks/manifests/official_holdout_v1.json')['cases']:
        d=by_id.get(c.get('document_id'));c=dict(c)
        if d:c.update(entity=d.ente,code=d.codice,title=d.titolo_ufficiale,version=d.versione)
        prior.append(c)
    return prior

def plan():
    # Round 3 metadata plan is historical and never regenerated/overwritten.
    choices=read('benchmarks/results/round3/holdout_plan.json');prior=previous();excluded=[];options=defaultdict(list)
    for c in choices['positive_options']:
        overlap=next((collision(c,p) for p in prior if collision(c,p)),None)
        if overlap:excluded.append(dict(url=c['url'],reason=overlap));continue
        options[c['source_key']].append(c)
    positives=[]
    while options:
        for key in sorted(list(options)):
            if options[key]:positives.append(options[key].pop(0))
            else:del options[key]
    negatives=[c for c in choices['negative_options'] if not any(collision(c,p) for p in prior)]
    value=dict(schema_version=1,selection='Frozen metadata-only SHA ordering and source round-robin; no extracted text or recognition in selection. 75 negative resources reserved first; target 200 positives, cap 40 per source. Prior development and historical v1 excluded by identity/template/URL/hash. At most 400 network requests, stop a source after 3 non-document responses. No bypass or new catalog identities.',positive_options=positives,negative_options=negatives,excluded=excluded,positive_counts=dict(Counter(c['source_key'] for c in positives)),targets=dict(positive=200,negative=75,sources=8,issuers=8,max_concentration=.2))
    write(OUT+'holdout_v2_plan.json',value);print('Fresh options',value['positive_counts'],'negative',len(negatives),flush=True)

def freeze():
    if (ROOT/FREEZE).exists():raise ValueError('Freeze event already exists.')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('Commit completed engine and tests before freezing.')
    event=dict(schema_version=1,runtime_sha256=runtime_hash(),catalog_sha256=hashlib.sha256((ROOT/'data/catalog_seed.sqlite3').read_bytes()).hexdigest(),frozen_at=datetime.now(UTC).isoformat(),commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),policy='Exactly one v2 evaluation after this committed freeze. No runtime, catalog or feature edits after results. A failure stays NOT_READY; next cycle needs v3.')
    write(FREEZE,event);print('Frozen',event,flush=True)

def require_freeze():
    event=read(FREEZE)
    assert event['runtime_sha256']==runtime_hash(),'Frozen runtime changed'
    assert event['catalog_sha256']==hashlib.sha256((ROOT/'data/catalog_seed.sqlite3').read_bytes()).hexdigest()
    return event

def leakage_report(cases):
    result=check(previous(),cases)
    result.update(corpus_id='official_holdout_v2',prior_corpora=['official_documents_v1','official_documents_v2','official_holdout_v1_historical'],source_overlap='Same official sources permitted and reported; file/identity/code/annual/territorial templates prohibited.',structural_similarity='Metadata near-template grouping and byte hash checked; content/layout independence not fully established. No unsupported proof of structural independence.',related_acceptable=[dict(source=s,reason='Same institution, distinct identity/title/template') for s in sorted({c['source_key'] for c in cases})])
    return result

def evaluate():
    event=require_freeze();manifest=read(MANIFEST);leakage=leakage_report(manifest['cases']);write(OUT+'holdout_v2_leakage.json',leakage);assert leakage['passed']
    if (ROOT/RESULT).exists():raise ValueError('v2 first evaluation already reserved; no rerun allowed.')
    with (ROOT/RESULT).open('x',encoding='utf-8') as f:json.dump(dict(status='running',runtime_sha256=runtime_hash()),f)
    fetcher=Fetcher(ROOT/'benchmarks/cache',use_cache=True);docs,families=catalog();rows=[];attempts=[]
    family_by_id={143:10,167:12,165:11}
    for c in manifest['cases']:
        expected=dict(match_type='NO_MATCH') if c['expected_match_type']=='NO_MATCH' else dict(match_type='DOCUMENT_MATCH',document_id=c['document_id'],entity=c['entity'],version=c.get('version'))
        if c.get('document_id') in family_by_id:expected['family_id']=family_by_id[c['document_id']]
        try:
            raw=fetcher.read(Fetched(**c['receipt']));assert hashlib.sha256(raw).hexdigest()==c['sha256']
            start=time.perf_counter();ex=extract_document(raw,c['id']+'.'+c['format']);exms=(time.perf_counter()-start)*1000
            start=time.perf_counter();result=recognize_catalog(ex.text,docs,families)
            row=evaluate_case(dict(id=c['id'],group='document:'+str(c.get('document_id',c['sha256'])),category='official_holdout_v2',expected=expected),result,(time.perf_counter()-start)*1000)
            row.update(extraction_ms=exms,extraction_method=ex.method,used_ocr=ex.used_ocr,page_count=ex.total_pages,quality=text_quality(ex.text),extraction_warning=ex.warning)
            attempts.append(dict(id=c['id'],status='extracted'))
        except (ValueError,OSError,ExtractionError) as exc:
            row=evaluate_case(dict(id=c['id'],group='document:'+str(c.get('document_id',c['sha256'])),category='official_holdout_v2',expected=expected),recognize_catalog('',docs,families))
            row['extraction_failed']=True;attempts.append(dict(id=c['id'],status='extraction_failed',reason=str(exc)))
        row.update(source_key=c['source_key'],file_type=c['format'],input_sha256=c['sha256']);rows.append(row)
        if len(rows)%25==0:print('First evaluation',len(rows),'/',len(manifest['cases']),flush=True)
    positives=[c for c in manifest['cases'] if c['expected_match_type']!='NO_MATCH'];negatives=[c for c in manifest['cases'] if c['expected_match_type']=='NO_MATCH'];counts=Counter(c['source_key'] for c in positives);extracted=[r for r in rows if not r.get('extraction_failed')]
    report=dict(schema_version=1,status='executed',corpus_id='official_holdout_v2',independent=True,evaluated_at=datetime.now(UTC).isoformat(),freeze=event,identity=dict(runtime_sha256=runtime_hash(),code_sha256=code_hash(),manifest_sha256=hashlib.sha256((ROOT/MANIFEST).read_bytes()).hexdigest(),catalog_semantic_sha256=catalog_revision(docs,families)),cases=rows,attempts=attempts,summary=summary(rows),bootstrap_95=bootstrap(rows,10000),positive_n=len(positives),negative_n=len(negatives),sources=len(counts),issuers=len({c['entity'] for c in positives}),source_counts=dict(counts),max_source_concentration=max(counts.values())/len(positives) if positives else None,extraction=dict(success=len(extracted),total=len(rows),conditional_matching=summary(extracted),end_to_end=summary(rows)),wrong_accepted=sum(not r['correct'] and r['observed']['match_type']!='NO_MATCH' for r in rows),composition=dict(formats=dict(Counter(c['format'] for c in positives)),coded=sum(bool(c.get('code')) for c in positives),annual=sum(bool(c.get('version')) for c in positives),scanned=sum(r.get('used_ocr',False) for r in rows),title_limits='Metadata descriptive/generic classes not independently human adjudicated.'),limits='Single evaluation after committed freeze. Acquisition shortfalls remain explicit. Extraction failures remain in end-to-end denominators. Metadata leakage checks do not prove all structural independence; official listing labels are not human editorial validation.')
    write(RESULT,report)
    locks={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [MANIFEST,RESULT,OUT+'holdout_v2_leakage.json',FREEZE]}
    write('benchmarks/manifests/official_holdout_locks_v2.json',dict(sha256=locks,policy='Immutable first v2 evaluation. If release gates fail, historical in Round 5; use fresh v3.'))
    print('v2 first result:',len(positives),len(negatives),report['summary'],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','freeze','evaluate']);a=p.parse_args()
    globals()[a.action]()
