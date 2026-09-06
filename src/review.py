from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from src.database import DEFAULT_DB_PATH, connect_database, get_document, initialize_database
from src.explanations import (
    EXPLANATION_STATUS_REJECTED,
    EXPLANATION_STATUS_VERIFIED,
    _validate_timestamp,
    create_explanation,
    create_explanation_revision,
    get_explanation,
    normalize_review_notes,
    normalize_reviewer_name,
    record_review_event,
    reject_explanation,
    update_explanation,
    verify_explanation,
)
from src.models import DocumentExplanation


def editorial_lines_to_items(value: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in value.splitlines() if line.strip())


def save_editorial_changes(
    explanation_id: int,
    *,
    official_summary: str | None,
    simple_explanation: str | None,
    intended_use: str | None,
    possible_users: tuple[str, ...],
    facts_from_source: tuple[str, ...],
    missing_information: tuple[str, ...],
    warnings: tuple[str, ...],
    review_notes: str | None,
    db_path: str | Path = DEFAULT_DB_PATH,
    updated_at: str | None = None,
    reviewed_by: str = "Operatore locale non identificato",
) -> bool:
    initialize_database(db_path, seed_demo=False)
    timestamp = updated_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    with connect_database(db_path) as connection:
        current = get_explanation(connection, explanation_id)
        if current is None:
            return False
        updated = replace(
            current,
            official_summary=official_summary,
            simple_explanation=simple_explanation,
            intended_use=intended_use,
            possible_users=possible_users,
            facts_from_source=facts_from_source,
            missing_information=missing_information,
            warnings=warnings,
            review_notes=review_notes,
            updated_at=timestamp,
        )
        return update_explanation(connection, updated, reviewed_by=reviewed_by)


def submit_explanation_review(
    explanation_id: int,
    decision: str,
    reviewer: str,
    *,
    source_confirmed: bool,
    review_notes: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    reviewed_at: str | None = None,
) -> bool:
    initialize_database(db_path, seed_demo=False)
    with connect_database(db_path) as connection:
        if decision == EXPLANATION_STATUS_VERIFIED:
            return verify_explanation(
                connection,
                explanation_id,
                reviewer,
                source_confirmed=source_confirmed,
                review_notes=review_notes,
                verified_at=reviewed_at,
            )
        if decision == EXPLANATION_STATUS_REJECTED:
            return reject_explanation(
                connection,
                explanation_id,
                reviewed_by=reviewer,
                review_notes=review_notes,
                reviewed_at=reviewed_at,
            )
    raise ValueError("Decisione di revisione non valida.")


def submit_explanation_revision(
    explanation_id: int, new_version: str, reviewer: str, *,
    review_notes: str | None = None, db_path: str | Path = DEFAULT_DB_PATH,
    created_at: str | None = None,
) -> int:
    initialize_database(db_path, seed_demo=False)
    with connect_database(db_path) as connection:
        return create_explanation_revision(connection, explanation_id, new_version, reviewer,
                                           review_notes=review_notes, created_at=created_at)


