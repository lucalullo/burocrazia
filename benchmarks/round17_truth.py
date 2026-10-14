"""Prediction-free primary review, freshness and independent pool adequacy."""
from collections import Counter
from rapidfuzz.fuzz import ratio
from scripts.round17_common import *
from benchmarks.unknown_release import balance
from benchmarks.round3_audit import catalog
from maintenance.policy import canonical_url
from src.recognize import normalize_text
from src.fingerprint_v3 import features, read_bundle

def adequacy(cases):
    b = balance(cases)
    return dict(**b, passed=b['total']>=100 and b['sources']>=8 and b['max_concentration']<=.25 and b['type_groups']>=5,
                preferred_pass=b['total']>=110 and b['sources']>=10 and b['max_concentration']<=.20)

def opening(c):
    raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==c['SHA256']
    if c['mime']=='application/pdf':
        import pymupdf
        with pymupdf.open(stream=raw,filetype='pdf') as pdf:
            assert not pdf.needs_pass and 1<=len(pdf)<=100
            return '\n'.join(pdf[i].get_text() for i in range(min(2,len(pdf))))[:2000]
    from src.extract import extract_document
    return extract_document(raw,'official.docx').text[:2000]

def review():
    invariant()
    assert not (OUT/'freeze_manifest.json').exists()
    initial=read(OUT/'unknown_v3_truth_audit.json')
    decisions=read(OUT/'unknown_v3_primary_review_decisions.json')
    assert not (OUT/'unknown_v3_primary_truth_review.json').exists(), 'Primary review already completed'
    if (OUT/'unknown_v3_truth_audit_auto.json').exists():
        assert read(OUT/'unknown_v3_truth_audit_auto.json')==initial, 'Partial review snapshot changed'
    else:atomic_json(OUT/'unknown_v3_truth_audit_auto.json',initial)
    old=read('benchmarks/results/round16/unknown_v3_truth_audit.json')['confirmed_cases']
    docs,_=catalog();registry=read(REGISTRY)
    observed=set(registry['observed_resource_sha256'])
    urls={canonical_url(u) for c in registry['unknown_resources'] if c.get('prediction_observed') or c.get('release_v1') or c.get('unknown_development') for u in [c.get('official_url'),c.get('url'),c.get('receipt',{}).get('final_url')] if u}
    urls|={canonical_url(u) for r in read_bundle()['records'] for u in [r['url'],r['final_url']]}
    selected=list(old);queries={c['SHA256']:features(opening(c)) for c in old};reviews=[]
    for c in sorted(initial['confirmed_cases'],key=lambda c:c['SHA256']):
        d=decisions.get(c['case_id'])
        assert d and d['input_sha256']==c['SHA256'] and d['notes'], 'Missing actual primary review'
        text=opening(c);q=features(text)
        c.update(entity=d.get('entity',c['entity']),document_type=d.get('document_type',c['document_type']),title=d.get('title',c['title']),code=d.get('code',c['code']),version=d.get('version',c['version']))
        best=max(((ratio(normalize_text(c['title']),normalize_text(x.titolo_ufficiale)),x.id) for x in docs),default=(0,None))
        collisions=[]
        for h,v in queries.items():
            t=len(q['tokens']&v['tokens'])/max(1,len(q['tokens']|v['tokens']))
            ch=len(q['chars']['4']&v['chars']['4'])/max(1,len(q['chars']['4']|v['chars']['4']))
            if t>=.8 and ch>=.8:collisions.append(dict(sha256=h,token_jaccard=t,char4_jaccard=ch))
        state=d['classification']
        if c['SHA256'] in observed or canonical_url(c['receipt']['final_url']) in urls or canonical_url(c['official_url']) in urls:state='previously_seen'
        elif collisions:state='duplicate'
        elif best[0]>=92:state='ambiguous'
        evidence=dict(case_id=c['case_id'],input_sha256=c['SHA256'],classification=state,notes=d['notes'],entity=c['entity'],title=c['title'],document_type=c['document_type'],
            opening_sha256=hashlib.sha256(text.encode()).hexdigest(),normalized_title_nearest=dict(document_id=best[1],ratio=best[0]),near_fresh_resources=collisions,final_url=c['receipt']['final_url'],recognition_calls=0)
        c['audit_evidence']['round17_primary_review']=evidence
        reviews.append(evidence)
        if state=='confirmed_unknown':
            selected.append(c);queries[c['SHA256']]=q
    assert {c['SHA256'] for c in old}<={c['SHA256'] for c in selected}
    assert len({c['SHA256'] for c in selected})==len(selected)
    primary=dict(recognition_calls=0,reviewer='Codex technical primary-heading review; not human editorial verification',cases=reviews,created_at=now())
    save('unknown_v3_primary_truth_review',primary)
    states={r['case_id']:r['classification'] for r in reviews}
    for row in initial['cases']:
        state=states.get(row['case_id'],row['classification'])
        row['classification']={'possible_document_match':'possible_document','possible_family_match':'possible_family','duplicate_catalog_resource':'duplicate','unsupported_truth':'unsupported_input' if 'Input outside' in row['evidence']['classification_error'] or 'Input exceeds' in row['evidence']['classification_error'] else 'ambiguous'}.get(state,state)
    final=dict(initial,classification_counts=dict(Counter(r['classification'] for r in initial['cases'])),confirmed_cases=selected,confirmed_counts=balance(selected),primary_review_sha256=sha(OUT/'unknown_v3_primary_truth_review.json'),
               inherited_round16_truth_audit_sha256=sha('benchmarks/results/round16/unknown_v3_truth_audit.json'),recognition_calls=0)
    save('unknown_v3_truth_audit',final)
    stats=adequacy(selected)
    save('unknown_v3_preflight',dict(**stats,fresh_confirmed_unknown_total=len(selected),starting_fresh_count=95,new_candidates_acquired=len(initial['cases']),confirmed_new=len(selected)-95,
        input_supported_count=len(selected),contaminated_count=sum(c['classification']=='previously_seen' for c in reviews),ambiguous_count=sum(c['classification']=='ambiguous' for c in reviews),
        classifications=dict(Counter(c['classification'] for c in reviews)),truth_audit_sha256=sha(OUT/'unknown_v3_truth_audit.json'),registry_sha256=sha(REGISTRY),recognition_calls=0,created_at=now()))
    print('R17 fresh preflight',stats,'new',len(selected)-95,flush=True)

if __name__=='__main__': review()
