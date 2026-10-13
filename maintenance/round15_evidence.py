"""Official-only truth evidence acquisition; no recognition or catalog writes."""
import argparse,hashlib
from dataclasses import asdict
from pathlib import Path
from lxml import html
import pymupdf
from maintenance.fetch import Fetcher
from maintenance.build_fingerprints import receipts
from benchmarks.round3_audit import catalog
from benchmarks.transactional_writer import atomic_json
from scripts.round14_common import ROOT,read,now

def main():
    p=argparse.ArgumentParser();p.add_argument('--allow-network',action='store_true');a=p.parse_args()
    f=Fetcher(ROOT/'benchmarks/cache',allow_network=a.allow_network,use_cache=True);receipts(f)
    docs,_=catalog();by={d.id:d for d in docs};m=read('benchmarks/manifests/official_unknown_release_v2.json')
    critical=[c for c in m['cases'] if c['case_id'] in ['U14-5f0c017c3d56e6c5','U14-c1fc4765c01dcd62','U14-d6e51fa8e7f88431']]
    pages={by[1147].detail_url:'inail',by[615].detail_url:'anac'}
    pages.update({c['audit_evidence']['source_evidence']['listing_url']:c['source'] for c in critical})
    listings=[]
    for url,source in pages.items():
        try:
            r=f.fetch(url,source);raw=f.read(r);t=html.fromstring(raw)
            links=[dict(label=' '.join(n.text_content().split()),href=n.get('href')) for n in t.xpath('//a[@href]') if any(x in (n.text_content()+n.get('href','')).lower() for x in ['allegato 4','allegato 5','allegato 8','a.7','consultazione','regolamento'])]
            listings.append(dict(url=url,receipt=asdict(r),links=links,inspected_at=now()))
        except (ValueError,OSError) as e:listings.append(dict(url=url,error=str(e),inspected_at=now()))
    bundle=read('data/document_recognition_fingerprints_v3.json');files=[]
    for c in critical:
        r=c['receipt'];raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==c['SHA256']==r['sha256']
        with pymupdf.open(stream=raw,filetype='pdf') as pdf:
            files.append(dict(case_id=c['case_id'],receipt=r,pages=len(pdf),opening=pdf[0].get_text()[:2000],page_text_sha256=[__import__('hashlib').sha256(p.get_text().encode()).hexdigest() for p in pdf],inspected_at=now()))
    for did in [615,1147]:
        record=next(r for r in bundle['records'] if r['document_id']==did)
        h=record['canonical_file_sha256'];raw=(ROOT/'benchmarks/cache'/(h+'.body')).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==h
        opening=None
        if raw.startswith(b'%PDF'):
            with pymupdf.open(stream=raw,filetype='pdf') as pdf:opening=pdf[0].get_text()[:2000]
        files.append(dict(document_id=did,official_url=record['url'],catalog_download_url=by[did].download_url,canonical_sha256=h,opening=opening,record_pages=record['pages'],catalog=asdict(by[did]),inspected_at=now()))
    atomic_json(ROOT/'benchmarks/results/round15/official_truth_evidence.json',dict(schema_version=1,created_at=now(),recognition_calls=0,allow_network=a.allow_network,network_requests=f.requests,listings=listings,files=files,policy='Only institutional receipts and literal official content. Cached dates retained; inspection is not a new download or verification event. No retry of ANAC403; cached HTTP200 evidence is used.'))
    print('Official truth evidence saved',len(listings),len(files),flush=True)

if __name__=='__main__':main()
