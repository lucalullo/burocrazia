"""Read-only reconstruction of the Round 8 engine and persisted evidence."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import read,catalog,write
from benchmarks.evaluate import summary
from src.recognize import recognize_catalog,recognize_document
from src.fingerprint_decision_v3 import metadata_revision_supported,entity_evidence

OUT='benchmarks/results/round9/'
def main():
    freeze=read('benchmarks/results/round8/freeze.json')
    changed=subprocess.check_output(['git','diff','--name-only',freeze['commit'],'HEAD'],cwd=ROOT,text=True).splitlines()
    protected=[p for p in changed if p.startswith(('src/','data/recognition_profiles/','data/document_recognition_fingerprints')) or p in ['app.py','run.py','benchmarks/round8_fill.py','benchmarks/round8_evaluation.py']]
    assert not protected,protected
    metrics={}
    for n in ['canonical','robustness_v4','scan_v4','filled_v4','historical_development_compat_v2','unknown_v4']:
        r=read('benchmarks/results/round8/'+n+'.json');rows=r['cases']
        metrics[n]=dict(saved=len(rows),exact=sum(c['document_correct'] for c in rows),wrong=sum(c['observed']['match_type']=='DOCUMENT_MATCH' and not c['document_correct'] for c in rows),reject=sum(c['observed']['match_type']=='NO_MATCH' for c in rows),recomputed=summary(rows),status=r.get('status','complete'))
    docs,families=catalog();audit=[]
    for cc in read('tests/fixtures/benchmark_v2.json')['cases']:
        if cc['id'] not in ['EX02MISSINGREV','EX03MISSINGREV']:continue
        diag={};r=recognize_catalog(cc['text'],docs,families,fingerprint_diagnostics=diag);m=recognize_document(cc['text'],docs,known_entities=[d.ente for d in docs])
        audit.append(dict(case_id=cc['id'],corpus='tests/fixtures/benchmark_v2.json',historical_expected=cc['expected'],reference_truth_status='ambiguous',predicted_document=r.document.id if r.document else None,predicted_family=r.family.id if r.family else None,score=r.confidence_document,metadata_score=m.confidence,runner_up=m.confidence-(m.score_margin or 0),margin=m.score_margin,entities=sorted(entity_evidence(cc['text'],[d.ente for d in docs])),version_evidence=diag.get('version_evidence',[]),fingerprint_channels=diag.get('candidates',[])[:2],tier=diag.get('tier'),signals=list(r.document_signals),metadata_revision_inferred=metadata_revision_supported(cc['text'],r.document,docs) if r.document else False,root_cause='Catalog-unique title/code/issuer treated as evidence of a missing revision in metadata_revision_supported; metadata fallback bypasses missing_model_revision veto.',category='version_conflict_not_enforced'))
    original=read('benchmarks/results/round8/evaluation_checkpoint_preserved.json')
    profile=json.loads(next(l for l in (ROOT/'reports/round9-baseline-performance.json').read_text(encoding='utf-8-sig').splitlines() if l.startswith('{')))
    result=dict(branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),entry_working_tree='clean (verified before audit files)',freeze=freeze,post_freeze_files=changed,post_freeze_semantic_files=protected,raw_metrics=metrics,false_accepts=audit,performance=profile,error=dict(errno=22,stage='Path.open(wb) from Path.write_bytes in benchmarks.round3_audit.write, called at round8_evaluation checkpoint',exact_os_cause='undetermined: original log records no winerror, lock owner, filesystem state or OS trace; attributing antivirus/locking would be conjecture',infrastructure_defect='destructive non-atomic rewrite of entire checkpoint for each completed future, without fsync, dedupe or resume',case='A',original_saved=len(original['cases']),historical_completion_permitted=True,historical_completion_performed=False))
    write(OUT+'baseline_audit.json',result)
    (ROOT/'docs/ROUND9_BASELINE_AUDIT.md').write_bytes(('''# Round 9 baseline audit

Branch `{branch}`, HEAD `{head}`; working tree pulito all’ingresso. Freeze motore R8 `{freeze}`. Nessun file del motore, profilo, generatore filled o runner evaluation è cambiato dopo il freeze; i commit successivi riguardano report, audit e package. Elenco completo e metriche ricalcolate: `benchmarks/results/round9/baseline_audit.json`.

Canonical {canonical}/979. V4 originale: 50/356 salvati, {exact} exact, {wrong} wrong, 306 osservazioni indisponibili; non sono fallimenti dedotti. I due falsi accept sono EX02MISSINGREV e EX03MISSINGREV (INPS 13/12, revisione 1.1 assente). La causa è l’inferenza della revisione dalla sola unicità nel catalogo nel fallback metadata; truth ufficiale degli input sintetici ambigua, contratto storico NO mantenuto.

Il log prova OSError errno 22 in Path.open(wb), durante riscrittura evaluation_checkpoint.json. La causa OS esatta non è ricostruibile: mancano winerror, traccia OS e stato dei lock. Il difetto accertato dell’infrastruttura è la riscrittura non atomica, senza fsync/resume. Non viene inventata una causa antivirus. Caso A: completamento storico consentito, facoltativo, non effettuato; originali intatti e nessuna indipendenza R9 attribuita.

Profilo baseline nuovo, processo isolato e input R8 fissi: recognition warm p50 {p50:.2f} ms / p95 {p95:.2f} ms. Componenti e cProfile integrali nel raw; probes non additivi. Il profilo R8 dichiarava p95 350.13 ms; i confronti pagina dominano il costo. OCR/estrazione esclusi dai tempi recognition.

Ripresa: writer transazionale con prove d’interruzione, veto generale della revisione mancante, truth/unknown verificabili, recupero residui e ottimizzazione equivalente prima di qualsiasi freeze v5.
'''.format(branch=result['branch'],head=result['head'],freeze=freeze['commit'],canonical=metrics['canonical']['exact'],exact=metrics['robustness_v4']['exact'],wrong=metrics['robustness_v4']['wrong'],**profile['latency_ms'])).encode())
    print('Baseline complete',len(audit),profile['latency_ms'])
if __name__=='__main__':main()
