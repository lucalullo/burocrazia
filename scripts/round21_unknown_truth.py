"""Prediction-free official primary heading/input support review for unknown4."""
import re
from collections import Counter
from rapidfuzz.fuzz import ratio
from scripts.round21_common import *
from benchmarks.round3_audit import catalog
from src.recognize import normalize_text
from maintenance.round21_unknown_acquire import exclusions
from src.extract import extract_document

KINDS=[('circolare',r'\bcircolar[ei]\b'),('decreto',r'\bdecreto\b'),('delibera_determina',r'\b(?:delibera|determinazione|determina)\b'),('guida_manuale',r'\b(?:guida|manuale|istruzioni|linee guida)\b'),('avviso_bando',r'\b(?:avviso|bando|comunicato)\b'),('relazione_piano',r'\b(?:relazione|rapporto|bilancio|piano operativo|programma operativo)\b')]
def primary_kind(text,label):
    lines=[normalize_text(line) for line in text.splitlines() if line.strip()][:30]
    for name,pattern in KINDS:
        if any(re.match(pattern.replace(r'\b',r'\b',1),line) for line in lines[:15]):return name
        # Attachment-local official labels may identify a formal instrument,
        # corroborated by its own operative/issuing text, never a body citation.
        if re.match(pattern,normalize_text(label)) and re.search(r'\b(?:decreta|delibera|determina|il ministro|il direttore|il presidente|istruzioni|guida|manuale)\b',normalize_text(text)):
            return name
    return None
def balanced_capacity(counts):
    for n in range(sum(counts.values()),0,-1):
        cap=n//4;available={s:min(v,cap) for s,v in counts.items()}
        if cap and sum(available.values())>=n and sum(v>0 for v in available.values())>=8:
            return dict(N=n,sources=len(available),per_source_capacity=available,max_concentration_upper_bound=cap/n)
    return dict(N=0,sources=len(counts),per_source_capacity={},max_concentration_upper_bound=None)
