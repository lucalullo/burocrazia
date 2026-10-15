"""Local pre-prediction truth review; never calls a recognition function.

Correct provisional metadata using primary headings and actual catalog evidence.
The automatic audit is retained; correlated near-resource components contribute
one representative, chosen by SHA before any predictions.
"""
import copy,csv,re
from collections import Counter,defaultdict
from io import BytesIO
import pymupdf
from scripts.round16_common import *
from benchmarks.unknown_release import balance
from benchmarks.round3_audit import catalog
from src.fingerprint_v3 import read_bundle

def opening(c):
    raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['SHA256']
    if c['mime']=='application/pdf':
        with pymupdf.open(stream=raw,filetype='pdf') as pdf:return '\n'.join(pdf[j].get_text() for j in range(min(2,len(pdf))))[:2000]
    from docx import Document
    return '\n'.join(p.text for p in Document(BytesIO(raw)).paragraphs)[:2000]

def main():
    sealed();assert not (ROOT/'benchmarks/manifests/official_unknown_release_v3.json').exists(),'Truth fixed before predictions'
    path=OUT/'unknown_v3_truth_audit.json';auto=read(path);assert 'manual_review_sha256' not in auto
    backup=OUT/'unknown_v3_truth_audit_auto_before_review.json'
    if backup.exists():backup=OUT/('unknown_v3_truth_audit_auto_'+sha(path)[:12]+'.json')
    backup.write_bytes(path.read_bytes())
    docs,_=catalog();mef=[d.id for d in docs if 'RGS' in d.ente];agid=[d.id for d in docs if 'agid' in d.ente.lower() or 'italia digitale' in d.ente.lower()]
    assert not agid and mef==list(range(594,609))
    canonical582=next(r for r in read_bundle()['records'] if r['document_id']==582)
    reviewed=[];eligible=[]
    for original in auto['confirmed_cases']:
        c=copy.deepcopy(original);text=opening(c);flat=' '.join(text.replace('\u200b','').split());normal=flat.casefold();notes=[];status='confirmed_unknown';allowed=True
        # Primary PDF images were inspected for these four official letters.
        if c['case_id'] in ['U16-04774885d351cc0c','U16-2b9e01e915ca49f0','U16-83d4b269e550666d','U16-a7681bf22a185134']:
            c['entity']='Ministero dell’Interno';notes.append('First-page graphic heading literally Ministero dell’Interno, Gabinetto del Ministro. Citation of Prefettura in body is not issuer; local rendered header contact sheet inspected.')
        if c['source']=='agid':
            if normal.startswith('il presidente del consiglio dei ministri'):
                c['entity']='Presidente del Consiglio dei Ministri';notes.append('Literal primary issuing authority, not hosting AGID cited in the body.')
            elif 'ministro per l’innovazione tecnologica e la digitalizzazione' in normal[:500]:
                c['entity']='Ministro per l’innovazione tecnologica e la digitalizzazione';notes.append('Literal ministerial issuing role in primary heading.')
            elif normal.startswith('il ministro per l’innovazione tecnologica e la transizione digitale'):
                c['entity']='Ministro per l’innovazione tecnologica e la transizione digitale';notes.append('Literal ministerial issuing role in primary heading.')
        if c['source']=='mef':
            c['entity']="Ministero dell'Economia e delle Finanze / RGS"
            notes.append('Official revisionelegale.rgs.mef.gov.it resource and RGS/IGF departmental content; compound issuer spelling matches existing catalog, not a new alias or runtime rule.')
        if c['case_id']=='U16-9cc12ce840ecb6ff':
            assert normal.startswith('il ministro delle imprese e del made in italy')
            c['entity']='Ministero delle Imprese e del Made in Italy';notes.append('Current literal primary heading; historical Ministry name occurs only in cited previous legislation.')
        if c['case_id']=='U16-c00b52f57a957e53':
            c['entity']='Agenzia per la Cybersicurezza Nazionale / Garante per la protezione dei dati personali';notes.append('ACN literal cover and official attachment title ACN-GPDP establish joint publishers; a single hosting-entity label was incomplete.')
        if c['case_id']=='U16-624988878bfdd82f':
            c['entity']="Ministro delle Imprese e del Made in Italy / Ministro della Giustizia / Sottosegretario alla Presidenza del Consiglio per l'Innovazione Tecnologica";c['document_type']='specifiche_tecniche';notes.append('Literal first-page joint issuing roles and heading ALLEGATO TECNICO, SPECIFICHE TECNICHE. Hosting Giustizia alone is not the complete publisher; attachment is not the parent decree.')
        if c['case_id']=='U16-1217c6003f432da5':
            c['document_type']='istanza';notes.append('Independent form qualification: accreditation of training providers, not reviewer registration/exam/traineeship/cancellation. All15 MEF/RGS catalog identities594..608 inspected; different purpose and title, no code/fingerprint/family match. A cited decreto is not this form’s primary type.')
        if c['case_id']=='U16-3896ed6121e9831a':
            c['document_type']='convenzione';notes.append('Independent form qualification: template agreement for reviewer training providers, absent from complete MEF/RGS catalog594..608. Cited statute does not make it a decree.')
        if c['case_id']=='U16-ecefa8c6722ba7f9':
            c['document_type']='modello';notes.append('Independent form qualification: AGID accessibility self-assessment; no AGID document identity exists in the unchanged complete catalog. Literal heading and official issuer, no technical-near/family/code relation.')
        if c['case_id'] in ['U16-71017808173cb6ef','U16-a44e0b2c4dc6621c']:
            c['document_type']='guida';notes.append('Literal Regole di compilazione:30/37-page usage guide, not the application or a decree merely cited in the title.')
        if c['case_id']=='U16-afa8952e71adbb7a':c['document_type']='informativa';notes.append('Primary privacy notice; a cited EU Regulation is not its document type.')
        if c['case_id']=='U16-a5c12c672c57af99':
            allowed=False;status='ambiguous_catalog_relation';notes.append('Official2019 draft convention has the same MSE department, address, fiscal code80230390587, CIPE65/2015 and fund purpose as canonical582 schema2020. Counterparty Proponente vs Comune differs. Exact identity equivalence not established; cannot label a related prior version confirmed unknown. Both DOCX primary openings inspected before predictions.')
        # Preserve actual immutable evidence and make inference/review explicit.
        review=dict(case_id=c['case_id'],input_sha256=c['SHA256'],official_url=c['official_url'],opening_sha256=hashlib.sha256(text.encode()).hexdigest(),previous_entity=original['entity'],entity=c['entity'],previous_type=original['document_type'],document_type=c['document_type'],truth_status=status,eligible_for_fresh_benchmark=allowed,notes=notes or ['Official primary identity/title/receipt and existing negative catalog/code/family/technical-near checks reviewed; no recognition scores used.'])
        c['audit_evidence']['manual_primary_review']=review;c['classification_reason']+=' Independent primary-heading and catalog review completed before prediction.'
        if c['case_id']=='U16-a5c12c672c57af99':
            review['relation_evidence']=dict(catalog_document_id=582,canonical_sha256=canonical582['canonical_file_sha256'],canonical_url=canonical582['url'],candidate_url=c['official_url'],basis='Both actual DOCX openings compared; same issuer/department/agency fiscal code/fund, different counterparty and2019/2020 resource editions. No exact equivalence or confirmed unknown asserted.')
        reviewed.append(review)
        if allowed:eligible.append(c)
    groups=defaultdict(list)
    for c in eligible:groups[c['resource_group']].append(c)
    representatives=[]
    for group,items in sorted(groups.items()):
        ordered=sorted(items,key=lambda c:c['SHA256']);representatives.append(ordered[0])
        for c in ordered[1:]:
            r=next(r for r in reviewed if r['case_id']==c['case_id']);r.update(eligible_for_fresh_benchmark=False,independence_exclusion='Existing technical-near component; one SHA-ordered representative only, no scores.',representative_case_id=ordered[0]['case_id'])
    value=dict(schema_version=1,freeze_commit=sealed()['freeze_git_commit'],automatic_audit_sha256=sha(backup),automatic_audit=backup.relative_to(ROOT).as_posix(),criteria='Primary issuer/title override body citations; independently qualify form identity against complete catalog; exclude unresolved relation to582; one representative per existing near-resource component, lexical SHA. These are truth/independence qualifications before any selection or prediction, not runtime rules or score-based exclusions.',reviewed_at=now(),reviewer='Codex technical benchmark audit; no human editorial verification attributed',recognition_calls=0,cases=reviewed,counts=dict(automatically_qualified=len(reviewed),confirmed_independent=len(representatives),unresolved=sum(r['truth_status']!='confirmed_unknown' for r in reviewed),near_component_exclusions=sum('independence_exclusion' in r for r in reviewed)),script_sha256=sha('scripts/round16_unknown_review.py'),catalog_seed_sha256=sha('data/catalog_seed.sqlite3'))
    value['visual_primary_evidence']=dict(rendered_contact_sheet_sha256=sha('tmp-build/round16-interno-headers.png'),input_case_ids=['U16-04774885d351cc0c','U16-2b9e01e915ca49f0','U16-83d4b269e550666d','U16-a7681bf22a185134'],page=1,clip_pdf_points=[0,0,600,300],render_scale=1.5,interpretation='All four literal graphic headings read Ministero dell’Interno, Gabinetto del Ministro. Images public benchmark-only and ignored; raw PDF SHA are in each reviewed case.')
    save('unknown_v3_primary_truth_review',value)
    auto.update(schema_version=2,confirmed_cases=representatives,confirmed_counts=balance(representatives),manual_review_sha256=sha(OUT/'unknown_v3_primary_truth_review.json'),recognition_calls=0)
    atomic_json(path,auto)
    print('R16 reviewed qualification',value['counts'],balance(representatives),flush=True);sealed()

if __name__=='__main__':main()
