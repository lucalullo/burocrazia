"""Audit the fixed residual and derive legacy content without inventing identity.

No runtime bundle mutation. Derived candidates have a separate resource-level
manifest, never masquerade as official PDF bytes and do not inflate coverage.
"""
import csv,hashlib,re
from collections import defaultdict,Counter
from urllib.parse import unquote,urlsplit
from benchmarks.round3_audit import ROOT,catalog,read
from benchmarks.transactional_writer import atomic_json
from maintenance.legacy_convert import convert_official,converter_path
from maintenance.resolve_resources import sniff,SOURCES
from src.fingerprint_v3 import read_bundle,page_record,sketch
from src.fingerprint_match_v2 import safety_reason
from src.recognize import normalize_text
from src.title_evidence import exact_code_candidates

OUT=ROOT/'benchmarks/results/round10'

def main():
 docs,_=catalog();by={d.id:d for d in docs};bundle=read_bundle();active={r['document_id'] for r in bundle['records'] if r['status']=='active'}
 fixed={c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases'] if c['expected_resource_type']=='file_backed_document'}
 old={int(r['document_id']):r for r in csv.DictReader((ROOT/'benchmarks/results/round9/fingerprint_recovery_v2.csv').open(encoding='utf8'))}
 attempts=defaultdict(list);resources=defaultdict(dict)
 for round in [8,9]:
  for r in read(f'benchmarks/results/round{round}/recovery_attempts.json')['attempts']:
   attempts[r['document_id']].append(r)
   if r.get('sha256'):resources[r['document_id']][r['sha256']]=r
 for r in read('benchmarks/manifests/official_fingerprint_cache_v5.json')['files']:resources[r['document_id']][r['sha256']]=dict(r,url=r['url'])
 # Conversion and public content sketches are reused by official original SHA.
 conversions={};candidates=[];rows=[];work=ROOT/'benchmarks/work/round10-legacy';work.mkdir(parents=True,exist_ok=True)
 import pymupdf
 for did in sorted(fixed-active):
  d=by[did];previous=old[did];rs=resources[did];last=attempts[did][-1] if attempts[did] else {}
  row=dict(document_id=did,source=SOURCES[d.source_id],entity=d.ente,current_reason=previous['current_reason'],tier=4 if previous['current_reason']=='robots_or_policy_block' else 3 if previous['fingerprint_status']=='shared_resource_only' else 1,primary_url=d.download_url or d.detail_url or '',alternate_url=';'.join(sorted({r['url'] for r in rs.values() if r.get('url') and r['url']!=d.download_url})),resolver='existing official wrapper/multipart/redirect/IRI; bounded local legacy PDF derivation',previous_http_status=last.get('http_status',''),format='',planned_action='inspect cached alternatives and identity evidence',attempted=True,success=False,fingerprint_built=False,final_reason=previous['final_reason'])
  for sha,r in sorted(rs.items()):
   raw=(ROOT/'benchmarks/cache'/(sha+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
   mime=sniff(raw);path=unquote(urlsplit(r.get('url','')).path).lower();suffix=None
   if mime=='application/msword':suffix='.xls' if path.endswith('.xls') else '.doc'
   elif raw.lstrip().startswith(b'{\\rtf'):suffix='.rtf'
   elif mime=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':suffix='.xlsx'
   elif mime=='application/zip' and path.endswith('.odt'):suffix='.odt'
   if not suffix:continue
   row.update(tier=2,format=suffix,planned_action='preflight active/external content, isolated local conversion, original/derived SHA, opening identity guard')
   if sha not in conversions:
    try:
     pdf,meta=convert_official(raw,suffix,work);derived=work/(meta['derived_sha256']+'.pdf');derived.write_bytes(pdf)
     with pymupdf.open(stream=pdf,filetype='pdf') as doc:
      texts=[p.get_text() for p in doc];pages=[page_record(i+1,t,'',(),ocr_status='unavailable_docx_renderer') for i,t in enumerate(texts)]
      for page in pages:page['ocr_status']='not_requested_maintenance_digital_only'
     conversions[sha]=dict(success=True,**meta,pages_sketches=pages)
    except (ValueError,OSError,RuntimeError) as exc:conversions[sha]=dict(original_sha256=sha,original_format=suffix,success=False,reason=str(exc))
   result=conversions[sha]
   if not result['success']:row['final_reason']=result['reason'];continue
   with pymupdf.open(work/(result['derived_sha256']+'.pdf')) as doc:text='\n'.join(p.get_text() for p in doc)
   title=normalize_text(d.titolo_ufficiale.split(' / ')[0]);opening=normalize_text(text[:2000]);reason=safety_reason(text,d,docs,exact=True)
   supported=not reason and (d.id in exact_code_candidates(text,[d]) or len(title)>=20 and f' {title} ' in f' {opening} ')
   candidates.append(dict(document_id=did,source_id=d.source_id,official_url=r.get('url',d.download_url),original_sha256=sha,derived_sha256=result['derived_sha256'],identity_supported=bool(supported),identity_reason=reason or ('opening_title_or_code_supported' if supported else 'opening_identity_not_supported'),shared_resource=sum(sha in values for values in resources.values())>1,resource_fingerprint=bool(result['pages_sketches']),provenance='Official legacy source -> ignored temporary PDF -> public content sketches; not an official PDF or active runtime binding.'))
   row.update(success=True,final_reason=reason or ('derived_only_original_mime_not_supported_by_v3' if supported else 'opening_identity_not_supported'))
  rows.append(row)
  if len(rows)%20==0:print('Recovery residual',len(rows),'converted',sum(r['success'] for r in conversions.values()),flush=True)
 assert len(rows)==217 and len(active&fixed)==941
 with (OUT/'fingerprint_recovery_plan.csv').open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(sorted(rows,key=lambda r:(r['tier'],r['document_id'])))
 atomic_json(OUT/'legacy_resource_fingerprints.json',dict(schema_version=1,resources=list(conversions.values()),bindings=candidates,converter_available=bool(converter_path()),scope='Maintenance derivation audit only; public content sketches, no text or pixels. No runtime binding/count promotion without official/derived provenance support and unambiguous opening identity. Native DOC/RTF/XLS/XLSX/ODT uploads remain unsupported.'))
 supported={c['document_id'] for c in candidates if c['identity_supported'] and not c['shared_resource']}
 atomic_json(OUT/'fingerprint_coverage.json',dict(operational=1212,file_backed=1158,fingerprinted=941,coverage_all=941/1212,coverage_file_backed=941/1158,recovered=0,residual_audited=len(rows),derived_unique_identity_candidates=len(supported),derived_resource_count=sum(r['success'] for r in conversions.values()),derived_fingerprints_active=0,remaining_reasons=dict(Counter(r['final_reason'] for r in rows)),tiers=dict(Counter(str(r['tier']) for r in rows)),scope='Fixed R6 denominator. Derived resource sketches and shared bindings excluded from active unambiguous coverage. No scoring/policy or catalog mutation.'))
 print('Derived unique supported candidates',len(supported),'active recovery 0',flush=True)

if __name__=='__main__':main()
