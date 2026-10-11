"""Quarantine one confirmed informational file, retaining identity and audit."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
from src.review import submit_document_review

ROOT=Path(__file__).resolve().parents[1]

def main():
    manifest=json.loads((ROOT/'benchmarks/manifests/official_documents_v2.json').read_text(encoding='utf-8'))
    case=next(c for c in manifest['cases'] if c.get('document_id')==429)
    target=ROOT/'maintenance/staging/round2-quarantine/catalog.sqlite3'
    if target.exists():raise ValueError('Staging snapshot already exists')
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'data/catalog_seed.sqlite3',target)
    notes=('Rifiuto tecnico automatico Codex Round 2, non revisione umana né revoca ufficiale. '
           'Il PDF è una spiegazione delle modifiche all art.14 TU115/02 e dell obbligo di pagamento; '
           'non contiene un modulo autonomo da compilare. Identità, metadati e provenienza conservati. '
           f"Evidenza: {case['url']}; SHA-256 {case['sha256']}; benchmark {case['id']}.")
    assert submit_document_review(429,'rifiutato','Codex - audit tecnico automatico Round 2',review_notes=notes,db_path=target)
    print('Prepared explicit technical rejection of 429 in staging; no human verification attributed.')

if __name__=='__main__':main()
