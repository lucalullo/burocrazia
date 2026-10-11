"""Safety gates for public fingerprints; no file I/O or network on uploads."""
import re
from src.document_fingerprints import binding,features,public_index
from src.models import RecognitionResult


def match(text,documents,*,file_sha256=None,field_names=(),index=None,reference=False):
    from src.recognize import (_issuer_entities,normalize_text,_local_entity_conflict,
        _annual_version_evidence,_catalog_features,_qualifier_conflict,_informational_heading,DISTINCT_ENTITY_NAMES)
    index=public_index() if index is None else index
    if not index.records:return None
    docs={d.id:d for d in documents if d.stato_verifica not in {'demo','rifiutato'}}
    entities=_issuer_entities(text,[d.ente for d in documents]+list(DISTINCT_ENTITY_NAMES))
    opening=normalize_text(text[:2000]);opening_tokens=set(opening.split())

    def safe(docid,exact=False):
        d=docs.get(docid);r=index.records.get(docid)
        if not d or not r or r['catalog_binding_sha256']!=binding(d):return False
        if entities and normalize_text(d.ente) not in entities:return False
        if _local_entity_conflict(text,d.ente):return False
        f=_catalog_features(d)
        heading_tokens=set(normalize_text('\n'.join([line for line in text[:800].splitlines() if line.strip()][:5])).split())
        if _qualifier_conflict(f.title_tokens,opening_tokens,heading_tokens):return False
        annexes=set(re.findall(r'^\s*Allegato\s+(?:n[.]?\s*)?([1-9]\d?)\b',text[:300],re.I|re.M))
        if f.annex and annexes and f.annex not in annexes:return False
        _,conflict=_annual_version_evidence(text[:2000],d,opening)
        if conflict:
            # Canonical byte identity may resolve a missing year, never a
            # contradictory explicit model year/revision.
            explicit=re.search(r'\b(?:anno|annualità|annualita|versione|revisione|modello|730|cu|certificazione unica)\s*[:/ -]?\s*(?:19|20)\d{2}\b|\b(?:versione|rev\.)\s*\d+[.]\d+',text[:2000],re.I)
            if not exact or explicit:return False
        if not exact and d.versione:
            # Versioned lookalikes require explicit readable identity evidence.
            if re.fullmatch(r'(?:19|20)\d{2}',d.versione) and d.versione not in re.findall(r'\b(?:19|20)\d{2}\b',opening):return False
            if re.fullmatch(r'\d+(?:[.]\d+)+',d.versione) and not re.search(r'\b(?:versione|version|revisione|rev)\s*'+re.escape(d.versione)+r'\b',text[:2000],re.I):return False
        if not exact and _informational_heading(text):return False
        return True

    if file_sha256:
        ids=index.sha.get(file_sha256,set())
        # A shared attachment/hash collision cannot select an arbitrary ID.
        if len(ids)==1 and safe(next(iter(ids)),exact=True):
            docid=next(iter(ids))
            return RecognitionResult(True,100.0,docs[docid],('official_file_sha256_exact',),
                'File ufficiale canonico identico.',score_margin=100.0,candidate_ids=(docid,))
    query=features(text,field_names)
    if len(query['lexical'])<24:return None
    rows=index.similarities(query,reference=reference)
    eligible=[r for r in rows if r['eligible'] and safe(r['document_id'])]
    if not eligible:return None
    best=eligible[0];runner=eligible[1]['score'] if len(eligible)>1 else 0
    if best['score']-runner<.08:return None
    docid=best['document_id']
    return RecognitionResult(True,min(99.0,80+19*best['score']),docs[docid],
        ('content_fingerprint_match',f"content_containment:{best['containment']:.4f}",
         f"header_containment:{best['header']:.4f}"),
        'Contenuto coerente con una firma tecnica ufficiale.',
        score_margin=100*(best['score']-runner),candidate_ids=tuple(sorted(r['document_id'] for r in rows if r['eligible'])))
