"""Official attachment-context audit and deterministic R11 release selection."""
import csv,hashlib,json,re,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks.transactional_writer import atomic_json
from benchmarks.unknown_release import validate,select,balance,SEED
from src.fingerprint_v3 import read_bundle,public_index,features
from src.extract import extract_document
from src.recognize import normalize_text
from src.title_evidence import exact_code_candidates
from scripts.round9_truth import words
from scripts.round10_truth import document_metadata,TYPES
OUT=ROOT/'benchmarks/results/round11'

def attachment_role(opening,title,kind):
 """An annex form does not inherit the document type of its circular."""
 lines=[line.strip() for line in opening.splitlines() if line.strip() and not line.strip().isdigit()]
 head=normalize_text(' '.join(lines[:6]))
 if 'domanda di contributo' in head:
  stop=next(i for i,line in enumerate(lines) if 'domanda di contributo' in normalize_text(line))
  return ' '.join(lines[:stop+1])[:350],'domanda'
 if 'atto di indirizzo a valenza generale' in head:
  return ' '.join(lines[:3])[:350],'atto_indirizzo'
 return title,kind

def main():
 docs,families=catalog();ix=public_index();hashes={r['canonical_file_sha256'] for r in read_bundle()['records']};titles=[(d.id,normalize_text(d.titolo_ufficiale.split(' / ')[0])) for d in docs if d.stato_verifica not in ['demo','rifiutato']]
 old=read('benchmarks/manifests/official_unknown_v2.json')['cases'];master=[dict(c) for c in old];seen={c['SHA256'] for c in master};queries={};rows=[];headings=[]
 recognized={r['id'] for r in read('benchmarks/results/round10/unknown_development.json')['cases']}
 for c in master:
  assert c['SHA256'] not in hashes,'Old unknown conflicts with new canonical resource'
  c['historically_seen']=c['historically_seen'] or c['case_id'] in recognized
  p=next(ROOT/'tmp-build'/f'round{r}-truth-text'/(c['SHA256']+'.json') for r in [9,10] if (ROOT/'tmp-build'/f'round{r}-truth-text'/(c['SHA256']+'.json')).exists())
  queries[c['SHA256']]=features(json.loads(p.read_bytes())['opening'])
  rows.append(dict(case_id=c['case_id'],source=c['source'],entity=c['entity'],title=c['title'],official_url=c['official_url'],sha256=c['SHA256'],classification='confirmed_unknown',reason='Preserved R10 confirmed official truth; historical recognition exposure retained.',evidence=json.dumps(c['audit_evidence'],ensure_ascii=False)))
 for i,c in enumerate(read('benchmarks/results/round11/unknown_candidates.json')['candidates']):
  sha=c['sha256']
  if sha in seen:continue
  seen.add(sha);opening='';error='';top=None;hits=[];codes=[];fam=[];kind=None
  raw=(ROOT/'benchmarks/cache'/(sha+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
  context=c.get('source_evidence',{});label=c['title'];heading=context.get('context_heading','');title=label
  try:
   paths=[ROOT/'tmp-build'/f'round{r}-truth-text'/(sha+'.json') for r in [9,10,11]];cached=next((p for p in paths if p.exists()),None)
   if cached:opening=json.loads(cached.read_bytes())['opening']
   else:opening=extract_document(raw,'unknown.'+c['format']).text[:2000];atomic_json(paths[-1],dict(sha256=sha,opening=opening,scope='Official source audit only, ignored; never a runtime cache.'))
   normal=normalize_text(opening);nt=normalize_text(label);nh=normalize_text(heading)
   hits=[did for did,t in titles if len(t)>=20 and f' {t} ' in f' {normal} '];codes=list(exact_code_candidates(opening,docs))
   q=features(opening);scores=ix.similarities([q],n='3');top=scores[0] if scores else None;queries[sha]=q
   for f in families:
    if any(len(normalize_text(a))>=12 and f' {normalize_text(a)} ' in f' {normal} ' for a in [*f.identifying_phrases,f.nome]):fam.append(f.id)
   # The attachment label is often only "La circolare". The linked official
   # detail heading plus an actual OGGETTO/addressed act is stronger evidence.
   if len(words(label))<3 and len(words(heading))>=6:title=heading
   if c['source_key']=='regione_piemonte' and len(words(title))<3:
    lines=[x.strip() for x in opening.splitlines() if len(x.strip())>4]
    candidate=' '.join(lines[:4])[:350]
    if any(t in normalize_text(candidate).split() for t in TYPES+['note','nota']):title=candidate
   kinds=[t for t in TYPES+['nota','note'] if t in normalize_text(title).split() and t in normal.split()]
   if kinds:kind=kinds[0]
   if not kind and 'circolare' in nh.split() and 'oggetto' in normal.split() and len(words(heading)&words(opening))>=5:kind='circolare'
   if not kind and 'domanda' in nt.split() and 'chiede' in normal.split() and 'sottoscritto' in normal:kind='domanda';title=label+' — '+heading
   if 'linee guida' in normal and 'linee guida' in normalize_text(title):kind='guida'
   title,kind=attachment_role(opening,title,kind)
  except (ValueError,OSError,RuntimeError) as exc:error=type(exc).__name__+': '+str(exc)
  overlap=words(title)&words(opening);support=len(overlap)/max(1,len(words(title)))
  near=bool(hits or codes or top and top['score']>=.85 and top['digital']>=.8 and top['chars']>=.8)
  supported=bool(not error and kind and support>=.50 and len(overlap)>=4)
  state='duplicate_catalog_resource' if sha in hashes else 'possible_document_match' if near else 'possible_family_match' if fam else 'unsupported_truth' if error else 'confirmed_unknown' if supported else 'ambiguous'
  evidence=dict(official_sha256=sha,opening_sha256=hashlib.sha256(opening.encode()).hexdigest(),title_token_support=support,title_tokens_supported=len(overlap),catalog_title_hits=hits,catalog_code_hits=codes,family_hits=fam,nearest_catalog_id=top['document_id'] if top else None,nearest_content_score=top['score'] if top else None,nearest_digital=top['digital'] if top else None,nearest_chars=top['chars'] if top else None,document_type=kind,source_evidence=context,source_relationship='Official hosting authority; issuer not automatically inferred from hosting.',criteria='Actual official receipt, opening2000 content, linked official detail/attachment heading, explicit document type or formal addressed OGGETTO/CHIEDE structure; full catalog title/code, exact SHA, content-near and family exclusions. No recognition decision used.')
  reason=error or evidence['criteria'];case_id='U11-'+sha[:16]
  rows.append(dict(case_id=case_id,source=c['source_key'],entity=c['entity'],title=title,official_url=c['url'],sha256=sha,classification=state,reason=reason,evidence=json.dumps(evidence,ensure_ascii=False)))
  headings.append(f'{case_id} | {state} | {c["source_key"]} | {title}\n{opening[:1000]}\n\n')
  if state=='confirmed_unknown':
   code,version=document_metadata(opening)
   master.append(dict(case_id=case_id,source=c['source_key'],entity=c['entity'],title=title,official_url=c['url'],acquisition_date=c['receipt']['acquired_at'],SHA256=sha,mime='application/pdf' if c['format']=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',reference_truth_status=state,expected_result='NO_MATCH',classification_reason=reason,receipt=c['receipt'],audit_evidence=evidence,document_type=kind,code=code,version=version,historically_seen=False))
  if (i+1)%30==0:print('R11 truth',i+1,'master',len(master),flush=True)
 # Connected public near-resource components, used for split only, not labels.
 parent={c['SHA256']:c['SHA256'] for c in master};edges=[]
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 for i,a in enumerate(master):
  qa=queries[a['SHA256']]
  for b in master[:i]:
   qb=queries[b['SHA256']];token=len(qa['tokens']&qb['tokens'])/max(1,len(qa['tokens']|qb['tokens']));chars=len(qa['chars']['4']&qb['chars']['4'])/max(1,len(qa['chars']['4']|qb['chars']['4']))
   if token>=.8 and chars>=.8:parent[find(a['SHA256'])]=find(b['SHA256']);edges.append([a['case_id'],b['case_id']])
 groups=defaultdict(list)
 for c in master:groups[find(c['SHA256'])].append(c)
 for group in groups.values():
  gid='UG11-'+min(c['SHA256'] for c in group)[:16]
  for c in group:c['resource_group']=gid
 release=select(master);release_ids={c['case_id'] for c in release}
 for c in master:c['split']='unknown_release' if c['case_id'] in release_ids else 'unknown_dev'
 master_manifest=dict(schema_version=1,manifest_id='official-unknown-master-v1',cases=master,preserved_master_sha256=hashlib.sha256((ROOT/'benchmarks/manifests/official_unknown_v2.json').read_bytes()).hexdigest(),scope='All107 R10 confirmed cases retained; additions have official context evidence. No catalog additions or truth-label deletion.')
 release_manifest=dict(schema_version=1,manifest_id='official-unknown-release-v1',cases=release,selection_seed=SEED,source_cap=25,selection='All-or-none near-resource groups sorted SHA256(seed:group), accept while each source<=25; no score/outcome/ease filtering.',scope='Selected before recognition/freeze. Prior recognition exposure explicitly retained; selection does not make old cases independent. No R11 release recognition until freeze.')
 validate(master_manifest);validate(release_manifest)
 atomic_json(ROOT/'benchmarks/manifests/official_unknown_master_v1.json',master_manifest);atomic_json(ROOT/'benchmarks/manifests/official_unknown_release_v1.json',release_manifest)
 with (OUT/'unknown_truth_audit.csv').open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 (ROOT/'tmp-build/round11-unknown-headings.txt').write_bytes(''.join(headings).encode())
 atomic_json(OUT/'unknown_balance_final.json',dict(master=balance(master),release=balance(release),selection_seed=SEED,source_cap=25,new_confirmed=len(master)-len(old),classification_counts=dict(Counter(r['classification'] for r in rows)),near_resource_edges=edges,release_dev_sha_disjoint=not {c['SHA256'] for c in release}&{c['SHA256'] for c in master if c['split']=='unknown_dev'},release_dev_group_disjoint=not {c['resource_group'] for c in release}&{c['resource_group'] for c in master if c['split']=='unknown_dev'},release_recognition_calls=0))
 print('R11 unknown master/release',balance(master),balance(release),flush=True)

if __name__=='__main__':main()