def submit_explanation_draft(
    document_id: int, version: str, reviewer: str, source_access_date: str, *,
    review_notes: str | None = None, db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    """Prepara una bozza dai soli metadati già presenti, senza spiegazioni inventate."""
    author = normalize_reviewer_name(reviewer)
    initialize_database(db_path, seed_demo=False)
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    with connect_database(db_path) as connection:
        document = get_document(connection, document_id)
        if document is None:
            raise ValueError("Documento non trovato.")
        source_url = document.detail_url or document.fonte_url or document.download_url
        if not source_url:
            raise ValueError("Manca il riferimento istituzionale del documento.")
        if connection.execute("SELECT 1 FROM document_explanations WHERE document_id = ? AND version = ?", (document_id, version.strip())).fetchone():
            raise ValueError("La versione indicata esiste già per questo documento.")
        draft = DocumentExplanation(
            document_id=document_id, official_summary=document.descrizione_ufficiale,
            simple_explanation=None, intended_use=None, possible_users=(),
            facts_from_source=(f"Titolo registrato nel catalogo: {document.titolo_ufficiale}",),
            missing_information=("Spiegazione editoriale da preparare e confrontare con il materiale ufficiale locale.",),
            warnings=("Bozza non verificata; i metadati del catalogo non attestano la revisione del contenuto.",),
            source_url=source_url, source_access_date=source_access_date,
            verification_status="bozza", version=version, created_at=timestamp,
            updated_at=timestamp, review_notes=review_notes,
        )
        explanation_id, _ = create_explanation(connection, draft, created_by=author)
        return explanation_id


def submit_document_review(
    document_id: int, decision: str, reviewer: str, *, source_confirmed: bool = False,
    review_notes: str | None = None, db_path: str | Path = DEFAULT_DB_PATH,
    reviewed_at: str | None = None,
) -> bool:
    if decision not in {"verificato", "rifiutato", "da_verificare"}:
        raise ValueError("Decisione di revisione documento non valida.")
    author = normalize_reviewer_name(reviewer)
    notes = normalize_review_notes(review_notes)
    timestamp = _validate_timestamp(reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat())
    if decision == "verificato" and not source_confirmed:
        raise ValueError("Confermare il confronto con il materiale ufficiale prima della verifica.")
    initialize_database(db_path, seed_demo=False)
    with connect_database(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = get_document(connection, document_id)
        if current is None:
            return False
        if current.stato_verifica == "demo":
            raise ValueError("Un documento demo deve conservare lo stato dimostrativo.")
        if current.stato_verifica == "verificato" and decision != "verificato" and not notes:
            raise ValueError("La motivazione è obbligatoria per revocare una verifica documento.")
        if decision == "verificato":
            provenance = connection.execute("SELECT 1 FROM document_provenance WHERE document_id = ?", (document_id,)).fetchone()
            if current.source_id is None or provenance is None:
                raise ValueError("Una verifica richiede fonte e provenienza documentale registrate.")
        connection.execute("UPDATE documents SET stato_verifica = ? WHERE id = ?", (decision, document_id))
        after = asdict(replace(current, stato_verifica=decision))
        record_review_event(
            connection, entity_type="document", entity_id=document_id,
            object_version=current.versione, decision=decision, reviewer=author,
            reviewed_at=timestamp, before=asdict(current), after=after, notes=notes,
        )
    return True


def submit_resource_review(
    resource_id: int, decision: str, reviewer: str, *, source_confirmed: bool = False,
    review_notes: str | None = None, db_path: str | Path = DEFAULT_DB_PATH,
    resource_root: str | Path | None = None, reviewed_at: str | None = None,
) -> bool:
    from src.local_resources import LocalResource, read_resource_text

    if decision not in {"verificato", "rifiutato", "da_verificare"}:
        raise ValueError("Decisione di revisione risorsa non valida.")
    author = normalize_reviewer_name(reviewer)
    notes = normalize_review_notes(review_notes)
    timestamp = _validate_timestamp(reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat())
    if decision == "verificato" and not source_confirmed:
        raise ValueError("Confermare il confronto della risorsa con il materiale ufficiale.")
    initialize_database(db_path, seed_demo=False)
    with connect_database(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM local_resources WHERE id = ?", (resource_id,)).fetchone()
        if row is None:
            return False
        current = LocalResource(**dict(row))
        if current.verification_status == "demo":
            raise ValueError("Una risorsa demo deve conservare lo stato dimostrativo.")
        if current.verification_status == "verificato" and decision != "verificato" and not notes:
            raise ValueError("La motivazione è obbligatoria per revocare una verifica della risorsa.")
        if decision == "verificato":
            document = get_document(connection, current.document_id)
            if document is None or document.source_id != current.source_id:
                raise ValueError("La fonte della risorsa non coincide con quella del documento.")
            # Il controllo esplicito può riesaminare una risorsa ritirata; lo stato
            # persistito cambia soltanto dopo che impronta e dimensione sono valide.
            read_resource_text(replace(current, verification_status="da_verificare"),
                               resource_root, connection=connection)
        connection.execute("UPDATE local_resources SET verification_status = ? WHERE id = ?", (decision, resource_id))
        record_review_event(
            connection, entity_type="resource", entity_id=resource_id, object_version=current.version,
            decision=decision, reviewer=author, reviewed_at=timestamp, before=asdict(current),
            after=asdict(replace(current, verification_status=decision)), notes=notes,
        )
    return True
