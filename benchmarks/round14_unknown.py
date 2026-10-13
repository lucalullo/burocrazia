"""Fresh official truth audit, prediction-independent selection, one release run."""
import argparse,csv,hashlib,math,re
from collections import Counter,defaultdict
import pymupdf
from scripts.round14_common import *
from scripts.round9_truth import words
from scripts.round10_truth import document_metadata,TYPES
from scripts.round11_truth import attachment_role
from benchmarks.round3_audit import catalog
from benchmarks.transactional_writer import CaseJournal
from benchmarks.unknown_release import select,balance
from benchmarks.unknown_v2 import validate as validate_old_contract
from src.fingerprint_v3 import read_bundle,features,sketch
from src.recognize import normalize_text
from src.title_evidence import exact_code_candidates

MANIFEST='benchmarks/manifests/official_unknown_release_v2.json'
ALIASES={
 'inail':[('inail','INAIL')],'inps':[('inps','INPS')],
 'lavoro':[('ministero del lavoro','Ministero del Lavoro')],
 'agid':[('agid','Agenzia per l’Italia Digitale'),('agenzia per l italia digitale','Agenzia per l’Italia Digitale')],
 'anac':[('autorita nazionale anticorruzione','Autorità Nazionale Anticorruzione'),('anac','Autorità Nazionale Anticorruzione')],
 'mit':[('ministero delle infrastrutture','Ministero delle Infrastrutture e dei Trasporti'),('ministero dei trasporti','Ministero dei Trasporti'),('direzione generale per la motorizzazione','Direzione Generale per la Motorizzazione')],
 'mef':[('ministero dell economia','Ministero dell’Economia e delle Finanze'),('ragioneria generale dello stato','Ragioneria Generale dello Stato')],
 'interno':[('ministero dell interno','Ministero dell’Interno'),('prefettura','Prefettura (come indicata nel frontespizio)'),('dipartimento per le liberta civili','Dipartimento per le Libertà Civili e l’Immigrazione')],
 'regione_piemonte':[('regione piemonte','Regione Piemonte')],
 'mimit':[('ministero delle imprese','Ministero delle Imprese e del Made in Italy'),('ministero dello sviluppo economico','Ministero dello Sviluppo Economico'),('ministero delle comunicazioni','Ministero delle Comunicazioni')],
 'giustizia':[('ministero della giustizia','Ministero della Giustizia'),('tribunale','Tribunale (come indicato nel frontespizio)'),('dipartimento dell organizzazione giudiziaria','Dipartimento dell’Organizzazione Giudiziaria')],
 'salute':[('ministero della salute','Ministero della Salute')],'adm':[('agenzia delle dogane','Agenzia delle Dogane e dei Monopoli')],
 'aci':[('automobile club','Automobile Club d’Italia'),('aci','Automobile Club d’Italia')],
 'garante_privacy':[('garante per la protezione','Garante per la protezione dei dati personali')],
 'polizia':[('polizia di stato','Polizia di Stato')],'inl':[('ispettorato nazionale del lavoro','Ispettorato Nazionale del Lavoro')],
 'funzione_pubblica':[('funzione pubblica','Dipartimento della Funzione Pubblica')],
 'unioncamere':[('unioncamere','Unioncamere')],'ader':[('agenzia delle entrate riscossione','Agenzia delle Entrate-Riscossione')]}

def excluded():
    r=read(REGISTRY)
    return set(r['observed_resource_sha256'])|{c['sha256'] for c in r['unknown_resources'] if c['prediction_observed'] or c['release_v1'] or c['unknown_development']}

def validate_release(m):
    assert m['manifest_id']=='official-unknown-release-v2' and m['freeze_commit']==sealed()['freeze_git_commit']
    validate_old_contract(dict(m,schema_version=2,manifest_id='official-unknown-v2'))
    old={c['SHA256'] for c in read('benchmarks/manifests/official_unknown_release_v1.json')['cases']}
    assert not ({c['SHA256'] for c in m['cases']}&(excluded()|old))
    b=balance(m['cases']);assert b['total']>=100 and b['sources']>=8 and b['max_concentration']<=.25 and b['type_groups']>=5
    assert all(c['previously_seen'] is False and c['historically_seen'] is False for c in m['cases'])
    return m

