"""Re-evaluate development and historical evidence; never an independent test."""
from collections import Counter
import time
from benchmarks.round4_common import OUT, ROOT, catalog, read, write, texts, runtime_hash
from benchmarks.round3_audit import load_texts
from benchmarks.evaluate import summary, code_hash
from scripts.benchmark import evaluate_case
from src.recognize import recognize_catalog, normalize_text, _issuer_entities, _catalog_features

CAUSES = ('title_absent', 'indirect_entity', 'code_absent', 'version_absent', 'generic_template', 'metadata_inconsistent', 'extraction', 'source_structure', 'family_opportunity', 'insufficient_evidence')

def evaluate(manifest, values):
    docs, families = catalog(); rows = []
    for c in manifest['cases']:
        expected = dict(match_type='NO_MATCH') if c.get('expected_match_type') == 'NO_MATCH' else dict(match_type='DOCUMENT_MATCH', document_id=c['document_id'], entity=c['entity'], version=c.get('version'))
        ex = values[c['id']]; start = time.perf_counter()
        result = recognize_catalog(ex.get('text',''), docs, families)
        row = evaluate_case(dict(id=c['id'],group='document:'+str(c.get('document_id',c['id'])),category='official_diagnostic',expected=expected), result, (time.perf_counter()-start)*1000)
        row.update(source_key=c['source_key'], file_type=c['format'], extraction_failed=bool(ex.get('extraction_failed')), extraction_method=ex.get('method'), used_ocr=ex.get('used_ocr',False))
        rows.append(row)
    extracted = [r for r in rows if not r['extraction_failed']]
    return dict(schema_version=1, independent=False, runtime_sha256=runtime_hash(), code_sha256=code_hash(), cases=rows, summary=summary(rows), extraction=dict(success=len(extracted),total=len(rows),conditional_matching=summary(extracted),end_to_end=summary(rows)))

def blockers():
    before=read(OUT+'false_acceptance_before.json'); manifest,values=texts('official_holdout_v1',{r['case_id'] for r in before})
    after=evaluate(dict(cases=[c for c in manifest['cases'] if c['id'] in values and c['id'] in {r['case_id'] for r in before}]),values)
    causes = {
        'OH1-033': ('shared_code_pattern','A complete segmented model code outranks a generic onorificenza title, subject to issuer/version gates.','Prioritize exact code; preserve shared-code ambiguity.','test_segmented_code_over_generic_title'),
        'OH1-047': ('generic_title_overmatch','A short body phrase is not a form title even when its issuer is mentioned. The frozen judicial label and ADE file heading are inconsistent; neither is silently relabelled.','Require a short title in the heading or an exact code.','test_generic_body_title_not_identity'),
        'OH1-055': ('wrong_year_tolerated','An unversioned title must not absorb an explicitly annual peer with unsupported table years.','Catalog-derived annual-peer gate; no year inferred from a three-year table.','test_unversioned_annual_peer_refuses_table_years'),
        'OH1-063': ('generic_title_overmatch','A referenced Quadro C is not the heading of the annual rate communication.','Require a heading/code for short titles.','test_generic_body_title_not_identity'),
        'OH1-098': ('technical_anchor_overfit','Shared blank-form anchors cannot override an incompatible tutore/curatore subtype.','Declarative exclusive subtype contradiction gate.','test_exclusive_qualifiers_override_technical_anchors')}
    rows=[]; md='# Round 4 — false acceptance audit\n\nHistorical holdout v1 is now development diagnostics. Original bytes and labels are retained. Listing/file discrepancies below require human adjudication; a refusal is the safe result. Scores are evidence points, not probabilities.\n\n'
    for b in before:
        a=next(r for r in after['cases'] if r['id']==b['case_id']);cause,rule,fix,test=causes[b['case_id']]
        row=dict(b,root_cause=cause,general_rule_violated=rule,minimal_safe_fix=fix,regression_test=test,after=a,safer_after=a['document_correct'] or a['observed']['match_type']=='NO_MATCH')
        rows.append(row)
        md+=f"## {b['case_id']}\n\nExpected: `{b['expected']}`. Before: `{b['observed']}`. Score {b['score']}; runner `{b['runner_up']}`; margin {b['margin']}. Strong signals: {b['strong_signals']}; weak: {b['weak_signals']}. Ignored/unrepresented contradictions: {b['contradictions_ignored'] or 'not represented by old scoring; see rule below'}.\n\nCause: `{cause}`. {rule} Fix: {fix} Test: `{test}`. After: `{a['observed']}`; safe: {row['safer_after']}.\n\n"
    write(OUT+'false_acceptance_after.json',rows);(ROOT/OUT/'false_acceptance_audit.md').write_text(md,encoding='utf-8')
    assert all(r['safer_after'] for r in rows)
    print('Five historical blockers safe:',sum(r['safer_after'] for r in rows),flush=True)

def main():
    blockers();manifest=read('benchmarks/manifests/official_documents_v2.json');values=load_texts()
    report=evaluate(manifest,values);report['corpus_id']='official_development_v2';write(OUT+'development_after.json',report)
    docs,families=catalog();by_id={d.id:d for d in docs};clusters=[]
    for c,r in zip(manifest['cases'],report['cases']):
        if c.get('expected_match_type')=='NO_MATCH' or r['document_correct']:continue
        d=by_id[c['document_id']];text=values[c['id']]['text'];opening=normalize_text(text[:2000]);features=_catalog_features(d)
        if r['extraction_failed']:cause='extraction'
        elif d.stato_verifica=='rifiutato':cause='metadata_inconsistent'
        elif features.years and not features.years & set(__import__('re').findall(r'\b(?:19|20)\d{2}\b',text[:2000])):cause='version_absent'
        elif features.entity not in _issuer_entities(text,[x.ente for x in docs]):cause='indirect_entity'
        elif features.code and features.code not in opening:cause='code_absent'
        elif len(features.title_tokens)<4:cause='generic_template'
        elif features.title not in opening:cause='title_absent'
        elif r['observed']['match_type']=='FAMILY_MATCH':cause='family_opportunity'
        else:cause='insufficient_evidence'
        clusters.append(dict(id=c['id'],document_id=d.id,source=c['source_key'],cause=cause,result=r['observed'],safe_action='No inferred issuer/year/title; official identity or extraction evidence and paired hard negatives required.'))
    write(OUT+'development_rejection_clusters.json',dict(taxonomy=CAUSES,counts=dict(Counter(c['cause'] for c in clusters)),cases=clusters))
    manifest,values=texts('official_holdout_v1');historical=evaluate(manifest,values);historical['corpus_id']='official_holdout_v1_historical';write(OUT+'historical_holdout_diagnostic.json',historical)
    print('Development:',report['summary'],'historical:',historical['summary'],flush=True)

if __name__=='__main__':main()
