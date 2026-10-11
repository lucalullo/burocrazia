"""Quarantine one confirmed informational file, retaining identity and audit."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import sqlite3
import argparse
from src.review import submit_document_review

ROOT=Path(__file__).resolve().parents[1]

def main():
    manifest=json.loads((ROOT/'benchmarks/manifests/official_documents_v2.json').read_text(encoding='utf-8'))
    case=next(c for c in manifest['cases'] if c.get('document_id')==429)
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'maintenance/staging/round2-quarantine-faq/catalog.sqlite3');args=parser.parse_args()
    target=args.output
    if target.exists():raise ValueError('Staging snapshot already exists')
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'data/catalog_seed.sqlite3',target)
    notes=('Rifiuto tecnico automatico Codex Round 2, non revisione umana né revoca ufficiale. '
           'Il PDF è una spiegazione delle modifiche all art.14 TU115/02 e dell obbligo di pagamento; '
           'non contiene un modulo autonomo da compilare. Identità, metadati e provenienza conservati. '
           f"Evidenza: {case['url']}; SHA-256 {case['sha256']}; benchmark {case['id']}.")
    with sqlite3.connect(target) as db:
        if db.execute('SELECT stato_verifica FROM documents WHERE id=429').fetchone()[0]!='rifiutato':
            assert submit_document_review(429,'rifiutato','Codex - audit tecnico automatico Round 2',review_notes=notes,db_path=target)
    observations=json.loads((ROOT/'maintenance/releases/2026-10-11/resource_observations.json').read_text(encoding='utf-8'))
    for identifier in [1077,1081,1091]:
        item=next(o for o in observations if o.get('document_id')==identifier)['observation']
        assert item['ente']=='INAIL' and item['titolo_ufficiale'].casefold().startswith('faq')
        notes=('Rifiuto tecnico automatico Codex Round 2, non revisione umana né revoca ufficiale. '
               'La voce ufficiale è esplicitamente una FAQ, non un modello autonomo da compilare. '
               'Classificazione basata sull elenco, senza attribuire un hash del file non acquisito. '
               f"Titolo: {item['titolo_ufficiale']}; fonte {item['fonte_url']}; download {item['download_url']}; "
               f"SHA-256 risposta elenco {item['response_sha256']}; osservazione {item['acquired_at']}.")
        assert submit_document_review(identifier,'rifiutato','Codex - audit tecnico automatico Round 2',review_notes=notes,db_path=target)
    print('Prepared explicit technical rejection of one informational file and three FAQ records; no human verification attributed.')

if __name__=='__main__':main()
