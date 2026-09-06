from __future__ import annotations

import sqlite3
from typing import Iterable

from src.models import OfficialSource


VERIFICATION_DATE = "2026-08-04"
V05_VERIFICATION_DATE = "2026-08-05"
V051_VERIFICATION_DATE = "2026-08-05"
V052_VERIFICATION_DATE = "2026-08-10"
V053_VERIFICATION_DATE = "2026-08-10"
OLD_INITIAL_NOTE = "Voce iniziale del registro; indirizzi istituzionali da verificare."

COVERAGE_STATUSES = {
    "parziale",
    "completa_rispetto_alla_fonte",
    "da_valutare",
    "bloccata",
}

INITIAL_COVERAGE_BY_ENTITY = {
    "Indice delle Pubbliche Amministrazioni (IPA)": "parziale",
    "INPS": "parziale",
    "INAIL": "parziale",
    "Agenzia delle Entrate-Riscossione": "bloccata",
    "Agenzia delle Entrate": "parziale",
    "Ministero del Lavoro": "parziale",
    "Ispettorato Nazionale del Lavoro": "completa_rispetto_alla_fonte",
    "Garante per la protezione dei dati personali": "completa_rispetto_alla_fonte",
}

SOURCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ente TEXT NOT NULL,
    nome_fonte TEXT NOT NULL,
    tipo_ente TEXT NOT NULL,
    livello TEXT NOT NULL,
    ambito TEXT NOT NULL,
    url_principale TEXT,
    url_modulistica TEXT,
    metodo_acquisizione TEXT NOT NULL,
    stato_verifica TEXT NOT NULL,
    coverage_status TEXT NOT NULL DEFAULT 'da_valutare'
        CHECK (coverage_status IN (
            'parziale', 'completa_rispetto_alla_fonte',
            'da_valutare', 'bloccata'
        )),
    data_verifica TEXT,
    note TEXT,
    attiva INTEGER NOT NULL DEFAULT 1,
    UNIQUE (ente, nome_fonte)
);

