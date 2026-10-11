from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AdministrativeDocument:
    ente: str
    titolo_ufficiale: str
    categoria: str | None
    descrizione_ufficiale: str | None
    significato_semplice: str | None
    versione: str | None
    data_rilevazione: str
    stato_verifica: str
    parole_chiave: tuple[str, ...] = field(default_factory=tuple)
    codice: str | None = None
    fonte_url: str | None = None
    download_url: str | None = None
    detail_url: str | None = None
    data_pubblicazione: str | None = None
    source_id: int | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class OfficialSource:
    ente: str
    nome_fonte: str
    tipo_ente: str
    livello: str
    ambito: str
    metodo_acquisizione: str
    stato_verifica: str
    coverage_status: str = "da_valutare"
    attiva: bool = True
    url_principale: str | None = None
    url_modulistica: str | None = None
    data_verifica: str | None = None
    note: str | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Entity:
    codice_ipa: str
    denominazione: str
    categoria: str | None
    livello: str | None
    sito_istituzionale: str | None
    stato_catalogazione: str = "non_analizzato"
    last_checked_at: str | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class DocumentFamily:
    source_id: int | None
    ente: str
    nome: str
    categoria: str | None
    descrizione_ufficiale: str | None
    keywords: tuple[str, ...]
    identifying_phrases: tuple[str, ...]
    official_url: str | None
    stato_verifica: str
    data_verifica: str | None
    created_at: str | None = None
    updated_at: str | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class DocumentProvenance:
    document_id: int
    source_id: int
    listing_url: str | None
    detail_url: str | None
    download_url: str | None
    acquired_at: str
    last_seen_at: str
    content_hash: str | None
    acquisition_method: str
    source_status: str
    id: int | None = None


@dataclass(frozen=True, slots=True)
class DocumentExplanation:
    document_id: int
    official_summary: str | None
    simple_explanation: str | None
    intended_use: str | None
    possible_users: tuple[str, ...]
    facts_from_source: tuple[str, ...]
    missing_information: tuple[str, ...]
    warnings: tuple[str, ...]
    source_url: str
    source_access_date: str
    verification_status: str
    version: str
    created_at: str
    updated_at: str
    review_notes: str | None = None
    verified_by: str | None = None
    verified_at: str | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    recognized: bool
    confidence: float
    document: AdministrativeDocument | None = None
    matched_signals: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    score_margin: float | None = None
    candidate_ids: tuple[int, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class FamilyRecognitionResult:
    recognized: bool
    confidence: float
    family: DocumentFamily | None = None
    matched_signals: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    score_margin: float | None = None


@dataclass(frozen=True, slots=True)
class CatalogRecognitionResult:
    match_type: str
    confidence_document: float
    confidence_family: float
    document: AdministrativeDocument | None = None
    family: DocumentFamily | None = None
    document_signals: tuple[str, ...] = field(default_factory=tuple)
    family_signals: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    document_score_margin: float | None = None
    family_score_margin: float | None = None
    rules_version: str = ""
    catalog_revision: str = ""
    candidate_ids: tuple[int, ...] = field(default_factory=tuple)
    pipeline_stages: tuple[tuple[str, str], ...] = field(default_factory=tuple)
