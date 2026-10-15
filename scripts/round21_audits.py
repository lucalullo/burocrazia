"""Read every confirmed residual development miss without new predictions."""
import csv
from collections import Counter
from scripts.round21_common import *
from benchmarks.release_truth import load_release
from benchmarks.round3_audit import catalog
def main():
    preserved();docs,_=catalog();by={d.id:d for d in docs};raw=read('benchmarks/results/round20/calibration_v6.json');observed=read(raw['observations_path'])['cases']
    qualified={c['input_key'] for c in load_release()[2] if c['truth_domain']!='parser_limit_contract'}
    known=[c for c in observed if c.get('expected') and c['expected']['match_type']=='DOCUMENT_MATCH' and (c['group']!='historical' or c['original_id'] in qualified)]
    misses=[c for c in known if not c['document_correct']];rows=[]
    for c in misses:
        did=c['expected']['document_id'];diag=c['decision_diagnostics'];expected=diag.get('expected_candidate') or {};rank=c['candidate_ids'].index(did)+1 if did in c['candidate_ids'] else None
        runner=max((x['score'] for x in c['top_candidates'] if x['document_id']!=did),default=0.)
        margin=expected.get('score',0)-runner if expected else None;veto=diag.get('expected_veto');tier=diag.get('tier');char=expected.get('chars',0);content=max(expected.get('digital',0),expected.get('ocr',0))
        cause='other';rule='Preserve prudent refusal until corroborated evidence is proved.';possible=False
        if veto and 'entity' in veto:cause='explicit_entity_conflict';rule='Preserve hard issuer conflict.'
        elif veto and any(s in veto for s in ['revision','year','version']):cause='explicit_version_conflict';rule='Preserve explicit version/year conflicts and sibling ambiguity.'
        elif tier=='D_ambiguous':cause='candidate_rank1_but_margin' if rank==1 else 'shared_template';rule='Corroborate the top-ranked page with an exclusive complete heading; retain the global margin and all version siblings.';possible=rank==1
        elif rank==1 and char>=.85 and content>=.8:cause='char_overlap_high_but_unused';rule='Rank1 strong OCR/page containment plus strong chars and identity anchors; no explicit conflict; unchanged margin.';possible=True
        elif rank==1 and content>=.75 and char>=.65:cause='visual_support_high_but_unused';rule='Measure bounded layout only when text/chars/anchors corroborate; accept only a strong independent multichannel tier.';possible=True
        elif c['transform']=='first_page_only':cause='first_page_partial';rule='Use the existing canonical page alignment, never whole-document dilution.'
        elif char<.65 and content<.8:cause='extraction_noise';rule='No acceptance from weak OCR/layout alone; diagnose mixed-script OCR separately.'
        elif rank==1:cause='scan_OCR_low';rule='Preserve refusal unless another strong independent channel is established.'
        rows.append(dict(case_id=c['id'],document_id=did,source=by[did].source_id,transform=c.get('transform') or c['category'],representation_type=c['representation'],expected_rank=rank,expected_score=expected.get('score'),runner_up=runner if expected else None,margin=margin,OCR_score=expected.get('ocr'),char_score=expected.get('chars'),token_score=expected.get('digital'),visual_score=expected.get('visual'),anchor_score=expected.get('anchors'),page_score=expected.get('score'),entity_status='entity_conflict' if veto and 'entity' in veto else 'entity_confirmed' if diag.get('entity_evidence') else 'entity_unknown',version_status='version_conflict' if veto and any(s in veto for s in ['year','revision','version']) else 'version_confirmed' if not by[did].versione or diag.get('version_evidence') else 'version_unknown',decision_tier=tier,reject_reason=veto or diag.get('metadata_veto') or diag.get('reason_code') or 'insufficient_channels',root_cause=cause,safe_accept_possible=possible,proposed_general_rule=rule))
    with (OUT/'dev_false_reject_audit.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    def stats(rs):return dict(n=len(rs),retrieval={str(k):dict(count=sum(r['expected_rank'] is not None and r['expected_rank']<=k for r in rs),fraction=sum(r['expected_rank'] is not None and r['expected_rank']<=k for r in rs)/len(rs)) for k in [1,5,10,25]})
    v5=[r for r in rows if r['case_id'].startswith('DEV5:')]
    save('dev_retrieval_summary',dict(all_confirmed_false_rejects=stats(rows),V5_development_false_rejects=stats(v5),root_causes=dict(Counter(r['root_cause'] for r in rows)),V5_root_causes=dict(Counter(r['root_cause'] for r in v5)),original_observations_sha256=raw['observations_sha256'],recognition_calls=0,policy='Existing page retrieval retained. Expected_id is diagnostic truth only and must never influence runtime acceptance. Missing/unmeasured channel values remain null; visual0 may mean not rendered.'))
    print('R21 false reject audit',len(rows),'V5',len(v5),'rank1',stats(v5)['retrieval']['1'],flush=True)
if __name__=='__main__':main()
