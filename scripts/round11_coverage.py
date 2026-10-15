"""Audit shared resource eligibility separately from unique canonical identity."""
import csv,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog
from benchmarks.transactional_writer import atomic_json
from src.fingerprint_v3 import read_bundle,public_index,page_record
from src.document_fingerprints import binding
from src.extract import extract_document
from src.fingerprint_decision_v5 import match
from src.fingerprint_pages import prepare
from maintenance.legacy_convert import convert_official
from maintenance.policy import validate_url
from maintenance.resolve_resources import SOURCES
OUT=ROOT/'benchmarks/results/round11'
REJECT={176:'The Segnalazione/Reclamo information sheet is not the TFTP access/rectification form.',583:'The bytes are Allegato3 Proposta progettuale, not Allegato2 Domanda.',921:'The shared PDF requests regional registration, not the national list identified by this row.',983:'The shared PDF is explicitly Mod.SL Stati paga, not Libro unico.',1151:'The shared PDF is the principal port-authority application, not its Allegato1 spreadsheet.'}
EVIDENCE={114:'Common bollo declaration, EQ/MA official associations.',115:'Common bollo declaration, EQ/MA official associations.',152:'Official INL17 access-documentale form; bollo is an additional shared attachment.',166:'Official linked Segnalazione/Reclamo guidance sheet; resource support only, not an application form.',311:'Official SR06 common template.',621:'Official SR06 common template.',314:'SC80 Italian form also listed with English catalog title.',399:'SC80 Italian form also listed with English catalog title.',315:'Official AP160 common template.',623:'Official AP160 common template.',331:'EN025 Italian form also listed with English catalog title.',728:'EN025 Italian form also listed with English catalog title.',400:'The certification explicitly covers acceptance and renunciation of inheritance.',500:'The certification explicitly covers acceptance and renunciation of inheritance.',517:'Published generic tutela-minore application.',536:'Published generic tutela application sharing the minore template; no unique scope inferred.',569:'Allegato2 ex9 electronic communications declaration.',570:'Allegato2 ex9 electronic communications declaration.',584:'Actual opening ALLEGATO3 Proposta progettuale.',586:'Official common regional SCIA extra-alberghiere template.',587:'Official common communication of variation in accommodation template.',590:'Official common regional SCIA alberghiere template.',939:'Actual shared form requests entry into regional INAIL lists.',959:'Common declaration explicitly titled DICHIARAZIONE TRACCIABILITA.',968:'Common declaration explicitly titled DICHIARAZIONE TRACCIABILITA.',985:'Actual Mod.SL Stati paga laser-print request.',1150:'Actual principal port-authority Fondo amianto application.',1184:'Official20SM form associated with this annual listing; annual identity remains unresolved.',1185:'Official20SM common template; no annuality inferred from byte match.',1186:'20SM common templates only; the unrelated parametri resource is excluded.',1187:'Official20SM common template; no annuality inferred from byte match.',1193:'Actual opening Retribuzioni Medie Giornaliere.',1196:'Actual opening Parametri per il calcolo del tasso specifico aziendale.',177:'Published simplified cartello with variable controller/issuer: common form, no unique SHA identity.'}

