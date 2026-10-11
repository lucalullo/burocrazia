"""Frozen public family stress cases; supplemental official evidence stays local."""
from collections import Counter
from dataclasses import replace
import hashlib
import time
from benchmarks.round4_common import ROOT, OUT, read, write, catalog
from benchmarks.evaluate import summary, code_hash
from scripts.benchmark import evaluate_case
from src.models import CatalogRecognitionResult
from src.recognize import recognize_document_family, recognize_catalog

CORPUS='benchmarks/corpora/family_release_v1.json'

def build():
    if (ROOT/CORPUS).exists():raise ValueError('Family corpus already frozen.')
    docs,families=catalog();cases=[]
    for f in sorted(families,key=lambda f:f.id):
        phrases=list(dict.fromkeys([f.nome,*f.identifying_phrases]))
        if f.id==3:phrases+=['avviso di presa in carico']
        if f.id==4:phrases+=['crediti previdenziali']
        issuers=['Comune di Esempio Alfa','Comune di Esempio Beta'] if f.id==15 else ['Regione Esempio Alfa','Regione Esempio Beta'] if f.id==16 else [f.ente]
        for i in range(5):
            parts=phrases[i%len(phrases):]+phrases[:i%len(phrases)]
            text=issuers[i%len(issuers)]+'\n'+'\n'.join(parts)+'\nFacsimile sintetico senza dati personali.'
            if i==3:text=text.upper()
            if i==4:text=text.replace('\n','\n\n')
            expected=dict(match_type='FAMILY_MATCH',family_id=f.id)
            if f.id not in {15,16}:expected['entity']=f.ente
            cases.append(dict(id=f'FR{f.id:02}-P{i+1}',group=f'family:{f.id}',category='family_positive',source=issuers[i%len(issuers)],noise='synthetic_layout',target_family_id=f.id,text=text,expected=expected))
        positive=cases[-5]['text'];body='\n'.join(phrases)
        negatives=[('wrong_issuer','INAIL\n'+body),('instructions',issuers[0]+'\nGuida\n'+body),('body_only', 'Documento generico\n'+'Contesto neutro. '*150+'\n'+positive),('missing_issuer',body),('recipient_mention','INAIL\nDestinatario '+issuers[0]+'\n'+body)]
        for i,(kind,text) in enumerate(negatives):
            cases.append(dict(id=f'FR{f.id:02}-N{i+1}',group=f'family:{f.id}',category='family_negative',source='synthetic',noise=kind,target_family_id=f.id,text=text,expected=dict(match_type='NO_MATCH')))
    r061=next(c for c in read('benchmarks/corpora/release_locked_v2.json')['cases'] if c['id']=='R061')
    cases.append(dict(r061,id='R061',target_family_id=4))
    corpus=dict(schema_version=1,corpus_id='family_release_v1',split='development_family_release',synthetic=True,purpose='Five synthetic positives and five paired hard negatives per verified family; layout variants are correlated, not independent evidence. R061 permanent. No new editorial family verification.',cases=cases)
    write(CORPUS,corpus)
    write('benchmarks/manifests/family_release_locks_v1.json',dict(sha256={CORPUS:hashlib.sha256((ROOT/CORPUS).read_bytes()).hexdigest()}))

def run(version=3):
    docs,families=catalog();corpus=read(f'benchmarks/corpora/family_release_v{version}.json');rows=[];end_to_end=[]
    for c in corpus['cases']:
        start=time.perf_counter();r=recognize_document_family(c['text'],families,known_entities=[d.ente for d in docs])
        result=CatalogRecognitionResult(match_type='FAMILY_MATCH' if r.recognized else 'NO_MATCH',confidence_document=0,confidence_family=r.confidence,family=r.family,reason=r.reason)
        row=evaluate_case(c,result,(time.perf_counter()-start)*1000);row['target_family_id']=c['target_family_id'];rows.append(row)
        end_to_end.append(evaluate_case(c,recognize_catalog(c['text'],docs,families)))
    per={str(f.id):summary([r for r in rows if r['target_family_id']==f.id]) for f in families}
    precisions=[v['metrics']['family_precision']['value'] for v in per.values() if v['metrics']['family_precision']['value'] is not None]
    report=dict(schema_version=1,corpus_id=corpus['corpus_id'],independent=False,synthetic=True,code_sha256=code_hash(),summary=summary(rows),cases=rows,per_family=per,macro_precision=sum(precisions)/len(precisions) if precisions else None,macro_recall=sum(v['metrics']['family_recall']['value'] or 0 for v in per.values())/len(per),macro_f1=sum(v['metrics']['family_f1']['value'] or 0 for v in per.values())/len(per),end_to_end=summary(end_to_end),end_to_end_cases=end_to_end,official_evidence='No official files redistributed; this gate isolates the family fallback. Real-file fallback is measured separately in development and independent holdout.',false_positives=sum(r['observed']['match_type']=='FAMILY_MATCH' and not r['family_correct'] for r in rows))
    report['gate_passed']=report['false_positives']==0 and (report['summary']['metrics']['family_precision']['value'] or 0)>=.995 and (report['macro_precision'] or 0)>=.99
    write(OUT+corpus['corpus_id']+'.json',report);print('Family gate:',report['summary'],'macro',report['macro_precision'],'FP',report['false_positives'],flush=True)
    return report

def official_supplement():
    from benchmarks.round3_audit import load_texts
    docs,families=catalog();values=load_texts();mapping={143:10,165:11,167:12};references=[];rows=[]
    for c in read('benchmarks/manifests/official_documents_v2.json')['cases']:
        if c.get('document_id') not in mapping:continue
        family_id=mapping[c['document_id']];references.append(dict(id=c['id'],document_id=c['document_id'],family_id=family_id,url=c['url'],sha256=c['sha256'],acquired_at=c['acquired_at'],label_basis='Existing catalog document/family identity, not recognition-derived.'))
        r=recognize_document_family(values[c['id']]['text'],families,known_entities=[d.ente for d in docs])
        result=CatalogRecognitionResult(match_type='FAMILY_MATCH' if r.recognized else 'NO_MATCH',confidence_document=0,confidence_family=r.confidence,family=r.family,reason=r.reason)
        rows.append(evaluate_case(dict(id=c['id'],group='document:'+str(c['document_id']),category='real_family_development',expected=dict(match_type='FAMILY_MATCH',family_id=family_id,entity=c['entity'])),result))
    write('benchmarks/manifests/family_official_v1.json',dict(independent=False,cases=references,limits='Supplement available within frozen local development files only. Other family scopes have no independently labelled official files available; synthetic coverage is not a substitute.'))
    write(OUT+'family_official_v1.json',dict(independent=False,summary=summary(rows),cases=rows))

if __name__=='__main__':
    import sys
    if '--build' in sys.argv:build()
    elif '--official' in sys.argv:official_supplement()
    else:run()