def audit():
    freeze=sealed();assert not (ROOT/MANIFEST).exists(),'Release selection already locked'
    prior_path=OUT/'unknown_v2_truth_audit.json'
    if prior_path.exists() and not (OUT/'unknown_v2_truth_audit_initial.json').exists():
        (OUT/'unknown_v2_truth_audit_initial.json').write_bytes(prior_path.read_bytes())
        (OUT/'unknown_v2_truth_audit_initial.csv').write_bytes((OUT/'unknown_v2_truth_audit.csv').read_bytes())
    docs,families=catalog();bundle=read_bundle();hashes={r['canonical_file_sha256'] for r in bundle['records']};seen=excluded()
    titles=[(d.id,normalize_text(d.titolo_ufficiale.split(' / ')[0])) for d in docs if d.stato_verifica not in ['demo','rifiutato']]
    pages=[(r['document_id'],set(p['digital']),set(p['chars']['4'])) for r in bundle['records'] for p in r['pages']]
    candidates=read('benchmarks/results/round14/unknown_v2_candidates.json')['candidates'];rows=[];confirmed=[];queries={};headings=[]
    policy=dict(head_character_limit=2000,minimum_title_overlap=4,minimum_title_support=.5,near_fingerprint_min_overlap=.85,
                near_unknown_token_jaccard=.8,near_unknown_char4_jaccard=.8,source_quota=20,selection_seed=SEED,
                note='Truth similarity excludes near duplicates; it is a direct sketch overlap, not recognition confidence/ranking. No recognize or decision function is called before final selection.')
    policy_path=OUT/'unknown_v2_audit_policy.json'
    if policy_path.exists():
        previous_policy=read(policy_path)
        assert all(previous_policy[k]==v for k,v in policy.items()),'Truth audit policy already fixed'
    else:save('unknown_v2_audit_policy',dict(**policy,freeze_commit=freeze['freeze_git_commit'],declared_at=now()))
    for i,c in enumerate(candidates,1):
        h=c['sha256'];raw=(ROOT/'benchmarks/cache'/(h+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==h
        opening='';error='';near=[];hits=[];codes=[];fam=[];entity=None;title=c['title'];kind=None;page_count=None;query=None;title_basis='official_attachment_label';context=c.get('source_evidence',{})
        try:
            if c['format']=='pdf':
                with pymupdf.open(stream=raw,filetype='pdf') as pdf:
                    page_count=len(pdf);opening='\n'.join(pdf[j].get_text() for j in range(min(2,len(pdf))))[:2000]
            else:
                from src.extract import extract_document
                opening=extract_document(raw,'official.docx').text[:2000]
            if len(words(opening))<20:raise ValueError('Official opening lacks sufficient digital truth evidence; no prediction/OCR probe used to admit it')
            normal=normalize_text(opening)
            entity=next((label for alias,label in ALIASES.get(c['source_key'],[]) if f' {normalize_text(alias)} ' in f' {normal} '),None)
            if entity and 'come indicat' in entity:
                lines=[s.strip() for s in opening.splitlines() if s.strip()]
                j=next((j for j,s in enumerate(lines) if 'tribunale' in normalize_text(s) or 'prefettura' in normalize_text(s)),None)
                if j is not None:entity=' '.join(lines[j:j+2])[:200]
            heading=context.get('context_heading','')
            if len(words(title))<4 or len(words(title)&words(opening))/max(1,len(words(title)))<.5:
                if len(words(heading))>=4 and len(words(heading)&words(opening))/max(1,len(words(heading)))>=.5:title=heading;title_basis='linked_official_heading'
                else:
                    lines=[line.strip() for line in opening.splitlines() if line.strip() and not line.strip().isdigit()]
                    candidate=' '.join(lines[:8])[:500]
                    if any(t in normalize_text(candidate).split() for t in TYPES+['nota','note','informativa','scheda','comunicazione']):title=candidate;title_basis='literal_official_opening_heading'
            kinds=[t for t in TYPES+['nota','note','informativa','scheda','comunicazione'] if t in normalize_text(title).split() and t in normal.split()]
            kind=kinds[0] if kinds else None
            if not kind and 'oggetto' in normal and 'circolare' in normalize_text(heading):kind='circolare'
            if 'linee guida' in normal and 'linee guida' in normalize_text(title):kind='guida'
            title,kind=attachment_role(opening,title,kind)
            hits=[did for did,t in titles if len(t)>=20 and f' {t} ' in f' {normal} ']
            codes=list(exact_code_candidates(opening,docs))
            fam=[f.id for f in families if any(len(normalize_text(a))>=12 and f' {normalize_text(a)} ' in f' {normal} ' for a in [*f.identifying_phrases,f.nome])]
            query=features(opening);qd=set(sketch(query['tokens'],64));qc=set(sketch(query['chars']['4'],64))
            for did,pg,ch in pages:
                digital=len(qd&pg)/max(1,min(len(qd),len(pg)));char=len(qc&ch)/max(1,min(len(qc),len(ch)))
                if len(pg)>=24 and len(ch)>=24 and digital>=.85 and char>=.85:near.append(dict(document_id=did,digital_sketch_overlap=digital,char4_sketch_overlap=char))
        except (ValueError,RuntimeError,OSError) as exc:error=type(exc).__name__+': '+str(exc)
        overlap=words(title)&words(opening);support=len(overlap)/max(1,len(words(title)))
        state='previously_seen' if h in seen else 'duplicate_catalog_resource' if h in hashes else 'possible_document_match' if hits or codes or near else 'possible_family_match' if fam else 'unsupported_truth' if error or not entity else 'confirmed_unknown' if kind and support>=.5 and len(overlap)>=4 else 'ambiguous'
        code,version=document_metadata(opening)
        evidence=dict(official_sha256=h,opening_sha256=hashlib.sha256(opening.encode()).hexdigest(),title_basis=title_basis,title_tokens_supported=len(overlap),title_support=support,
                      catalog_title_hits=hits,catalog_code_hits=codes,near_fingerprint=near,family_hits=fam,source_relationship='Official receipt establishes hosting; entity admitted only from a literal alias in the opening2000.',
                      entity_basis='Literal official opening alias' if entity else 'Issuer not established; excluded',document_type=kind,source_evidence=context,page_count=page_count,
                      classification_error=error,code=code,version=version,previously_seen=h in seen,criteria=policy)
        row=dict(case_id='U14-'+h[:16],source=c['source_key'],entity=entity,title=title,official_url=c['url'],sha256=h,classification=state,evidence=evidence);rows.append(row)
        headings.append(row['case_id']+' | '+state+' | '+c['source_key']+' | '+title+'\n'+opening+'\n\n')
        if state=='confirmed_unknown':
            queries[h]=query
            confirmed.append(dict(case_id=row['case_id'],source=c['source_key'],entity=entity,title=title,official_url=c['url'],acquisition_date=c['receipt']['acquired_at'],SHA256=h,
                mime='application/pdf' if c['format']=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',reference_truth_status=state,expected_result='NO_MATCH',
                classification_reason='Official opening and receipt establish a distinct noncatalog identity; full title/code/family/SHA/technical-near exclusions passed before recognition.',
                receipt=c['receipt'],audit_evidence=evidence,document_type=kind,code=code,version=version,historically_seen=False,previously_seen=False,split='unknown_eval'))
        if i%25==0:print('R14 truth',i,'/',len(candidates),'confirmed',len(confirmed),flush=True)
    parent={c['SHA256']:c['SHA256'] for c in confirmed}
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for i,a in enumerate(confirmed):
        qa=queries[a['SHA256']]
        for b in confirmed[:i]:
            qb=queries[b['SHA256']];t=len(qa['tokens']&qb['tokens'])/max(1,len(qa['tokens']|qb['tokens']));ch=len(qa['chars']['4']&qb['chars']['4'])/max(1,len(qa['chars']['4']|qb['chars']['4']))
            if t>=.8 and ch>=.8:parent[find(a['SHA256'])]=find(b['SHA256'])
    for c in confirmed:c['resource_group']='UG14-'+find(c['SHA256'])[:16]
    save('unknown_v2_truth_audit',dict(schema_version=1,freeze_commit=freeze['freeze_git_commit'],candidates_sha256=sha('benchmarks/results/round14/unknown_v2_candidates.json'),
        audit_policy=policy,classification_counts=dict(Counter(r['classification'] for r in rows)),confirmed_counts=balance(confirmed),cases=rows,confirmed_cases=confirmed,recognition_calls=0,created_at=now()))
    with (OUT/'unknown_v2_truth_audit.csv').open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['case_id','source','entity','title','official_url','sha256','classification','evidence'],lineterminator='\n');writer.writeheader()
        for r in rows:writer.writerow(dict(r,evidence=json.dumps(r['evidence'],ensure_ascii=False)))
    work=ROOT/'tmp-build/round14-truth';work.mkdir(exist_ok=True);(work/'official-openings.txt').write_text(''.join(headings),encoding='utf8')
    print('R14 truth final',dict(Counter(r['classification'] for r in rows)),balance(confirmed),flush=True);sealed()

def selection():
    freeze=sealed();assert not (ROOT/MANIFEST).exists(),'Selection already frozen'
    audit=read('benchmarks/results/round14/unknown_v2_truth_audit.json');chosen=select(audit['confirmed_cases'],seed=SEED,source_cap=20);preferred=balance(chosen);cap=20
    # User's mandatory concentration is 25%; 20% is preferred. Fallback is
    # driven solely by metadata adequacy before any recognition call.
    if preferred['total']<100:chosen=select(audit['confirmed_cases'],seed=SEED,source_cap=25);cap=25
    b=balance(chosen)
    passed=b['total']>=100 and b['sources']>=8 and b['max_concentration']<=.25 and b['type_groups']>=5
    result=dict(schema_version=1,status='locked' if passed else 'insufficient_pool',passed=passed,freeze_commit=freeze['freeze_git_commit'],selection_seed=SEED,
                truth_audit_sha256=sha('benchmarks/results/round14/unknown_v2_truth_audit.json'),registry_sha256=sha(REGISTRY),selection=b,preferred_cap20_selection=preferred,absolute_source_cap=cap,
                case_ids=[c['case_id'] for c in chosen],recognition_calls=0,
                method='All-or-none technical near-resource components, SHA(seed:group) order; preferred max20/source, fallback max25 only if N<100. Final mandatory <=25% checked. Strata source/entity/type/code/version reported. No confidence, recognition score, label tuning or predictions used.',created_at=now())
    prior_path=OUT/'unknown_v2_selection.json'
    if prior_path.exists() and not (OUT/'unknown_v2_selection_initial.json').exists():(OUT/'unknown_v2_selection_initial.json').write_bytes(prior_path.read_bytes())
    if passed:
        m=dict(schema_version=2,manifest_id='official-unknown-release-v2',freeze_commit=freeze['freeze_git_commit'],selection_seed=SEED,cases=chosen,created_at=now(),
               registry_sha256=sha(REGISTRY),truth_audit_sha256=result['truth_audit_sha256'],selection_policy=result['method'])
        validate_release(m);atomic_json(ROOT/MANIFEST,m);result['manifest_sha256']=sha(MANIFEST)
    save('unknown_v2_selection',result);print('R14 unknown selection',b,'passed',passed,flush=True)

def interval(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;den=1+z*z/n;center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return dict(lower=max(0,center-half),upper=min(1,center+half),method='Wilson score 95% two sided')

def metrics(values):
    n=len(values);no=sum(r['observed']['match_type']=='NO_MATCH' and not r['extraction_failed'] for r in values)
    wd=sum(r['observed']['match_type']=='DOCUMENT_MATCH' for r in values);wf=sum(r['observed']['match_type']=='FAMILY_MATCH' for r in values)
    versions=sum(r['observed']['match_type']=='DOCUMENT_MATCH' and bool(r['provenance'].get('truth_version')) and r['observed'].get('version') is not None
                 and normalize_text(str(r['observed']['version'])) not in [normalize_text(v) for v in r['provenance']['truth_version'].split(';')] for r in values)
    from src.recognize import ENTITY_ALIASES
    canonical=lambda s:ENTITY_ALIASES.get(normalize_text(s),normalize_text(s))
    entities=sum(r['observed']['match_type']!='NO_MATCH' and bool(r['observed'].get('entity')) and bool(r['provenance'].get('entity'))
                 and canonical(r['observed']['entity'])!=canonical(r['provenance']['entity']) for r in values)
    return dict(n=n,correct_no_match=no,wrong_document_match=wd,wrong_family_match=wf,extraction_failed=sum(r['extraction_failed'] for r in values),
                rejection_rate=no/n if n else None,false_acceptance_rate=(wd+wf)/n if n else None,confidence_interval_95=interval(no,n),entity_errors=entities,version_errors=versions)

def validate_observations(value):
    import jsonschema
    jsonschema.validate(value,read('benchmarks/schemas/round14_unknown_observations.schema.json'))
    ids=[r['id'] for r in value['cases']]
    assert len(ids)==len(set(ids))==value['expected_count']==value['completed'] and value['complete']
    assert all(r['input_sha256']==r['provenance']['sha256'] for r in value['cases'])
    return value

def run():
    freeze=sealed();manifest=validate_release(read(MANIFEST));target=OUT/'unknown_release_v2.json'
    assert not target.exists(),'Release already completed; no replay'
    from benchmarks import round8_common as common
    from benchmarks.evaluate import code_hash
    common.SEED=SEED;ident=common.identity();key=dict(freeze_commit=freeze['freeze_git_commit'],manifest_sha256=sha(MANIFEST),runtime_sha256=ident['runtime_sha256'],fingerprint_sha256=ident['fingerprint_sha256'],runner_code_sha256=code_hash(),registry_sha256=sha(REGISTRY))
    assert ident['runtime_sha256']==freeze['runtime_sha256'] and ident['fingerprint_sha256']==freeze['fingerprint_dataset_sha256']
    journal=CaseJournal(ROOT/'benchmarks/work/round14/unknown-release-v2.sqlite',identity=key,expected_ids=[c['case_id'] for c in manifest['cases']]);pending=set(journal.pending());docs,families=catalog()
    marker=OUT/'unknown_v2_started.json'
    if marker.exists():assert read(marker)['identity']==key
    else:save('unknown_v2_started',dict(identity=key,expected_count=len(manifest['cases']),started_at=now(),single_shot=True))
    for i,c in enumerate(manifest['cases'],1):
        if c['case_id'] not in pending:continue
        raw=(ROOT/'benchmarks/cache'/(c['SHA256']+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['SHA256']
        cc=dict(id=c['case_id'],group=c['resource_group'],category=c['document_type'],expected=dict(match_type='NO_MATCH'),label_status='confirmed_unknown',representation='official_original',
                provenance=dict(source=c['source'],entity=c['entity'],document_type=c['document_type'],sha256=c['SHA256'],previously_seen=False,official_url=c['official_url'],truth_version=c['version']))
        journal.append(common.case_result(cc,raw,'unknown.pdf' if c['mime']=='application/pdf' else 'unknown.docx',docs,families))
        if i%10==0:print('R14 unknown persisted',i,'/',len(manifest['cases']),flush=True)
    rows=journal.rows();export=OUT/'unknown_release_v2_observations.json';journal.export(export,complete=True);validate_observations(read(export))
    assert len(rows)==len(manifest['cases'])
    m=metrics(rows);stats=balance(manifest['cases'])
    save('unknown_release_v2',dict(schema_version=1,status='complete',identity=ident,freeze_commit=freeze['freeze_git_commit'],manifest_sha256=sha(MANIFEST),
        expected_count=len(rows),actual_count=len(rows),unique_case_ids=len({r['id'] for r in rows}),recognition_calls=len(rows),**m,selection=stats,
        per_source={s:metrics([r for r in rows if r['provenance']['source']==s]) for s in stats['counts_per_source']},
        per_entity={s:metrics([r for r in rows if r['provenance']['entity']==s]) for s in sorted({c['entity'] for c in manifest['cases']})},
        per_type={s:metrics([r for r in rows if r['category']==s]) for s in stats['document_types']},
        wrong_accepts=[dict(id=r['id'],observed=r['observed'],signals=r['signals']) for r in rows if r['observed']['match_type']!='NO_MATCH'],
        observations_sha256=sha(export),passed=m['rejection_rate']>=.99 and m['entity_errors']==0 and m['version_errors']==0,
        error_basis='Entity errors compare an emitted entity to the literal verified issuer, applying only existing public ENTITY_ALIASES. Version errors count explicit contradictory version/year only. Every document/family acceptance is false acceptance even when entity/version are compatible.',
        scope='First single-shot on byte-identical freeze engine. Fresh prediction SHA, no release v1/development/observed resource overlap. Known v5 may run only if this gate passes.'))
    sealed();print('R14 unknown result',m,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['audit','selection','run']);a=p.parse_args();globals()[a.mode]()
