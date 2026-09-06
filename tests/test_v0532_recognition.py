from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

import pytest

import app
from src.database import connect_database, initialize_database
from src.families import list_document_families
from src.models import AdministrativeDocument
from src.recognize import recognize_catalog


FIXTURES = Path(__file__).parent / "fixtures"
ADE_URL = "https://www.agenziaentrate.gov.it/portale/modello-annuale-test"


def annual_document(model: str, year: str) -> AdministrativeDocument:
    if model == "730":
        code = "730"
        title = f"Modello 730/{year}"
    else:
        code = "CU"
        title = f"Certificazione Unica {year}"
    return AdministrativeDocument(
        ente="Agenzia delle Entrate",
        codice=code,
        titolo_ufficiale=title,
        categoria="Dichiarazioni",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione=year,
        data_rilevazione="2026-08-13",
        stato_verifica="da_verificare",
        detail_url=f"{ADE_URL}-{model.casefold()}-{year}",
    )


def seeded_families(tmp_path):
    db_path = tmp_path / "families.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        return list_document_families(connection)


@pytest.mark.parametrize(
    "text",
    (
        "Agenzia delle Entrate - Certificazione Unica 2024 - relativa all'anno 2023",
        "Agenzia delle Entrate - CU 2024",
        "Agenzia delle Entrate - CU2024",
    ),
)
def test_cu_2024_aliases_match_the_exact_version_when_present(
    tmp_path, text: str
) -> None:
    families = seeded_families(tmp_path)
    cu_2024 = annual_document("CU", "2024")
    cu_2026 = annual_document("CU", "2026")

    result = recognize_catalog(text, [cu_2026, cu_2024], families)

    assert result.match_type == "DOCUMENT_MATCH"
    assert result.document is cu_2024
    assert result.document.detail_url.endswith("-cu-2024")


def test_cu_2024_falls_back_to_family_when_only_2026_is_cataloged(tmp_path) -> None:
    families = seeded_families(tmp_path)

    result = recognize_catalog(
        "Agenzia delle Entrate - CU2024",
        [annual_document("CU", "2026")],
        families,
    )

    assert result.match_type == "FAMILY_MATCH"
    assert result.family and result.family.nome == "Certificazione Unica"
    assert result.family.official_url and result.family.official_url.startswith("https://")


@pytest.mark.parametrize(
    "text",
    (
        "Agenzia delle Entrate - Certificazione Unica",
        "Agenzia delle Entrate - CU",
    ),
)
def test_cu_without_explicit_year_matches_family_not_an_arbitrary_version(
    tmp_path, text: str
) -> None:
    result = recognize_catalog(
        text,
        [annual_document("CU", "2024"), annual_document("CU", "2026")],
        seeded_families(tmp_path),
    )

    assert result.match_type == "FAMILY_MATCH"
    assert result.family and result.family.nome == "Certificazione Unica"


def test_730_year_is_contextual_and_does_not_use_the_fiscal_year(tmp_path) -> None:
    families = seeded_families(tmp_path)
    model_2024 = annual_document("730", "2024")
    model_2026 = annual_document("730", "2026")
    text = "Agenzia delle Entrate - Modello 730/2024 - Redditi 2023"

    result = recognize_catalog(text, [model_2026, model_2024], families)

    assert result.match_type == "DOCUMENT_MATCH"
    assert result.document is model_2024
    assert result.document.detail_url.endswith("-730-2024")


def test_730_2024_never_matches_730_2026_and_uses_family_fallback(tmp_path) -> None:
    families = seeded_families(tmp_path)

    result = recognize_catalog(
        "Agenzia delle Entrate - Modello 730/2024 - Redditi 2023",
        [annual_document("730", "2026")],
        families,
    )

    assert result.match_type == "FAMILY_MATCH"
    assert result.document is None
    assert result.family and result.family.nome == "Modello 730"


def test_730_2026_keeps_its_exact_document_match(tmp_path) -> None:
    model_2026 = annual_document("730", "2026")

    result = recognize_catalog(
        "Agenzia delle Entrate - MODELLO 730/2026",
        [model_2026],
        seeded_families(tmp_path),
    )

    assert result.match_type == "DOCUMENT_MATCH"
    assert result.document is model_2026


def test_generic_annual_document_rejects_an_explicit_different_version() -> None:
    document = AdministrativeDocument(
        ente="Agenzia delle Entrate",
        codice=None,
        titolo_ufficiale="Bonus edilizi 2026",
        categoria="Agevolazioni",
        descrizione_ufficiale=None,
        significato_semplice=None,
        versione="2026",
        data_rilevazione="2026-08-13",
        stato_verifica="da_verificare",
    )

    result = recognize_catalog(
        "Agenzia delle Entrate - Bonus edilizi 2024",
        [document],
        [],
    )

    assert result.match_type == "NO_MATCH"


