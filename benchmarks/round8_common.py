"""Round 8 evidence helpers, no network and no persistent personal input cache."""
import hashlib,json,subprocess,time
from datetime import UTC,datetime
from benchmarks.round3_audit import ROOT,catalog,read,write
from benchmarks.evaluate import code_hash,summary
from benchmarks.round4_common import runtime_hash
from src.fingerprint_v3 import revision,read_bundle
from src.fingerprint_decision_v4 import PATH as PROFILE
from src.extract import extract_document
from src.fingerprint_pages import prepare
from src.recognize import recognize_catalog
from src.models import CatalogRecognitionResult
from scripts.benchmark import evaluate_case

OUT='benchmarks/results/round8/'
SEED=2026101208
TRUTH='benchmarks/reference/reference_truth_v1.json'

def identity():
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),runtime_sha256=runtime_hash(),code_sha256=code_hash(),fingerprint_sha256=revision(),seed=SEED,executed_at=datetime.now(UTC).isoformat())

def checked():
    f=read(OUT+'freeze.json');current=identity()
    for k in ['runtime_sha256','code_sha256','fingerprint_sha256']:assert f[k]==current[k],'Frozen Round8 bytes changed: '+k
    for name,key in [(OUT+'calibration_v4.json','calibration_sha256'),(TRUTH,'truth_sha256'),('data/recognition_profiles/fingerprint_decision_v4.json','profile_sha256')]:assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==f[key],name
    return f

def freeze():
    if (ROOT/OUT/'freeze.json').exists():raise ValueError('Round8 already frozen')
    cal=read(OUT+'calibration_v4.json');f=identity()
    assert f['runtime_sha256']==cal['runtime_sha256'] and f['fingerprint_sha256']==cal['fingerprint_sha256']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Commit all source/evidence before freeze'
    f.update(calibration_sha256=hashlib.sha256((ROOT/OUT/'calibration_v4.json').read_bytes()).hexdigest(),truth_sha256=hashlib.sha256((ROOT/TRUTH).read_bytes()).hexdigest(),profile_sha256=hashlib.sha256(PROFILE.read_bytes()).hexdigest())
    write(OUT+'freeze.json',f);print('Round8 frozen',f['commit'],flush=True)

def active_records():return [r for r in read_bundle()['records'] if r['status']=='active']

def raw_record(r):
    raw=(ROOT/'benchmarks/cache'/(r['canonical_file_sha256']+'.body')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r['canonical_file_sha256'];return raw

def case(r,name,params=None):
    d=next(d for d in catalog()[0] if d.id==r['document_id'])
    from benchmarks.round5_recognition import family_label
    return dict(id=f'R8-{d.id}-{name}',group=f'document:{d.id}',category='known_official',expected=dict(match_type='DOCUMENT_MATCH',document_id=d.id,family_id=family_label(d),entity=d.ente,version=d.versione),label_status='confirmed',representation=name,provenance=dict(document_id=d.id,canonical_sha256=r['canonical_file_sha256'],canonical_url=r['url'],source_id=r['source_id'],canonical_mime_type=r['mime_type'],seed=SEED,transform=params or {},label_basis='Official canonical resource and catalog binding; unambiguous existing identity, no editorial verification implied.'))

def case_result(cc,raw,filename,docs=None,families=None):
    if docs is None:docs,families=catalog()
    started=time.perf_counter();ex=None;diagnostics={'expected_id':cc['expected'].get('document_id')};error=None;request=None
    try:
        ex=extract_document(raw,filename);request=prepare(raw,filename,ex);extraction_ms=(time.perf_counter()-started)*1000
        before=time.perf_counter();result=recognize_catalog(ex.text,docs,families,file_sha256=hashlib.sha256(raw).hexdigest(),page_context=request,fingerprint_diagnostics=diagnostics);matching_ms=(time.perf_counter()-before)*1000
    except (ValueError,RuntimeError,OSError) as exc:
        error=type(exc).__name__+': '+str(exc);extraction_ms=(time.perf_counter()-started)*1000;matching_ms=0
        result=CatalogRecognitionResult('NO_MATCH',0,0,reason='Extraction failed')
    row=evaluate_case(cc,result,matching_ms);scores=diagnostics.get('candidates',[]);ranks=diagnostics.get('candidate_ids',[r['document_id'] for r in scores])
    expected=cc['expected'].get('document_id');rank=ranks.index(expected)+1 if expected in ranks else None
    if 'official_file_sha256_exact' in result.document_signals:rank=1
    row.update(provenance=cc.get('provenance',{}),label_status=cc.get('label_status','historical_only'),representation=cc.get('representation','unknown'),input_sha256=hashlib.sha256(raw).hexdigest(),extraction_failed=error is not None,extraction_error=error,extraction_ms=extraction_ms,matching_ms=matching_ms,visual_ms=request.counters.get('visual_ms',0) if request else 0,end_to_end_ms=(time.perf_counter()-started)*1000,used_ocr=bool(ex and ex.used_ocr),extraction_method=ex.method if ex else None,representation_type=request.representation if request else 'unknown',signals=list(result.document_signals),candidate_rank=rank,candidate_recall_at_k={str(k):rank is not None and rank<=k for k in [1,5,10,25]},retrieval_scores=scores,decision_diagnostics=diagnostics,counters=dict(request.counters) if request else {})
    return row

def save(name,rows,**extra):
    value=dict(schema_version=4,identity=identity(),summary=summary(rows),cases=rows,**extra)
    value['counts']=dict(exact=sum(r['document_correct'] for r in rows),family=sum(r['family_correct'] for r in rows),reject=sum(r['observed']['match_type']=='NO_MATCH' for r in rows),wrong=sum(r['observed']['match_type']=='DOCUMENT_MATCH' and not r['document_correct'] for r in rows),extraction_failed=sum(r.get('extraction_failed',False) for r in rows))
    value['candidate_recall_at_k']={str(k):dict(numerator=sum(r.get('candidate_recall_at_k',{}).get(str(k),False) for r in rows),denominator=len(rows)) for k in [1,5,10,25]}
    value['by_transformation']={name:summary([r for r in rows if r.get('representation')==name]) for name in sorted({r.get('representation','') for r in rows})}
    value['by_source']={name:summary([r for r in rows if str(r.get('provenance',{}).get('source_id','unlabelled'))==name]) for name in sorted({str(r.get('provenance',{}).get('source_id','unlabelled')) for r in rows})}
    write(OUT+name+'.json',value);return value