def main():
 docs,_=catalog();by={d.id:d for d in docs};bundle=read_bundle();index=public_index();active={r['document_id'] for r in bundle['records'] if r['status']=='active'};audit=[];supported=set();physical={};fingerprint_tests=[]
 for r in bundle['records']:
  if r['status']!='shared':continue
  did=r['document_id'];sha=r['canonical_file_sha256'];d=by[did]
  raw=(ROOT/'benchmarks/cache'/(sha+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
  validate_url(r['url'],SOURCES[d.source_id]);validate_url(r['final_url'],SOURCES[d.source_id]);assert r['catalog_binding_sha256']==binding(d)
  if sha not in physical:
   ex=extract_document(raw,'resource.pdf' if r['mime_type']=='application/pdf' else 'resource.docx');physical[sha]=(raw,ex)
   result=match(ex.text,docs,file_sha256=sha,pages=prepare(raw,'resource.pdf' if r['mime_type']=='application/pdf' else 'resource.docx',ex))
   fingerprint_tests.append(dict(sha256=sha,observed_document_id=result.document.id if result and result.recognized else None,signals=list(result.matched_signals) if result else [],exact_sha_tier=bool(result and 'A_exact_sha' in result.matched_signals)))
  allowed=did in EVIDENCE and did not in REJECT and not (did==1186 and sha.startswith('319b1ad8773f'))
  if allowed:supported.add(did)
  audit.append(dict(document_id=did,source=SOURCES[d.source_id],sha256=sha,official_url=r['url'],shared_resource=True,ambiguity_group='RESOURCE-'+sha[:16],runtime_status=r['status'],eligible=allowed,reason=EVIDENCE.get(did) if allowed else REJECT.get(did,'Wrong companion resource or no new eligibility claim; active identity coverage counted separately.'),additional_signals_required='Unique explicit catalog code, compatible entity/version and sufficient content margin; SHA alone forbidden.',opening_sha256=hashlib.sha256(physical[sha][1].text[:2000].encode()).hexdigest()))
 assert not any(r['exact_sha_tier'] for r in fingerprint_tests),'Shared source improperly entered exact-SHA tier'
 atomic_json(OUT/'shared_resource_audit.json',dict(cases=audit,eligible_ids=sorted(supported),shared_only_eligible_ids=sorted(supported-active),fingerprint_policy_observations=fingerprint_tests,scope='Manual content/provenance adjudication, before any release evaluation. Resource support is not unambiguous identity accuracy. Wrong old associations excluded from coverage without rewriting their historical observations.'))
 # Recheck the only previously useful legacy identities; temporary output is
 # deleted by the converter. Public sketches remain outside the runtime bundle.
 legacy=read('benchmarks/results/round10/legacy_resource_fingerprints.json');legacy_results=[];work=ROOT/'benchmarks/work/round11-legacy'
 import pymupdf
 for did in [422,1101]:
  c=next(c for c in legacy['bindings'] if c['document_id']==did and c['identity_supported']);r=next(r for r in legacy['resources'] if r['original_sha256']==c['original_sha256']);raw=(ROOT/'benchmarks/cache'/(c['original_sha256']+'.body')).read_bytes()
  try:
   pdf,meta=convert_official(raw,r['original_format'],work)
   with pymupdf.open(stream=pdf,filetype='pdf') as p:text='\n'.join(page.get_text() for page in p)
   fp=page_record(1,text,'',(),ocr_status='unavailable_docx_renderer');fp['ocr_status']='not_requested_maintenance_digital_only'
   legacy_results.append(dict(document_id=did,**meta,content_fingerprint=fp,runtime_supported=False,reason='Original format unsupported by frozen runtime/v3 MIME contract; derived content remains separate.'))
   del pdf
  except (ValueError,OSError,RuntimeError) as exc:legacy_results.append(dict(document_id=did,runtime_supported=False,reason=str(exc)))
 atomic_json(OUT/'legacy_final_pass.json',dict(cases=legacy_results,temporary_outputs_deleted=not list(work.iterdir()),scope='No converted bytes committed or retained by this pass; no native legacy upload support or active fingerprint promotion claimed. Other63 R10 legacy resources retain their prior immutable audit; failures deduplicated, not blindly retried.'))
 fixed={c['document_id'] for c in read('benchmarks/results/round6/resource_audit.json')['cases'] if c['expected_resource_type']=='file_backed_document'};eligible=(active|supported)&fixed
 per={}
 for sid,key in SOURCES.items():
  operative={d.id for d in docs if d.source_id==sid and d.stato_verifica not in ['demo','rifiutato']};n=len(operative&fixed)
  per[key]=dict(operational_total=len(operative),file_backed_total=n,fingerprinted=len(eligible&operative),unambiguous=len(active&operative),shared_only=len((supported-active)&operative),remaining=len((fixed-eligible)&operative))
 plan=list(csv.DictReader((OUT/'fingerprint_recovery_plan.csv').open(encoding='utf8')));build=read('benchmarks/results/round11/fingerprint_build.json');added=build['added'];by_added={r['document_id']:r for r in added};rejections=defaultdict(set)
 for r in build['rejected']:rejections[r['document_id']].add(r['reason'])
 for row in plan:
  did=int(row['document_id'])
  row['acquisition_success']=row.get('acquisition_success',row['success']);row['success']=did in eligible
  if did in eligible:
   row['fingerprint_built']=did in by_added;row['success']=True;row['final_reason']='new_official_unambiguous_fingerprint' if did in active else 'audited_shared_resource_supported_identity_ambiguous'
  elif did in REJECT:row['final_reason']='shared_association_rejected: '+REJECT[did]
  elif rejections[did]:row['final_reason']='; '.join(sorted(rejections[did]))
 with (OUT/'fingerprint_recovery_plan.csv').open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(plan[0]),lineterminator='\n');w.writeheader();w.writerows(plan)
 remaining=Counter(r['final_reason'] for r in plan if int(r['document_id']) not in eligible)
 result=dict(operational_total=1212,file_backed_total=len(fixed),initial_fingerprinted=941,fingerprinted_file_backed=len(eligible),file_backed_percent=100*len(eligible)/len(fixed),all_operational_percent=100*len(eligible)/1212,recovered_round11=len(eligible)-941,new_signature_identities=len({r['document_id'] for r in added}),previous_shared_now_eligible=len((supported-active)-{r['document_id'] for r in added}),unambiguous_identities=len(active),shared_only_supported=len(supported-active),remaining_by_reason=dict(remaining),per_source=per,eligible_ids=sorted(eligible),scope='R11 explicitly allows genuinely associated shared-resource support. R10 unambiguous941/1158 metric retained alongside this distinct coverage measure; no denominator change or shared canonical-identity inflation.')
 atomic_json(OUT/'coverage_final.json',result);print('R11 coverage',len(eligible),'/1158, unambiguous',len(active),'shared-only',len(supported-active),flush=True)

if __name__=='__main__':main()
