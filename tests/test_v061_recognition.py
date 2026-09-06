"""A01/A04: esclusione operativa e impronta, su dati sintetici o copie locali."""
from dataclasses import replace

import pytest

from src import recognize
from src.bootstrap import prepare_database
from src.database import connect_database, get_document, list_documents
from src.explanations import list_review_events
from src.families import list_document_families
from src.models import AdministrativeDocument, DocumentFamily
from src.review import submit_document_review


def sr211(status="da_verificare", identifier=1):
    return AdministrativeDocument(
        id=identifier, ente="INPS", codice="SR211",
        titolo_ufficiale="Rinuncia dei beneficiari alla Carta Acquisti",
        categoria="prestazioni", descrizione_ufficiale=None, significato_semplice=None,
        versione=None, data_rilevazione="2026-09-05", stato_verifica=status,
    )


def annual_family(status="verificato"):
    return DocumentFamily(
        id=1, source_id=1, ente="Agenzia delle Entrate", nome="Modello 730",
        categoria=None, descrizione_ufficiale=None, keywords=(),
        identifying_phrases=("Modello 730",), official_url=None,
        stato_verifica=status, data_verifica=None,
    )


def test_rejected_sr211_is_not_scored_or_reported_as_candidate(monkeypatch):
    scored_ids = []
    original_score = recognize._score_candidate

    def score(*args):
        scored_ids.append(args[2].id)
        return original_score(*args)

    monkeypatch.setattr(recognize, "_score_candidate", score)
    result = recognize.recognize_catalog("INPS SR211", [sr211("rifiutato")], [])
    assert scored_ids == []
    assert result.match_type == "NO_MATCH"
    assert result.document is None and result.candidate_ids == ()
    assert result.document_signals == () and result.confidence_document == 0.0


def test_direct_recognition_also_excludes_rejected_documents():
    result = recognize.recognize_document("INPS SR211", [sr211("rifiutato")])
    assert not result.recognized and result.document is None
    assert result.candidate_ids == ()


@pytest.mark.parametrize("status", ["da_verificare", "verificato", "demo"])
def test_non_rejected_documents_remain_eligible_under_existing_rules(status):
    document = sr211(status)
    result = recognize.recognize_catalog("INPS SR211", [document], [])
    assert result.match_type == "DOCUMENT_MATCH" and result.document is document
    assert result.candidate_ids == (document.id,)
    assert recognize.recognize_catalog("INPS", [document], []).match_type == "NO_MATCH"


def test_rejected_tied_candidate_does_not_block_an_eligible_match():
    accepted = sr211(identifier=2)
    rejected = sr211("rifiutato")
    first = recognize.recognize_catalog("INPS SR211", [rejected, accepted], [])
    second = recognize.recognize_catalog("INPS SR211", [accepted, rejected], [])
    assert first.match_type == "DOCUMENT_MATCH" and first.document is accepted
    assert first.candidate_ids == (2,) and first.document_score_margin >= recognize.MIN_SCORE_MARGIN
    assert first == second


def test_rejected_document_entity_still_protects_against_a_wrong_issuer():
    rejected = replace(sr211("rifiutato"), ente="Ente Previdenziale Esempio")
    eligible = replace(sr211(identifier=2), ente="Ente Previdenziale Diverso")
    result = recognize.recognize_catalog("Ente Previdenziale Esempio SR211", [rejected, eligible], [])
    assert result.match_type == "NO_MATCH"
    assert "ente incompatibile" in result.conflicts
    assert rejected.id not in result.candidate_ids


@pytest.mark.parametrize("family_status, expected", [
    ("verificato", "FAMILY_MATCH"), ("da_verificare", "NO_MATCH"), ("rifiutato", "NO_MATCH"),
])
def test_family_fallback_depends_on_its_own_evidence_and_admission(family_status, expected):
    document = replace(sr211("rifiutato"), ente="Agenzia delle Entrate", codice="730",
                       titolo_ufficiale="Modello 730/2026", versione="2026")
    family = annual_family(family_status)
    text = "Agenzia delle Entrate Modello 730/2026"
    result = recognize.recognize_catalog(text, [document], [family])
    independent = recognize.recognize_catalog(text, [], [family])
    assert result.match_type == expected and result.document is None
    assert result.candidate_ids == () and result.document_signals == ()
    assert result.family == independent.family
    assert result.family_signals == independent.family_signals
    assert result.confidence_family == independent.confidence_family
    assert result.confidence_document == 0.0


