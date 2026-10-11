"""Evaluation of the official development set, explicitly not independent."""
from __future__ import annotations
from collections import Counter
from datetime import UTC,datetime
import hashlib
import json
import subprocess
import time
from benchmarks.round3_audit import ROOT,read,write,catalog,load_texts
from benchmarks.evaluate import summary,bootstrap,code_hash
from scripts.benchmark import evaluate_case
from src.recognize import recognize_catalog,RULES_VERSION,catalog_revision
from src.text_quality import text_quality


def main():
    manifest=read('benchmarks/manifests/official_documents_v2.json');texts=load_texts();docs,families=catalog();rows=[]
    for item in manifest['cases']:
        negative=item.get('expected_match_type')=='NO_MATCH'
        expected=dict(match_type='NO_MATCH') if negative else dict(match_type='DOCUMENT_MATCH',document_id=item['document_id'],entity=item['entity'],version=item.get('version'))
        # Existing family 10 is explicitly tied to the intervention document in
        # the official catalog, and its fallback is scored separately.
        if not negative and item['document_id']==143:expected['family_id']=10
        ex=texts[item['id']];start=time.perf_counter();result=recognize_catalog(ex['text'],docs,families)
        case=dict(id=item['id'],group='document:'+str(item.get('document_id',item['id'])),category='official_development',source=item['entity'],noise='official_original',expected=expected)
        row=evaluate_case(case,result,(time.perf_counter()-start)*1000)
        row.update(source_key=item['source_key'],file_type=item['format'],extraction_method=ex['method'],quality=text_quality(ex['text']),used_ocr=ex['used_ocr'],page_count=ex['total_pages'],extraction_warning=ex['warning'],input_sha256=item['sha256'],stages=dict(extraction_quality='usable' if text_quality(ex['text'])['usable'] else 'unusable',exact_code_and_title='evaluated',entity_version_constraints='evaluated',document_score=result.confidence_document,family_score=result.confidence_family,decision=result.match_type,conflicts=list(result.conflicts)))
        rows.append(row)
    report=dict(schema_version=3,corpus_id='official_development_v2',independent=False,executed_at=datetime.now(UTC).isoformat(),cases=rows,summary=summary(rows),bootstrap_95=bootstrap(rows),identity=dict(code_sha256=code_hash(),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),rules_version=RULES_VERSION,catalog_file_sha256=hashlib.sha256((ROOT/'data/catalog_seed.sqlite3').read_bytes()).hexdigest(),catalog_semantic_sha256=catalog_revision(docs,families)),limits='Development after repeated use; frozen original labels retained, with explicit existing-family fallback label for document 143. Not an independent gate.')
    write('benchmarks/results/round3/official_development_v2.json',report)
    print('Development:',Counter(r['observed']['match_type'] for r in rows),'correct exact',sum(r['document_correct'] for r in rows),'correct family',sum(r['family_correct'] for r in rows),'wrong',sum(not r['correct'] and r['observed']['match_type']!='NO_MATCH' for r in rows),flush=True)

if __name__=='__main__':main()
