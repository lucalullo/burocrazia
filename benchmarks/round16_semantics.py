"""Before/after public decisions on locked canonical and development inputs."""
import argparse,hashlib,json,re
from dataclasses import asdict
from collections import Counter
from scripts.round16_common import *
from benchmarks.round3_audit import catalog
from src.extract import extract_document
from src.fingerprint_pages import prepare,RequestPages
from src.fingerprint_v3 import read_bundle
from src.recognize import recognize_catalog

WORK=ROOT/'benchmarks/work/round16'
PREPARED=WORK/'semantic-inputs.json'

def prepare_inputs():
    assert not PREPARED.exists(),'Prepared inputs already locked'
    rows=[];cache={};WORK.mkdir(parents=True,exist_ok=True)
    extracted=WORK/'extracted';extracted.mkdir(exist_ok=True)
    extraction_revision=sha('src/extract.py')+sha('src/ocr.py')
    def text_case(c,category):
        rows.append(dict(id=category+':'+c['id'],category=category,text=c['text'],texts=[c['text']],representation='unknown',numbers=[],field_set=[],filename='',raw_file=None,sha256=None,expected=c['expected']))
    def file_case(ident,path,category,expected=None):
        raw=path.read_bytes();h=hashlib.sha256(raw).hexdigest();suffix=path.suffix if path.suffix!='.body' else '.docx' if raw.startswith(b'PK\x03\x04') else '.pdf'
        name='reference'+suffix;key=(h,suffix)
        if key not in cache:
            checkpoint=extracted/(h+suffix+'.json')
            if checkpoint.exists():
                prior=read(checkpoint);assert prior['input_sha256']==h and prior['extraction_revision']==extraction_revision
                cache[key]=prior['prepared']
            else:
                ex=extract_document(raw,name);ctx=prepare(raw,name,ex)
                cache[key]=dict(text=ex.text,texts=list(ctx.texts),representation=ctx.representation,numbers=list(ctx.numbers),field_set=list(ctx.field_set))
                atomic_json(checkpoint,dict(input_sha256=h,extraction_revision=extraction_revision,prepared=cache[key],scope='Ignored public/synthetic benchmark preparation only, never an application upload cache.'))
        rows.append(dict(id=ident,category=category,**cache[key],filename=name,raw_file=path.relative_to(ROOT).as_posix(),sha256=h,expected=expected))
    records=read_bundle()['records']
    for r in records:
        if r['status']!='active':continue
        if r['mime_type'] in ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            path=ROOT/'benchmarks/cache'/(r['canonical_file_sha256']+'.body');suffix='.pdf' if r['mime_type']=='application/pdf' else '.docx'
            if suffix=='.docx':
                dest=WORK/(r['canonical_file_sha256']+'.docx');dest.write_bytes(path.read_bytes());path=dest
            file_case('canonical:'+str(r['document_id'])+':'+r['canonical_file_sha256'][:12],path,'canonical',dict(match_type='DOCUMENT_MATCH',document_id=r['document_id']))
        elif r['ocr_metadata'].get('source_kind')=='maintenance_derived_legacy':
            from maintenance.legacy_convert import convert_official
            from maintenance.round13_legacy import normalize_pdf
            raw=(ROOT/'benchmarks/cache'/(r['canonical_file_sha256']+'.body')).read_bytes()
            prior=WORK/(r['ocr_metadata']['derived_sha256']+'.pdf')
            derived=prior.read_bytes() if prior.exists() else normalize_pdf(convert_official(raw,r['ocr_metadata']['original_format'],WORK/'legacy')[0]);h=hashlib.sha256(derived).hexdigest()
            assert h==r['ocr_metadata']['derived_sha256']
            path=WORK/(h+'.pdf');path.write_bytes(derived)
            file_case('legacy:'+str(r['document_id']),path,'canonical_legacy',dict(match_type='DOCUMENT_MATCH',document_id=r['document_id']))
        if len(rows)%100==0:print('Semantic preparation canonical',len(rows),flush=True)
    for name in ['development_regression','release_locked_v1','release_locked_v2','hard_negatives_v1','hard_negatives_v2']:
        for c in read('benchmarks/corpora/'+name+'.json')['cases']:text_case(c,name)
    for c in read('tests/fixtures/benchmark_v2.json')['cases']:text_case(c,'development_compat_v2')
    # Real, already observed development bytes. No new release identity/file is
    # probed. Fixed seeded filename order, never outcome/score based selection.
    categories=[('round6_scan_development','round6-representations',10),('round6_filled_development','round6-filled',8),('round8_filled_development','round8-development-filled',8)]
    for category,folder,n in categories:
        files=[p for p in (ROOT/'benchmarks/work'/folder).glob('*') if p.suffix in ['.pdf','.png','.jpg']]
        files.sort(key=lambda p:hashlib.sha256((str(SEED)+p.name).encode()).hexdigest())
        ids=set();selected=[]
        for p in files:
            did=re.match(r'(?:R8DEV-)?(\d+)',p.name).group(1)
            if did in ids:continue
            selected.append(p);ids.add(did)
            if len(selected)==n:break
        assert len(selected)==n
        for p in selected:file_case(category+':'+p.name,p,category)
    # The R8 partial checkpoint is historical/observed, not an independent v5.
    old=read('benchmarks/results/round8/evaluation_checkpoint_preserved.json')['cases'];needed={c['input_sha256']:c for c in old}
    files={}
    for folder in ['round6-representations','round8-evaluation']:
        for p in (ROOT/'benchmarks/work'/folder).glob('*'):
            if p.suffix in ['.pdf','.png','.jpg']:
                h=hashlib.sha256(p.read_bytes()).hexdigest()
                if h in needed:files[h]=p
    selected=sorted(files,key=lambda h:hashlib.sha256((str(SEED)+h).encode()).hexdigest())[:10];assert len(selected)==10
    for h in selected:file_case('round8_observed:'+needed[h]['id'],files[h],'round8_observed_development')
    # R7 development scans reused the locked R6 representations; separately
    # label the unchanged fixed input contract rather than inventing new bytes.
    for c in rows[:]:
        if c['category']=='round6_scan_development':rows.append(dict(c,id='round7_development:'+c['id'],category='round7_development'))
    c=read('tests/fixtures/round15_confirmed_false_accept.json');text_case(dict(id=c['case_id'],text=c['official_opening'],expected=dict(match_type='NO_MATCH')),'ANAC')
    for c in read('benchmarks/results/round15/verification.json')['historical_five']:
        h=c['input_sha256'];path=ROOT/'benchmarks/cache'/(h+'.body');file_case('old_false_accept:'+c['id'],path,'old_false_accept',c['expected'])
    assert len({c['id'] for c in rows})==len(rows)
    atomic_json(PREPARED,dict(rows=rows,created_at=now(),seed=SEED))
    manifest=[dict(case_id=c['id'],category=c['category'],sha256=c['sha256'],text_sha256=hashlib.sha256(c['text'].encode()).hexdigest(),representation=c['representation']) for c in rows]
    save('semantic_inputs_manifest',dict(cases=manifest,counts=dict(Counter(c['category'] for c in rows)),selection_seed=SEED,prepared_sha256=sha(PREPARED),purpose='Historical semantic equivalence only; no fresh release benchmark resources.',created_at=now()))
    print('Semantic inputs locked',len(rows),flush=True)

