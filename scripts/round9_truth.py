"""Offline official unknown adjudication against complete public catalog/families.

Truth uses receipts, titles, opening evidence and public near-duplicate tests;
recognition predictions are never used to choose a label. Uncertainty excluded.
"""
import csv,hashlib,json,re,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from benchmarks.round3_audit import catalog,read
from benchmarks.transactional_writer import atomic_json
from benchmarks.truth_v2 import validate_registry,validate_unknown,classify_unknown
from src.extract import extract_document
from src.fingerprint_v3 import read_bundle,public_index,features
from src.recognize import normalize_text
from maintenance.iri import iri_to_uri
OUT=ROOT/'benchmarks/results/round9'

def words(s):return set(re.findall(r'[a-z0-9]{3,}',normalize_text(s)))-{'del','della','delle','degli','per','con','che','dei','dal','alla','alle','dello','nell','sulla','gli','una','www','gov','pdf'}
def main():
    docs,families=catalog();bundle=read_bundle();ix=public_index();hashes={r['canonical_file_sha256'] for r in bundle['records']};titles=[(d.id,normalize_text(d.titolo_ufficiale.split(' / ')[0])) for d in docs if d.stato_verifica not in ['demo','rifiutato']]
    rows=[];confirmed=[];headings=[]
    for i,c in enumerate(read('benchmarks/results/round9/unknown_candidates.json')['candidates']):
        sha=c['sha256'];error=None;opening='';top=None;fam=[];matches=[]
        raw=(ROOT/'benchmarks/cache'/(sha+'.body')).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
        try:
            cached=ROOT/'tmp-build/round9-truth-text'/(sha+'.json')
            if cached.exists():opening=json.loads(cached.read_bytes())['opening']
            else:
                ex=extract_document(raw,'unknown.'+c['format']);opening=ex.text[:2000]
                atomic_json(cached,dict(opening=opening,sha256=sha,scope='Official source bytes only, ignored temporary truth audit; never imported by runtime.'))
            normal=normalize_text(opening)
            # Complete title within first2000 chars; no fuzzy inference of truth.
            matches=[did for did,title in titles if len(title)>=20 and f' {title} ' in f' {normal} ']
            q=features(opening);scores=ix.similarities([q],n='3');top=scores[0] if scores else None
            for f in families:
                aliases=tuple(f.identifying_phrases)+(f.nome,)
                if isinstance(aliases,str):aliases=[aliases]
                if any(len(normalize_text(a))>=12 and f' {normalize_text(a)} ' in f' {normal} ' for a in aliases):fam.append(f.id)
        except (ValueError,OSError,RuntimeError) as exc:error=type(exc).__name__+': '+str(exc)
        title=c['title'];tw=words(title);ow=words(opening);support=len(tw&ow)/max(1,len(tw))
        # Informational title must also appear in the document opening. An
        # attachment named as a form cannot be confirmed just by a low score.
        types=[k for k in ['circolare','decreto','direttiva','regolamento','manuale','istruzioni','guida','provvedimento','comunicato'] if k in normalize_text(title).split()]
        kind=types[0] if types else None
        near=bool(matches or top and top['score']>=.85 and top['digital']>=.80 and top['chars']>=.80)
        status=classify_unknown(duplicate=sha in hashes,near_catalog=near,possible_family=bool(fam),heading_supported=not error and support>=.55 and len(tw&ow)>=3,informational_type=bool(kind and kind in normalize_text(opening).split()))
        receipt=c.get('receipt',{});date=receipt.get('acquired_at')
        if status=='confirmed_unknown' and (receipt.get('sha256')!=sha or not date):status='ambiguous'
        evidence=dict(official_sha256=sha,opening_sha256=hashlib.sha256(opening.encode()).hexdigest(),title_token_support=support,document_type=kind,catalog_title_hits=matches,family_hits=fam,nearest_catalog_id=top['document_id'] if top else None,nearest_content_score=top['score'] if top else None,criteria='Distinct informational heading supported by official opening, no complete catalog title, no high near-duplicate, no explicit family alias, unique official receipt. Not based on recognition outcome.')
        rows.append(dict(case_id='U9-'+sha[:16],title=title,code=';'.join(sorted(re.findall(r'\b[A-Z]{1,5}[- ]?\d{2,6}\b',opening[:800]))),entity=c['entity'],version=';'.join(re.findall(r'\b(?:versione|rev[.]?)\s*(\d+(?:[.]\d+)*)',opening,re.I)),url=c['url'],source=c['source_key'],sha256=sha,classification=status,catalog_title_hits=json.dumps(matches),family_hits=json.dumps(fam),fingerprint_near_duplicate=json.dumps(evidence),extraction_error=error or ''))
        headings.append(f"{rows[-1]['case_id']} | {status} | {c['source_key']} | {title}\n{opening[:1000]}\n\n")
        if status=='confirmed_unknown':confirmed.append(dict(case_id=rows[-1]['case_id'],title=title,code=rows[-1]['code'],entity=c['entity'],version=rows[-1]['version'],source_key=c['source_key'],url=iri_to_uri(c['url']),sha256=sha,format=c['format'],classification=status,expected_status='NO_MATCH',evidence_date=date,receipt=receipt,audit_evidence=evidence,document_type=kind,split='development' if int(sha[:8],16)%5==0 else 'evaluation',historically_seen=c['origin']=='historical_unknown_candidate',independent=False))
        if (i+1)%25==0:print('Truth audited',i+1,'confirmed',len(confirmed),flush=True)
    with (OUT/'unknown_truth_audit.csv').open('w',encoding='utf8',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (ROOT/'tmp-build/round9-unknown-headings.txt').write_bytes(''.join(headings).encode())
    counts=Counter(c['source_key'] for c in confirmed)
    manifest=dict(schema_version=1,manifest_id='official-unknown-v1',cases=confirmed,candidates_audited=len(rows),classification_counts=dict(Counter(r['classification'] for r in rows)),sources=dict(counts),entities=sorted({c['entity'] for c in confirmed}),source_concentration=max(counts.values(),default=0)/len(confirmed) if confirmed else None,independence='Retrospective official truth audit. Historical and fresh discovery explicitly marked; never independent v5 evidence.',adequacy=dict(minimum_count=100,target_count=150,minimum_sources=8,max_source_concentration=.25))
    validate_unknown(manifest);atomic_json(ROOT/'benchmarks/manifests/official_unknown_v1.json',manifest)
    prior=read('benchmarks/reference/reference_truth_v1.json');cases=[];seen=set()
    for c in prior['cases']:
        expected=c.get('reconciled_expected') or c['historical_expected'];evidence=[dict(e,sha256=e.get('sha256','')) for e in c['official_evidence']];status='confirmed' if c['label_status']=='confirmed' else 'excluded' if c['status']=='historical_fixture_error' else 'ambiguous'
        item=dict(case_id=c['case_id'],corpus=c['corpus'],expected_status=expected['match_type'],expected_document_id=expected.get('document_id'),expected_family_id=expected.get('family_id'),source_evidence=evidence,source_url=next((e['url'] for e in evidence if e.get('sha256')),None),evidence_date=next((e.get('acquired_at') for e in evidence if e.get('sha256')),None),confidence_status=status,notes=c['notes']);cases.append(item);seen.add((item['corpus'],item['case_id']))
    for p in sorted([*ROOT.glob('benchmarks/corpora/*.json'),*ROOT.glob('tests/fixtures/benchmark*.json')]):
        data=json.loads(p.read_bytes());items=data.get('cases',[]) if isinstance(data,dict) else data;corpus=p.relative_to(ROOT).as_posix()
        if not isinstance(items,list):continue
        for c in items:
            if not isinstance(c,dict) or not isinstance(c.get('expected'),dict) or not c.get('id') or (corpus,c['id']) in seen:continue
            e=c['expected'];cases.append(dict(case_id=c['id'],corpus=corpus,expected_status=e['match_type'],expected_document_id=e.get('document_id'),expected_family_id=e.get('family_id'),source_evidence=[],source_url=None,evidence_date=None,confidence_status='historical_only',notes='Historical/synthetic label retained; no official source bytes independently proving this exact input label.'));seen.add((corpus,c['id']))
    for c in confirmed:cases.append(dict(case_id=c['case_id'],corpus='official_unknown_v1',expected_status='NO_MATCH',expected_document_id=None,expected_family_id=None,source_evidence=[dict(sha256=c['sha256'],receipt=c['receipt'],audit=c['audit_evidence'])],source_url=c['url'],evidence_date=c['evidence_date'],confidence_status='confirmed',notes='Official informational document, distinct from complete catalog identities and explicit family aliases; retrospective truth, not independent recognition evidence.'))
    for r in bundle['records']:
        if r['status']!='active':continue
        cases.append(dict(case_id='CANONICAL-'+str(r['document_id'])+'-'+r['canonical_file_sha256'][:16],corpus='official_unambiguous_canonical',expected_status='DOCUMENT_MATCH',expected_document_id=r['document_id'],expected_family_id=None,source_evidence=[dict(sha256=r['canonical_file_sha256'],catalog_binding_sha256=r['catalog_binding_sha256'],evidence='Existing official SHA-verified unambiguous binding, unchanged from R8; canonical recognition is not generalization.')],source_url=iri_to_uri(r['url']),evidence_date=r['acquisition_date'],confidence_status='confirmed',notes='Resource identity only; no new catalog identity, source, historical event or editorial verification. Shared ambiguous bindings excluded.'))
    registry=dict(schema_version=2,registry_id='reference-truth-v2',supersedes='reference-truth-v1 (preserved)',cases=cases,historical_locks=prior['corpus_sha256'],counts=dict(Counter(c['confidence_status'] for c in cases)),unclassified_contradictions=0)
    validate_registry(registry);atomic_json(ROOT/'benchmarks/reference/reference_truth_v2.json',registry)
    (ROOT/'docs/REFERENCE_TRUTH_V2.md').write_bytes(('''# Reference truth v2

Nuovo registro, senza riscrivere v1 né i locked. Tutte le etichette dei corpus testuali sono censite; solo le prove ufficiali sostengono `confirmed`. Le contraddizioni R8 conservano le decisioni motivate v1, inclusa l’ambiguità dei due input INPS senza revisione. I contratti storici NO sono comunque testati separatamente.

Stati: {counts}. Unknown ufficiali confermati: {n}, fonti {sources}; concentrazione {concentration}. Audit completo in `benchmarks/results/round9/unknown_truth_audit.csv`. Il classificatore non usa predizioni di riconoscimento: controlla ricevuta/SHA, intestazione informativa, titolo completo, duplicati/near-duplicate e alias di famiglia. Ogni dubbio è escluso dal manifest. I casi storici restano development contaminato, anche quando la truth è confermata; lo split non conferisce nuova indipendenza.

Le date provengono dalle ricevute effettive. Nessuna verifica editoriale o nuova identità del catalogo attribuita. Corpus unknown valido soltanto con almeno100 file,8 fonti e nessuna fonte oltre25%; la presenza del manifest non implica il superamento dei minimi.
'''.format(counts=json.dumps(registry['counts']),n=len(confirmed),sources=len(counts),concentration=manifest['source_concentration'])).encode())
    print('Truth v2',registry['counts'],'unknown',len(confirmed),dict(counts),flush=True)
if __name__=='__main__':main()