def main():
    preserved();assert not (OUT/'freeze_manifest.json').exists()
    excluded,_=exclusions();docs,_=catalog();prospects=read(OUT/'unknown_v4_candidates.json')['candidates'];decisions=[];confirmed=[]
    catalog_titles=[(d.id,normalize_text(d.titolo_ufficiale)) for d in docs]
    from maintenance.round17_unknown_acquire import ENTITIES
    issuer_names=set(ENTITIES.values())|{d.ente for d in docs}|{'Presidenza del Consiglio dei Ministri','Dipartimento della Funzione Pubblica'}
    inherited={c['SHA256']:c for c in read('benchmarks/results/round18/unknown_master_pool.json')['eligible_cases'] if c['SHA256'] not in excluded}
    for c in prospects:
        raw=(ROOT/'benchmarks/cache'/(c['sha256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256'];text='';error=None;pages=None
        try:
            if c['format']=='pdf':
                import pymupdf
                with pymupdf.open(stream=raw,filetype='pdf') as pdf:
                    if pdf.needs_pass or not 1<=len(pdf)<=100:raise ValueError('unsupported_encryption_or_page_limit')
                    pages=len(pdf);text='\n'.join(pdf[i].get_text() for i in range(min(2,len(pdf))))[:2000]
            else:text=extract_document(raw,'official.docx').text[:2000]
            if len(text.strip())<80:raise ValueError('primary_heading_not_legible_without_OCR_review')
        except (ValueError,RuntimeError,OSError) as ex:error=str(ex)
        heading=' '.join(line.strip() for line in text.splitlines() if line.strip())[:500];label=c.get('source_evidence',{}).get('attachment_label','');context=c.get('source_evidence',{}).get('context_heading','')
        normalized=normalize_text(heading);kind=primary_kind(text,label)
        header_lines=[line.strip() for line in text.splitlines() if line.strip()][:12]
        title_options=[normalize_text(t) for t in [label]+[' '.join(header_lines[i:i+3]) for i in range(len(header_lines))] if len(t.strip())>=12]
        nearest=max(((ratio(t,title),did) for did,title in catalog_titles for t in title_options),default=(0,None))
        normalized_lines=[normalize_text(t) for t in header_lines]
        form_index=next((i for i,line in enumerate(normalized_lines) if re.match(r'^(?:mod|modello|modulo|istanza|richiesta|domanda|dichiarazione|scheda|allegato|all)\b',line)),None)
        instrument_index=next((i for i,line in enumerate(normalized_lines) if any(re.match(pattern,line) for _,pattern in KINDS)),None)
        form_precedes=form_index is not None and (instrument_index is None or form_index<instrument_index)
        issuer_hits=sorted([(normalize_text(text[:700]).find(normalize_text(n)),n) for n in issuer_names if len(n)>=12 and normalize_text(n) in normalize_text(text[:700])])
        actual_entity=issuer_hits[0][1] if issuer_hits else c['entity']
        state='unsupported_input' if error else 'catalog_or_prior_resource' if c['sha256'] in excluded else 'ambiguous' if nearest[0]>=92 or form_precedes and c['sha256'] not in inherited else 'confirmed_unknown' if kind or c['sha256'] in inherited else 'insufficient_evidence'
        decision=dict(case_id=c['id'],SHA256=c['sha256'],source=c['source_key'],classification=state,input_supported=not error,primary_opening_sha256=hashlib.sha256(text.encode()).hexdigest(),primary_heading=heading[:180],document_type=kind,nearest_catalog_title=dict(document_id=nearest[1],ratio=nearest[0]),form_heading_precedes_instrument=form_precedes,entity=actual_entity,entity_basis='Explicit primary heading' if issuer_hits else 'Official source provenance; document issuer not separately resolved',primary_issuer_names=[n for _,n in issuer_hits],error=error,recognition_calls=0,notes='Technical primary-heading and official receipt review only; no human editorial verification, no recognition scores/predictions. Catalog-title ambiguity and a form heading before normative citations remain excluded.')
        decisions.append(decision)
        if state=='confirmed_unknown':
            if c['sha256'] in inherited:
                item=dict(inherited[c['sha256']]);item['case_id']='U21-'+c['sha256'][:16];item['audit_evidence']=dict(item.get('audit_evidence',{}),round21_review=decision)
            else:item=dict(case_id='U21-'+c['sha256'][:16],source=c['source_key'],entity=actual_entity,entity_basis=decision['entity_basis'],document_type=kind,title=label or heading[:180],code=None,version=None,SHA256=c['sha256'],mime='application/pdf' if c['format']=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',official_url=c['url'],receipt=c['receipt'],audit_evidence=dict(round21_review=decision),truth_status='confirmed_unknown',expected=dict(match_type='NO_MATCH'),input_supported=True,contamination='fresh',pages=pages)
            confirmed.append(item)
    counts=Counter(c['source'] for c in confirmed);n=len(confirmed);concentration=max(counts.values())/n if n else None
    balanced=balanced_capacity(counts)
    requirements=dict(count=balanced['N']>=100,sources=balanced['sources']>=8,concentration=balanced['max_concentration_upper_bound'] is not None and balanced['max_concentration_upper_bound']<=.25,no_contamination=not {c['SHA256'] for c in confirmed}&excluded,input_supported=all(c.get('input_supported',True) for c in confirmed))
    save('unknown_v4_truth_audit',dict(protocol_version='unknown-v4-primary-v2',cases=decisions,confirmed_cases=confirmed,classifications=dict(Counter(c['classification'] for c in decisions)),recognition_calls=0,reviewer='Codex technical official primary-heading review with stratified heading spot checks; not human editorial verification',created_at=now()))
    save('unknown_v4_preflight',dict(N=balanced['N'],sources=balanced['sources'],counts_per_source=dict(counts),max_concentration=balanced['max_concentration_upper_bound'],master_N=n,master_max_concentration=concentration,balanced_capacity=balanced,requirements=requirements,passed=all(requirements.values()),recognition_calls=0,truth_audit_sha256=sha(OUT/'unknown_v4_truth_audit.json'),candidate_pool_sha256=sha(OUT/'unknown_v4_candidates.json'),scope='Fresh never-predicted master; preflight proves balanced subset capacity without selecting any release IDs. Actual deterministic selection is after freeze and must satisfy the same limits.'))
    print('R21 unknown4 truth',n,dict(counts),'concentration',concentration,'passed',all(requirements.values()),flush=True)
if __name__=='__main__':main()