def prepare_supplement():
    """Add continuation-required cases without rewriting the locked first set."""
    path=WORK/'semantic-supplement.json';assert not path.exists()
    rows=[]
    for c in read('benchmarks/corpora/family_release_v3.json')['cases']:
        rows.append(dict(id='family_release_v3:'+c['id'],category='family_release_v3',text=c['text'],texts=[c['text']],representation='unknown',numbers=[],field_set=[],filename='',raw_file=None,sha256=None,expected=c['expected'],recognition='family'))
    for c in read(TRUTH)['cases']:
        if c['confidence'] not in ['ambiguous','confirmed']:continue
        h=c['official_evidence']['download_receipt']['sha256'];raw_path=ROOT/'benchmarks/cache'/(h+'.body');raw=raw_path.read_bytes();assert hashlib.sha256(raw).hexdigest()==h
        ex=extract_document(raw,'historical.pdf');ctx=prepare(raw,'historical.pdf',ex)
        rows.append(dict(id='official_diagnostic:'+c['case_id'],category='INAIL_ambiguous' if c['confidence']=='ambiguous' else 'ANAC_full_pdf',text=ex.text,texts=list(ctx.texts),representation=ctx.representation,numbers=list(ctx.numbers),field_set=list(ctx.field_set),filename='historical.pdf',raw_file=raw_path.relative_to(ROOT).as_posix(),sha256=h,expected=dict(match_type=c['historical_expected']),truth_confidence=c['confidence']))
    atomic_json(path,dict(rows=rows,created_at=now(),seed=SEED,purpose='Additive continuation scope: isolated family contracts, both ambiguous INAIL PDFs, full ANAC PDF.'))
    save('semantic_supplement_manifest',dict(prepared_sha256=sha(path),cases=[dict(case_id=c['id'],category=c['category'],sha256=c['sha256'],text_sha256=hashlib.sha256(c['text'].encode()).hexdigest()) for c in rows],counts=dict(Counter(c['category'] for c in rows))))

