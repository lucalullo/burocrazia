"""Sparse, reproducible technical anchors from official DEVELOPMENT files only."""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from benchmarks.round3_audit import ROOT,read,write,catalog,load_texts
from src.recognize import normalize_text,_heading_entities,_detect_entities
from src.title_evidence import tokens

def fingerprint(document):
    return hashlib.sha256(json.dumps(asdict(document),ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def main():
    manifest=read('benchmarks/manifests/official_documents_v2.json');texts=load_texts();docs,_=catalog();by_id={d.id:d for d in docs}
    heads={c['id']:set(tokens(texts[c['id']]['text'][:800])) for c in manifest['cases']}
    counts=Counter(t for v in heads.values() for t in v);features=[]
    findings=ROOT/'benchmarks/results/round3/official_label_findings.json'
    excluded={r['document_id'] for r in json.loads(findings.read_text(encoding='utf-8'))} if findings.exists() else set()
    for item in manifest['cases']:
        if item.get('expected_match_type')=='NO_MATCH':continue
        d=by_id[item['document_id']]
        if d.stato_verifica in {'demo','rifiutato'} or d.id in excluded:continue
        opening=normalize_text(texts[item['id']]['text'][:2000])
        detected=_heading_entities(texts[item['id']]['text'],[x.ente for x in docs]) or _detect_entities(opening,[x.ente for x in docs])
        if normalize_text(d.ente) not in detected:continue
        # Version support is checked by the engine, not inferred by this generator.
        anchor=sorted(heads[item['id']]-{'moduli','aggior','gennai','firma','cognom','fiscal','codice','nome','sottos','dichiara'},key=lambda t:(counts[t],t))[:8]
        if len(anchor)<8:continue
        features.append(dict(document_id=d.id,catalog_fingerprint=fingerprint(d),anchor_tokens=sorted(anchor),
                             official_url=item['url'],file_sha256=item['sha256'],development_case=item['id'],
                             acquired_at=item['acquired_at'],technical_only=True))
    write('data/recognition_features.json',dict(schema_version=1,version='round3-1',generator='python -m benchmarks.build_recognition_features',split='official_development_v2',independent=False,
          policy='Eight sparse stem tokens from first 800 characters; require explicit matching issuer, no version conflict, unique technical candidate and unchanged catalog record. Tokens are technical derivatives, not official metadata or editorial verification.',features=features))
    print('Technical development anchors:',len(features))

if __name__=='__main__':main()
