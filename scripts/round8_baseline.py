"""Read-only Round 7 baseline and historical-label inventory, before tuning."""
import argparse,cProfile,hashlib,json,pstats,re,subprocess,sys,time
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import catalog,read,write
from benchmarks.evaluate import summary,quantile,verify_locks
from benchmarks.round7_recognition import checked

OUT='benchmarks/results/round8/baseline/'

def label(e):return tuple(e.get(k) for k in ['match_type','document_id','family_id','entity','version'])

def metrics():
    freeze=checked();verify_locks()
    rows={}
    for n in ['canonical','robustness_v3','scan_v3','filled_v3','unknown_v3']:
        r=read('benchmarks/results/round7/'+n+'.json');s=summary(r['cases'])
        assert s['metrics']==r['summary']['metrics'],n
        rows[n]=dict(metrics=s['metrics'],counts=r['counts'],cases=len(r['cases']))
    bytext=defaultdict(list);byid=defaultdict(list);files={}
    for p in sorted([*ROOT.glob('benchmarks/corpora/*.json'),*ROOT.glob('tests/fixtures/benchmark*.json')]):
        data=json.loads(p.read_bytes());cases=data.get('cases',[]) if isinstance(data,dict) else data
        if not isinstance(cases,list):continue
        files[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        for c in cases:
            if not isinstance(c,dict) or not c.get('text') or not isinstance(c.get('expected'),dict):continue
            item=dict(case_id=c['id'],corpus=p.relative_to(ROOT).as_posix(),expected=c['expected'],text_sha256=hashlib.sha256(c['text'].encode()).hexdigest(),text=c['text'])
            key=re.sub(r'\s+',' ',c['text'].casefold()).strip()
            bytext[key].append(item);byid[c['id']].append(item)
    conflicts=[dict(kind='same_normalized_text',cases=v) for v in bytext.values() if len({label(x['expected']) for x in v})>1]
    changes=[dict(kind='same_case_id_different_expectation',cases=v) for v in byid.values() if len({label(x['expected']) for x in v})>1]
    raw={}
    for round_no in [6,7]:
        for p in sorted((ROOT/f'benchmarks/results/round{round_no}').rglob('*.json')):
            raw[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    write(OUT+'metrics.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),working_tree=subprocess.check_output(['git','status','--porcelain'],text=True).splitlines(),freeze=freeze,raw_metrics=rows,corpus_sha256=files,prior_raw_sha256=raw))
    write(OUT+'contradictions.json',dict(exact_text_conflicts=conflicts,case_id_label_changes=changes,scope='All text cases in public corpora and benchmark fixtures. Case-ID changes can be intentional revised inputs and require classification; normalized-text conflicts are direct contradictions.'))
    # An optional operator prompt must be supplied explicitly, never from a personal path.
    prompt_path=__import__('os').environ.get('BUROCRAZIA_ROUND8_PROMPT')
    if prompt_path:
        (ROOT/'tmp-build').mkdir(exist_ok=True)
        (ROOT/'tmp-build/ROUND8_PROMPT.md').write_bytes(Path(prompt_path).read_bytes())
    print('Baseline raw verified; direct contradictions',len(conflicts),'case-ID changes',len(changes), 'prior raw',len(raw))

def profile():
    from benchmarks.round6_recognition import raw_record
    from src.extract import extract_document
    from src.fingerprint_visual import visual_for_bytes
    from src.fingerprint_v2 import read_bundle,public_index,features,visual_similarity,overlap
    import src.recognize as recognition
    import src.fingerprint_match_v2 as matcher
    docs,families=catalog();index=public_index();cases=[]
    for c in read('benchmarks/corpora/development_regression.json')['cases']:cases.append((c['text'],()))
    for item in read('benchmarks/results/round7/baseline/performance_sample.json')['resources']:
        r=next(r for r in read_bundle()['records'] if r['document_id']==item['document_id'] and r['canonical_file_sha256']==item['sha256'])
        raw=raw_record(r);name='canonical'+('.pdf' if r['mime_type']=='application/pdf' else '.docx')
        cases.append((extract_document(raw,name).text,visual_for_bytes(raw,name)))
    for text,visual in cases:recognition.recognize_catalog(text,docs,families,visual_fingerprint=visual)
    samples=defaultdict(list)
    def timed(name,fn):
        start=time.perf_counter();result=fn();samples[name].append((time.perf_counter()-start)*1000);return result
    for _ in range(6):
        for text,visual in cases:
            timed('recognition_total',lambda:recognition.recognize_catalog(text,docs,families,visual_fingerprint=visual))
            timed('normalization',lambda:recognition.normalize_text(text[:2000]))
            query=timed('input_fingerprint_generation',lambda:features(text))
            ids=timed('candidate_retrieval',lambda:list(index.candidates(query,visual)))
            def ocr_compare():
                return [sum(index.weights.get(h,1) for h in index.records[i]['ocr'] if h in query['tokens'])/index.denominators[i][1] if index.denominators[i][1] else 0 for i in ids]
            timed('ocr_sketch_compare',ocr_compare)
            timed('char_overlap',lambda:[overlap(index.records[i]['chars'],query['chars']) for i in ids])
            timed('visual_compare',lambda:[visual_similarity(visual,index.records[i]['visual']) for i in ids])
            timed('decision_fusion_inclusive',lambda:matcher.match(text,docs,visual=visual,index=index))
            timed('family_fallback',lambda:recognition.recognize_document_family(text,families,known_entities=[d.ente for d in docs]))
    prof=cProfile.Profile();prof.enable()
    for text,visual in cases:recognition.recognize_catalog(text,docs,families,visual_fingerprint=visual)
    prof.disable();stats=pstats.Stats(prof)
    top=[dict(file=Path(file).name,line=line,function=name,calls=v[1],own_seconds=v[2],cumulative_seconds=v[3]) for (file,line,name),v in sorted(stats.stats.items(),key=lambda kv:-kv[1][3])[:40]]
    report=dict(cases=len(cases),repetitions=6,components={k:dict(n=len(v),p50=quantile(v,.5),p95=quantile(v,.95),p99=quantile(v,.99)) for k,v in samples.items()},cprofile=top,scope='Isolated warm Round7 baseline. Phase probes repeat primitives outside total recognition and are non-additive; fusion includes retrieval/compare. OCR and visual generation excluded from recognition_total.')
    write(OUT+'performance_profile_components.json',report);print(json.dumps(report['components'],indent=2))

def finish():
    m=read(OUT+'metrics.json');p=read(OUT+'performance_profile_components.json');c=read(OUT+'contradictions.json')
    log=(ROOT/'reports/round8-baseline-tests.log').read_bytes();match=re.search(rb'(\d+) passed, (\d+) skipped in ([\d.]+)s',log);assert match and b' failed' not in log
    tests=dict(passed=int(match[1]),skipped=int(match[2]),failed=0,seconds=float(match[3]),log_sha256=hashlib.sha256(log).hexdigest());write(OUT+'tests.json',tests)
    rows='\n'.join(f"| {k} | {v['p50']:.3f} | {v['p95']:.3f} |" for k,v in p['components'].items())
    text=f"""# Round 8 — audit baseline prima delle modifiche runtime

Branch `{m['branch']}`, ingresso `{m['commit']}`. Working tree iniziale pulito prima della creazione dello script di audit. Software 0.6.1, schema 610; catalogo e corpus congelati invariati. Nessun push/tag/release.

Raw Round 7 ricalcolati dai casi: canonical 979/979; robustness 183/372 (49.1935%); scansioni 134/280 (47.8571%); filled 7/50, con soltanto 9 generati e 41 generation failures. Zero wrong accepted. I risultati R6/R7 diventano development; non sono prova indipendente Round 8. File coverage 941/1158 (81.2608%), totale 941/1212 (77.6403%). Il vecchio p95 registrato era 444.6542 ms.

Suite completa iniziale: {tests['passed']} passati, {tests['skipped']} saltati, 0 falliti, {tests['seconds']} s; log SHA `{tests['log_sha256']}`. {len(m['prior_raw_sha256'])} JSON R6/R7 conservati per hash. Le misure non vengono sostituite.

Inventario etichette prima del tuning: {len(c['exact_text_conflicts'])} gruppi con testo normalizzato identico e expected discordanti; {len(c['case_id_label_changes'])} case_id con expected differenti, inclusi cambi di input intenzionali da distinguere dalle contraddizioni. Registro riconciliato separato, mai riscrittura dei locked.

## Profilo warm per componente

51 input fissi (35 sintetici e 16 risorse ufficiali già usate in R7), 6 ripetizioni. Probes dei componenti non additivi: ripetono la primitiva fuori dalla misura totale, senza costo Tesseract o rendering. cProfile separato per la diagnosi delle funzioni.

| Componente | p50 ms | p95 ms |
|---|---:|---:|
{rows}

Raw: `benchmarks/results/round8/baseline/`; full scan e sicurezza storica restano i riferimenti. Nessuna nuova identità o fonte autorizzata.

## Interferenza individuata

Un helper diagnostico di questa stessa attività, avviato nel Round 7 con `run_benchmark()` da stdin, era rimasto attivo e consumava CPU. La sua identità e gerarchia di processi sono state verificate prima di terminarlo. La suite iniziale ha condiviso parte della CPU con questo helper; il profilo warm riportato sopra è stato eseguito dopo la sua terminazione e dopo la suite. Le precedenti misure R7 sono conservate, ma l'interferenza limita il confronto dei tempi assoluti. Non vengono sostituite con il nuovo numero.
"""
    (ROOT/'docs/ROUND8_BASELINE_AUDIT.md').write_bytes(text.encode());print('Baseline audit complete')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['metrics','profile','finish']);args=a.parse_args();globals()[args.mode]()
