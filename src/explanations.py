from __future__ import annotations

import json
import sqlite3
import unicodedata
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from functools import wraps
from typing import Iterable

from src.models import DocumentExplanation
from src.official_urls import OFFICIAL_DOMAIN_ALLOWLIST, is_official_url


EXPLANATION_STATUS_DRAFT = "bozza"
EXPLANATION_STATUS_PENDING = "da_verificare"
EXPLANATION_STATUS_VERIFIED = "verificato"
EXPLANATION_STATUS_REJECTED = "rifiutato"
EXPLANATION_STATUSES = frozenset(
    {
        EXPLANATION_STATUS_DRAFT,
        EXPLANATION_STATUS_PENDING,
        EXPLANATION_STATUS_VERIFIED,
        EXPLANATION_STATUS_REJECTED,
    }
)
PRELIMINARY_EXPLANATION_STATUSES = frozenset(
    {EXPLANATION_STATUS_DRAFT, EXPLANATION_STATUS_PENDING}
)
MAX_REVIEWER_NAME_LENGTH = 120
MAX_REVIEW_NOTES_LENGTH = 1_000


def _atomic_review_write(function):
    @wraps(function)
    def wrapped(connection, *args, **kwargs):
        started = not connection.in_transaction
        if started:
            connection.execute("BEGIN")
        connection.execute("SAVEPOINT burocrazia_review_write")
        try:
            result = function(connection, *args, **kwargs)
            connection.execute("RELEASE burocrazia_review_write")
        except Exception:
            connection.execute("ROLLBACK TO burocrazia_review_write")
            connection.execute("RELEASE burocrazia_review_write")
            if started:
                connection.rollback()
            raise
        if kwargs.get("commit", True):
            connection.commit()
        return result
    return wrapped


def create_review_events_table(connection: sqlite3.Connection) -> None:
    """Registro locale append-only; nessuna ricostruzione di verifiche pregresse.

    Gli ID restano nel registro anche quando il record originale viene eliminato.
    I trigger impediscono modifiche accidentali, non proteggono da chi controlla SQLite.
    """
    connection.execute("""
        CREATE TABLE IF NOT EXISTS review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL CHECK (entity_type IN ('document', 'explanation', 'resource')),
            entity_id INTEGER NOT NULL,
            object_version TEXT NOT NULL,
            decision TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            reviewer TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
            reviewed_at TEXT NOT NULL,
            notes TEXT,
            before_json TEXT,
            after_json TEXT NOT NULL
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_review_events_object ON review_events (entity_type, entity_id, id)")
    for operation in ("UPDATE", "DELETE"):
        connection.execute(f"""
            CREATE TRIGGER IF NOT EXISTS review_events_no_{operation.lower()}
            BEFORE {operation} ON review_events BEGIN
                SELECT RAISE(ABORT, 'Il registro di revisione è append-only');
            END
        """)


def record_review_event(
    connection: sqlite3.Connection, *, entity_type: str, entity_id: int,
    object_version: str | None, decision: str, reviewer: str, reviewed_at: str,
    before: dict | None, after: dict, notes: str | None = None,
) -> int:
    reviewer = normalize_reviewer_name(reviewer)
    timestamp = _validate_timestamp(reviewed_at)
    status_field = "stato_verifica" if entity_type == "document" else "verification_status"
    cursor = connection.execute("""
        INSERT INTO review_events (entity_type, entity_id, object_version, decision,
            previous_status, new_status, reviewer, reviewed_at, notes, before_json, after_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (entity_type, entity_id, object_version or "non dichiarata", decision,
          before.get(status_field) if before and before.get("id") == entity_id else None, after[status_field], reviewer,
          timestamp, normalize_review_notes(notes),
          json.dumps(before, ensure_ascii=False, sort_keys=True) if before else None,
          json.dumps(after, ensure_ascii=False, sort_keys=True)))
    return int(cursor.lastrowid)


def list_review_events(
    connection: sqlite3.Connection, *, object_type: str | None = None,
    object_id: int | None = None,
) -> list[dict]:
    conditions, parameters = [], []
    if object_type is not None:
        if object_type not in {"document", "explanation", "resource"}:
            raise ValueError("Tipo di oggetto revisione non valido.")
        conditions.append("entity_type = ?")
        parameters.append(object_type)
    if object_id is not None:
        conditions.append("entity_id = ?")
        parameters.append(object_id)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    return [dict(row) for row in connection.execute("SELECT * FROM review_events" + where + " ORDER BY id", parameters)]


def create_explanations_table(connection: sqlite3.Connection) -> None:
    allowed_statuses = ", ".join(
        f"'{status}'" for status in sorted(EXPLANATION_STATUSES)
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS document_explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            official_summary TEXT,
            simple_explanation TEXT,
            intended_use TEXT,
            possible_users TEXT NOT NULL DEFAULT '[]',
            facts_from_source TEXT NOT NULL DEFAULT '[]',
            missing_information TEXT NOT NULL DEFAULT '[]',
            warnings TEXT NOT NULL DEFAULT '[]',
            source_url TEXT NOT NULL,
            source_access_date TEXT NOT NULL,
            verification_status TEXT NOT NULL CHECK (
                verification_status IN ({allowed_statuses})
            ),
            verified_by TEXT,
            verified_at TEXT,
            review_notes TEXT,
            version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (document_id, version)
        )
        """
    )
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(document_explanations)"
        ).fetchall()
    }
    if "review_notes" not in columns:
        connection.execute(
            "ALTER TABLE document_explanations ADD COLUMN review_notes TEXT"
        )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_document_explanations_document
        ON document_explanations (document_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_document_explanations_status
        ON document_explanations (verification_status)
        """
    )


