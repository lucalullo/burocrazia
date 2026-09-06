"""Synthetic regressions used to develop rules; not an independent OCR benchmark."""
from dataclasses import asdict, replace
import json

import pytest

from src.models import AdministrativeDocument, DocumentFamily
from src.recognize import RULES_VERSION, recognize_catalog, recognize_document


def annual(model: str, year: str = "2026") -> AdministrativeDocument:
    return AdministrativeDocument(
        id=1 if model == "730" else 2, ente="Agenzia delle Entrate", codice=model,
        titolo_ufficiale=f"Modello 730/{year}" if model == "730" else f"Certificazione Unica {year}",
        categoria="dichiarazioni", descrizione_ufficiale=None, significato_semplice=None,
        versione=year, data_rilevazione="2026-08-13", stato_verifica="da_verificare",
    )


def families() -> list[DocumentFamily]:
    return [DocumentFamily(
        id=index, source_id=1, ente="Agenzia delle Entrate", nome=name, categoria=None,
        descrizione_ufficiale=None, keywords=(), identifying_phrases=(name,),
        official_url=None, stato_verifica="verificato", data_verifica=None,
    ) for index, name in enumerate(("Modello 730", "Certificazione Unica"), 1)]


@pytest.mark.parametrize(("text", "expected"), [
    ("AGENZIA DELLE ENTRATE\nMODELLO 73O / 2O24\nRedditi 2023", "Modello 730"),
    ("AGENZIA DELLE ENTRATE\nMODELLO 7 3 0 / 2 0 2 4\nRedditi 2023", "Modello 730"),
    ("M0DELL0 73O / 2O24\nDichiarazione dei redditi", "Modello 730"),
    ("AGENZIA DELLE ENTRATE\nCERTIFICAZlONE UNlCA 2O24\nPeriodo d'imposta 2023", "Certificazione Unica"),
    ("AGENZIA DELLE ENTRATE\nC U 2 O 2 4\nSostituto d'imposta", "Certificazione Unica"),
    ("CERTIFICAZIONEUNICA 2O24\nSostituto d'imposta", "Certificazione Unica"),
])
def test_noisy_annual_headers_only_identify_family(text: str, expected: str) -> None:
    result = recognize_catalog(text, [annual("730"), annual("CU")], families())
    assert result.match_type == "FAMILY_MATCH"
    assert result.document is None and result.family.nome == expected
    assert "versione non" in result.reason
    assert "alias di famiglia con rumore OCR" in result.family_signals
    assert result.conflicts


@pytest.mark.parametrize("model", ["730", "CU"])
def test_conflicting_explicit_model_years_never_pick_the_one_catalogued(model: str) -> None:
    result = recognize_catalog(f"Agenzia delle Entrate {model}/2024 e {model}/2026", [annual(model)], families())
    assert result.match_type == "FAMILY_MATCH"
    assert result.document is None
    assert "annualità assente, ambigua o incompatibile" in result.conflicts


def test_title_and_version_disagreement_in_catalog_prevents_exact_match() -> None:
    document = replace(annual("730"), versione="2024")
    result = recognize_catalog("Agenzia delle Entrate Modello 730/2026", [document], families())
    assert result.match_type == "FAMILY_MATCH"
    assert result.document is None


def test_fiscal_year_cannot_supply_the_missing_model_year() -> None:
    result = recognize_catalog("Agenzia delle Entrate Modello 730 redditi 2026", [annual("730")], families())
    assert result.match_type == "FAMILY_MATCH"
    assert result.document is None


@pytest.mark.parametrize("issuer", ["INAIL", "Istituto nazionale per l'assicurazione contro gli infortuni sul lavoro"])
def test_known_conflicting_authority_is_detected_without_its_own_catalog_record(issuer: str) -> None:
    document = replace(annual("730"), ente="INPS", codice="SR211", titolo_ufficiale="Rinuncia alla carta acquisti", versione=None)
    result = recognize_catalog(f"{issuer}\nSR211 Rinuncia alla carta acquisti", [document], [])
    assert result.match_type == "NO_MATCH"
    assert "ente incompatibile" in result.conflicts


