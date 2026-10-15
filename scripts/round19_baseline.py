"""Read-only checks before the first Round19 audit artifact is written."""
import csv
from collections import Counter
from scripts.round19_common import *

def main():
    from scripts.round18_common import sealed as old_sealed
    from benchmarks.round4_common import runtime_hash
    f=old_sealed()
    assert head()==BASE
    # Only these newly added audit helpers may be present at first collection.
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()
    assert not changed
    rows=list(csv.DictReader((ROOT/'benchmarks/results/round18/evaluation_v5_pool_audit.csv').open(encoding='utf8')))
    eligible={int(r['document_id']):r for r in rows if r['eligible']=='True'}
    assert len(eligible)==351 and len({r['source'] for r in eligible.values()})==5
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'benchmarks/results/round18','benchmarks/reference','benchmarks/manifests/official_unknown_release_v3.json','docs/ROUND18_REPORT.md'],cwd=ROOT,text=True).splitlines()
    preserved={p:sha(p) for p in paths}
    # Verify the entire previous round against committed bytes, not just summaries.
    for p in paths:
        raw=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
        assert (ROOT/p).read_bytes()==raw or (ROOT/p).read_bytes().replace(b'\r\n',b'\n')==raw,p
    u=read('benchmarks/results/round18/unknown_release_v3.json')
    assert u['passed'] and u['n']==u['correct_no_match']==116 and u['wrong_document_match']==u['wrong_family_match']==0
    assert runtime_hash()==f['recognition_semantic_sha256']
    post=subprocess.check_output(['git','diff','--name-only',FREEZE,BASE],cwd=ROOT,text=True).splitlines()
    assert not set(post)&set(engine_files())
    save('baseline_audit',dict(entry_commit=BASE,branch='codex/coverage-benchmark-v0.7.0',entry_working_tree='clean',entry_modified=0,entry_untracked=0,
         freeze_commit=FREEZE,recognition_semantic_sha256=runtime_hash(),fingerprint_sha256=f['fingerprint_dataset_sha256'],decision_policy_sha256=f['decision_policy_sha256'],
         preserved_sha256=preserved,post_freeze_changed_paths=post,post_freeze_engine_changes=[],unknown_result_sha256=sha('benchmarks/results/round18/unknown_release_v3.json'),
         round18_pool=dict(identities=351,records=sum(r['eligible']=='True' for r in rows),source_counts=dict(Counter(r['source'] for r in eligible.values()))),checked_at=now()))
    (ROOT/'docs/ROUND19_BASELINE_AUDIT.md').write_text(f'''# Round19 — baseline verificata

Ingresso pulito: branch `codex/coverage-benchmark-v0.7.0`, HEAD `{BASE}`, 0 modificati / 0 non tracciati. Software pubblico0.6.1, schema610.

Freeze candidato riusato `{FREEZE}`. Nessuna modifica successiva nei file motore/catalogo/truth sigillati. Runtime `{runtime_hash()}`, fingerprint `{f['fingerprint_dataset_sha256']}`, decision policy `{f['decision_policy_sha256']}`. Tutti i byte Round18 e reference preesistenti verificati contro Git e vincolati nel JSON audit. L'eccezione storica catalog_manifest CRLF/LF resta invariata.

Unknown v3 PASS116/116,13 fonti,25% concentrazione,0 false DOCUMENT/FAMILY; SHA risultato `{sha('benchmarks/results/round18/unknown_release_v3.json')}`. Manifest/raw/label immutati, nessun replay. Canonici1007/1007, equivalenza1563/0diff, coverage1002/1158, mediana p95234.4921ms, test829/0/3: prove Round18 preservate, distinte dalla validazione finale Round19.

Pool Round18:351 identità /352 record /5 source_id; V5 mai avviata. Prossima attività: definire la semantica identity/representation/source prima del nuovo audit; riesaminare le prove storiche senza modificare motore, catalogo o gate6.
''',encoding='utf8',newline='\n')
    print('R19 baseline PASS; R18 artifacts preserved',len(paths),flush=True)

if __name__=='__main__':main()
