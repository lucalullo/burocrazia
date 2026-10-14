"""Audit unchanged recognition and prior generation failures without recognition."""
import csv
from collections import Counter
from scripts.round22_common import *

def main():
    assert not (OUT/'baseline_audit.json').exists();f=boundary();assert head()==BASE
    assert not (ROOT/'benchmarks/results/round21/evaluation_v6_started.json').exists()
    assert not (ROOT/'benchmarks/results/round21/evaluation_v6_observations.json').exists()
    assert not (ROOT/'benchmarks/work/round21/evaluation_v6.sqlite').exists()
    from scripts.round21_common import preserved
    preserved()
    p=read('dist/package-verification-round21.json');assert sha('dist/'+p['archive'])==p['sha256']
    status=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT,text=True).splitlines()
    files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    allowed={'benchmarks/latest_summary.json','docs/BENCHMARK.md','docs/release_gates.json','scripts/package_candidate.py','AGENTS.md','docs/CONTINUITA_OPERATIVA.md'}
    protected={n:sha(n) for n in sorted(set(files)) if n not in allowed and 'round22' not in n and (ROOT/n).is_file()}
    save('baseline_audit',dict(entry_head=BASE,entry_branch='codex/coverage-benchmark-v0.7.0',source_tree_round21=ROUND21_TREE,working_tree=status,modified_count=sum(x[:2]!='??' for x in status),untracked_count=sum(x[:2]=='??' for x in status),protected_sha256=protected,original_index_sha256=sha('.git/index'),round21_archive_sha256=p['sha256'],baseline_tests=read('benchmarks/results/round21/final_tests_on_freeze.json'),unknown_v4_recognition_calls=120,V6_recognition_calls=0,leakage=read('benchmarks/results/round21/evaluation_v6_leakage.json'),created_at=now()))
    files=recognition_files();save('recognition_freeze_check',dict(recognition_files_sha256=files,recognition_semantic_sha256=f['recognition_semantic_hash'],fingerprint_policy_sha256={p:h for p,h in files.items() if 'fingerprint' in p and p.startswith('src/')},decision_v7_sha256=sha('data/recognition_profiles/fingerprint_decision_v7.json'),source_profile_sha256={p:h for p,h in files.items() if 'source' in p and 'profiles' in p},catalog_semantic_sha256=catalog_semantic(),fingerprint_dataset_sha256=sha('data/document_recognition_fingerprints_v3.json'),unknown_v4_engine_sha256=read('benchmarks/results/round21/unknown_release_v4.json')['identity']['runtime_sha256'],matches_round21=True,recognition_calls=0,checked_at=now()))
    import pymupdf
    plan=read('benchmarks/results/round21/evaluation_v6_plan.json');by={c['document_id']:c for c in plan['selected']}
    failed=[r for r in read('benchmarks/results/round21/evaluation_v6_prepared.json')['generation_audit'] if r['filled'] and not r['generated']];assert len(failed)==25
    rows=[];stats={};folder=WORK/'audit';folder.mkdir(parents=True,exist_ok=True)
    for did in sorted({r['document_id'] for r in failed}):
        c=by[did];raw=(ROOT/'benchmarks/cache'/(c['canonical_sha']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['canonical_sha']
        with pymupdf.open(stream=raw,filetype='pdf') as pdf:
            widgets=[w for p in pdf for w in (p.widgets() or ())]
            stats[did]=dict(source=c['source_id'],pages=len(pdf),widget_count=len(widgets),acroform_present=bool(widgets),page_rect=list(pdf[0].rect),words=len(pdf[0].get_text('words')),drawings=len(pdf[0].get_drawings()))
            pdf[0].get_pixmap(matrix=pymupdf.Matrix(1,1)).save(folder/(str(did)+'-original.png'))
    for r in failed:
        s=stats[r['document_id']];rows.append(dict(case_id=r['case_id'],document_id=r['document_id'],source=s['source'],canonical_format='application/pdf',generator_mode='static_overlay_after_native_attempt',acroform_present=s['acroform_present'],widget_count=s['widget_count'],pages=s['pages'],attempted_operation='Place seven fixed-width245x12 overlay lines on first page, two fixed x origins and17point y grid',generated=False,reopen_success=False,synthetic_values_verified=False,template_integrity_ok='canonical source unchanged; no output',failure_stage='safe_rectangle_search',exception_type='ValueError',exception_message=r['error'].removeprefix('ValueError: '),root_cause='static_overlay_failure',safe_fix_possible=True,notes='Fixed wide boxes require every one of7 lines; preserve all failures, design generic deterministic content/raster whitespace placement with bounded adaptive widths, multi-page search and validated partial overlays before any aggregate regeneration. No recognition calls.'))
    with (OUT/'filled_generation_failure_audit.csv').open('w',encoding='utf8',newline='') as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    save('filled_failure_geometry',dict(documents=stats,recognition_calls=0,canonical_bytes_unchanged=True))
    text=f'''# Round22 — baseline audit

Branch `codex/coverage-benchmark-v0.7.0`,HEAD `{BASE}`. Working tree inherited unchanged:12 modified/156 untracked at delivery Round21; new audit helpers are additive. Original index `{sha('.git/index')}`. Round21 archive `{p['sha256']}` verified; protected public files and previous evidence are hashed in baseline_audit.json. No commit/push/tag/release.

Runtime `{f['recognition_semantic_hash']}` and every recognition/profile/catalog/dataset byte match Round21. Unknown4 manifest/raw SHA verified:120/120 correct rejection,0FA,compatible runtime. Never replay unknown4. V6 marker,raw and journal absent:0 predictions. Selected40IDs/8sources and639reserved pool unchanged; leakage0. Existing tests878/0/3 are the unchanged entry baseline,not a duplicated run.

Generation100attempts/75valid/25failed: five variants each of IDs484,264,263,558,414. Error `No safe blank overlay rectangle`; source metadata `{stats}`. Three unrelated normalized DOCX C14N failures remain preserved,not repaired in this generator-only round. Existing497 nonfilled representations are unpredicted and eligible to carry forward with exact hashes and the original plan. Old75filled outputs also remain preserved; all100 will be regenerated under a separately frozen v2 policy before any V6 prediction.

Only new generator,validation,runner/checkpoint and infrastructure docs/tests may change. Every old recognition test is protected. A new content-addressed evaluation freeze replaces no prior freeze and creates no commit. Official Goal active; former heartbeat absent,so no periodic automatic wakeup is claimed. Checkpoints persist privately and resume verifies actual outputs/processes first.
'''
    (ROOT/'docs/ROUND22_BASELINE_AUDIT.md').write_text(text,encoding='utf8',newline='\n')
    (ROOT/'docs/ROUND22_FILLED_GENERATION_AUDIT.md').write_text('# Round22 — filled generation audit\n\nAll25 failures: static_overlay_failure, first-page fixed wide rectangle search. Original sources remain byte-identical. See CSV for every original case and filled_failure_geometry.json for five canonical layouts. Images are private benchmark work; no recognition was invoked. Policy v2 will be fixed before aggregate generation; no replacement of selected IDs or seeds.\n',encoding='utf8',newline='\n')
    boundary();checkpoint('Round22 baseline and25 generation-failure audit complete','Recognition/unknown4/old evidence verified unchanged. V6 predictions0. Only generation work authorized.', 'Inspect five original page layouts; define and freeze filled policy v2 before aggregate corrections; add synthetic generator tests.')
    print('R22 baseline verified',len(protected),'protected files;25failures,5IDs;0recognition calls',flush=True)

if __name__=='__main__':main()
