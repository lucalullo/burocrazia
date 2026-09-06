from __future__ import annotations

from datetime import UTC, datetime
import json
import sqlite3

from src.models import DocumentFamily


FAMILIES_TABLE_SCHEMA = """
CREATE TABLE {if_not_exists}document_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER REFERENCES sources(id),
    ente TEXT NOT NULL,
    nome TEXT NOT NULL,
    categoria TEXT,
    descrizione_ufficiale TEXT,
    keywords TEXT NOT NULL DEFAULT '[]',
    identifying_phrases TEXT NOT NULL DEFAULT '[]',
    official_url TEXT,
    stato_verifica TEXT NOT NULL,
    data_verifica TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (source_id, nome)
);
"""

FAMILIES_INDEX_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_families_source ON document_families (source_id);
CREATE INDEX IF NOT EXISTS idx_families_entity ON document_families (ente);
CREATE INDEX IF NOT EXISTS idx_families_status ON document_families (stato_verifica);
"""

CARTELLA_FAMILY_URL = (
    "https://www.agenziaentrateriscossione.gov.it/it/"
    "la-guida-alla-cartella-di-pagamento/la-cartella-di-pagamento/"
)
ADER_PAGOPA_URL = (
    "https://www.agenziaentrateriscossione.gov.it/it/Per-saperne-di-piu/"
    "documenti-della-riscossione/Modulo-di-pagamento-pagoPA/"
)
ADER_ACCERTAMENTO_URL = (
    "https://www.agenziaentrateriscossione.gov.it/it/la-guida-alla-cartella-"
    "di-pagamento/lavviso-di-presa-in-carico-e-lavviso-di-accertamento-"
    "esecutivo/cosa-sono/index.html"
)
ADER_ADDEBITO_URL = (
    "https://www.agenziaentrateriscossione.gov.it/it/Per-saperne-di-piu/"
    "documenti-della-riscossione/accertamento-esecutivo-e-avviso-di-addebito-inps/"
)
ADER_AVVISI_URL = (
    "https://www.agenziaentrateriscossione.gov.it/it/Per-saperne-di-piu/"
    "documenti-della-riscossione/avvisi-e-solleciti/index.html"
)
MIT_PATENTI_URL = (
    "https://mit.gov.it/come-fare-per/patenti-mezzi-e-abilitazioni/"
    "patenti-mezzi-stradali"
)
MIT_CONVERSIONE_URL = "https://www.mit.gov.it/conversione-patente-estera"
MIT_PRATICHE_URL = "https://mit.gov.it/come-fare-per/patenti-mezzi-e-abilitazioni"
INL_INTERVENTION_URL = (
    "https://www.ispettorato.gov.it/servizio/richiesta-di-intervento-ispettivo/"
)
GARANTE_COMPLAINT_URL = (
    "https://www.garanteprivacy.it/diritti/"
    "come-agire-per-tutelare-i-tuoi-dati-personali/reclamo"
)
GARANTE_RIGHTS_URL = (
    "https://www.garanteprivacy.it/home/modulistica-e-servizi-online"
)


def create_families_table(connection: sqlite3.Connection) -> None:
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'document_families'"
    ).fetchone()
    if table_exists is None:
        connection.execute(
            FAMILIES_TABLE_SCHEMA.format(if_not_exists="IF NOT EXISTS ")
        )
    else:
        columns = {
            str(row["name"]): int(row["notnull"])
            for row in connection.execute(
                "PRAGMA table_info(document_families)"
            ).fetchall()
        }
        if columns.get("source_id") or columns.get("official_url"):
            _migrate_families_to_optional_source(connection)
    connection.executescript(FAMILIES_INDEX_SCHEMA)


def _migrate_families_to_optional_source(connection: sqlite3.Connection) -> None:
    """Make source metadata optional without changing existing family rows."""
    old_count = int(
        connection.execute("SELECT COUNT(*) FROM document_families").fetchone()[0]
    )
    connection.execute("SAVEPOINT migrate_families_optional_source")
    try:
        connection.execute(
            "ALTER TABLE document_families RENAME TO document_families_backup"
        )
        connection.execute(FAMILIES_TABLE_SCHEMA.format(if_not_exists=""))
        connection.execute(
            """
            INSERT INTO document_families (
                id, source_id, ente, nome, categoria, descrizione_ufficiale,
                keywords, identifying_phrases, official_url, stato_verifica,
                data_verifica, created_at, updated_at
            )
            SELECT
                id, source_id, ente, nome, categoria, descrizione_ufficiale,
                keywords, identifying_phrases, official_url, stato_verifica,
                data_verifica, created_at, updated_at
            FROM document_families_backup
            """
        )
        new_count = int(
            connection.execute("SELECT COUNT(*) FROM document_families").fetchone()[0]
        )
        if new_count != old_count:
            raise RuntimeError("Migrazione famiglie incompleta.")
        connection.execute("DROP TABLE document_families_backup")
        connection.execute("RELEASE SAVEPOINT migrate_families_optional_source")
    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT migrate_families_optional_source")
        connection.execute("RELEASE SAVEPOINT migrate_families_optional_source")
        raise


def _row_to_family(row: sqlite3.Row) -> DocumentFamily:
    return DocumentFamily(
        id=row["id"],
        source_id=row["source_id"],
        ente=row["ente"],
        nome=row["nome"],
        categoria=row["categoria"],
        descrizione_ufficiale=row["descrizione_ufficiale"],
        keywords=tuple(json.loads(row["keywords"] or "[]")),
        identifying_phrases=tuple(json.loads(row["identifying_phrases"] or "[]")),
        official_url=row["official_url"],
        stato_verifica=row["stato_verifica"],
        data_verifica=row["data_verifica"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def insert_document_family(
    connection: sqlite3.Connection,
    family: DocumentFamily,
) -> int:
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    cursor = connection.execute(
        """
        INSERT INTO document_families (
            source_id, ente, nome, categoria, descrizione_ufficiale,
            keywords, identifying_phrases, official_url, stato_verifica,
            data_verifica, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            family.source_id,
            family.ente,
            family.nome,
            family.categoria,
            family.descrizione_ufficiale,
            json.dumps(family.keywords, ensure_ascii=False),
            json.dumps(family.identifying_phrases, ensure_ascii=False),
            family.official_url,
            family.stato_verifica,
            family.data_verifica,
            family.created_at or now,
            family.updated_at or now,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def list_document_families(
    connection: sqlite3.Connection,
) -> list[DocumentFamily]:
    rows = connection.execute(
        "SELECT * FROM document_families ORDER BY ente, nome, id"
    ).fetchall()
    return [_row_to_family(row) for row in rows]


def seed_initial_families(connection: sqlite3.Connection) -> int:
    source_rows = connection.execute(
        """
        SELECT id, ente, url_modulistica FROM sources
        WHERE ente IN (
            'Agenzia delle Entrate-Riscossione',
            'Agenzia delle Entrate',
            'Ministero delle Infrastrutture e dei Trasporti',
            'Ispettorato Nazionale del Lavoro',
            'Garante per la protezione dei dati personali'
        )
          AND stato_verifica = 'verificato'
          AND attiva = 1
        ORDER BY id
        """
    ).fetchall()
    source_ids = {str(row["ente"]): int(row["id"]) for row in source_rows}
    source_urls = {
        str(row["ente"]): row["url_modulistica"] for row in source_rows
    }
    ader_source_id = source_ids.get("Agenzia delle Entrate-Riscossione")
    ade_source_id = source_ids.get("Agenzia delle Entrate")
    mit_source_id = source_ids.get("Ministero delle Infrastrutture e dei Trasporti")
    inl_source_id = source_ids.get("Ispettorato Nazionale del Lavoro")
    garante_source_id = source_ids.get(
        "Garante per la protezione dei dati personali"
    )
    candidates: list[DocumentFamily] = []
    if ader_source_id is not None:
        candidates.extend(
            (
                DocumentFamily(
                    source_id=ader_source_id,
                    ente="Agenzia delle Entrate-Riscossione",
                    nome="Cartella di pagamento",
                    categoria="riscossione",
                    descrizione_ufficiale=(
                        "Atto notificato da Agenzia delle Entrate-Riscossione "
                        "per il recupero dei crediti affidati dagli enti creditori."
                    ),
                    keywords=("modulo di pagamento", "pagoPA"),
                    identifying_phrases=(
                        "cartella di pagamento",
                        "agenzia delle entrate-riscossione",
                        "agente della riscossione",
                    ),
                    official_url=CARTELLA_FAMILY_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
                DocumentFamily(
                    source_id=ader_source_id,
                    ente="Agenzia delle Entrate-Riscossione",
                    nome="Modulo di pagamento pagoPA",
                    categoria="pagamenti",
                    descrizione_ufficiale=(
                        "Modulo adottato da Agenzia delle Entrate-Riscossione "
                        "per i pagamenti tramite il sistema pagoPA."
                    ),
                    keywords=("pagoPA", "modulo di pagamento"),
                    identifying_phrases=(
                        "modulo di pagamento pagopa",
                        "nuovo modulo di pagamento pagopa",
                        "codice modulo di pagamento",
                    ),
                    official_url=ADER_PAGOPA_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
                DocumentFamily(
                    source_id=ader_source_id,
                    ente="Agenzia delle Entrate-Riscossione",
                    nome="Accertamento esecutivo",
                    categoria="riscossione",
                    descrizione_ufficiale=(
                        "Atto notificato direttamente dagli enti creditori che "
                        "contiene l'intimazione ad adempiere al pagamento."
                    ),
                    keywords=("avviso di presa in carico",),
                    identifying_phrases=(
                        "avviso di accertamento esecutivo",
                        "accertamento esecutivo",
                    ),
                    official_url=ADER_ACCERTAMENTO_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
                DocumentFamily(
                    source_id=ader_source_id,
                    ente="Agenzia delle Entrate-Riscossione",
                    nome="Avviso di addebito INPS",
                    categoria="riscossione previdenziale",
                    descrizione_ufficiale=(
                        "Atto notificato dall'INPS per la riscossione dei crediti "
                        "previdenziali e avente valore di titolo esecutivo."
                    ),
                    keywords=("crediti previdenziali", "INPS"),
                    identifying_phrases=(
                        "avviso di addebito inps",
                        "avviso di addebito",
                    ),
                    official_url=ADER_ADDEBITO_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
                DocumentFamily(
                    source_id=ader_source_id,
                    ente="Agenzia delle Entrate-Riscossione",
                    nome="Avvisi e solleciti",
                    categoria="riscossione",
                    descrizione_ufficiale=(
                        "Comunicazioni di sollecito, preavviso e avviso che "
                        "Agenzia delle Entrate-Riscossione trasmette ai cittadini."
                    ),
                    keywords=("sollecito", "preavviso", "avviso"),
                    identifying_phrases=(
                        "sollecito di pagamento",
                        "preavviso di fermo",
                        "avviso di intimazione",
                    ),
                    official_url=ADER_AVVISI_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
            )
        )
    if mit_source_id is not None:
        candidates.extend(
            (
                DocumentFamily(
                    source_id=mit_source_id,
                    ente="Ministero delle Infrastrutture e dei Trasporti",
                    nome="Patente di guida",
                    categoria="motorizzazione",
                    descrizione_ufficiale=(
                        "Famiglia delle patenti per i mezzi stradali trattata "
                        "nelle procedure del Ministero."
                    ),
                    keywords=("patente", "motorizzazione civile"),
                    identifying_phrases=(
                        "patente di guida",
                        "ufficio motorizzazione civile",
                    ),
                    official_url=MIT_PATENTI_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
                DocumentFamily(
                    source_id=mit_source_id,
                    ente="Ministero delle Infrastrutture e dei Trasporti",
                    nome="Conversione patente",
                    categoria="motorizzazione",
                    descrizione_ufficiale=(
                        "Procedura di sostituzione di una patente estera con "
                        "un documento di guida italiano."
                    ),
                    keywords=("patente estera", "TT2112"),
                    identifying_phrases=(
                        "conversione patente estera",
                        "domanda di conversione",
                        "ufficio motorizzazione civile",
                    ),
                    official_url=MIT_CONVERSIONE_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
                DocumentFamily(
                    source_id=mit_source_id,
                    ente="Ministero delle Infrastrutture e dei Trasporti",
                    nome="Pratiche motorizzazione",
                    categoria="motorizzazione",
                    descrizione_ufficiale=(
                        "Procedure e modulistica dell'area patenti, mezzi e "
                        "abilitazioni del Ministero."
                    ),
                    keywords=("pratica", "motorizzazione"),
                    identifying_phrases=(
                        "pratica di motorizzazione",
                        "ufficio motorizzazione civile",
                    ),
                    official_url=MIT_PRATICHE_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
                DocumentFamily(
                    source_id=mit_source_id,
                    ente="Ministero delle Infrastrutture e dei Trasporti",
                    nome="Immatricolazione",
                    categoria="motorizzazione",
                    descrizione_ufficiale=(
                        "Famiglia delle pratiche di immatricolazione dei veicoli."
                    ),
                    keywords=("veicolo", "motorizzazione"),
                    identifying_phrases=(
                        "domanda di immatricolazione",
                        "immatricolazione del veicolo",
                        "ufficio motorizzazione civile",
                    ),
                    official_url=MIT_PRATICHE_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-05",
                ),
            )
        )

    if inl_source_id is not None:
        candidates.append(
            DocumentFamily(
                source_id=inl_source_id,
                ente="Ispettorato Nazionale del Lavoro",
                nome="Richiesta di intervento ispettivo",
                categoria="vigilanza",
                descrizione_ufficiale=None,
                keywords=("INL 31", "ispettorato territoriale del lavoro"),
                identifying_phrases=(
                    "richiesta di intervento ispettivo",
                    "modulo INL 31",
                ),
                official_url=INL_INTERVENTION_URL,
                stato_verifica="verificato",
                data_verifica="2026-08-10",
            )
        )

    if garante_source_id is not None:
        candidates.extend(
            (
                DocumentFamily(
                    source_id=garante_source_id,
                    ente="Garante per la protezione dei dati personali",
                    nome="Reclamo",
                    categoria="protezione dati personali",
                    descrizione_ufficiale=None,
                    keywords=("Garante", "violazione"),
                    identifying_phrases=(
                        "reclamo al Garante",
                        "modello facsimile per il reclamo",
                    ),
                    official_url=GARANTE_COMPLAINT_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-10",
                ),
                DocumentFamily(
                    source_id=garante_source_id,
                    ente="Garante per la protezione dei dati personali",
                    nome="Esercizio dei diritti privacy",
                    categoria="protezione dati personali",
                    descrizione_ufficiale=None,
                    keywords=("articoli 15 22", "titolare del trattamento"),
                    identifying_phrases=(
                        "esercizio dei diritti in materia di protezione dei dati personali",
                        "modello per l'esercizio dei diritti",
                    ),
                    official_url=GARANTE_RIGHTS_URL,
                    stato_verifica="verificato",
                    data_verifica="2026-08-10",
                ),
            )
        )

    if ade_source_id is not None:
        ade_official_url = source_urls.get("Agenzia delle Entrate")
        candidates.extend(
            (
                DocumentFamily(
                    source_id=ade_source_id,
                    ente="Agenzia delle Entrate",
                    nome="Modello 730",
                    categoria="dichiarazioni",
                    descrizione_ufficiale=None,
                    keywords=("730", "redditi"),
                    identifying_phrases=(
                        "modello 730",
                        "dichiarazione dei redditi modello 730",
                    ),
                    official_url=ade_official_url,
                    stato_verifica="verificato",
                    data_verifica="2026-08-13",
                ),
                DocumentFamily(
                    source_id=ade_source_id,
                    ente="Agenzia delle Entrate",
                    nome="Certificazione Unica",
                    categoria="certificazioni fiscali",
                    descrizione_ufficiale=None,
                    keywords=("CU",),
                    identifying_phrases=(
                        "certificazione unica",
                        "modello CU",
                    ),
                    official_url=ade_official_url,
                    stato_verifica="verificato",
                    data_verifica="2026-08-13",
                ),
            )
        )

    candidates.extend(
        (
            DocumentFamily(
                source_id=None,
                ente="Polizia Locale / Ente locale",
                nome="Verbale di violazione al Codice della Strada",
                categoria="sanzioni amministrative",
                descrizione_ufficiale=None,
                keywords=("comune", "comando"),
                identifying_phrases=(
                    "verbale di contestazione",
                    "codice della strada",
                    "polizia locale",
                ),
                official_url=None,
                stato_verifica="verificato",
                data_verifica="2026-08-13",
            ),
            DocumentFamily(
                source_id=None,
                ente="Regione / Ente regionale",
                nome="Atto di accertamento tassa automobilistica regionale",
                categoria="tributi regionali",
                descrizione_ufficiale=None,
                keywords=("regione", "veicolo"),
                identifying_phrases=(
                    "atto di accertamento",
                    "tassa automobilistica regionale",
                    "omesso o irregolare versamento",
                    "irrogazione di sanzioni",
                ),
                official_url=None,
                stato_verifica="verificato",
                data_verifica="2026-08-13",
            ),
        )
    )

    inserted = 0
    for candidate in candidates:
        existing = connection.execute(
            """
            SELECT id FROM document_families
            WHERE source_id IS ? AND nome = ? COLLATE NOCASE
            """,
            (candidate.source_id, candidate.nome),
        ).fetchone()
        if existing is not None:
            continue
        insert_document_family(connection, candidate)
        inserted += 1
    return inserted