def test_rejected_identity_is_not_automatically_converted_into_family_match():
    family = replace(annual_family(), ente="INPS", nome="Carta Acquisti",
                     identifying_phrases=("rinuncia del beneficio", "restituzione della carta"))
    result = recognize.recognize_catalog("INPS SR211", [sr211("rifiutato")], [family])
    assert result.match_type == "NO_MATCH" and result.document is None and result.family is None
    assert result.candidate_ids == ()


def test_sr211_rejection_preserves_full_record_catalog_and_append_only_history(tmp_path):
    path = prepare_database(tmp_path / "catalog.db")
    with connect_database(path) as connection:
        original_documents = list_documents(connection)
        families = list_document_families(connection)
        target = next(document for document in original_documents if document.codice == "SR211")
    text = f"{target.ente} {target.codice} {target.titolo_ufficiale}"
    assert recognize.recognize_catalog(text, original_documents, families).document == target
    assert submit_document_review(target.id, "da_verificare", "Revisore di prova", db_path=path)
    with connect_database(path) as connection:
        previous_events = list_review_events(connection)
    assert submit_document_review(target.id, "rifiutato", "Revisore di prova", db_path=path,
                                  review_notes="Esclusione operativa per prova di regressione.")
    with connect_database(path) as connection:
        updated_documents = list_documents(connection)
        assert get_document(connection, target.id) == replace(target, stato_verifica="rifiutato")
        assert updated_documents == [replace(document, stato_verifica="rifiutato")
                                     if document.id == target.id else document for document in original_documents]
        assert list_document_families(connection) == families
        events = list_review_events(connection)
        assert events[:-1] == previous_events and events[-1]["new_status"] == "rifiutato"
        assert events[-1]["entity_id"] == target.id
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    result = recognize.recognize_catalog(text, updated_documents, families)
    assert result.match_type == "NO_MATCH" and result.document is None
    assert target.id not in result.candidate_ids


def test_catalog_revision_changes_on_refusal_and_is_repeatable():
    document = sr211()
    original = recognize.recognize_catalog("INPS SR211", [document], [])
    refused = recognize.recognize_catalog("INPS SR211", [replace(document, stato_verifica="rifiutato")], [])
    repeated = recognize.recognize_catalog("testo differente", [replace(document, stato_verifica="rifiutato")], [])
    assert original.catalog_revision != refused.catalog_revision
    assert refused.catalog_revision == repeated.catalog_revision
    assert refused.catalog_revision.startswith("sha256:")


@pytest.mark.parametrize("field, value", [
    ("id", 2), ("ente", "INAIL"), ("codice", "SR212"), ("titolo_ufficiale", "Altro titolo"),
    ("versione", "1.0"), ("parole_chiave", ("Carta Acquisti",)), ("stato_verifica", "verificato"),
])
def test_catalog_revision_covers_document_scoring_and_admission_fields(field, value):
    document = sr211()
    original = recognize.recognize_catalog("", [document], [])
    changed = recognize.recognize_catalog("", [replace(document, **{field: value})], [])
    assert original.catalog_revision != changed.catalog_revision


@pytest.mark.parametrize("field, value", [
    ("id", 2), ("ente", "INAIL"), ("nome", "Altro modello"), ("keywords", ("dichiarazione",)),
    ("identifying_phrases", ("dichiarazione dei redditi",)), ("stato_verifica", "rifiutato"),
])
def test_catalog_revision_covers_family_scoring_and_admission_fields(field, value):
    family = annual_family()
    original = recognize.recognize_catalog("", [], [family])
    changed = recognize.recognize_catalog("", [], [replace(family, **{field: value})])
    assert original.catalog_revision != changed.catalog_revision


def test_catalog_revision_ignores_iteration_order_and_unused_editorial_dates():
    documents = [sr211(), sr211("rifiutato", 2)]
    families = [annual_family(), replace(annual_family(), id=2, nome="Certificazione Unica")]
    original = recognize.recognize_catalog("", documents, families)
    reordered = recognize.recognize_catalog("", reversed(documents), reversed(families))
    editorial_changes = [replace(document, descrizione_ufficiale="Nota editoriale",
                                data_rilevazione="2026-09-06") for document in documents]
    unrelated = recognize.recognize_catalog("", editorial_changes, families)
    assert original.catalog_revision == reordered.catalog_revision == unrelated.catalog_revision
    assert recognize.catalog_revision(iter(documents), iter(families)) == original.catalog_revision