def test_unknown_local_authority_cannot_inherit_catalog_municipality() -> None:
    document = replace(annual("730"), ente="Comune di Prova", codice="V-TEST-01", titolo_ufficiale="Verbale di contestazione", versione=None)
    result = recognize_catalog("COMUNE DI ALTROVE\nV-TEST-01\nVerbale di contestazione", [document], [])
    assert result.match_type == "NO_MATCH"
    assert "ente incompatibile" in result.conflicts


def test_entrate_riscossione_does_not_become_entrate() -> None:
    result = recognize_catalog("Agenzia delle Entrate-Riscossione Modello 730/2026", [annual("730")], families())
    assert result.match_type == "NO_MATCH"
    assert result.document is None and result.family is None


@pytest.mark.parametrize("text", ["Promemoria numero 730123", "Una CU qualsiasi", "INPS", "Importo 730 euro"])
def test_short_fragments_and_numeric_substrings_are_not_annual_family_evidence(text: str) -> None:
    assert recognize_catalog(text, [annual("730"), annual("CU")], families()).match_type == "NO_MATCH"


def test_partial_title_does_not_become_a_complete_identity() -> None:
    document = replace(annual("730"), ente="INPS", codice=None, titolo_ufficiale="INPS domanda di prestazione per lavoratori", versione=None)
    assert not recognize_document("INPS", [document]).recognized


def test_explainability_is_deterministic_and_does_not_store_uploaded_text() -> None:
    documents, available_families = [annual("730"), annual("CU")], families()
    personal_text = "dato-personale-sintetico-da-non-conservare"
    first = recognize_catalog(f"Modello 730/2026\n{personal_text}", documents, available_families)
    reordered = recognize_catalog("Modello 730/2026", reversed(documents), reversed(available_families))
    assert first.match_type == "DOCUMENT_MATCH"
    assert first.rules_version == RULES_VERSION
    assert first.catalog_revision.startswith("sha256:")
    assert first.catalog_revision == reordered.catalog_revision
    assert first.reason and first.document_score_margin is not None
    assert personal_text not in json.dumps(asdict(first))
    changed = recognize_catalog("Modello 730/2026", [replace(documents[0], versione="2025")], available_families)
    assert first.catalog_revision != changed.catalog_revision


def test_tied_identities_are_rejected_with_margin_reason() -> None:
    document = replace(annual("730"), titolo_ufficiale="Domanda di contributo", codice="ABC-01", versione=None)
    result = recognize_catalog("ABC-01 Domanda di contributo", [document, replace(document, id=5)], [])
    assert result.match_type == "NO_MATCH"
    assert result.document_score_margin == 0
    assert "ambigua" in result.reason
    assert result.candidate_ids == (1, 5)


def test_generic_numeric_annual_model_requires_its_year() -> None:
    document = replace(annual("730"), codice="770", titolo_ufficiale="770/2026")
    assert not recognize_document("Agenzia delle Entrate 770", [document]).recognized
    assert recognize_document("Agenzia delle Entrate 770/2026", [document]).recognized


def test_explicit_revision_conflict_cannot_be_overridden_by_exact_code() -> None:
    document = replace(annual("730"), ente="INPS", codice="SR211", titolo_ufficiale="Rinuncia alla carta acquisti", versione="1.0")
    assert not recognize_document("INPS SR211 versione 2.0", [document]).recognized
    assert recognize_document("INPS SR211 versione 1.0", [document]).recognized


def test_model_year_does_not_prove_a_missing_document_subtype() -> None:
    document = replace(annual("730"), titolo_ufficiale="Istruzioni Modello 730/2026")
    result = recognize_catalog("Agenzia delle Entrate Modello 730/2026", [document], families())
    assert result.match_type == "FAMILY_MATCH"
    assert result.document is None
    assert recognize_document("Agenzia delle Entrate Istruzioni Modello 730/2026", [document]).recognized


@pytest.mark.parametrize("reference", ["Protocollo 730/2026", "Importo 730 euro", "Pratica n. 730/2026"])
def test_incidental_numbers_do_not_identify_a_tax_form(reference: str) -> None:
    result = recognize_catalog(f"Agenzia delle Entrate\n{reference}", [annual("730")], families())
    assert result.match_type == "NO_MATCH"