def serialize_string_list(values: Iterable[str] | None) -> str:
    cleaned = []
    for value in values or ():
        if not isinstance(value, str):
            continue
        item = value.strip()
        if item:
            cleaned.append(item)
    return json.dumps(cleaned, ensure_ascii=False)


def deserialize_string_list(raw_value: object) -> tuple[str, ...]:
    if raw_value is None or raw_value == "":
        return ()
    try:
        parsed = json.loads(str(raw_value))
    except (json.JSONDecodeError, TypeError, ValueError):
        return ()
    if not isinstance(parsed, list):
        return ()
    return tuple(
        item.strip()
        for item in parsed
        if isinstance(item, str) and item.strip()
    )


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def validate_explanation_status(status: str) -> str:
    cleaned = status.strip() if isinstance(status, str) else ""
    if cleaned not in EXPLANATION_STATUSES:
        raise ValueError("Stato spiegazione non valido.")
    return cleaned


def normalize_reviewer_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Inserire il nome del revisore prima della revisione.")
    normalized = unicodedata.normalize("NFKC", value)
    visible = "".join(
        character
        for character in normalized
        if unicodedata.category(character) not in {"Cc", "Cf"}
    )
    cleaned = " ".join(visible.split())
    if not cleaned or not any(
        unicodedata.category(character)[0] in {"L", "N"}
        for character in cleaned
    ):
        raise ValueError("Inserire il nome del revisore prima della revisione.")
    if len(cleaned) > MAX_REVIEWER_NAME_LENGTH:
        raise ValueError(
            f"Il nome del revisore non può superare {MAX_REVIEWER_NAME_LENGTH} caratteri."
        )
    return cleaned


def reviewer_name_is_valid(value: str) -> bool:
    try:
        normalize_reviewer_name(value)
    except ValueError:
        return False
    return True


def normalize_review_notes(value: str | None) -> str | None:
    cleaned = _clean_optional(value)
    if cleaned is None:
        return None
    if not any(unicodedata.category(character)[0] in {"L", "N"} for character in cleaned):
        return None
    if len(cleaned) > MAX_REVIEW_NOTES_LENGTH:
        raise ValueError(
            f"Le note di revisione non possono superare {MAX_REVIEW_NOTES_LENGTH} caratteri."
        )
    return cleaned


def can_verify_explanation(
    reviewer: str, source_confirmed: bool, *, explanation: DocumentExplanation | None = None,
    document_status: str | None = None,
) -> bool:
    return (bool(source_confirmed) and reviewer_name_is_valid(reviewer) and document_status != "rifiutato"
            and (explanation is None or bool(_clean_optional(explanation.simple_explanation))))


