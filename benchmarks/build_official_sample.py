"""Acquire a stratified official sample, separately from catalog maintenance."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import unquote
from maintenance.fetch import Fetcher, AcquisitionError
from maintenance.policy import validate_url

ROOT=Path(__file__).resolve().parents[1]

def file_format(url):
    path=unquote(url).lower()
    if '.docx' in path:return 'docx'
    if '.pdf' in path:return 'pdf'
    return None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--allow-network',action='store_true');p.add_argument('--target',type=int,default=150);a=p.parse_args()
    if not 100<=a.target<=180:raise ValueError('Target must be 100..180')
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;docs={d['id']:dict(d) for d in db.execute("SELECT * FROM documents WHERE stato_verifica NOT IN ('demo','rifiutato')")}
    sources=json.loads((ROOT/'maintenance/sources.json').read_text(encoding='utf-8'));keys={s['ente']:s['key'] for s in sources}
    observations=json.loads((ROOT/'maintenance/releases/2026-10-11/resource_observations.json').read_text(encoding='utf-8'))
    choices=defaultdict(list);seen=set()
    for d in docs.values():
        url=d['download_url'];key=keys.get(d['ente'])
        if not key or not url or not file_format(url):continue
        if url in seen:continue
        seen.add(url)
        choices[key].append(dict(url=url,source_key=key,entity=d['ente'],document_id=d['id'],version=d['versione'],title=d['titolo_ufficiale'],format=file_format(url),expected_match_type='DOCUMENT_MATCH',label_basis='Official listing-to-resource identity, not manually validated file contents'))
    # Sort within strata by a stable hash, not recognizer success or convenient IDs.
    for key in choices:choices[key].sort(key=lambda d:hashlib.sha256(d['url'].encode()).hexdigest())
    plan=[]
    while choices and len(plan)<a.target*2:
        for key in sorted(list(choices)):
            if choices[key]:plan.append(choices[key].pop(0))
            else:del choices[key]
    census=json.loads((ROOT/'docs/source_census.json').read_text(encoding='utf-8'))
    negatives=[]
    for s in census['sources']:
        for e in s['excluded']:
            if not file_format(e['url']) or e['url'] in seen:continue
            # Avoid assuming that every excluded attachment is a negative form.
            if not re.match(r'^(?:guida|istruzioni|tutorial|manuale|decreto|direttiva|comunicato|tabella)\b',e['title'],re.I):continue
            try:validate_url(e['url'],s['source_key'])
            except ValueError:continue
            seen.add(e['url']);negatives.append(dict(url=e['url'],source_key=s['source_key'],entity=s['ente'],title=e['title'],format=file_format(e['url']),expected_match_type='NO_MATCH',label_basis='Official informational/regulatory resource explicitly excluded from form catalog',exclusion=e))
    # Negative resources are reviewed by explicit informational headings.
    selected=[];ncounts=Counter()
    for item in negatives:
        if ncounts[item['source_key']]<6:selected.append(item);ncounts[item['source_key']]+=1
    fetcher=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True)
    cases=[];attempts=[];hashes=set();counts=Counter();positive=negative=0
    for item in selected+plan:
        is_negative=item['expected_match_type']=='NO_MATCH'
        if is_negative and negative>=12:continue
        if not is_negative and (positive>=a.target or counts[item['source_key']]>=int(a.target*.30)):continue
        try:
            receipt=fetcher.fetch(item['url'],item['source_key']);raw=fetcher.read(receipt)
            if not (raw.startswith(b'%PDF-') if item['format']=='pdf' else raw.startswith(b'PK')):raise ValueError('Resource is not the declared file format')
            if receipt.sha256 in hashes:
                attempts.append(dict(url=item['url'],source_key=item['source_key'],status='duplicate_content',sha256=receipt.sha256));continue
            hashes.add(receipt.sha256);positive+=not is_negative;negative+=is_negative;counts[item['source_key']]+=not is_negative
            case=dict(item,id=f'OR2-{len(cases)+1:03}',sha256=receipt.sha256,acquired_at=receipt.acquired_at,cache_key=receipt.sha256+'.body',receipt=asdict(receipt),reuse_conditions='Redistribution rights not established; file kept only in ignored local cache.')
            cases.append(case);attempts.append(dict(url=item['url'],source_key=item['source_key'],status='downloaded',sha256=receipt.sha256))
        except (ValueError,OSError) as exc:
            attempts.append(dict(url=item['url'],source_key=item['source_key'],status='failed',reason=str(exc)))
        if positive>=a.target and negative>=10:break
        if len(attempts)%10==0:print('official acquisition',positive,'positive',negative,'negative',len(attempts),'attempts',flush=True)
    manifest=dict(schema_version=2,corpus_id='official-local-v2',synthetic=False,executed_at=datetime.now(UTC).isoformat(),selection='Deterministic SHA-256 order within issuer strata, round-robin; max 30% positives per source. Labels derived from official listing, not adjusted to recognition. No file content redistributed.',cases=cases)
    target=ROOT/'benchmarks/manifests/official_documents_v2.json';target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report=dict(schema_version=1,target_positives=a.target,downloaded_positives=positive,downloaded_negatives=negative,source_counts=dict(counts),source_concentration=max(counts.values())/positive if positive else None,attempts=attempts,manifest_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    (ROOT/'benchmarks/results/round2/official_acquisition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('official final',positive,negative,dict(counts),flush=True)

if __name__=='__main__':main()
