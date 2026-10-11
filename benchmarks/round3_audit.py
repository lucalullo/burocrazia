"""Audit the frozen Round 2 official development set; extracted text stays ignored."""
from __future__ import annotations
import csv
from collections import Counter
from contextlib import closing
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

from benchmarks.evaluate import metrics, code_hash, verify_locks
from maintenance.fetch import Fetcher
from scripts.verify_catalog import verify
from src.database import list_documents
from src.families import list_document_families
from src.extract import extract_document
from src.text_quality import text_quality
from src import recognize as engine

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'benchmarks/results/round3'
TEXT=ROOT/'benchmarks/work/round3-development-text.json'
CAUSES=('metadata_title_not_present_in_document','code_not_present_in_document','entity_not_present_or_indirect','version_not_present','extraction_noise','pdf_text_order_problem','ocr_problem','generic_title','near_duplicate','recognizer_threshold','candidate_generation','family_missing','family_pattern_missing','source_metadata_wrong','expected_identity_wrong','unsupported_document_structure','other')

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def write(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
def catalog():
    with closing(sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        return list_documents(db),list_document_families(db)
def csv_write(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def load_texts():
    manifest=read('benchmarks/manifests/official_documents_v2.json')
    if TEXT.exists():
        values=json.loads(TEXT.read_text(encoding='utf-8'))
        assert set(values)=={c['id'] for c in manifest['cases']}
        return values
    fetcher=Fetcher(ROOT/'benchmarks/cache',use_cache=True)
    values={}
    for item in manifest['cases']:
        receipt=fetcher.fetch(item['url'],item['source_key']);raw=fetcher.read(receipt)
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        extracted=extract_document(raw,item['id']+'.'+item['format'])
        values[item['id']]=asdict(extracted)
    TEXT.parent.mkdir(exist_ok=True,parents=True);TEXT.write_text(json.dumps(values,ensure_ascii=False),encoding='utf-8')
    return values

def main():
    OUT.mkdir(parents=True,exist_ok=True);verify_locks()
    original=read('benchmarks/results/round2/official_documents_v2.json')
    derived=metrics(original['cases']);assert derived==original['summary']['metrics']
    baseline=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),verification=verify(ROOT/'data/catalog_seed.sqlite3'),
                  original_metrics_recomputed=derived,locked_v1=read('benchmarks/results/round2/final/release_locked_v1.json')['summary'],
                  locked_v2=read('benchmarks/results/round2/final/release_locked_v2.json')['summary'],
                  original_tests=read('docs/validation_latest.json'),code_sha256=code_hash(),executed_at=datetime.now(UTC).isoformat())
    write('benchmarks/results/round3/baseline_recomputed.json',baseline)
    texts=load_texts();docs,families=catalog();by_id={d.id:d for d in docs};audit=[];opportunities=[]
    manifest=read('benchmarks/manifests/official_documents_v2.json')
    for item in manifest['cases']:
        if item.get('expected_match_type')=='NO_MATCH':continue
        d=by_id[item['document_id']];ex=texts[item['id']];text=ex['text'];opening=engine.normalize_text(text[:2000]);tokens=set(opening.split())
        q=text_quality(text);features=engine._catalog_features(d)
        entities=engine._heading_entities(text,[x.ente for x in docs]) or engine._detect_entities(opening,[x.ente for x in docs])
        scores=[];score=engine._score_candidate
        def traced(*args,**kwargs):
            value=score(*args,**kwargs);scores.append(value);return value
        engine._score_candidate=traced
        try:result=engine.recognize_catalog(text,docs,families)
        finally:engine._score_candidate=score
        scores.sort(key=lambda x:x.score,reverse=True)
        expected=next((s for s in scores if s.document.id==d.id),None)
        code_found=bool(features.code and any(features.code_pattern.search(engine.normalize_text(line)) for line in text[:2000].splitlines()))
        title_found=sorted(features.title_tokens & tokens);years=sorted(features.years & set(engine.YEAR_PATTERN.findall(text[:2000])))
        own_entity=features.entity in entities
        if result.document and result.document.id==d.id:cause='other';notes='Correct exact identity at Round 2 baseline.'
        elif d.stato_verifica=='rifiutato':cause='expected_identity_wrong';notes='Frozen expected label points to explicitly rejected informational resource.'
        elif not q['usable']:cause='extraction_noise';notes='Text quality gate.'
        elif features.years and not years:cause='version_not_present';notes='Listing version is not established by opening text.'
        elif features.code and not code_found:cause='code_not_present_in_document';notes='Catalog code absent from opening lines.'
        elif not own_entity:cause='entity_not_present_or_indirect';notes='Issuer not established, or recipient/reference preferred by old heading heuristic.'
        elif len(features.title_tokens)<3:cause='generic_title';notes='Insufficiently distinctive title.'
        elif features.title not in opening:cause='metadata_title_not_present_in_document';notes='Listing title differs from file heading/order/boilerplate.'
        elif result.document_score_margin is not None and result.document_score_margin<5:cause='near_duplicate';notes='Ambiguous identity.'
        else:cause='recognizer_threshold';notes='Remaining score/constraint refusal.'
        family_candidates=[f for f in families if f.ente==d.ente and set(engine.normalize_text(f.nome).split()) & tokens]
        safe=cause in {'metadata_title_not_present_in_document','recognizer_threshold','entity_not_present_or_indirect','code_not_present_in_document'} and q['usable']
        row=dict(case_id=item['id'],source=item['source_key'],entity=d.ente,document_id=d.id,expected_title=d.titolo_ufficiale,expected_code=d.codice or '',expected_version=d.versione or '',file_type=item['format'],extraction_method=ex['method'],extracted_chars=len(text),extracted_text_quality=json.dumps(q),exact_code_found=code_found,title_tokens_found='|'.join(title_found),entity_tokens_found='|'.join(sorted(entities)),year_tokens_found='|'.join(years),expected_family='|'.join(str(f.id) for f in family_candidates),current_result=result.match_type,current_document_id=result.document.id if result.document else '',current_family=result.family.id if result.family else '',current_score=result.confidence_document,runner_up=scores[1].document.id if len(scores)>1 else '',score_margin=result.document_score_margin if result.document_score_margin is not None else '',root_cause=cause,safe_fix_possible='requires evidence' if safe else 'no automatic safe fix',notes=notes,expected_candidate_score=expected.score if expected else 0)
        audit.append(row)
        if result.match_type=='NO_MATCH':
            opportunities.append(dict(case_id=item['id'],document_id=d.id,source=item['source_key'],entity=d.ente,expected_family=row['expected_family'],current_family_candidates='|'.join(f'{f.id}:{f.nome}' for f in family_candidates),missing_anchors='No independently supported family with issuer evidence' if not family_candidates else 'Missing identifying phrases or issuer evidence',safe_family_possible='requires official family evidence',negatives_needed='wrong issuer; instructions; subtype; year conflict; unrelated form',action='Inspect official metadata; do not invent verified family'))
    assert len(audit)==150 and len(opportunities)==123
    csv_write(OUT/'official_positive_audit.csv',audit);csv_write(OUT/'family_opportunities.csv',opportunities)
    report='# Round 3: audit dei 150 positivi ufficiali\n\nIl corpus Round 2 è `official_development_v2`, pubblico e usato per sviluppo. Nessuna indipendenza. Audit iniziale sul motore Round 2; tutti i positivi inclusi, non soltanto i rifiuti. Cause euristiche deterministiche, da distinguere da una revisione editoriale umana. Nessun testo estratto viene pubblicato.\n\n'
    for field in ['source','entity','file_type','exact_code_found','expected_version','root_cause','current_result']:
        report+='## '+field+'\n\n| Valore | N |\n|---|---:|\n'
        counts=Counter(bool(r[field]) if field=='expected_version' else r[field] for r in audit)
        report+=''.join(f'| {k} | {v} |\n' for k,v in sorted(counts.items(),key=lambda x:str(x[0])))+'\n'
    (ROOT/'docs/ROUND3_OFFICIAL_AUDIT.md').write_bytes(report.encode())
    print('Round 2 recomputed; audit',len(audit),'family opportunities',len(opportunities),Counter(r['root_cause'] for r in audit),flush=True)

if __name__=='__main__':main()
