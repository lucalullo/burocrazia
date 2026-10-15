"""Append verified official resources, preserving all existing v3 records."""
import hashlib
from collections import Counter
from benchmarks.round3_audit import ROOT,read,catalog
from benchmarks.transactional_writer import atomic_json
from maintenance.build_fingerprints_v3 import atomic,resource_pages
from src.fingerprint_v3 import read_bundle,PATH,sketch
from src.document_fingerprints import binding
from src.extract import extract_document
from src.fingerprint_match_v2 import safety_reason
from src.recognize import normalize_text
from src.title_evidence import exact_code_candidates

def main():
 docs,_=catalog();by={d.id:d for d in docs};bundle=read_bundle();original=hashlib.sha256(PATH.read_bytes()).hexdigest();seen={(r['document_id'],r['canonical_file_sha256']) for r in bundle['records']};added=[];rejected=[]
 for c in read('benchmarks/manifests/official_fingerprint_cache_v6.json')['files']:
  key=(c['document_id'],c['sha256'])
  if key in seen:continue
  d=by[c['document_id']]
  try:
   raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256']
   text=extract_document(raw,'canonical.pdf' if c['mime']=='application/pdf' else 'canonical.docx').text
   title=normalize_text(d.titolo_ufficiale.split(' / ')[0]);opening=normalize_text(text[:2000]);reason=safety_reason(text,d,docs,exact=True)
   common=d.id==177 and 'modello semplificato cartello videosorveglianza' in opening and '/CARTELLO+' in c['url']
   strong=not reason and (d.id in exact_code_candidates(text,[d]) or len(title)>=20 and f' {title} ' in f' {opening} ')
   if not strong and not common:raise ValueError(reason or 'opening_identity_not_supported')
   if any(r['canonical_file_sha256']==c['sha256'] and r['document_id']!=d.id for r in bundle['records']):raise ValueError('new_cross_identity_binding_requires_separate_adjudication')
   rec=dict(document_id=d.id,source_id=d.source_id,catalog_binding_sha256=binding(d),canonical_file_sha256=c['sha256'],mime_type=c['mime'],url=c['url'],final_url=c['final_url'],acquisition_date=c['acquisition_date'],size_bytes=len(raw))
   data=resource_pages(rec)
   rec.update(generated_at=data['generated_at'],status='shared' if common else 'active',shared_kind='common_form' if common else 'unambiguous',pages=data['pages'],aggregate=sketch({int(h,16) for p in data['pages'] for k in ['digital','ocr'] for h in p[k]},192),field_set=data['field_set'],ocr_metadata=dict(status='unavailable_docx_renderer' if c['mime']!='application/pdf' else 'generated',scope='Official original bytes; existing extraction/fingerprint parameters unchanged.',resource_association='Published Garante standard cartello with variable controller/issuer; resource support only, no exact SHA identity.' if common else 'Explicit code/full catalog title and unchanged entity/version safety guard.'))
   bundle['records'].append(rec);seen.add(key);added.append(dict(document_id=d.id,sha256=c['sha256'],status=rec['status'],receipt=c['receipt'],association=rec['ocr_metadata']['resource_association']))
  except (ValueError,OSError,RuntimeError) as exc:rejected.append(dict(document_id=d.id,sha256=c['sha256'],reason=str(exc)))
 if added:atomic(bundle)
 atomic_json(ROOT/'benchmarks/results/round11/fingerprint_build.json',dict(original_bundle_sha256=original,bundle_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),added=added,rejected=rejected,original_records_preserved=1027,semantic_engine_changed=False,parameters_changed=False,scope='Additive official v3 data only; no derived legacy SHA masquerading as an official PDF. Shared common form177 cannot use active exact-SHA tier.'))
 print('R11 fingerprints added',[(r['document_id'],r['status']) for r in added],flush=True)

if __name__=='__main__':main()
