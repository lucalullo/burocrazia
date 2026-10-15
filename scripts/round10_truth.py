"""Offline unknown v2 audit, never labels from recognition outcomes."""
import csv,hashlib,json,re,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import catalog,read
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_v2 import validate
from src.extract import extract_document
from src.fingerprint_v3 import read_bundle,public_index,features
from src.recognize import normalize_text
from src.title_evidence import exact_code_candidates
from scripts.round9_truth import words
OUT=ROOT/'benchmarks/results/round10'
TYPES=['circolare','decreto','direttiva','regolamento','manuale','istruzioni','guida','provvedimento','delibera','modulo','domanda','richiesta']

def document_metadata(opening):
 """A cited statute year is not a document year or revision."""
 header=opening[:800]
 codes=re.findall(r'\b(?:circolare|delibera|decreto|modulo|modello)\s+n[.°]?\s*([A-Z]{0,5}[- /]?\d{1,8}(?:[./-]\d{1,8})*)',header,re.I)
 codes+=re.findall(r'\bprot(?:ocollo)?[.]?\s*(?:n[.]?\s*)?(\d{1,8}(?:[./-]\d{1,8})*)',header,re.I)
 versions=re.findall(r'\b(?:versione|version|rev(?:isione)?[.]?)\s*[: ]\s*(\d+(?:[.]\d+)*)',header,re.I)
 years=re.findall(r'\b(?:edizione|anno)\s*[: ]\s*((?:19|20)\d{2})\b',header,re.I)
 return ';'.join(sorted(set(codes))),';'.join(sorted(set(versions+years)))