@pytest.mark.parametrize(
    ("fixture_name", "expected_family"),
    (
        ("verbale_cds_comune_a.txt", "Verbale di violazione al Codice della Strada"),
        ("verbale_cds_comune_b.txt", "Verbale di violazione al Codice della Strada"),
        ("tassa_auto_regionale.txt", "Atto di accertamento tassa automobilistica regionale"),
    ),
)
def test_generic_local_and_regional_families_use_combined_strong_patterns(
    tmp_path, fixture_name: str, expected_family: str
) -> None:
    families = seeded_families(tmp_path)
    text = (FIXTURES / fixture_name).read_text(encoding="utf-8")

    result = recognize_catalog(text, [], families)

    assert result.match_type == "FAMILY_MATCH"
    assert result.family and result.family.nome == expected_family
    assert result.family.source_id is None
    assert result.family.official_url is None
    assert result.family.descrizione_ufficiale is None


@pytest.mark.parametrize(
    "text",
    (
        "È disponibile una certificazione relativa al pagamento.",
        "È stato redatto un verbale interno.",
        "Promemoria informale privo di riferimenti amministrativi.",
    ),
)
def test_generic_fragments_and_unknown_text_do_not_match(tmp_path, text: str) -> None:
    result = recognize_catalog(text, [], seeded_families(tmp_path))

    assert result.match_type == "NO_MATCH"


def test_optional_family_schema_migration_preserves_existing_rows(tmp_path) -> None:
    db_path = tmp_path / "migration.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        source_id = int(connection.execute("SELECT MIN(id) FROM sources").fetchone()[0])
        connection.execute("DROP TABLE document_families")
        connection.executescript(
            """
            CREATE TABLE document_families (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL REFERENCES sources(id),
                ente TEXT NOT NULL,
                nome TEXT NOT NULL,
                categoria TEXT,
                descrizione_ufficiale TEXT,
                keywords TEXT NOT NULL DEFAULT '[]',
                identifying_phrases TEXT NOT NULL DEFAULT '[]',
                official_url TEXT NOT NULL,
                stato_verifica TEXT NOT NULL,
                data_verifica TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (source_id, nome)
            );
            """
        )
        connection.execute(
            """
            INSERT INTO document_families (
                source_id, ente, nome, official_url, stato_verifica,
                created_at, updated_at
            ) VALUES (?, 'Ente legacy', 'Famiglia legacy',
                      'https://example.test/legacy', 'verificato', 'prima', 'prima')
            """,
            (source_id,),
        )
        connection.commit()

    initialize_database(db_path, seed_demo=True)
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        columns = {
            row["name"]: row["notnull"]
            for row in connection.execute(
                "PRAGMA table_info(document_families)"
            ).fetchall()
        }
        names = {
            row["nome"]
            for row in connection.execute("SELECT nome FROM document_families")
        }

    assert columns["source_id"] == 0
    assert columns["official_url"] == 0
    assert "Famiglia legacy" in names
    assert len(names) == 17


def test_family_without_verified_url_hides_the_link_button(tmp_path, monkeypatch) -> None:
    family = next(
        family
        for family in seeded_families(tmp_path)
        if family.nome == "Verbale di violazione al Codice della Strada"
    )

    class FakeStreamlit:
        def __init__(self) -> None:
            self.writes: list[str] = []
            self.links: list[tuple[str, str]] = []

        @staticmethod
        def header(*_args, **_kwargs) -> None:
            pass

        @staticmethod
        def subheader(*_args, **_kwargs) -> None:
            pass

        @staticmethod
        def markdown(*_args, **_kwargs) -> None:
            pass

        @staticmethod
        def caption(*_args, **_kwargs) -> None:
            pass

        @staticmethod
        def info(*_args, **_kwargs) -> None:
            pass

        @staticmethod
        def warning(*_args, **_kwargs) -> None:
            pass

        @staticmethod
        def expander(*_args, **_kwargs):
            return nullcontext()

        def write(self, value: str) -> None:
            self.writes.append(value)

        def text(self, value: str) -> None:
            self.writes.append(value)

        def link_button(self, label: str, url: str) -> None:
            self.links.append((label, url))

    fake_streamlit = FakeStreamlit()
    monkeypatch.setattr(app, "st", fake_streamlit)

    app.show_family_recognition(family, 80.0)

    assert fake_streamlit.links == []
    assert "Fonte non disponibile." in fake_streamlit.writes
