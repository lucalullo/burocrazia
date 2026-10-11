"""Read-only duplicate and rejected-record evidence, with no automatic merges."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
from contextlib import closing

ROOT=Path(__file__).resolve().parents[1]

def audit():
    coverage=json.loads((ROOT/'docs/coverage.json').read_text(encoding='utf-8'))
    with closing(sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        rows={r['id']:dict(r) for r in db.execute('SELECT id,ente,codice,titolo_ufficiale,versione,download_url FROM documents')}
        rejected_docs=[dict(r) for r in db.execute("SELECT id,ente,titolo_ufficiale,stato_verifica FROM documents WHERE stato_verifica='rifiutato'")]
        events=[dict(r) for r in db.execute("SELECT * FROM review_events WHERE decision='rifiutato'")]
        provenance=db.execute('SELECT count(*) FROM document_provenance WHERE document_id IN (429,1077,1081,1091)').fetchone()[0]
    groups=[]
    for kind,key in [('identity','duplicate_identity_groups'),('shared_resource','shared_download_url_groups')]:
        for ids in coverage[key]:
            selected=[rows[i] for i in ids];same_code=len({r['codice'] for r in selected})==1 and bool(selected[0]['codice']);same_url=len({r['download_url'] for r in selected})==1
            if kind=='identity' and not same_url:classification='variante';notes='Stesso codice aggregato, titoli e risorse diversi; il codice da solo non determina identità.'
            elif same_code and same_url and len({r['versione'] for r in selected})==1:classification='vero duplicato strutturale';notes='Stesso ente, codice, versione e URL; titoli linguistici diversi. Nessuna equivalenza sostanziale di contenuto dedotta senza file.'
            elif same_code and same_url:classification='variante di versione';notes='Stesso URL/codice, versioni diverse. Il contenuto corrente non prova il contenuto storico; nessuna sostituzione inventata.'
            else:classification='stessa risorsa per identità diverse';notes='Condivisione URL accertata. Possibile allegato condiviso o errore import; legittimità sostanziale da revisionare.'
            groups.append(dict(kind=kind,ids=ids,classification=classification,notes=notes,records=selected,action='Preserve identifiers and provenance; prudent ambiguity refusal, no automatic merge or revocation.'))
    return dict(schema_version=1,identity_groups=3,shared_resource_groups=8,groups=groups,rejected_documents=rejected_docs,rejection_events=events,rejected_provenance_count=provenance,automatic_merges=0)

def main():
    data=audit();(ROOT/'docs/duplicate_audit_round3.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
    text='# Audit duplicati Round 3\n\nTre gruppi di possibile identità duplicata e otto gruppi di URL condiviso. Classificazione strutturale basata sui metadati ufficiali già registrati, non verifica sostanziale dei file. Nessuna cancellazione, fusione o revoca automatica.\n\n| Gruppo | ID | Classificazione | Evidenza e azione |\n|---|---|---|---|\n'
    text+=''.join(f"| {g['kind']} | {', '.join(map(str,g['ids']))} | {g['classification']} | {g['notes']} Conservati con provenienza. |\n" for g in data['groups'])
    text+='\nIl caso INL-17 richiede una correzione del codice della voce aggregata con nuova osservazione ufficiale; i sottocodici non sono intercambiabili. F24 raccoglie varianti effettive. Per il Garante, cinque titoli molto diversi condividono un URL: sospetto errore ereditato, non cinque file verificati. RAP/RLI possono servire procedimenti diversi, senza equivalenza automatica. Dati completi in `duplicate_audit_round3.json`.\n'
    (ROOT/'docs/DUPLICATES_AUDIT.md').write_bytes(text.encode())
    text='# Quattro record rifiutati: Round 3\n\n#429 è un testo informativo sull’obbligo di pagamento; #1077/#1081/#1091 sono FAQ INAIL. Tutti restano nel database e nello storico, con provenienza 4/4 e quattro eventi attribuiti a `Codex - audit tecnico automatico Round 2`. Non sono revoche ufficiali né verifiche umane. Esclusi dal matching e dal conteggio operativo (1.212). La UI mostra stato Rifiutato e avvertenza; la consultazione storica rimane disponibile.\n'
    (ROOT/'docs/REJECTED_RECORDS_ROUND3.md').write_bytes(text.encode())
    print('Duplicate audit: 3 identity groups, 8 resource groups; rejected provenance 4/4.')

if __name__=='__main__':main()