def main():
 docs,families=catalog();ix=public_index();official_hashes={r['canonical_file_sha256'] for r in read_bundle()['records']}
 titles=[(d.id,normalize_text(d.titolo_ufficiale.split(' / ')[0])) for d in docs if d.stato_verifica not in ['demo','rifiutato']]
 confirmed=[];rows=[];headings=[];seen=set()
 for c in read('benchmarks/manifests/official_unknown_v1.json')['cases']:
  confirmed.append(dict(case_id=c['case_id'],source=c['source_key'],entity=c['entity'],title=c['title'],official_url=c['url'],acquisition_date=c['evidence_date'],SHA256=c['sha256'],mime='application/pdf' if c['format']=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',classification_reason='Preserved Round9 confirmed truth; all Round9 observations are development, including the old nominal evaluation split.',reference_truth_status='confirmed_unknown',expected_result='NO_MATCH',receipt=c['receipt'],audit_evidence=c['audit_evidence'],split='unknown_dev',historically_seen=True,code=c['code'],version=c['version'],document_type=c['document_type']))
  seen.add(c['sha256'])
  opening=json.loads((ROOT/'tmp-build/round9-truth-text'/(c['sha256']+'.json')).read_bytes())['opening']
  item=confirmed[-1];item['prior_lexical_code']=item['code'];item['prior_version_observation']=item['version'];item['code'],item['version']=document_metadata(opening)
 for i,c in enumerate(read('benchmarks/results/round10/unknown_candidates.json')['candidates']):
  sha=c['sha256']
  if sha in seen:continue
  seen.add(sha);opening='';error='';top=None;title=c['title'];kind=None;matches=[];fam=[];codes=[]
  raw=(ROOT/'benchmarks/cache'/(sha+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
  try:
   cache=ROOT/'tmp-build/round10-truth-text'/(sha+'.json')
   if cache.exists():opening=json.loads(cache.read_bytes())['opening']
   else:
    opening=extract_document(raw,'unknown.'+c['format']).text[:2000];atomic_json(cache,dict(sha256=sha,opening=opening,scope='Official source bytes only; ignored audit cache, never imported by runtime.'))
   normal=normalize_text(opening)
   matches=[did for did,t in titles if len(t)>=20 and f' {t} ' in f' {normal} ']
   codes=list(exact_code_candidates(opening,docs))
   scores=ix.similarities([features(opening)],n='3');top=scores[0] if scores else None
   for f in families:
    if any(len(normalize_text(a))>=12 and f' {normalize_text(a)} ' in f' {normal} ' for a in [*f.identifying_phrases,f.nome]):fam.append(f.id)
   nt=normalize_text(title)
   kinds=[t for t in TYPES if t in normal.split() and t in nt.split()]
   if 'linee guida' in normal and 'linee guida' in nt:kinds=['guida']
   kind=kinds[0] if kinds else None
  except (ValueError,OSError,RuntimeError) as exc:error=type(exc).__name__+': '+str(exc)
  tw=words(title);overlap=tw&words(opening);support=len(overlap)/max(1,len(tw))
  near=bool(matches or codes or top and top['score']>=.85 and top['digital']>=.8 and top['chars']>=.8)
  state='duplicate_of_catalog' if sha in official_hashes else 'possible_document_match' if near else 'possible_family_match' if fam else 'unsupported_truth' if error else 'confirmed_unknown' if kind and support>=.55 and len(overlap)>=3 else 'ambiguous'
  receipt=c['receipt']
  evidence=dict(official_sha256=sha,opening_sha256=hashlib.sha256(opening.encode()).hexdigest(),title_token_support=support,title_tokens_supported=len(overlap),catalog_title_hits=matches,catalog_code_hits=codes,family_hits=fam,nearest_catalog_id=top['document_id'] if top else None,nearest_content_score=top['score'] if top else None,nearest_digital=top['digital'] if top else None,nearest_chars=top['chars'] if top else None,document_type=kind,criteria='Actual official receipt and positively supported document-type/title in first2000 chars; complete catalog title/code and family scan; exact SHA and public content near duplicate excluded. No recognition predictions used.')
  code,years=document_metadata(opening)
  rows.append(dict(case_id='U10-'+sha[:16],source=c['source_key'],entity=c['entity'],title=title,official_url=c['url'],sha256=sha,classification=state,code=code,version_year=years,extraction_error=error,evidence=json.dumps(evidence,ensure_ascii=False)))
  headings.append(f"{rows[-1]['case_id']} | {state} | {c['source_key']} | {title}\n{opening[:1000]}\n\n")
  if state=='confirmed_unknown':
   confirmed.append(dict(case_id=rows[-1]['case_id'],source=c['source_key'],entity=c['entity'],title=title,official_url=c['url'],acquisition_date=receipt['acquired_at'],SHA256=sha,mime='application/pdf' if c['format']=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',classification_reason=evidence['criteria'],reference_truth_status=state,expected_result='NO_MATCH',receipt=receipt,audit_evidence=evidence,split='unknown_eval' if int(sha[:8],16)%5 else 'unknown_dev',historically_seen=False,code=code,version=years,document_type=kind))
  if (i+1)%20==0:print('Truth audit',i+1,'confirmed total',len(confirmed),flush=True)
 with (OUT/'unknown_truth_audit.csv').open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 (ROOT/'tmp-build/round10-unknown-headings.txt').write_bytes(''.join(headings).encode())
 manifest=dict(schema_version=2,manifest_id='official-unknown-v2',cases=confirmed,classification_counts=dict(Counter(r['classification'] for r in rows)),preserved_round9_count=68,scope='All R9 cases retained as historically seen development. New SHA deterministic80/20 evaluation/development assignment after truth adjudication; evaluation not recognized before freeze. Resources disjoint by exact SHA; semantic/near overlaps separately audited.')
 validate(manifest);atomic_json(ROOT/'benchmarks/manifests/official_unknown_v2.json',manifest)
 counts=Counter(c['source'] for c in confirmed);n=len(confirmed)
 atomic_json(OUT/'unknown_balance.json',dict(total_confirmed=n,sources=len(counts),entities=len({c['entity'] for c in confirmed}),counts_per_source=dict(counts),max_concentration=max(counts.values())/n,document_types=dict(Counter(c['document_type'] for c in confirmed)),with_code=sum(bool(c['code']) for c in confirmed),without_code=sum(not c['code'] for c in confirmed),versioned=sum(bool(c['version']) for c in confirmed),unversioned=sum(not c['version'] for c in confirmed),split=dict(Counter(c['split'] for c in confirmed)),new_candidates_audited=len(rows),classification_counts=manifest['classification_counts'],scope='Only positively confirmed unknowns count. All68 R9 cases retained; no downsampling to improve balance. Code requires explicit document-number/protocol marker in opening800; version/year requires explicit version/revision/edition/year marker. Cited statute years do not make a document versioned; absent proof remains unversioned. R9 lexical observations preserved separately, no truth-label changes.'))
 print('Unknown balance',n,dict(counts),'max',max(counts.values())/n,flush=True)

if __name__=='__main__':main()