def _validate_explanation(explanation: DocumentExplanation) -> None:
    if explanation.document_id <= 0:
        raise ValueError("La spiegazione deve essere collegata a un documento valido.")
    validate_explanation_status(explanation.verification_status)
    if not explanation.version.strip():
        raise ValueError("La versione della spiegazione è obbligatoria.")
    if not explanation.source_url.strip():
        raise ValueError("La fonte della spiegazione è obbligatoria.")
    if not any(is_official_url(explanation.source_url, key) for key in OFFICIAL_DOMAIN_ALLOWLIST):
        raise ValueError("La fonte della spiegazione deve essere una URL istituzionale ufficiale registrata.")
    if not explanation.source_access_date.strip():
        raise ValueError("La data di accesso alla fonte è obbligatoria.")
    try:
        date.fromisoformat(explanation.source_access_date.strip())
    except ValueError as exc:
        raise ValueError("La data di accesso alla fonte deve essere in formato ISO.") from exc
    try:
        datetime.fromisoformat(explanation.created_at)
        datetime.fromisoformat(explanation.updated_at)
    except ValueError as exc:
        raise ValueError("I timestamp della spiegazione devono essere in formato ISO.") from exc
    if serialize_string_list(explanation.facts_from_source) == "[]":
        raise ValueError("La spiegazione deve contenere almeno un fatto dalla fonte.")
    if explanation.verification_status == EXPLANATION_STATUS_VERIFIED:
        if not explanation.verified_by or not explanation.verified_at:
            raise ValueError(
                "Una spiegazione verificata richiede revisore e data di verifica."
            )
        normalize_reviewer_name(explanation.verified_by)
    normalize_review_notes(explanation.review_notes)


def validate_explanation_for_verification(
    connection: sqlite3.Connection, explanation: DocumentExplanation,
) -> None:
    """Minimo strutturale della verifica; non sostituisce il confronto umano con la fonte.

    Le bozze possono restare incomplete. Uso previsto e altri campi editoriali
    facoltativi non diventano obbligatori nella transizione a verificato.
    """
    _validate_explanation(explanation)
    if not _clean_optional(explanation.simple_explanation):
        raise ValueError("La spiegazione semplice deve essere compilata prima della verifica.")
    document = connection.execute("SELECT stato_verifica FROM documents WHERE id = ?", (explanation.document_id,)).fetchone()
    if document is None:
        raise ValueError("Il documento collegato alla spiegazione non è disponibile.")
    if document["stato_verifica"] == "rifiutato":
        raise ValueError("Non è possibile verificare una spiegazione associata a un documento rifiutato.")


