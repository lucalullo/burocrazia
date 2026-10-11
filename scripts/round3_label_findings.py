"""Explicit pre-holdout review findings; never rewrite frozen development labels."""
from __future__ import annotations
from collections import Counter
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FINDINGS={
 'OR2-017':('expected_identity_wrong','Official file is explicitly COMUNICATO 2022, not a form; frozen positive remains counted.'),
 'OR2-042':('expected_identity_wrong','Official file describes approval of an ENASARCO board resolution, not an autonomous fillable form.'),
 'OR2-071':('expected_identity_wrong','Official file describes an EPAP board resolution, not an autonomous fillable form.'),
 'OR2-076':('source_metadata_wrong','File issuer heading is REGIONE BASILICATA, while catalog source entity is Ministero del Lavoro. Aggregator and issuer differ; safe refusal retained.'),
 'OR2-121':('expected_identity_wrong','Official resource is titled Istruzioni alla compilazione and begins DSU PARTE 1 INTRODUZIONE; not the form.'),
 'OR2-148':('expected_identity_wrong','Official file describes an ENPAF resolution, not an autonomous fillable form.'),
}

def main():
    path=ROOT/'benchmarks/results/round3/official_positive_audit.csv'
    with path.open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    manifest=json.loads((ROOT/'benchmarks/manifests/official_documents_v2.json').read_text(encoding='utf-8'));items={c['id']:c for c in manifest['cases']}
    findings=[]
    for r in rows:
        if r['case_id'] not in FINDINGS:continue
        cause,note=FINDINGS[r['case_id']];r['root_cause']=cause;r['safe_fix_possible']='No recognizer relaxation; source/label review needed';r['notes']=note
        c=items[r['case_id']];findings.append(dict(case_id=c['id'],document_id=c['document_id'],root_cause=cause,note=note,official_url=c['url'],sha256=c['sha256'],frozen_expected_unchanged=True,reviewer='Codex - technical content audit Round 3, not human editorial verification'))
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    target=ROOT/'benchmarks/results/round3/official_label_findings.json';target.write_bytes((json.dumps(findings,ensure_ascii=False,indent=2)+'\n').encode())
    report='# Round 3: audit dei 150 positivi ufficiali\n\n`official_development_v2` è pubblico e usato per sviluppo, non indipendente. Audit iniziale di tutti i 150 positivi sul motore Round 2. Le cause automatiche sono integrate da sei osservazioni esplicite sul contenuto, con URL/hash nel raw. Non è una revisione editoriale umana. Le etichette congelate e i denominatori restano invariati, anche per risorse informative; nessun successo artificiale mediante rietichettatura.\n\n'
    for field in ['source','entity','file_type','exact_code_found','expected_version','root_cause','current_result']:
        counts=Counter(bool(r[field]) if field=='expected_version' else r[field] for r in rows)
        report+='## '+field+'\n\n| Valore | N |\n|---|---:|\n'+''.join(f'| {k} | {v} |\n' for k,v in sorted(counts.items(),key=lambda x:str(x[0])))+'\n'
    report+='## Family fallback\n\nTutti i 123 rifiuti sono in `family_opportunities.csv`. La maggioranza delle 16 famiglie esistenti riguarda ADE/ADER/MIT e non le otto fonti del corpus. Per INAIL e le varianti tutelari mancano famiglie revisionate; aggiungerle come verificate automaticamente violerebbe le istruzioni del progetto. Nessuna nuova verifica attribuita. La regola generale di intestazione completa più ente migliora il fallback delle famiglie già verificate; non identifica emittenti assenti né inventa annualità. Nuove famiglie richiedono fonte, autore/storico e positivi/negativi vicini prima dell’ammissione.\n'
    (ROOT/'docs/ROUND3_OFFICIAL_AUDIT.md').write_bytes(report.encode())
    print('Six explicit source/label findings recorded; frozen labels unchanged.')

if __name__=='__main__':main()