CREATE INDEX IF NOT EXISTS idx_sources_ente ON sources (ente);
CREATE INDEX IF NOT EXISTS idx_sources_ambito ON sources (ambito);
CREATE INDEX IF NOT EXISTS idx_sources_stato ON sources (stato_verifica);
"""


INITIAL_SOURCES = (
    OfficialSource(
        ente="Indice delle Pubbliche Amministrazioni (IPA)",
        nome_fonte="Registro IPA",
        tipo_ente="altro ente pubblico",
        livello="nazionale",
        ambito="generale",
        url_principale="https://indicepa.gov.it/",
        url_modulistica="https://indicepa.gov.it/ipa-dati/dataset/enti",
        metodo_acquisizione="ipa_api",
        stato_verifica="verificato",
        data_verifica=V05_VERIFICATION_DATE,
        note="Catalogo Open Data strutturato; non è una fonte di modulistica.",
    ),
    OfficialSource(
        ente="INPS",
        nome_fonte="Fonte istituzionale INPS",
        tipo_ente="ente nazionale",
        livello="nazionale",
        ambito="previdenza",
        url_principale="https://www.inps.it/it/it.html",
        url_modulistica="https://www.inps.it/it/it/moduli.html",
        metodo_acquisizione="pagina_html",
        stato_verifica="verificato",
        data_verifica=VERIFICATION_DATE,
        note="Pagina dedicata con ricerca e filtri per i moduli.",
    ),
    OfficialSource(
        ente="Agenzia delle Entrate-Riscossione",
        nome_fonte="Fonte istituzionale ADER",
        tipo_ente="ente pubblico economico",
        livello="nazionale",
        ambito="riscossione",
        url_principale="https://www.agenziaentrateriscossione.gov.it/it/",
        url_modulistica=(
            "https://www.agenziaentrateriscossione.gov.it/it/modulistica/index.html"
        ),
        metodo_acquisizione="ader_html",
        stato_verifica="verificato",
        data_verifica=V05_VERIFICATION_DATE,
        note="Pagina ufficiale della modulistica; importatore dedicato disponibile.",
    ),
    OfficialSource(
        ente="INAIL",
        nome_fonte="Fonte istituzionale INAIL",
        tipo_ente="ente nazionale",
        livello="nazionale",
        ambito="lavoro",
        url_principale="https://www.inail.it/portale/it.html",
        url_modulistica=(
            "https://www.inail.it/portale/it/atti-e-documenti/moduli-e-modelli/"
            "altri-moduli/abilitazione-ai-servizi-online.html"
        ),
        metodo_acquisizione="inail_html",
        stato_verifica="verificato",
        data_verifica=V051_VERIFICATION_DATE,
        note=(
            "Pagina pubblica verificata con collegamenti diretti ai moduli per "
            "l'abilitazione ai servizi online; importatore metadati disponibile."
        ),
    ),
    OfficialSource(
        ente="Agenzia delle Entrate",
        nome_fonte="Fonte istituzionale Agenzia delle Entrate",
        tipo_ente="agenzia",
        livello="nazionale",
        ambito="fiscale",
        url_principale="https://www.agenziaentrate.gov.it/portale/",
        url_modulistica=(
            "https://www.agenziaentrate.gov.it/portale/strumenti/modelli/"
            "tutti-i-modelli"
        ),
        metodo_acquisizione="ade_html",
        stato_verifica="verificato",
        data_verifica=V052_VERIFICATION_DATE,
        note=(
            "Raccolta ufficiale Tutti i modelli; acquisizione sequenziale dei "
            "soli metadati e collegamenti istituzionali."
        ),
    ),
    OfficialSource(
        ente="Ministero del Lavoro",
        nome_fonte="Fonte istituzionale Ministero del Lavoro",
        tipo_ente="ministero",
        livello="nazionale",
        ambito="lavoro",
        url_principale="https://www.lavoro.gov.it/",
        url_modulistica="https://www.lavoro.gov.it/strumenti-e-servizi/Modulistica/Pagine/Modulistica",
        metodo_acquisizione="lavoro_html",
        stato_verifica="verificato",
        data_verifica=V052_VERIFICATION_DATE,
        note="Pagina dedicata con filtri e collegamenti ai moduli.",
    ),
    OfficialSource(
        ente="Ministero dell'Interno",
        nome_fonte="Fonte istituzionale Ministero dell'Interno",
        tipo_ente="ministero",
        livello="nazionale",
        ambito="anagrafe",
        url_principale="https://www.interno.gov.it/it",
        url_modulistica="https://www.interno.gov.it/it/servizi/modulistica-norme-e-pareri",
        metodo_acquisizione="pagina_html",
        stato_verifica="verificato",
        data_verifica=VERIFICATION_DATE,
        note="Pagina tematica con modulistica e raccolte per settore.",
    ),
    OfficialSource(
        ente="Ministero delle Infrastrutture e dei Trasporti",
        nome_fonte="Fonte istituzionale Ministero dei Trasporti",
        tipo_ente="ministero",
        livello="nazionale",
        ambito="motorizzazione",
        url_principale="https://www.mit.gov.it/",
        url_modulistica=None,
        metodo_acquisizione="da_definire",
        stato_verifica="verificato",
        data_verifica=VERIFICATION_DATE,
        note="Modulistica distribuita nelle singole aree e procedure.",
    ),
    OfficialSource(
        ente="Ministero della Giustizia",
        nome_fonte="Fonte istituzionale Ministero della Giustizia",
        tipo_ente="ministero",
        livello="nazionale",
        ambito="giustizia",
        url_principale="https://www.giustizia.it/giustizia/it/homepage.page",
        url_modulistica=None,
        metodo_acquisizione="da_definire",
        stato_verifica="verificato",
        data_verifica=VERIFICATION_DATE,
        note="Moduli distribuiti tra servizi e siti degli uffici giudiziari.",
    ),
    OfficialSource(
        ente="Ministero della Salute",
        nome_fonte="Fonte istituzionale Ministero della Salute",
        tipo_ente="ministero",
        livello="nazionale",
        ambito="salute",
        url_principale="https://www.salute.gov.it/new/it/",
        url_modulistica=None,
        metodo_acquisizione="da_definire",
        stato_verifica="verificato",
        data_verifica=VERIFICATION_DATE,
        note="Moduli distribuiti nelle schede dei singoli servizi online.",
    ),
    OfficialSource(
        ente="Ministero delle Imprese e del Made in Italy",
        nome_fonte="Fonte istituzionale MIMIT",
        tipo_ente="ministero",
        livello="nazionale",
        ambito="imprese",
        url_principale="https://www.mimit.gov.it/it/",
        url_modulistica="https://www.mimit.gov.it/it/amministrazione-trasparente/attivita-e-procedimenti/tipologie-di-procedimento",
        metodo_acquisizione="pagina_html",
        stato_verifica="verificato",
        data_verifica=VERIFICATION_DATE,
        note="Modulistica raggiungibile dalle singole tipologie di procedimento.",
    ),
    OfficialSource(
        ente="Dipartimento della Funzione Pubblica",
        nome_fonte="Modulistica standardizzata Funzione Pubblica",
        tipo_ente="dipartimento",
        livello="nazionale",
        ambito="amministrazione pubblica",
        url_principale="https://www.funzionepubblica.gov.it/",
        url_modulistica=(
            "https://www.funzionepubblica.gov.it/it/il-dipartimento/"
            "area-di-interesse/semplificazione/"
            "la-semplificazione-della-modulistica/"
        ),
        metodo_acquisizione="da_definire",
        stato_verifica="verificato",
        data_verifica=V05_VERIFICATION_DATE,
        note="Pagina ufficiale dedicata alla modulistica unificata e standardizzata.",
    ),
    OfficialSource(
        ente="ACI / PRA",
        nome_fonte="Modulistica ufficiale PRA",
        tipo_ente="ente nazionale",
        livello="nazionale",
        ambito="pratiche automobilistiche",
        url_principale="https://www.aci.it/",
        url_modulistica=(
            "https://www.aci.it/servizi/guide-utili/guida-pratiche-auto/modulistica"
        ),
        metodo_acquisizione="da_definire",
        stato_verifica="verificato",
        data_verifica=V05_VERIFICATION_DATE,
        note="Pagina ufficiale dei modelli validi per le pratiche PRA.",
    ),
    OfficialSource(
        ente="Garante per la protezione dei dati personali",
        nome_fonte="Modulistica e servizi online Garante Privacy",
        tipo_ente="autorità indipendente",
        livello="nazionale",
        ambito="protezione dati personali",
        url_principale="https://www.garanteprivacy.it/",
        url_modulistica=(
            "https://www.garanteprivacy.it/home/modulistica-e-servizi-online"
        ),
        metodo_acquisizione="garante_html",
        stato_verifica="verificato",
        data_verifica=V052_VERIFICATION_DATE,
        note=(
            "Pagina ufficiale con modulistica e servizi telematici; "
            "importatore limitato alla raccolta dichiarata."
        ),
    ),
    OfficialSource(
        ente="Ispettorato Nazionale del Lavoro",
        nome_fonte="Servizi e modulistica INL",
        tipo_ente="agenzia",
        livello="nazionale",
        ambito="lavoro",
        url_principale="https://www.ispettorato.gov.it/",
        url_modulistica=(
            "https://www.ispettorato.gov.it/servizi-e-modulistica/"
            "scopri-i-servizi-e-la-modulistica/"
        ),
        metodo_acquisizione="inl_html",
        stato_verifica="verificato",
        data_verifica=V052_VERIFICATION_DATE,
        note=(
            "Raccolta ufficiale dei servizi e della modulistica per lavoratori "
            "e datori di lavoro o delegati."
        ),
    ),
)


def create_sources_table(connection: sqlite3.Connection) -> None:
    connection.executescript(SOURCE_SCHEMA)
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(sources)").fetchall()
    }
    if "coverage_status" not in columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN coverage_status TEXT NOT NULL "
            "DEFAULT 'da_valutare' CHECK (coverage_status IN "
            "('parziale', 'completa_rispetto_alla_fonte', "
            "'da_valutare', 'bloccata'))"
        )
    connection.commit()


def insert_source(connection: sqlite3.Connection, source: OfficialSource) -> int:
    cursor = connection.execute(
        """
        INSERT INTO sources (
            ente, nome_fonte, tipo_ente, livello, ambito,
            url_principale, url_modulistica, metodo_acquisizione,
            stato_verifica, coverage_status, data_verifica, note, attiva
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source.ente,
            source.nome_fonte,
            source.tipo_ente,
            source.livello,
            source.ambito,
            source.url_principale,
            source.url_modulistica,
            source.metodo_acquisizione,
            source.stato_verifica,
            source.coverage_status,
            source.data_verifica,
            source.note,
            int(source.attiva),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def insert_sources(
    connection: sqlite3.Connection,
    sources: Iterable[OfficialSource],
) -> int:
    inserted = 0
    for source in sources:
        insert_source(connection, source)
        inserted += 1
    return inserted


def update_source(connection: sqlite3.Connection, source: OfficialSource) -> bool:
    if source.id is None:
        raise ValueError("La fonte deve avere un ID per poter essere aggiornata.")

    cursor = connection.execute(
        """
        UPDATE sources SET
            ente = ?, nome_fonte = ?, tipo_ente = ?, livello = ?, ambito = ?,
            url_principale = ?, url_modulistica = ?, metodo_acquisizione = ?,
            stato_verifica = ?, coverage_status = ?, data_verifica = ?,
            note = ?, attiva = ?
        WHERE id = ?
        """,
        (
            source.ente,
            source.nome_fonte,
            source.tipo_ente,
            source.livello,
            source.ambito,
            source.url_principale,
            source.url_modulistica,
            source.metodo_acquisizione,
            source.stato_verifica,
            source.coverage_status,
            source.data_verifica,
            source.note,
            int(source.attiva),
            source.id,
        ),
    )
    connection.commit()
    return cursor.rowcount > 0


def _row_to_source(row: sqlite3.Row) -> OfficialSource:
    return OfficialSource(
        id=row["id"],
        ente=row["ente"],
        nome_fonte=row["nome_fonte"],
        tipo_ente=row["tipo_ente"],
        livello=row["livello"],
        ambito=row["ambito"],
        url_principale=row["url_principale"],
        url_modulistica=row["url_modulistica"],
        metodo_acquisizione=row["metodo_acquisizione"],
        stato_verifica=row["stato_verifica"],
        coverage_status=row["coverage_status"],
        data_verifica=row["data_verifica"],
        note=row["note"],
        attiva=bool(row["attiva"]),
    )


def get_source(
    connection: sqlite3.Connection,
    source_id: int,
) -> OfficialSource | None:
    row = connection.execute(
        "SELECT * FROM sources WHERE id = ?",
        (source_id,),
    ).fetchone()
    return _row_to_source(row) if row else None


def list_sources(connection: sqlite3.Connection) -> list[OfficialSource]:
    rows = connection.execute("SELECT * FROM sources ORDER BY ente, id").fetchall()
    return [_row_to_source(row) for row in rows]


def search_sources_by_ente(
    connection: sqlite3.Connection,
    ente: str,
) -> list[OfficialSource]:
    rows = connection.execute(
        """
        SELECT * FROM sources
        WHERE instr(lower(ente), lower(?)) > 0
        ORDER BY ente, id
        """,
        (ente.strip(),),
    ).fetchall()
    return [_row_to_source(row) for row in rows]


def search_sources_by_ambito(
    connection: sqlite3.Connection,
    ambito: str,
) -> list[OfficialSource]:
    rows = connection.execute(
        """
        SELECT * FROM sources
        WHERE ambito = ? COLLATE NOCASE
        ORDER BY ente, id
        """,
        (ambito.strip(),),
    ).fetchall()
    return [_row_to_source(row) for row in rows]


def list_active_sources(connection: sqlite3.Connection) -> list[OfficialSource]:
    rows = connection.execute(
        "SELECT * FROM sources WHERE attiva = 1 ORDER BY ente, id"
    ).fetchall()
    return [_row_to_source(row) for row in rows]


def filter_sources_by_status(
    connection: sqlite3.Connection,
    stato_verifica: str,
) -> list[OfficialSource]:
    rows = connection.execute(
        """
        SELECT * FROM sources
        WHERE stato_verifica = ? COLLATE NOCASE
        ORDER BY ente, id
        """,
        (stato_verifica.strip(),),
    ).fetchall()
    return [_row_to_source(row) for row in rows]


def update_source_coverage(
    connection: sqlite3.Connection,
    source_id: int,
    coverage_status: str,
) -> bool:
    if coverage_status not in COVERAGE_STATUSES:
        raise ValueError("Stato di copertura non valido.")
    cursor = connection.execute(
        "UPDATE sources SET coverage_status = ? WHERE id = ?",
        (coverage_status, source_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def seed_initial_sources(connection: sqlite3.Connection) -> int:
    count = int(connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
    if not count:
        inserted = insert_sources(connection, INITIAL_SOURCES)
        for entity, coverage_status in INITIAL_COVERAGE_BY_ENTITY.items():
            connection.execute(
                "UPDATE sources SET coverage_status = ? "
                "WHERE ente = ? COLLATE NOCASE",
                (coverage_status, entity),
            )
        connection.commit()
        return inserted

    inserted = 0
    for source in INITIAL_SOURCES:
        existing = connection.execute(
            """
            SELECT id FROM sources
            WHERE ente = ? COLLATE NOCASE AND nome_fonte = ? COLLATE NOCASE
            """,
            (source.ente, source.nome_fonte),
        ).fetchone()
        if existing is None:
            insert_source(connection, source)
            inserted += 1
            continue
        connection.execute(
            """
            UPDATE sources SET
                url_principale = ?, url_modulistica = ?,
                metodo_acquisizione = ?, stato_verifica = ?,
                data_verifica = ?, note = ?
            WHERE ente = ? AND nome_fonte = ?
              AND stato_verifica = 'da_verificare'
              AND url_principale IS NULL
              AND data_verifica IS NULL
              AND note = ?
            """,
            (
                source.url_principale,
                source.url_modulistica,
                source.metodo_acquisizione,
                source.stato_verifica,
                source.data_verifica,
                source.note,
                source.ente,
                source.nome_fonte,
                OLD_INITIAL_NOTE,
            ),
        )
    connection.execute(
        """
        UPDATE sources SET
            url_principale = 'https://indicepa.gov.it/',
            url_modulistica = 'https://indicepa.gov.it/ipa-dati/dataset/enti',
            metodo_acquisizione = 'ipa_api',
            data_verifica = ?
        WHERE ente = 'Indice delle Pubbliche Amministrazioni (IPA)'
          AND stato_verifica = 'verificato'
          AND url_modulistica IS NULL
          AND url_principale = 'https://www.indicepa.gov.it/ipa-portale/'
        """,
        (V05_VERIFICATION_DATE,),
    )
    connection.execute(
        """
        UPDATE sources SET
            url_modulistica = ?, metodo_acquisizione = 'inail_html',
            data_verifica = ?, note = ?
        WHERE ente = 'INAIL'
          AND stato_verifica = 'verificato'
          AND url_modulistica =
              'https://www.inail.it/portale/it/atti-e-documenti/moduli-e-modelli.html'
        """,
        (
            INITIAL_SOURCES[3].url_modulistica,
            V051_VERIFICATION_DATE,
            INITIAL_SOURCES[3].note,
        ),
    )
    for source in (
        INITIAL_SOURCES[4],
        INITIAL_SOURCES[5],
        INITIAL_SOURCES[13],
    ):
        connection.execute(
            """
            UPDATE sources SET
                url_principale = ?, url_modulistica = ?,
                metodo_acquisizione = ?, data_verifica = ?, note = ?
            WHERE ente = ? COLLATE NOCASE
              AND nome_fonte = ? COLLATE NOCASE
              AND stato_verifica = 'verificato'
            """,
            (
                source.url_principale,
                source.url_modulistica,
                source.metodo_acquisizione,
                source.data_verifica,
                source.note,
                source.ente,
                source.nome_fonte,
            ),
        )
    for entity, coverage_status in INITIAL_COVERAGE_BY_ENTITY.items():
        connection.execute(
            """
            UPDATE sources SET coverage_status = ?
            WHERE ente = ? COLLATE NOCASE
              AND coverage_status = 'da_valutare'
            """,
            (coverage_status, entity),
        )
    connection.commit()
    return inserted