def observe(stage,supplement=False):
    stem='semantic_supplement_' if supplement else 'semantic_'
    source=WORK/'semantic-supplement.json' if supplement else PREPARED
    target=OUT/(stem+stage+'.json');assert not target.exists(),'Semantic stage already completed'
    if stage=='before':
        assert not subprocess.check_output(['git','diff',BASE,'--','src','app.py','run.py','data'],cwd=ROOT,text=True).strip(),'Engine changed before reference snapshot'
    from benchmarks.round8_common import identity
    docs,families=catalog();prepared=read(source);results=[]
    for i,c in enumerate(prepared['rows'],1):
        raw=(ROOT/c['raw_file']).read_bytes() if c['raw_file'] else b''
        if raw:assert hashlib.sha256(raw).hexdigest()==c['sha256']
        ctx=RequestPages(tuple(c['texts']),c['representation'],tuple(c['field_set']),tuple(c['numbers']),raw,c['filename']);diag={}
        if c.get('recognition')=='family':
            from src.recognize import recognize_document_family
            from src.models import CatalogRecognitionResult
            family=recognize_document_family(c['text'],families,known_entities=[d.ente for d in docs])
            result=CatalogRecognitionResult('FAMILY_MATCH' if family.recognized else 'NO_MATCH',0,family.confidence,family=family.family)
        else:result=recognize_catalog(c['text'],docs,families,page_context=ctx,file_sha256=c['sha256'],fingerprint_diagnostics=diag)
        public=asdict(result);candidates=diag.get('candidates',[])
        signature=dict(result=public,result_type=result.match_type,document_id=result.document.id if result.document else None,family_id=result.family.id if result.family else None,
            score=result.confidence_document,runner_up=candidates[1] if len(candidates)>1 else None,score_margin=result.document_score_margin,entity_conflicts=[s for s in result.conflicts if 'ente' in s],version_conflicts=[s for s in result.conflicts if 'annual' in s or 'version' in s],reason_code=diag.get('reason_code'),tier=diag.get('tier'),candidate_ids=diag.get('candidate_ids',[]),top_candidates=candidates,version_evidence=diag.get('version_evidence'),entity_evidence=diag.get('entity_evidence'))
        results.append(dict(case_id=c['id'],category=c['category'],signature=json.loads(json.dumps(signature,ensure_ascii=False))))
        if i%200==0:print('Semantic',stage,i,'/',len(prepared['rows']),flush=True)
    atomic_json(target,dict(identity=identity(),prepared_sha256=sha(source),cases=results,complete=True,expected_count=len(prepared['rows']),created_at=now()))
    if stage=='after':
        before=read(OUT/(stem+'before.json'));assert before['prepared_sha256']==sha(source)
        assert len(before['cases'])==len(results)
        differences=[dict(case_id=a['case_id'],before=a['signature'],after=b['signature']) for a,b in zip(before['cases'],results) if a['case_id']!=b['case_id'] or a['signature']!=b['signature']]
        save(stem+'equivalence' if supplement else 'semantic_main_equivalence',dict(passed=not differences,before_sha256=sha(OUT/(stem+'before.json')),after_sha256=sha(target),manifest_sha256=sha(OUT/('semantic_supplement_manifest.json' if supplement else 'semantic_inputs_manifest.json')),n=len(results),counts=dict(Counter(c['category'] for c in results)),differences=differences,
            compared_fields=['complete_public_result','result_type','document_id','family_id','score','runner_up','score_margin','entity_conflicts','version_conflicts','reason_code','tier','candidate_ids','top_candidates','entity_evidence','version_evidence'],timing_fields_excluded=['visual_ms'],scope='Same actual extracted inputs and raw bytes, fresh request objects for every recognition. OCR extracted once before optimization to isolate recognition; baseline/final OCR product tests remain separate. No independent-release inputs used.'))
        assert not differences,'Optimization changes semantics: revert it'
    print('Semantic',stage,'complete',len(results),flush=True)

def combine():
    a=read(OUT/'semantic_main_equivalence.json');b=read(OUT/'semantic_supplement_equivalence.json')
    counts=Counter(a['counts']);counts.update(b['counts'])
    save('semantic_equivalence',dict(passed=a['passed'] and b['passed'],n=a['n']+b['n'],counts=dict(counts),differences=a['differences']+b['differences'],compared_fields=a['compared_fields'],artifacts_sha256={n:sha(OUT/n) for n in ['semantic_main_equivalence.json','semantic_supplement_equivalence.json','semantic_before.json','semantic_after.json','semantic_supplement_before.json','semantic_supplement_after.json','semantic_inputs_manifest.json','semantic_supplement_manifest.json']},scope=a['scope']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','before','after','prepare_supplement','before_supplement','after_supplement','combine']);a=p.parse_args()
    if a.mode=='prepare':prepare_inputs()
    elif a.mode=='prepare_supplement':prepare_supplement()
    elif a.mode=='combine':combine()
    else:observe(a.mode.split('_')[0],supplement=a.mode.endswith('_supplement'))
