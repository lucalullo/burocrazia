import json
from pathlib import Path
import sqlite3
import pytest
from benchmarks.evaluate import canonical_cases, verify_locks
from src.database import list_documents
from src.families import list_document_families
from src.recognize import recognize_catalog

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def catalog():
    with sqlite3.connect((ROOT/'data/catalog_seed.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        return list_documents(db),list_document_families(db)

@pytest.mark.parametrize('name',['development_regression','release_locked_v1','hard_negatives_v1','release_locked_v2','hard_negatives_v2','canonical'])
def test_optimized_full_scan_equals_reference(name,catalog):
    docs,families=catalog
    cases=canonical_cases(docs) if name=='canonical' else json.loads((ROOT/f'benchmarks/corpora/{name}.json').read_text(encoding='utf-8'))['cases']
    for case in cases:
        assert recognize_catalog(case['text'],docs,families)==recognize_catalog(case['text'],docs,families,reference_full_scan=True),case['id']

def test_all_corpus_locks():
    verify_locks()

@pytest.mark.parametrize('title',['Modulo offerta persona fisica minore','Amministratore di sostegno-Rinuncia eredità'])
def test_longer_complete_title_disambiguates_literal_subtitle(title,catalog):
    docs,families=catalog
    document=next(d for d in docs if d.titolo_ufficiale==title)
    result=recognize_catalog(document.ente+'\n'+title,docs,families)
    assert result.document and result.document.id==document.id
    wrong=recognize_catalog('Tribunale di Milano\n'+title,docs,families)
    assert wrong.match_type=='NO_MATCH'

@pytest.mark.parametrize('heading',['FAQ','Provvedimento'])
def test_informational_headings_are_not_forms(heading,catalog):
    result=recognize_catalog('Ispettorato Nazionale del Lavoro\n'+heading+'\nRichiesta di intervento ispettivo\nModulo INL31',*catalog)
    assert result.match_type=='NO_MATCH'

@pytest.mark.parametrize('case_id,text,expected_id',[
    ('OR2-023','Modulo INL 29.2\nRichiesta di duplicato del patentino per generatori di vapore',1215),
    ('OR2-030','Alla cortese attenzione del\nMINISTRO DEL LAVORO E\nDELLE POLITICHE SOCIALI\nEnte privato\nRichiesta di patrocinio\nCHIEDE la concessione del patrocinio',None),
    ('OR2-031','Ministero delle Imprese e del Made in Italy\nRichiesta duplicato del certificato GOC ROC LRC SRC\nRadio operatori GMDSS',None),
    ('OR2-070','Modulo INL 1.4\nDichiarazione sostitutiva per marca da bollo',1225),
    ('OR2-098','Comunicazione su rapporto di lavoro\nInformazioni amministrative\nModulo INL\n2\nDati del lavoratore',None),
    ('OR2-136','Nota di iscrizione a ruolo\nAmministrazione di sostegno\nDati del ricorrente\nValore controversia\nEsenzione dal contributo unificato',None),
    ('OR2-145','Modifica della domanda e intervento autonomo\nDisposizioni sulle spese di giustizia\nArticolo di legge\nObbligo di pagamento\nLa parte versa il contributo unificato',None),
    ('OR2-147','Istanza di revoca del provvedimento di sospensione\n'+'Dati della istanza e riferimenti amministrativi. '*70+'\nPagamento mediante F24',None),
    ('OR2-161','Alla cortese attenzione del\nMINISTRO DEL LAVORO E\nDELLE POLITICHE SOCIALI\nEnte pubblico\nRichiesta di patrocinio\nCHIEDE la concessione del patrocinio',None),
])
def test_official_wrong_matches_have_synthetic_regressions(case_id,text,expected_id,catalog):
    result=recognize_catalog(text,*catalog)
    assert (result.document.id if result.document else None)==expected_id,case_id
    if expected_id is None:assert result.match_type=='NO_MATCH'
