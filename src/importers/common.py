from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping

from src import offline_transport as requests

from src.models import AdministrativeDocument
from src.recognize import normalize_text


DEFAULT_BATCH_SIZE = 50
MAX_BATCH_SIZE = 500
REQUEST_TIMEOUT = (5, 20)
MAX_HTTP_ATTEMPTS = 2
USER_AGENT = "BurOCRazia/0.5.3 (sequential official-source metadata importer)"


def validate_batch_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Il limite deve essere un numero intero.")
    if not 1 <= limit <= MAX_BATCH_SIZE:
        raise ValueError(
            f"Il limite deve essere compreso tra 1 e {MAX_BATCH_SIZE}."
        )
    return limit


def validate_record_limit(limit: int, *, maximum: int, source_name: str) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Il limite deve essere un numero intero.")
    if not 1 <= limit <= maximum:
        raise ValueError(
            f"Il limite {source_name} deve essere compreso tra 1 e {maximum}."
        )
    return limit


def validate_offset(offset: int) -> int:
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise ValueError("L'offset deve essere un numero intero.")
    if offset < 0:
        raise ValueError("L'offset non pu\u00f2 essere negativo.")
    return offset


def fetch_official_html(
    url: str,
    *,
    source_name: str,
    url_validator: Callable[[str | None], bool],
    error_type: type[RuntimeError],
    request_get: Callable[..., Any] = requests.get,
) -> str:
    """Scarica una sola pagina HTML ufficiale con retry minimo e blocchi rispettati."""
    if not url_validator(url):
        raise error_type(f"La URL registrata non appartiene a {source_name}.")
    last_error: Exception | None = None
    for _attempt in range(MAX_HTTP_ATTEMPTS):
        try:
            response = request_get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                timeout=REQUEST_TIMEOUT,
            )
            if getattr(response, "status_code", None) in {403, 429}:
                raise error_type(
                    f"La fonte {source_name} ha rifiutato o limitato la richiesta; "
                    "l'importatore non tenta di aggirare il blocco."
                )
            response.raise_for_status()
            return str(response.text)
        except error_type:
            raise
        except requests.RequestException as exc:
            last_error = exc
    raise error_type(
        f"La fonte {source_name} non è raggiungibile tramite HTTP semplice."
    ) from last_error


def clean_text(value: object) -> str | None:
    if value is None or isinstance(value, (dict, list, tuple)):
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned or None


def find_existing_document(
    *,
    code: str | None,
    official_urls: tuple[str | None, ...],
    title: str,
    documents: list[AdministrativeDocument],
) -> AdministrativeDocument | None:
    if code:
        normalized_code = code.casefold().strip()
        for document in documents:
            if document.codice and document.codice.casefold().strip() == normalized_code:
                return document

    candidate_urls = {url for url in official_urls if url}
    if candidate_urls:
        for document in documents:
            document_urls = {
                document.fonte_url,
                document.detail_url,
                document.download_url,
            }
            if candidate_urls.intersection(document_urls):
                return document

    normalized_title = normalize_text(title)
    return next(
        (
            document
            for document in documents
            if normalize_text(document.titolo_ufficiale) == normalized_title
        ),
        None,
    )


def metadata_hash(values: Mapping[str, object]) -> str:
    serialized = json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(serialized.encode("utf-8")).hexdigest()
