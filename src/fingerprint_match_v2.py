"""Safety-constrained fusion of public v2 signatures. No acquisition imports."""
import re
from src.document_fingerprints import binding
from src.fingerprint_v2 import public_index,features,thresholds,fused
from src.models import RecognitionResult

def safety_reason(text,document,documents,*,exact=False,entities=None):
    from src.recognize import (_issuer_entities,normalize_text,_local_entity_conflict,
        _candidate_annual_model,_annual_version_evidence,_catalog_features,
        _qualifier_conflict,DISTINCT_ENTITY_NAMES)
    if document.stato_verifica in {'demo','rifiutato'}:return 'non_operational'
    opening=text[:2000];normal=normalize_text(opening)
    if entities is None:
        from src.fingerprint_decision_v3 import entity_evidence
        entities=entity_evidence(opening,[d.ente for d in documents]+list(DISTINCT_ENTITY_NAMES))
    entities=entities-{'comune','comuni','regione','regioni','enti locali'}
    if entities and normalize_text(document.ente) not in entities:return 'explicit_entity_conflict'
    if _local_entity_conflict(opening,document.ente):return 'explicit_local_entity_conflict'
    # Exclusive subtype only from a heading. Body fields/references such as
    # 'curatore' within a curatela form do not contradict its title.
    heading=set(normalize_text('\n'.join([s for s in opening[:800].splitlines() if s.strip()][:5])).split())
    heading.update({'vendita'} if 'vendere' in heading else ())
    heading.update({'acquisto'} if 'acquistare' in heading else ())
    if _qualifier_conflict(_catalog_features(document).title_tokens,heading,heading):return 'explicit_subtype_conflict'
    model=_candidate_annual_model(document)
    if model is not None:
        _,conflict=_annual_version_evidence(opening,document,normal)
        if conflict:
            # An exact file may supply a missing year, never another model year.
            if not exact or re.search(r'\b(?:730|cu|certificazione unica|anno|annualit[aà])\s*[:/ -]?\s*(?:19|20)\d{2}\b',opening,re.I):return 'explicit_or_missing_model_year'
    version=document.versione or ''
    if re.fullmatch(r'\d+(?:[.]\d+)+',version):
        observed=set(re.findall(r'\b(?:versione|version|revisione|rev[.])\s*[:=]?\s*(\d+(?:[.]\d+)+)\b',opening,re.I))
        if observed and observed!={version}:return 'explicit_revision_conflict'
        if not exact and not observed:return 'missing_revision'
    elif re.fullmatch(r'(?:19|20)\d{2}',version):
        # Publication year, competence year, cited laws and dated revisions are
        # distinct. Only a declared version/model heading is a hard contradiction.
        observed=set(re.findall(r'^\s*(?:anno|annualit[aà]|versione|revisione|comunicato|modello(?:\s+\w+)?)\s*[:/ -]?\s*((?:19|20)\d{2})\b',opening,re.I|re.M))
        if observed and observed!={version}:return 'explicit_version_year_conflict'
        if not exact and version not in re.findall(r'\b(?:19|20)\d{2}\b',opening):return 'missing_version_year'
    annex=_catalog_features(document).annex
    actual=set(re.findall(r'^\s*Allegato\s+(?:n[.]?\s*)?([1-9]\d?)\b',opening[:300],re.I|re.M))
    if annex and actual and annex not in actual:return 'explicit_annex_conflict'
    return None

def match(text,documents,*,file_sha256=None,visual=(),index=None,reference=False,diagnostics=None):
    index=public_index() if index is None else index
    if not index.records:return None
    docs={d.id:d for d in documents if d.stato_verifica not in {'demo','rifiutato'}}
    from src.recognize import _issuer_entities,DISTINCT_ENTITY_NAMES
    from src.fingerprint_decision_v3 import entity_evidence,tier,profile,VERSION
    entities=entity_evidence(text,[d.ente for d in documents]+list(DISTINCT_ENTITY_NAMES))
    decisions={}
    def safe(i,exact=False):
        key=(i,exact)
        if key in decisions:return decisions[key]
        r=index.records[i];d=docs.get(r['document_id'])
        decisions[key]=d is not None and r['catalog_binding_sha256']==binding(d) and safety_reason(text,d,documents,exact=exact,entities=entities) is None
        return decisions[key]
    if file_sha256:
        ids=index.sha.get(file_sha256,set())
        if len(ids)==1:
            did=next(iter(ids));resources=[i for i,r in enumerate(index.records) if r['document_id']==did and r['canonical_file_sha256']==file_sha256]
            if any(safe(i,True) for i in resources):
                return RecognitionResult(True,100.,docs[did],('official_file_sha256_exact','fingerprint_v2',VERSION,'A_exact_sha'),
                    'File ufficiale canonico identico.',score_margin=100.,candidate_ids=(did,))
    query=features(text)
    if len(query['tokens'])<20:return None
    rows=index.similarities(query,visual,reference);t=profile()
    from src.title_evidence import exact_code_candidates
    codes=set(exact_code_candidates(text,documents,reference=reference))
    choose=lambda r:tier(r,t,code_anchor=r['document_id'] in codes)
    eligible=[r for r in rows if choose(r) and safe(r['resource_index'])]
    if not eligible:
        if diagnostics is not None:
            # Decision reference scans all rows; the user-facing diagnostic
            # describes the same indexed retrieval view in either mode.
            diagnostic_rows=index.similarities(query,visual) if reference else rows
            best=diagnostic_rows[0] if diagnostic_rows else None
            d=docs.get(best['document_id']) if best else None
            diagnostics.update(reason_code=safety_reason(text,d,documents,entities=entities) if d else 'no_candidate',
                tier='D_template_uncertain' if best and choose(best) else 'insufficient_channels',candidate_ids=tuple(r['document_id'] for r in diagnostic_rows[:25]))
        return None
    best=eligible[0]
    # Competing supported identities remain ambiguous even if a competitor is
    # just below its acceptance threshold; don't manufacture a large margin.
    runner=max((r['score'] for r in rows if r['document_id']!=best['document_id'] and r['score']>=best['score']-t['margin'] and safe(r['resource_index'])),default=0.)
    if best['score']-runner<t['margin']:
        if diagnostics is not None:diagnostics.update(reason_code='margin',tier='D_template_uncertain')
        return None
    return RecognitionResult(True,min(99.,80+19*best['score']),docs[best['document_id']],
        ('content_fingerprint_match','fingerprint_v2',VERSION,choose(best),*(f"{k}:{best[k]:.4f}" for k in ['text','chars','anchors','visual'])),
        'Firma del contenuto: '+choose(best)+'; ente e versione compatibili.',
        score_margin=100*(best['score']-runner),candidate_ids=tuple(r['document_id'] for r in rows))
