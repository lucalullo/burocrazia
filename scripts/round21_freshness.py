"""Conservative exact normalized-opening dedupe before unknown4 freeze."""
from collections import Counter,defaultdict
from scripts.round21_common import *
from scripts.round21_unknown_truth import balanced_capacity
from maintenance.round21_unknown_acquire import exclusions
from src.recognize import normalize_text
def opening(raw):
    if raw.startswith(b'%PDF'):
        import pymupdf
        with pymupdf.open(stream=raw,filetype='pdf') as p:
            if p.needs_pass or not 1<=len(p)<=100:return ''
            return '\n'.join(p[i].get_text() for i in range(min(2,len(p))))[:2000]
    if raw.startswith(b'PK'):
        from src.extract import extract_document
        return extract_document(raw,'canonical.docx').text[:2000]
    return ''
def main():
    preserved();assert not (OUT/'freeze_manifest.json').exists()
    initial=OUT/'unknown_v4_truth_primary_v2.json'
    if not initial.exists():atomic_json(initial,read(OUT/'unknown_v4_truth_audit.json'))
    audit=read(initial);seen,_=exclusions();old={};errors=Counter()
    for h in sorted(seen):
        p=ROOT/'benchmarks/cache'/(h+'.body')
        if not p.exists():continue
        try:
            text=normalize_text(opening(p.read_bytes()))
            if len(text)>=80:old.setdefault(hashlib.sha256(text.encode()).hexdigest(),h)
        except (ValueError,RuntimeError,OSError) as ex:errors[type(ex).__name__]+=1
    retained=[];groups={};changes=[];decisions={c['SHA256']:c for c in audit['cases']}
    for c in sorted(audit['confirmed_cases'],key=lambda c:c['SHA256']):
        text=normalize_text(opening((ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes()));sig=hashlib.sha256(text.encode()).hexdigest()
        state='duplicate_prior_normalized_opening' if sig in old else 'duplicate_fresh_normalized_opening' if sig in groups else 'confirmed_unknown'
        decisions[c['SHA256']]['normalized_opening_sha256']=sig
        if state!='confirmed_unknown':
            decisions[c['SHA256']]['classification']=state;changes.append(dict(SHA256=c['SHA256'],classification=state,representative_sha256=old.get(sig,groups.get(sig))))
        else:retained.append(c);groups[sig]=c['SHA256']
    counts=Counter(c['source'] for c in retained);balanced=balanced_capacity(counts);n=len(retained)
    final=dict(audit,protocol_version='unknown-v4-primary-v3-exact-opening-dedupe',cases=list(decisions.values()),confirmed_cases=retained,classifications=dict(Counter(c['classification'] for c in decisions.values())),prior_primary_v2_sha256=sha(initial),freshness=dict(excluded_SHA_count=len(seen),prior_readable_openings=len(old),duplicates=changes,parser_errors=dict(errors)),created_at=now())
    save('unknown_v4_truth_audit',final)
    requirements=dict(count=balanced['N']>=100,sources=balanced['sources']>=8,concentration=balanced['max_concentration_upper_bound'] is not None and balanced['max_concentration_upper_bound']<=.25,no_contamination=not {c['SHA256'] for c in retained}&seen,input_supported=True)
    save('unknown_v4_preflight',dict(N=balanced['N'],sources=balanced['sources'],counts_per_source=dict(counts),max_concentration=balanced['max_concentration_upper_bound'],master_N=n,master_max_concentration=max(counts.values())/n if n else None,balanced_capacity=balanced,requirements=requirements,passed=all(requirements.values()),recognition_calls=0,truth_audit_sha256=sha(OUT/'unknown_v4_truth_audit.json'),candidate_pool_sha256=sha(OUT/'unknown_v4_candidates.json'),scope='Exact normalized native opening dedupe excludes known/prior/mirrored inputs and within-master duplicates before freeze. These are conservative exclusions; no scores/predictions, no statistical independence claim for remaining related templates. Balanced capacity is metadata-only, release IDs selected after freeze.'))
    save('unknown_v4_truth_revision_history',dict(initial_auto_sha256=sha(OUT/'unknown_v4_truth_initial_auto.json'),initial_primary_sha256=sha(OUT/'unknown_v4_truth_primary_initial.json'),primary_v2_sha256=sha(initial),final_truth_sha256=sha(OUT/'unknown_v4_truth_audit.json'),all_revisions_before_freeze=True,recognition_calls=0,reasons=['Exclude all known catalog cache resources, including missing active fingerprints.','Require document-kind heading/official local label corroboration, never body citation alone.','Exclude form heading before a normative instrument unless previously confirmed unobserved master truth.','Distinguish explicit primary issuer from institutional source provenance.','Conservatively deduplicate exact normalized first2000-char openings against prior/canonical and fresh master.']))
    print('R21 final fresh unknown master',n,dict(counts),'duplicates',len(changes),'balanced',balanced['N'],'PASS',all(requirements.values()),flush=True)
if __name__=='__main__':main()
