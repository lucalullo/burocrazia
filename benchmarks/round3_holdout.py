"""Acquire after runtime freeze; evaluate once, without feedback into rules."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
from datetime import UTC,datetime
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from benchmarks.round3_audit import ROOT,read,write,catalog
from benchmarks.holdout_leakage import check,collision
from benchmarks.evaluate import summary,bootstrap,code_hash
from maintenance.fetch import Fetcher
from maintenance.iri import iri_to_uri
from src.extract import extract_document,ExtractionError
from src.recognize import recognize_catalog,RULES_VERSION,catalog_revision
from src.text_quality import text_quality
from scripts.benchmark import evaluate_case

MANIFEST='benchmarks/manifests/official_holdout_v1.json'
RESULT='benchmarks/results/round3/official_holdout_v1.json'
FREEZE='benchmarks/results/round3/engine_freeze.json'

def runtime_hash():
    files=sorted([*ROOT.glob('src/**/*.py'),ROOT/'app.py',ROOT/'run.py',ROOT/'data/recognition_features.json'])
    return hashlib.sha256(b''.join(p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes()+b'\0' for p in files)).hexdigest()

def development():
    docs,_=catalog();by_id={d.id:d for d in docs};items=[]
    for filename in ['official_documents_v1.json','official_documents_v2.json']:
        for c in read('benchmarks/manifests/'+filename)['cases']:
            d=by_id.get(c.get('document_id'));c=dict(c)
            if d:c.update(code=d.codice,title=d.titolo_ufficiale,entity=d.ente)
            items.append(c)
    return items

def plan():
    docs,_=catalog();sources=read('maintenance/sources.json');keys={s['ente']:s['key'] for s in sources};dev=development()
    resources=defaultdict(list)
    for item in read('maintenance/releases/2026-10-11/resource_observations.json'):
        for r in item['observation'].get('resources',[]):resources[item.get('document_id')].append(r['url'])
    options=defaultdict(list);seen=set();excluded=[]
    for d in docs:
        if d.stato_verifica in {'demo','rifiutato'} or d.ente not in keys:continue
        candidates=[d.download_url,*resources[d.id]]
        candidates=[u for u in candidates if u and (re.search(r'\.(?:pdf|docx)(?:\W|$)',u,re.I) or 'garante/document?' in u)]
        for url in sorted(set(candidates),key=lambda u:hashlib.sha256(u.encode()).hexdigest()):
            if url in seen:continue
            seen.add(url);c=dict(id='plan-'+str(d.id),document_id=d.id,entity=d.ente,source_key=keys[d.ente],url=url,title=d.titolo_ufficiale,code=d.codice,version=d.versione,expected_match_type='DOCUMENT_MATCH')
            overlap=next((collision(c,x) for x in dev if collision(c,x)),None)
            if overlap:excluded.append(dict(document_id=d.id,url=url,reason=overlap));continue
            options[keys[d.ente]].append(c)
    for values in options.values():values.sort(key=lambda c:hashlib.sha256(c['url'].encode()).hexdigest())
    positives=[]
    while options:
        for key in sorted(list(options)):
            if options[key]:positives.append(options[key].pop(0))
            else:del options[key]
    negatives=[]
    for source in read('docs/source_census.json')['sources']:
        for e in source['excluded']:
            if not re.search(r'\.(?:pdf|docx)(?:\W|$)',e['url'],re.I):continue
            if not re.match(r'^(?:guida|istruzioni|tutorial|manuale|decreto|direttiva|comunicato|faq|regolamento|circolare|provvedimento)\b',e['title'],re.I):continue
            c=dict(id='negative-plan-'+str(len(negatives)),entity=source['ente'],source_key=source['source_key'],url=e['url'],title=e['title'],expected_match_type='NO_MATCH')
            if any(collision(c,x) for x in dev):continue
            negatives.append(c)
    negatives.sort(key=lambda c:hashlib.sha256(c['url'].encode()).hexdigest())
    result=dict(schema_version=1,selection='Metadata-only SHA order, round-robin by existing source; no extraction or recognition used for selection. Positive cap 37 per source, at most 150 positives; first 50 distinct official informational resources. No new catalog sources or identities.',positive_options=positives,negative_options=negatives,development_exclusions=excluded)
    write('benchmarks/results/round3/holdout_plan.json',result)
    print('Holdout plan:',Counter(c['source_key'] for c in positives),'negative options',len(negatives),flush=True)
    return result

def freeze():
    if (ROOT/FREEZE).exists():raise ValueError('Runtime already frozen; do not rewrite the freeze event.')
    write(FREEZE,dict(schema_version=1,runtime_sha256=runtime_hash(),catalog_sha256=hashlib.sha256((ROOT/'data/catalog_seed.sqlite3').read_bytes()).hexdigest(),frozen_at=datetime.now(UTC).isoformat(),commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),policy='No runtime, feature or catalog changes after first holdout evaluation. Report generators and packaging may change without affecting the runtime hash.'))
    print('Runtime frozen',runtime_hash(),flush=True)

def require_freeze():
    event=read(FREEZE)
    assert event['runtime_sha256']==runtime_hash(),'Runtime differs from frozen engine'
    assert event['catalog_sha256']==hashlib.sha256((ROOT/'data/catalog_seed.sqlite3').read_bytes()).hexdigest()
    return event

def acquire(allow_network):
    event=require_freeze()
    if (ROOT/MANIFEST).exists():raise ValueError('Holdout manifest exists; never overwrite it.')
    choices=read('benchmarks/results/round3/holdout_plan.json');fetcher=Fetcher(ROOT/'benchmarks/cache',allow_network=allow_network,use_cache=True)
    cases=[];attempts=[];hashes={c.get('sha256') for c in development()};counts=Counter();used_ids=set();positive=negative=0
    for c in choices['positive_options']+choices['negative_options']:
        is_negative=c['expected_match_type']=='NO_MATCH'
        if is_negative and negative>=50:continue
        if not is_negative and (positive>=150 or counts[c['source_key']]>=37 or c['document_id'] in used_ids):continue
        if fetcher.requests>=385:break
        try:
            receipt=fetcher.fetch(c['url'],c['source_key']);raw=fetcher.read(receipt)
            fmt='pdf' if raw.startswith(b'%PDF-') else 'docx' if raw.startswith(b'PK') else None
            if not fmt:raise ValueError('Unsupported or non-document response; legacy DOC is not silently converted.')
            if receipt.sha256 in hashes:
                attempts.append(dict(url=c['url'],status='duplicate_or_development_hash',sha256=receipt.sha256));continue
            item=dict(c,id=f'OH1-{len(cases)+1:03}',format=fmt,sha256=receipt.sha256,acquired_at=receipt.acquired_at,cache_key=receipt.sha256+'.body',receipt=asdict(receipt),label_basis='Official catalog listing/resource identity; negative labels from explicit informational headings. Not recognition-derived.',reuse_conditions='Redistribution rights not established; ignored local cache only.')
            if any(collision(item,x) for x in development()):
                attempts.append(dict(url=c['url'],status='leakage_excluded'));continue
            if any(collision(item,x) for x in cases):
                attempts.append(dict(url=c['url'],status='holdout_identity_or_template_duplicate'));continue
            cases.append(item);hashes.add(receipt.sha256)
            if is_negative:negative+=1
            else:positive+=1;counts[c['source_key']]+=1;used_ids.add(c['document_id'])
            attempts.append(dict(url=c['url'],source_key=c['source_key'],status='downloaded',sha256=receipt.sha256))
        except (ValueError,OSError) as exc:attempts.append(dict(url=c['url'],source_key=c['source_key'],status='failed',reason=str(exc)))
        if len(attempts)%10==0:print('Holdout acquisition:',positive,negative,len(attempts),'attempts',flush=True)
        if positive>=150 and negative>=50:break
    manifest=dict(schema_version=3,corpus_id='official_holdout_v1',independent=True,freeze=event,created_at=datetime.now(UTC).isoformat(),selection=choices['selection'],cases=cases)
    write(MANIFEST,manifest)
    write('benchmarks/results/round3/holdout_acquisition.json',dict(positives=positive,negatives=negative,source_counts=dict(counts),attempts=attempts,complete_target=positive>=150 and negative>=50,manifest_sha256=hashlib.sha256((ROOT/MANIFEST).read_bytes()).hexdigest()))
    leakage=check(development(),cases);write('benchmarks/results/round3/holdout_leakage_check.json',leakage)
    assert leakage['passed']
    print('Holdout acquired:',positive,negative,dict(counts),flush=True)

def evaluate():
    event=require_freeze()
    if (ROOT/RESULT).exists():raise ValueError('First holdout evaluation is immutable. Start a new development cycle instead of rerunning it.')
    manifest=read(MANIFEST);leakage=check(development(),manifest['cases']);assert leakage['passed']
    # Reserve the first evaluation before reading any held-out text.
    with (ROOT/RESULT).open('x',encoding='utf-8') as f:json.dump(dict(status='running',runtime_sha256=runtime_hash()),f)
    fetcher=Fetcher(ROOT/'benchmarks/cache',use_cache=True);docs,families=catalog();rows=[];attempts=[]
    family_by_id={167:12,165:11}
    for c in manifest['cases']:
        expected=dict(match_type='NO_MATCH') if c['expected_match_type']=='NO_MATCH' else dict(match_type='DOCUMENT_MATCH',document_id=c['document_id'],entity=c['entity'],version=c.get('version'))
        if c.get('document_id') in family_by_id:expected['family_id']=family_by_id[c['document_id']]
        try:
            raw=fetcher.read(__import__('maintenance.fetch',fromlist=['Fetched']).Fetched(**c['receipt']))
            assert hashlib.sha256(raw).hexdigest()==c['sha256']
            begin=time.perf_counter();ex=extract_document(raw,c['id']+'.'+c['format']);elapsed=(time.perf_counter()-begin)*1000
            begin=time.perf_counter();result=recognize_catalog(ex.text,docs,families)
            row=evaluate_case(dict(id=c['id'],group='document:'+str(c.get('document_id',c['sha256'])),category='official_holdout',source=c['entity'],noise='original',expected=expected),result,(time.perf_counter()-begin)*1000)
            row.update(source_key=c['source_key'],file_type=c['format'],extraction_method=ex.method,extraction_ms=round(elapsed,3),quality=text_quality(ex.text),used_ocr=ex.used_ocr,page_count=ex.total_pages,extraction_warning=ex.warning,input_sha256=c['sha256'],stages=result.pipeline_stages)
            rows.append(row);attempts.append(dict(id=c['id'],status='extracted'))
        except (ValueError,OSError,ExtractionError) as exc:
            # Extraction failures remain false negatives/rejections in the denominator.
            observed=dict(match_type='NO_MATCH',document_id=None,family_id=None,entity=None,version=None)
            rows.append(dict(id=c['id'],group='document:'+str(c.get('document_id',c['id'])),expected=expected,observed=observed,correct=expected['match_type']=='NO_MATCH',document_correct=False,family_correct=False,entity_error=False,version_error=False,entity_labelled=False,version_labelled=False,matching_ms=0,source_key=c['source_key'],file_type=c['format'],extraction_failed=True))
            attempts.append(dict(id=c['id'],status='extraction_failed',reason=str(exc)))
    positives=[c for c in manifest['cases'] if c['expected_match_type']!='NO_MATCH'];negatives=[c for c in manifest['cases'] if c['expected_match_type']=='NO_MATCH'];counts=Counter(c['source_key'] for c in positives)
    report=dict(schema_version=3,status='executed',corpus_id='official_holdout_v1',independent=True,evaluated_at=datetime.now(UTC).isoformat(),freeze=event,identity=dict(runtime_sha256=runtime_hash(),code_sha256=code_hash(),manifest_sha256=hashlib.sha256((ROOT/MANIFEST).read_bytes()).hexdigest(),catalog_semantic_sha256=catalog_revision(docs,families)),cases=rows,attempts=attempts,summary=summary(rows),bootstrap_95=bootstrap(rows,2000),positive_n=len(positives),negative_n=len(negatives),sources=len(counts),issuers=len({c['entity'] for c in positives}),max_source_concentration=max(counts.values())/len(positives) if positives else None,extraction_success=sum(a['status']=='extracted' for a in attempts),wrong_accepted=sum(not r['correct'] and r['observed']['match_type']!='NO_MATCH' for r in rows),limits='Single first evaluation after runtime freeze. Metadata-based leakage grouping cannot prove all template independence. Listing labels are not a complete human editorial adjudication; acquisition/extraction shortfalls are explicit, never removed from evaluated denominators.')
    write(RESULT,report);print('FIRST holdout evaluation:',len(positives),len(negatives),'exact',sum(r['document_correct'] for r in rows),'family',sum(r['family_correct'] for r in rows),'wrong',report['wrong_accepted'],flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','freeze','acquire','evaluate']);p.add_argument('--allow-network',action='store_true');a=p.parse_args()
    if a.action=='plan':plan()
    elif a.action=='freeze':freeze()
    elif a.action=='acquire':acquire(a.allow_network)
    else:evaluate()

if __name__=='__main__':main()