def _row_to_explanation(row: sqlite3.Row) -> DocumentExplanation:
    return DocumentExplanation(
        id=row["id"],
        document_id=row["document_id"],
        official_summary=row["official_summary"],
        simple_explanation=row["simple_explanation"],
        intended_use=row["intended_use"],
        possible_users=deserialize_string_list(row["possible_users"]),
        facts_from_source=deserialize_string_list(row["facts_from_source"]),
        missing_information=deserialize_string_list(row["missing_information"]),
        warnings=deserialize_string_list(row["warnings"]),
        source_url=row["source_url"],
        source_access_date=row["source_access_date"],
        verification_status=row["verification_status"],
        verified_by=row["verified_by"],
        verified_at=row["verified_at"],
        review_notes=row["review_notes"],
        version=row["version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@_atomic_review_write
def create_explanation(
    connection: sqlite3.Connection,
    explanation: DocumentExplanation,
    *,
    created_by: str = "Importazione locale",
    commit: bool = True,
    audit_decision: str = "creazione",
    previous: DocumentExplanation | None = None,
) -> tuple[int, bool]:
    _validate_explanation(explanation)
    if explanation.verification_status not in PRELIMINARY_EXPLANATION_STATUSES:
        raise ValueError(
            "Una nuova spiegazione deve iniziare come bozza o da verificare."
        )
    if explanation.verified_by is not None or explanation.verified_at is not None:
        raise ValueError("Una nuova spiegazione non può contenere una verifica precompilata.")
    author = normalize_reviewer_name(created_by)
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO document_explanations (
            document_id, official_summary, simple_explanation, intended_use,
            possible_users, facts_from_source, missing_information, warnings,
            source_url, source_access_date, verification_status, verified_by,
            verified_at, review_notes, version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            explanation.document_id,
            _clean_optional(explanation.official_summary),
            _clean_optional(explanation.simple_explanation),
            _clean_optional(explanation.intended_use),
            serialize_string_list(explanation.possible_users),
            serialize_string_list(explanation.facts_from_source),
            serialize_string_list(explanation.missing_information),
            serialize_string_list(explanation.warnings),
            explanation.source_url.strip(),
            explanation.source_access_date.strip(),
            explanation.verification_status,
            _clean_optional(explanation.verified_by),
            explanation.verified_at,
            normalize_review_notes(explanation.review_notes),
            explanation.version.strip(),
            explanation.created_at,
            explanation.updated_at,
        ),
    )
    created = cursor.rowcount > 0
    if created:
        explanation_id = int(cursor.lastrowid)
        current = get_explanation(connection, explanation_id)
        record_review_event(
            connection, entity_type="explanation", entity_id=explanation_id,
            object_version=current.version, decision=audit_decision, reviewer=author,
            reviewed_at=current.created_at, before=asdict(previous) if previous else None,
            after=asdict(current), notes=current.review_notes,
        )
    else:
        row = connection.execute(
            """
            SELECT id FROM document_explanations
            WHERE document_id = ? AND version = ?
            """,
            (explanation.document_id, explanation.version.strip()),
        ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError("Impossibile recuperare la spiegazione esistente.")
        explanation_id = int(row["id"])
    return explanation_id, created


def get_explanation(
    connection: sqlite3.Connection,
    explanation_id: int,
) -> DocumentExplanation | None:
    row = connection.execute(
        "SELECT * FROM document_explanations WHERE id = ?",
        (explanation_id,),
    ).fetchone()
    return _row_to_explanation(row) if row else None


def get_explanation_for_document(
    connection: sqlite3.Connection,
    document_id: int,
) -> DocumentExplanation | None:
    row = connection.execute(
        """
        SELECT * FROM document_explanations
        WHERE document_id = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (document_id,),
    ).fetchone()
    return _row_to_explanation(row) if row else None


def list_explanations(
    connection: sqlite3.Connection,
    *,
    verification_status: str | None = None,
) -> list[DocumentExplanation]:
    if verification_status is None:
        rows = connection.execute(
            "SELECT * FROM document_explanations ORDER BY document_id, id"
        ).fetchall()
    else:
        verification_status = validate_explanation_status(verification_status)
        rows = connection.execute(
            """
            SELECT * FROM document_explanations
            WHERE verification_status = ?
            ORDER BY document_id, id
            """,
            (verification_status,),
        ).fetchall()
    return [_row_to_explanation(row) for row in rows]


def filter_explanations_by_status(
    connection: sqlite3.Connection,
    verification_status: str,
) -> list[DocumentExplanation]:
    return list_explanations(
        connection,
        verification_status=verification_status,
    )


@_atomic_review_write
def update_explanation(
    connection: sqlite3.Connection,
    explanation: DocumentExplanation,
    *,
    reviewed_by: str = "Operatore locale non identificato",
) -> bool:
    if explanation.id is None:
        raise ValueError("La spiegazione deve avere un ID per essere aggiornata.")
    existing = get_explanation(connection, explanation.id)
    if existing is None:
        return False
    protected_fields = (
        "document_id",
        "source_url",
        "source_access_date",
        "version",
        "created_at",
        "verification_status",
        "verified_by",
        "verified_at",
    )
    if any(
        getattr(existing, field_name) != getattr(explanation, field_name)
        for field_name in protected_fields
    ):
        raise ValueError(
            "I campi protetti documento, fonte, versione e stato non possono "
            "essere modificati dall'editor."
        )
    _validate_explanation(explanation)
    was_verified = connection.execute(
        "SELECT 1 FROM review_events WHERE entity_type = 'explanation' AND entity_id = ? "
        "AND (previous_status = 'verificato' OR new_status = 'verificato') LIMIT 1",
        (explanation.id,),
    ).fetchone()
    if existing.verification_status == EXPLANATION_STATUS_VERIFIED or was_verified:
        raise ValueError(
            "Una spiegazione verificata richiede una nuova versione per essere modificata."
        )
    reviewer = normalize_reviewer_name(reviewed_by)
    cursor = connection.execute(
        """
        UPDATE document_explanations SET
            official_summary = ?, simple_explanation = ?, intended_use = ?,
            possible_users = ?, facts_from_source = ?, missing_information = ?,
            warnings = ?, review_notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            _clean_optional(explanation.official_summary),
            _clean_optional(explanation.simple_explanation),
            _clean_optional(explanation.intended_use),
            serialize_string_list(explanation.possible_users),
            serialize_string_list(explanation.facts_from_source),
            serialize_string_list(explanation.missing_information),
            serialize_string_list(explanation.warnings),
            normalize_review_notes(explanation.review_notes),
            explanation.updated_at,
            explanation.id,
        ),
    )
    if cursor.rowcount:
        current = get_explanation(connection, explanation.id)
        record_review_event(
            connection, entity_type="explanation", entity_id=explanation.id,
            object_version=explanation.version, decision="modifica_editoriale", reviewer=reviewer,
            reviewed_at=explanation.updated_at, before=asdict(existing), after=asdict(current),
            notes=explanation.review_notes,
        )
    return cursor.rowcount > 0


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _validate_timestamp(value: str) -> str:
    try:
        datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("La data di revisione deve essere in formato ISO.") from exc
    return value


@_atomic_review_write
def verify_explanation(
    connection: sqlite3.Connection,
    explanation_id: int,
    verified_by: str,
    *,
    source_confirmed: bool,
    review_notes: str | None = None,
    verified_at: str | None = None,
) -> bool:
    if not source_confirmed:
        raise ValueError(
            "Confermare il confronto con la fonte INPS o altra fonte istituzionale ufficiale prima della verifica."
        )
    reviewer = normalize_reviewer_name(verified_by)
    notes = normalize_review_notes(review_notes)
    timestamp = _validate_timestamp(verified_at or _utc_now())
    existing = get_explanation(connection, explanation_id)
    if existing is None:
        return False
    validate_explanation_for_verification(connection, existing)
    cursor = connection.execute(
        """
        UPDATE document_explanations SET
            verification_status = ?,
            verified_by = ?, verified_at = ?, review_notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            EXPLANATION_STATUS_VERIFIED,
            reviewer,
            timestamp,
            notes,
            timestamp,
            explanation_id,
        ),
    )
    current = get_explanation(connection, explanation_id)
    record_review_event(
        connection, entity_type="explanation", entity_id=explanation_id,
        object_version=current.version, decision="verifica", reviewer=reviewer,
        reviewed_at=timestamp, before=asdict(existing), after=asdict(current), notes=notes,
    )
    return cursor.rowcount > 0


@_atomic_review_write
def reject_explanation(
    connection: sqlite3.Connection,
    explanation_id: int,
    *,
    reviewed_by: str,
    review_notes: str | None = None,
    reviewed_at: str | None = None,
) -> bool:
    reviewer = normalize_reviewer_name(reviewed_by)
    notes = normalize_review_notes(review_notes)
    timestamp = _validate_timestamp(reviewed_at or _utc_now())
    existing = get_explanation(connection, explanation_id)
    if existing is None:
        return False
    if existing.verification_status == EXPLANATION_STATUS_VERIFIED and not notes:
        raise ValueError("La motivazione è obbligatoria per rifiutare una spiegazione verificata.")
    cursor = connection.execute(
        """
        UPDATE document_explanations SET
            verification_status = ?,
            verified_by = ?, verified_at = NULL, review_notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (EXPLANATION_STATUS_REJECTED, reviewer, notes, timestamp, explanation_id),
    )
    current = get_explanation(connection, explanation_id)
    record_review_event(
        connection, entity_type="explanation", entity_id=explanation_id,
        object_version=current.version, decision="rifiuto", reviewer=reviewer,
        reviewed_at=timestamp, before=asdict(existing), after=asdict(current), notes=notes,
    )
    return cursor.rowcount > 0


def create_explanation_revision(
    connection: sqlite3.Connection, explanation_id: int, new_version: str,
    reviewed_by: str, *, review_notes: str | None = None, created_at: str | None = None,
) -> int:
    """Duplica il testo in una nuova bozza, lasciando intatta la versione precedente."""
    current = get_explanation(connection, explanation_id)
    if current is None:
        raise ValueError("Spiegazione non trovata.")
    reviewer = normalize_reviewer_name(reviewed_by)
    version = new_version.strip()
    if not version or version == current.version:
        raise ValueError("Inserire una nuova versione distinta da quella esistente.")
    if connection.execute("SELECT 1 FROM document_explanations WHERE document_id = ? AND version = ?", (current.document_id, version)).fetchone():
        raise ValueError("La versione indicata esiste già per questo documento.")
    timestamp = _validate_timestamp(created_at or _utc_now())
    draft = replace(current, id=None, version=version, verification_status=EXPLANATION_STATUS_DRAFT,
                    verified_by=None, verified_at=None, created_at=timestamp, updated_at=timestamp,
                    review_notes=normalize_review_notes(review_notes))
    new_id, created = create_explanation(connection, draft, created_by=reviewer, audit_decision="nuova_versione", previous=current)
    if not created:
        raise ValueError("La versione indicata esiste già per questo documento.")
    return new_id


def get_latest_verified_explanation(
    connection: sqlite3.Connection,
    document_id: int,
) -> DocumentExplanation | None:
    row = connection.execute(
        """
        SELECT * FROM document_explanations
        WHERE document_id = ? AND verification_status = ?
        ORDER BY verified_at DESC, id DESC
        LIMIT 1
        """,
        (document_id, EXPLANATION_STATUS_VERIFIED),
    ).fetchone()
    return _row_to_explanation(row) if row else None
