from __future__ import annotations

import sqlite3
from pathlib import Path

import streamlit as st

from src.catalog_metrics import catalog_summary, get_catalog_metrics
from src.bootstrap import prepare_database
from src.benchmark_display import load_summary, metric_label
from src.database import DEFAULT_DB_PATH, connect_database, list_documents
from src.explanations import (
    EXPLANATION_STATUS_REJECTED, EXPLANATION_STATUS_VERIFIED, MAX_REVIEWER_NAME_LENGTH,
    MAX_REVIEW_NOTES_LENGTH, PRELIMINARY_EXPLANATION_STATUSES, can_verify_explanation,
    list_explanations, list_review_events, reviewer_name_is_valid,
)
from src.extract import MAX_UPLOAD_BYTES, ExtractionError, ExtractionResult, extract_document
from src.families import list_document_families
from src.local_packages import catalog_state
from src.local_resources import list_local_resources, read_resource_text, resolve_resource_root, resource_status
from src.models import AdministrativeDocument, DocumentExplanation, DocumentFamily, OfficialSource, RecognitionResult
from src.offline import install_network_guard
from src.recognize import MIN_CONFIDENCE, recognize_catalog
from src.review import (
    editorial_lines_to_items, save_editorial_changes, submit_document_review,
    submit_explanation_draft, submit_explanation_review, submit_explanation_revision, submit_resource_review,
)
from src.sources import list_sources

NAVIGATION_AREAS = ("BurOCRazia", "Catalogo", "Fonti", "Revisione", "Benchmark")
NAVIGATION_LABELS = {"BurOCRazia": "Riconosci", "Catalogo": "Catalogo", "Fonti": "Fonti e provenienza", "Revisione": "Revisione editoriale", "Benchmark": "Benchmark"}
PRELIMINARY_EXPLANATION_MESSAGE = "Spiegazione preliminare non ancora revisionata"
VERIFIED_EXPLANATION_MESSAGE = "Spiegazione revisionata"
NO_EXPLANATION_MESSAGE = "Documento riconosciuto, ma BurOCRazia non dispone ancora di una spiegazione."
REJECTED_EXPLANATION_MESSAGE = "Documento riconosciuto, ma la spiegazione disponibile non ha superato la revisione."
UNKNOWN_DOCUMENT_MESSAGE = "BurOCRazia non è riuscita a identificare questo documento con sufficiente sicurezza."
LOCAL_PROCESSING_MESSAGE = "Elaborazione locale: il file non viene inviato a servizi esterni."
MISSING_RESOURCE_MESSAGE = "Riferimento registrato; materiale non disponibile localmente."
OCR_PREVIEW_MAX_CHARACTERS = 4_000


def load_application_data() -> tuple[list[AdministrativeDocument], list[OfficialSource], list[DocumentExplanation], list[DocumentFamily]]:
    prepare_database(DEFAULT_DB_PATH)
    with connect_database(DEFAULT_DB_PATH) as connection:
        return list_documents(connection), list_sources(connection), list_explanations(connection), list_document_families(connection)


def select_explanation_for_display(explanations: list[DocumentExplanation]) -> DocumentExplanation | None:
    verified = [item for item in explanations if item.verification_status == EXPLANATION_STATUS_VERIFIED]
    if verified:
        return max(verified, key=lambda item: (item.verified_at or "", item.id or 0))
    preliminary = [item for item in explanations if item.verification_status in PRELIMINARY_EXPLANATION_STATUSES]
    return max(preliminary, key=lambda item: (item.updated_at, item.id or 0)) if preliminary else None


def explanation_display_state(explanation: DocumentExplanation | None) -> str:
    if explanation is None or explanation.verification_status == EXPLANATION_STATUS_REJECTED:
        return "non_disponibile"
    return "verificata" if explanation.verification_status == EXPLANATION_STATUS_VERIFIED else "preliminare"


def explanation_collection_state(explanations: list[DocumentExplanation]) -> str:
    selected = select_explanation_for_display(explanations)
    if selected is not None:
        return explanation_display_state(selected)
    return "rifiutata" if any(item.verification_status == EXPLANATION_STATUS_REJECTED for item in explanations) else "non_disponibile"


def format_date_it(value: str | None, *, fallback: str = "Non disponibile") -> str:
    """Formatta date ISO/SQLite come GG/MM/AAAA senza alterare i dati salvati."""
    if not value or not str(value).strip():
        return fallback
    text = str(value).strip()
    date_part = text[:10]
    if len(date_part) == 10 and date_part[4] == "-" and date_part[7] == "-":
        year, month, day = date_part.split("-")
        if year.isdigit() and month.isdigit() and day.isdigit():
            return f"{day}/{month}/{year}"
    return text


def format_catalog_version(value: str | None) -> tuple[str, str]:
    """Restituisce etichetta e valore leggibile della versione del catalogo."""
    if not value:
        return "Versione catalogo", "Non registrata"
    cleaned = value.removesuffix("-imported")
    parts = cleaned.split(".")
    if len(parts) == 3 and all(part.isdigit() for part in parts) and len(parts[0]) == 4:
        year, month, day = parts
        return "Catalogo aggiornato al", f"{day.zfill(2)}/{month.zfill(2)}/{year}"
    return "Versione catalogo", cleaned


def verified_revision_lines(explanation: DocumentExplanation) -> tuple[str, ...]:
    if explanation.verification_status != EXPLANATION_STATUS_VERIFIED:
        return ()
    return (f"Contenuto revisionato da: {explanation.verified_by}", f"Data della revisione: {format_date_it(explanation.verified_at)}")


def explanation_status_label(status: str | None) -> str:
    if status == EXPLANATION_STATUS_VERIFIED:
        return VERIFIED_EXPLANATION_MESSAGE
    return PRELIMINARY_EXPLANATION_MESSAGE if status in PRELIMINARY_EXPLANATION_STATUSES else "Spiegazione non disponibile"


def confidence_label(confidence: float) -> str:
    return f"Punteggio interno: {confidence:g}/100 (non è una probabilità di correttezza)"


def detected_text_preview(text: str) -> str:
    return text if len(text) <= OCR_PREVIEW_MAX_CHARACTERS else f"{text[:OCR_PREVIEW_MAX_CHARACTERS].rstrip()}\n\n[Anteprima abbreviata]"


def show_ocr_feedback(extraction: ExtractionResult) -> None:
    if extraction.used_ocr:
        st.info("Lettura tramite OCR locale: controllare eventuali errori nel testo rilevato.")
    if extraction.total_pages is not None:
        st.text(f"Pagine lette: {extraction.pages_processed or 0}/{extraction.total_pages}; pagine lette tramite OCR: {extraction.ocr_pages}.")
    if extraction.warning:
        st.warning("Lettura parziale o con limitazioni.")
        st.text(extraction.warning)


def show_detected_text(extraction: ExtractionResult) -> None:
    st.caption("Anteprima del testo estratto, presente soltanto nella sessione corrente.")
    st.text(detected_text_preview(extraction.text))


def display_category(category: str | None) -> str:
    if not category or not category.strip():
        return "Non disponibile"
    cleaned = category.strip()
    if cleaned.casefold().startswith("aree:"):
        cleaned = cleaned.split(":", maxsplit=1)[1]
    cleaned = " ".join(cleaned.replace("-", " ").replace("_", " ").split())
    return cleaned.capitalize() if cleaned else "Non disponibile"


def display_title(title: str, *, max_length: int = 140) -> str:
    title = title.split(" / ", maxsplit=1)[0].strip()
    if len(title) <= max_length:
        return title
    candidate = title[:max_length + 1]
    shortened = candidate.rsplit(" ", maxsplit=1)[0] if " " in candidate else title[:max_length]
    return f"{shortened.rstrip(' ,;:-')}…"


def document_status_label(status: str) -> str:
    return {"demo": "Dimostrativo", "da_verificare": "Da verificare", "verificato": "Verificato", "rifiutato": "Rifiutato"}.get(status, status.replace("_", " ").capitalize())


def recognition_result_state(result: RecognitionResult, explanations: list[DocumentExplanation]) -> str:
    if not result.recognized or result.document is None or result.document.stato_verifica == "rifiutato":
        return "non_riconosciuto"
    state = explanation_collection_state([item for item in explanations if item.document_id == result.document.id])
    return {"verificata": "riconosciuto_verificato", "preliminare": "riconosciuto_preliminare", "rifiutata": "riconosciuto_rifiutato", "non_disponibile": "riconosciuto_senza_spiegazione"}[state]


def source_to_display_row(source: OfficialSource) -> dict[str, str]:
    return {
        "Ente": source.ente, "Ambito": source.ambito, "Livello": source.livello,
        "URL principale": source.url_principale or "Non disponibile", "URL modulistica": source.url_modulistica or "Non disponibile",
        "Metodo acquisizione": source.metodo_acquisizione, "Stato verifica": source.stato_verifica,
        "Copertura": source.coverage_status, "Data verifica": format_date_it(source.data_verifica),
    }


def document_to_display_row(document: AdministrativeDocument) -> dict[str, str]:
    return {
        "Tipo record": "Demo" if document.stato_verifica == "demo" else "Reale importato", "Ente": document.ente,
        "Codice": document.codice or "Non disponibile", "Titolo": display_title(document.titolo_ufficiale),
        "Categoria": display_category(document.categoria), "Stato": document_status_label(document.stato_verifica),
        "Fonte": document.detail_url or document.fonte_url or "Non disponibile",
        "Versione": document.versione or "Non disponibile", "Data pubblicazione": format_date_it(document.data_pubblicazione),
        "Data rilevazione": format_date_it(document.data_rilevazione),
    }


def show_plain_table(rows: list[dict[str, str]]) -> None:
    """Text columns deliberately exclude Markdown, URL and embedded-content renderers."""
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch", column_config={name: st.column_config.TextColumn(name) for name in rows[0]})


def show_problem(message: str, error: Exception) -> None:
    st.error(message)
    st.text(str(error))


def show_catalog_state(catalog: list[AdministrativeDocument], sources: list[OfficialSource]) -> None:
    with connect_database(DEFAULT_DB_PATH) as connection:
        state = catalog_state(connection)
        metrics = get_catalog_metrics(connection)
        resources = list_local_resources(connection)
    version_label, version_value = format_catalog_version(state["catalog_version"])
    covered_entities = len(metrics.documents_by_entity)
    with st.sidebar.expander("Catalogo locale", expanded=False):
        st.markdown(f"**{version_label}:** {version_value}")
        st.markdown(f"**Documenti nel catalogo:** {metrics.documents_real}")
        st.markdown(f"**Famiglie riconoscibili:** {metrics.families}")
        st.markdown(f"**Enti coperti:** {covered_entities}")
        st.markdown(f"**Enti censiti:** {metrics.entities}")
        st.markdown(f"**Fonti verificate:** {metrics.verified_sources}")
        if resources:
            st.markdown(f"**Materiali ufficiali locali:** {len(resources)}")
        st.caption("BurOCRazia utilizza esclusivamente i dati installati sul computer e non controlla aggiornamenti online.")


def show_local_materials(document_id: int | None, *, key_prefix: str = "document") -> None:
    st.subheader("Materiale ufficiale locale")
    if document_id is None:
        st.info(MISSING_RESOURCE_MESSAGE)
        return
    with connect_database(DEFAULT_DB_PATH) as connection:
        resources = list_local_resources(connection, document_id=document_id)
        status = resource_status(connection, document_id)
        resource_root = resolve_resource_root(connection)
    if not resources:
        st.info(MISSING_RESOURCE_MESSAGE)
        return
    st.text(status)
    resources_by_id = {item.id: item for item in resources}
    selected_id = st.selectbox("Materiale da consultare", list(resources_by_id), format_func=lambda identifier: resources_by_id[identifier].title, key=f"{key_prefix}_resource_{document_id}")
    resource = resources_by_id[selected_id]
    st.text(f"Titolo: {resource.title}\nVersione: {resource.version or 'non disponibile'}\nAcquisito il: {format_date_it(resource.acquired_at)}\nStato: {resource.verification_status}")
    st.text(f"Provenienza: {resource.provenance}\nCondizioni di riuso: {resource.reuse_conditions or 'non registrate'}")
    if resource.verification_status == "demo":
        st.warning("Materiale sintetico dimostrativo: non è un documento ufficiale.")
    elif resource.verification_status == "rifiutato":
        st.warning("Materiale ritirato dalla consultazione dopo revisione. Lo storico resta disponibile nell'area Revisione.")
        return
    elif resource.verification_status != "verificato":
        st.warning("Materiale locale da verificare: l'impronta del file non ne certifica l'autenticità.")
    st.caption("Consultazione testuale. Eventuali indirizzi e contenuti incorporati non vengono attivati.")
    with st.expander("Leggi il testo del materiale"):
        try:
            st.text(read_resource_text(resource, resource_root))
        except (ValueError, OSError) as exc:
            show_problem("Il materiale non è consultabile in sicurezza.", exc)


def show_recognized_document(document: AdministrativeDocument, confidence: float | None, explanations: list[DocumentExplanation] | None = None, extraction: ExtractionResult | None = None) -> None:
    rejected = document.stato_verifica == "rifiutato"
    st.header("Documento riconosciuto" if confidence is not None and not rejected else "Scheda del catalogo")
    st.text(document.titolo_ufficiale)
    st.text(f"Ente: {document.ente}\nCodice: {document.codice or 'non presente'}\nVersione documento: {document.versione or 'non disponibile'}")
    st.text(f"Stato del record: {document_status_label(document.stato_verifica)}\nPubblicazione: {format_date_it(document.data_pubblicazione, fallback='non disponibile')}\nRilevazione: {format_date_it(document.data_rilevazione, fallback='non disponibile')}")
    if document.stato_verifica == "demo":
        st.warning("Record dimostrativo sintetico: non rappresenta un documento amministrativo reale.")
    elif rejected:
        st.warning("Documento rifiutato: escluso dal riconoscimento. Il record e lo storico restano consultabili per la revisione.")
    elif document.stato_verifica != "verificato":
        st.warning("I metadati del documento non hanno ancora completato la verifica editoriale.")
    if extraction is not None:
        show_ocr_feedback(extraction)

    available = explanations or []
    selected = None if rejected else select_explanation_for_display(available)
    state = explanation_collection_state(available)
    st.subheader("Spiegazione BurOCRazia")
    if rejected:
        st.info("La spiegazione collegata non è proposta per l'uso operativo, anche se verificata in precedenza. Testo e decisioni restano nell'area Revisione.")
    elif state == "rifiutata":
        st.info(REJECTED_EXPLANATION_MESSAGE)
    elif selected is None:
        st.info(NO_EXPLANATION_MESSAGE)
    elif state == "preliminare":
        st.warning(PRELIMINARY_EXPLANATION_MESSAGE)
        st.info("Il testo preliminare è consultabile nell'area Revisione. Non è ancora disponibile una spiegazione validata.")
    else:
        st.success(VERIFIED_EXPLANATION_MESSAGE)
        for title, value in (("Che cos'è", selected.simple_explanation), ("A cosa serve", selected.intended_use)):
            st.subheader(title)
            st.text(value or "Non indicato nella scheda.")
        st.subheader("Possibili utilizzatori")
        st.text("\n".join(selected.possible_users) or "Non indicato nella scheda.")
        for title, items in (("Fatti ricavati dalla fonte", selected.facts_from_source), ("Informazioni mancanti", selected.missing_information), ("Avvertenze", selected.warnings)):
            if items:
                st.subheader(title)
                st.text("\n".join(items))
        for line in verified_revision_lines(selected):
            st.text(line)
        st.text(f"Versione della spiegazione: {selected.version}\nAccesso alla fonte della scheda: {format_date_it(selected.source_access_date, fallback='non disponibile')}")

    st.subheader("Provenienza registrata")
    st.caption("Gli indirizzi sono conservati esclusivamente come testo.")
    st.text(document.detail_url or document.fonte_url or "Riferimento non disponibile.")
    if selected is not None and selected.source_url not in (document.detail_url, document.fonte_url):
        st.text(selected.source_url)
    show_local_materials(document.id, key_prefix="recognized" if confidence is not None else "catalog")
    with st.expander("Dettagli del riconoscimento e del record" if confidence is not None else "Altri metadati"):
        st.text(f"Categoria: {display_category(document.categoria)}")
        if confidence is not None:
            st.text(confidence_label(confidence))
        if document.descrizione_ufficiale:
            st.caption("Descrizione registrata nella fonte; mantiene lo stato di verifica del record.")
            st.text(document.descrizione_ufficiale)
        if selected is not None:
            st.text(f"Stato spiegazione: {selected.verification_status}\nVersione scheda: {selected.version}\nData di accesso alla fonte: {format_date_it(selected.source_access_date, fallback='non disponibile')}")
        if extraction is not None:
            show_detected_text(extraction)


def reset_document_session() -> None:
    generation = int(st.session_state.get("upload_generation", 0)) + 1
    for key in list(st.session_state):
        del st.session_state[key]
    st.session_state["upload_generation"] = generation
    st.session_state["reset_completed"] = True


def show_document_recognition(catalog: list[AdministrativeDocument], explanations: list[DocumentExplanation], families: list[DocumentFamily] | None = None) -> None:
    generation = st.session_state.get("upload_generation", 0)
    uploaded_file = st.file_uploader("Carica un documento", type=("pdf", "docx", "txt", "jpg", "jpeg", "png"), key=f"document_upload_{generation}", help=f"PDF, DOCX, TXT, JPG, JPEG e PNG. Massimo {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB.")
    if uploaded_file is None:
        return
    try:
        if uploaded_file.size > MAX_UPLOAD_BYTES:
            raise ExtractionError(f"Il file supera il limite di {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB.")
        with st.spinner("Lettura locale del documento..."):
            extraction = extract_document(uploaded_file.getvalue(), uploaded_file.name, mime_type=getattr(uploaded_file, "type", None))
    except ExtractionError as exc:
        st.warning("Impossibile acquisire il testo. Controlla il file o riprova con una copia leggibile.")
        st.text(str(exc))
        return
    import hashlib
    recognition = recognize_catalog(extraction.text, catalog, families or [], min_document_confidence=MIN_CONFIDENCE,
        file_sha256=hashlib.sha256(uploaded_file.getvalue()).hexdigest())
    if recognition.match_type == "NO_MATCH":
        st.header("Documento non riconosciuto")
        st.text(UNKNOWN_DOCUMENT_MESSAGE)
        st.info("Il testo è leggibile, ma gli indizi non bastano a identificare un documento o una famiglia. Non viene proposta una spiegazione specifica.")
        show_ocr_feedback(extraction)
        with st.expander("Dettagli del riconoscimento"):
            st.text("Esito: NO_MATCH")
            show_detected_text(extraction)
    elif recognition.match_type == "FAMILY_MATCH":
        assert recognition.family is not None
        show_family_recognition(recognition.family, recognition.confidence_family, extraction)
    else:
        assert recognition.document is not None
        linked = [item for item in explanations if item.document_id == recognition.document.id]
        show_recognized_document(recognition.document, recognition.confidence_document, linked, extraction)
    with st.expander("Segnali della decisione"):
        method = ('File ufficiale identico' if 'official_file_sha256_exact' in recognition.document_signals
                  else 'Firma del contenuto' if 'content_fingerprint_match' in recognition.document_signals
                  else 'Famiglia' if recognition.match_type == 'FAMILY_MATCH' else 'Metadati')
        st.text('Metodo: '+method)
        st.text(f"Esito: {recognition.match_type}")
        st.text("\n".join((*recognition.document_signals, *recognition.family_signals)) or "Nessun segnale sufficiente.")
        for attribute in ("reason", "catalog_revision", "rules_version", "document_score_margin", "family_score_margin", "conflicts"):
            value = getattr(recognition, attribute, None)
            if value is not None:
                st.text(f"{attribute}: {value}")


def show_family_recognition(family: DocumentFamily, confidence: float, extraction: ExtractionResult | None = None) -> None:
    st.header("Tipo di documento rilevato")
    st.text(family.nome)
    st.info("È riconosciuta soltanto la famiglia. Il documento specifico, la versione e l'ente emittente del file non sono confermati.")
    if family.source_id is None:
        st.warning("Regole di riconoscimento sperimentali; fonte ufficiale non disponibile. Lo stato storico della famiglia non attesta una nuova verifica.")
    st.text(f"Ente di riferimento della famiglia nel catalogo: {family.ente}\nStato della famiglia: {document_status_label(family.stato_verifica)}\nData verifica: {format_date_it(family.data_verifica, fallback='non disponibile')}")
    if extraction is not None:
        show_ocr_feedback(extraction)
    st.subheader("Provenienza registrata")
    st.text(family.official_url or "Fonte non disponibile.")
    st.info(MISSING_RESOURCE_MESSAGE)
    with st.expander("Dettagli della famiglia"):
        st.text(f"Categoria: {display_category(family.categoria)}")
        st.text(confidence_label(confidence))
        if family.descrizione_ufficiale:
            st.caption("Descrizione generale registrata, soggetta allo stato di verifica della famiglia.")
            st.text(family.descrizione_ufficiale)
        if extraction is not None:
            show_detected_text(extraction)


def show_home(catalog: list[AdministrativeDocument], explanations: list[DocumentExplanation], families: list[DocumentFamily] | None = None) -> None:
    st.header("Riconosci un documento")
    st.write("Carica un PDF, DOCX, TXT o un'immagine. BurOCRazia analizza il contenuto in locale e prova a identificare il documento o la relativa famiglia.")
    st.caption(LOCAL_PROCESSING_MESSAGE)
    st.caption("Progetto sperimentale: verifica sempre le informazioni sul materiale ufficiale. Per le prove usa documenti sintetici o privi di dati personali.")
    show_document_recognition(catalog, explanations, families)


def show_document_catalog(catalog: list[AdministrativeDocument], families: list[DocumentFamily] | None = None, explanations: list[DocumentExplanation] | None = None) -> None:
    st.header("Catalogo")
    st.caption("Catalogo installato: i record dimostrativi sono separati dai documenti reali. La provenienza istituzionale non equivale alla verifica dei contenuti.")
    summary = catalog_summary(catalog, families or [])
    metrics = (("Documenti reali", summary.real_documents), ("Enti coperti", summary.covered_entities), ("Famiglie", summary.families), ("Da verificare", summary.pending), ("Verificati", summary.verified))
    for column, (label, value) in zip(st.columns(5), metrics, strict=True):
        column.metric(label, value)
    left, right = st.columns(2)
    with left:
        entity = st.selectbox("Ente", ["Tutti", *sorted({item.ente for item in catalog})], key="catalog_entity")
    with right:
        status = st.selectbox("Stato verifica", ["Tutti", *sorted({item.stato_verifica for item in catalog})], format_func=lambda value: value if value == "Tutti" else document_status_label(value), key="catalog_status")
    search = st.text_input("Cerca codice o titolo", key="catalog_search").casefold().strip()
    documents = [item for item in catalog if (entity == "Tutti" or item.ente == entity) and (status == "Tutti" or item.stato_verifica == status) and (not search or search in (item.codice or "").casefold() or search in item.titolo_ufficiale.casefold())]
    if not documents:
        st.info("Nessun documento corrisponde ai filtri selezionati.")
        return
    visible = ("Tipo record", "Ente", "Codice", "Titolo", "Stato", "Versione", "Data pubblicazione", "Data rilevazione")
    show_plain_table([{key: row[key] for key in visible} for row in map(document_to_display_row, documents)])
    by_id = {item.id: item for item in documents}
    selected = st.selectbox("Consulta un documento", list(by_id), format_func=lambda identifier: f"{by_id[identifier].codice or 'Senza codice'} — {display_title(by_id[identifier].titolo_ufficiale)}", key="catalog_document")
    show_recognized_document(by_id[selected], None, [item for item in explanations or [] if item.document_id == selected])
    with st.expander("Aggiorna da un pacchetto locale"):
        st.write("I pacchetti si importano tramite lo strumento locale incluso nel progetto. La guida PACCHETTI_LOCALI descrive anteprima, controllo dell'impronta e conferma.")
        st.code("python scripts/import_package.py percorso/pacchetto.zip", language="bash")
        st.caption("Il comando mostra soltanto l'anteprima; nessun sito viene contattato.")


def show_sources_registry(sources: list[OfficialSource]) -> None:
    st.header("Fonti")
    st.caption("La verifica di una fonte non certifica tutti i documenti collegati. Gli indirizzi storici sono soltanto dati di provenienza.")
    left, right = st.columns(2)
    with left:
        entity = st.selectbox("Ente", ["Tutti", *sorted({item.ente for item in sources})], key="sources_entity")
    with right:
        scope = st.selectbox("Ambito", ["Tutti", *sorted({item.ambito for item in sources})], key="sources_scope")
    status = st.selectbox("Stato verifica", ["Tutti", *sorted({item.stato_verifica for item in sources})], key="sources_status")
    filtered = [item for item in sources if (entity == "Tutti" or item.ente == entity) and (scope == "Tutti" or item.ambito == scope) and (status == "Tutti" or item.stato_verifica == status)]
    if not filtered:
        st.info("Nessuna fonte corrisponde ai filtri selezionati.")
        return
    columns = ("Ente", "Ambito", "Livello", "Stato verifica", "Copertura", "Data verifica")
    show_plain_table([{key: row[key] for key in columns} for row in map(source_to_display_row, filtered)])
    by_id = {item.id: item for item in filtered}
    identifier = st.selectbox("Dettagli della fonte", list(by_id), format_func=lambda value: f"{by_id[value].ente} — {by_id[value].nome_fonte}", key="source_detail")
    source = by_id[identifier]
    for label, value in source_to_display_row(source).items():
        st.text(f"{label}: {value}")
    if source.note:
        st.text(source.note)
    with connect_database(DEFAULT_DB_PATH) as connection:
        resources = [item for item in list_local_resources(connection) if item.source_id == source.id]
    st.text(f"Materiali locali registrati per questa fonte: {len(resources)}")
    if not resources:
        st.info(MISSING_RESOURCE_MESSAGE)
    else:
        st.caption("I materiali sono consultabili nella scheda del documento collegato nel Catalogo.")
        show_plain_table([{"Documento ID": str(item.document_id), "Titolo": item.title, "Acquisizione": format_date_it(item.acquired_at), "Stato": item.verification_status} for item in resources])


def show_explanation_editor(catalog: list[AdministrativeDocument], explanations: list[DocumentExplanation]) -> None:
    if not explanations:
        st.info("Non sono presenti spiegazioni da revisionare.")
        return
    documents = {item.id: item for item in catalog}
    by_id = {item.id: item for item in explanations if item.id is not None}
    pending_selection = st.session_state.pop("pending_review_selection", None)
    if pending_selection in by_id:
        st.session_state["explanation_review_selection"] = pending_selection

    def label(identifier: int) -> str:
        item = by_id[identifier]
        document = documents.get(item.document_id)
        return f"{document.codice or display_title(document.titolo_ufficiale, max_length=65) if document else item.document_id} — {item.verification_status} — v{item.version}"

    identifier = st.selectbox("Scheda da revisionare", list(by_id), format_func=label, key="explanation_review_selection")
    selected = by_id[identifier]
    document = documents.get(selected.document_id)
    if document is None:
        st.error("Il documento collegato non è disponibile.")
        return
    st.text(f"Documento: {document.codice or 'senza codice'} — {document.titolo_ufficiale}\nEnte: {document.ente}\nVersione documento: {document.versione or 'non disponibile'}")
    st.text(f"Versione spiegazione: {selected.version}\nStato: {selected.verification_status}\nAccesso fonte: {format_date_it(selected.source_access_date)}\nUltimo aggiornamento: {format_date_it(selected.updated_at)}")
    st.subheader("Fonte registrata")
    st.text(selected.source_url)
    st.caption("Identità del documento e provenienza non sono modificabili da questo editor.")
    show_local_materials(document.id, key_prefix="review")
    reviewer = st.text_input("Nome del revisore", max_chars=MAX_REVIEWER_NAME_LENGTH, key=f"explanation_reviewer_{identifier}")
    reviewer_valid = reviewer_name_is_valid(reviewer)
    notes = st.text_area("Note di revisione", value=selected.review_notes or "", max_chars=MAX_REVIEW_NOTES_LENGTH, key=f"review_notes_{identifier}")
    with connect_database(DEFAULT_DB_PATH) as connection:
        history = list_review_events(connection, object_type="explanation", object_id=identifier)
    was_verified = any("verificato" in (event["previous_status"], event["new_status"]) for event in history)
    editable = selected.verification_status != EXPLANATION_STATUS_VERIFIED and not was_verified
    with st.expander("Campi editoriali", expanded=True):
        if not editable:
            st.info("Questa versione è stata verificata. Per modificarne il contenuto crea una nuova versione in bozza.")
        fields = {}
        field_labels = {"official_summary": "Sintesi dalla fonte", "simple_explanation": "Spiegazione semplice", "intended_use": "Uso generale", "possible_users": "Possibili utilizzatori — uno per riga", "facts_from_source": "Fatti dalla fonte — uno per riga", "missing_information": "Informazioni mancanti — una per riga", "warnings": "Avvertenze — una per riga"}
        for name, field_label in field_labels.items():
            value = getattr(selected, name)
            fields[name] = st.text_area(field_label, value="\n".join(value) if isinstance(value, tuple) else value or "", disabled=not editable, key=f"{name}_{identifier}")
        if st.button("Salva correzioni editoriali", disabled=not editable or not reviewer_valid, key=f"save_editorial_{identifier}"):
            for name in ("possible_users", "facts_from_source", "missing_information", "warnings"):
                fields[name] = editorial_lines_to_items(fields[name])
            try:
                saved = save_editorial_changes(identifier, **fields, review_notes=notes, reviewed_by=reviewer, db_path=DEFAULT_DB_PATH)
                if not saved:
                    st.error("La scheda selezionata non è più disponibile.")
                else:
                    st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                show_problem("Impossibile salvare la revisione.", exc)
    source_confirmed = st.checkbox("Confermo di aver confrontato questa versione con il materiale ufficiale indicato.", key=f"source_confirmed_{identifier}")
    unsaved_changes = any(value != ("\n".join(getattr(selected, name)) if isinstance(getattr(selected, name), tuple) else getattr(selected, name) or "") for name, value in fields.items())
    verify_enabled = can_verify_explanation(reviewer, source_confirmed, explanation=selected, document_status=document.stato_verifica) and selected.verification_status != EXPLANATION_STATUS_VERIFIED and not unsaved_changes
    if document.stato_verifica == "rifiutato":
        st.warning("Documento rifiutato: non è possibile verificare una spiegazione collegata. Il testo e lo storico sono conservati.")
    if not (selected.simple_explanation or "").strip():
        st.warning("Per verificare la scheda, compila e salva la spiegazione semplice. La bozza può restare incompleta.")
    if unsaved_changes:
        st.warning("Sono presenti modifiche editoriali non salvate. Salvale prima di verificare la scheda.")
    reject_enabled = reviewer_valid and bool(notes.strip()) and selected.verification_status != EXPLANATION_STATUS_REJECTED
    st.caption("Salva le correzioni e conferma il confronto con la fonte prima di decidere. La verifica riguarda la versione salvata. Per un rifiuto è necessaria una motivazione.")
    left, right = st.columns(2)
    decision = None
    if left.button("Segna come verificata", disabled=not verify_enabled, key=f"verify_{identifier}"):
        decision = EXPLANATION_STATUS_VERIFIED
    if right.button("Rifiuta spiegazione", disabled=not reject_enabled, key=f"reject_{identifier}"):
        decision = EXPLANATION_STATUS_REJECTED
    if decision:
        try:
            submit_explanation_review(identifier, decision, reviewer, source_confirmed=source_confirmed, review_notes=notes, db_path=DEFAULT_DB_PATH)
            st.rerun()
        except (ValueError, sqlite3.Error) as exc:
            show_problem("Impossibile registrare la decisione.", exc)
    with st.expander("Crea una nuova versione"):
        version = st.text_input("Nuova versione della spiegazione", key=f"new_version_{identifier}", max_chars=80)
        st.caption("La versione precedente e le sue decisioni restano nello storico. La nuova scheda nasce in bozza.")
        if st.button("Crea versione in bozza", disabled=not reviewer_valid or not version.strip(), key=f"create_revision_{identifier}"):
            try:
                new_id = submit_explanation_revision(identifier, version.strip(), reviewer, review_notes=notes, db_path=DEFAULT_DB_PATH)
                st.session_state["pending_review_selection"] = new_id
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                show_problem("Impossibile creare la versione.", exc)


def show_document_review(catalog: list[AdministrativeDocument]) -> None:
    by_id = {item.id: item for item in catalog if item.id is not None and item.stato_verifica != "demo"}
    if not by_id:
        st.info("Non sono presenti documenti reali da revisionare.")
        return
    identifier = st.selectbox("Documento da revisionare", list(by_id), format_func=lambda value: f"{by_id[value].ente} — {display_title(by_id[value].titolo_ufficiale, max_length=80)}", key="document_review_selection")
    document = by_id[identifier]
    for label, value in document_to_display_row(document).items():
        st.text(f"{label}: {value}")
    show_local_materials(identifier, key_prefix="document_review")
    reviewer = st.text_input("Revisore del documento", key=f"document_reviewer_{identifier}", max_chars=MAX_REVIEWER_NAME_LENGTH)
    notes = st.text_area("Motivazione della decisione sul documento", key=f"document_notes_{identifier}", max_chars=MAX_REVIEW_NOTES_LENGTH)
    confirmed = st.checkbox("Ho confrontato identità, versione e metadati con il materiale ufficiale.", key=f"document_confirmed_{identifier}")
    decision = st.selectbox("Decisione sul documento", ("da_verificare", "verificato", "rifiutato"), format_func=document_status_label, key=f"document_decision_{identifier}")
    allowed = reviewer_name_is_valid(reviewer) and (decision != "verificato" or confirmed) and (decision != "rifiutato" or bool(notes.strip()))
    if st.button("Registra decisione sul documento", disabled=not allowed, key=f"document_submit_{identifier}"):
        try:
            submit_document_review(identifier, decision, reviewer, source_confirmed=confirmed, review_notes=notes, db_path=DEFAULT_DB_PATH)
            st.rerun()
        except (ValueError, sqlite3.Error) as exc:
            show_problem("Impossibile registrare la decisione sul documento.", exc)


def show_review_history() -> None:
    with connect_database(DEFAULT_DB_PATH) as connection:
        events = list_review_events(connection)
    st.caption("Gli eventi vengono aggiunti senza sovrascrivere le decisioni precedenti. Lo storico anteriore all'introduzione dell'audit può non essere disponibile.")
    if not events:
        st.info("Nessun evento di revisione registrato.")
        return
    event = st.selectbox("Evento da consultare", range(len(events)), format_func=lambda index: f"Evento {events[index].get('id', index + 1)} — {events[index].get('entity_type', '')} {events[index].get('entity_id', '')}", key="audit_event")
    for label, value in events[event].items():
        st.text(f"{label}: {value}")


def show_resource_review() -> None:
    with connect_database(DEFAULT_DB_PATH) as connection:
        resources = list_local_resources(connection)
        resource_root = resolve_resource_root(connection)
    by_id = {item.id: item for item in resources if item.verification_status != "demo"}
    if not by_id:
        st.info("Non sono presenti materiali ufficiali locali da revisionare. I materiali dimostrativi mantengono lo stato demo.")
        return
    identifier = st.selectbox("Materiale da revisionare", list(by_id), format_func=lambda value: by_id[value].title, key="resource_review_selection")
    resource = by_id[identifier]
    st.text(f"Titolo: {resource.title}\nDocumento ID: {resource.document_id}\nVersione: {resource.version or 'non disponibile'}\nAcquisizione: {format_date_it(resource.acquired_at)}\nStato: {resource.verification_status}")
    st.text(f"Provenienza: {resource.provenance}\nCondizioni di riuso: {resource.reuse_conditions}")
    if resource.verification_status != "rifiutato":
        with st.expander("Testo del materiale da revisionare"):
            try:
                st.text(read_resource_text(resource, resource_root))
            except (ValueError, OSError) as exc:
                show_problem("Il materiale non è consultabile in sicurezza.", exc)
    reviewer = st.text_input("Revisore del materiale", key=f"resource_reviewer_{identifier}", max_chars=MAX_REVIEWER_NAME_LENGTH)
    notes = st.text_area("Motivazione della decisione sul materiale", key=f"resource_notes_{identifier}", max_chars=MAX_REVIEW_NOTES_LENGTH)
    confirmed = st.checkbox("Ho verificato contenuto, provenienza e corrispondenza del materiale ufficiale.", key=f"resource_confirmed_{identifier}")
    decision = st.selectbox("Decisione sul materiale", ("da_verificare", "verificato", "rifiutato"), format_func=document_status_label, key=f"resource_decision_{identifier}")
    allowed = reviewer_name_is_valid(reviewer) and (decision != "verificato" or confirmed) and (decision != "rifiutato" or bool(notes.strip()))
    if st.button("Registra decisione sul materiale", disabled=not allowed, key=f"resource_submit_{identifier}"):
        try:
            submit_resource_review(identifier, decision, reviewer, source_confirmed=confirmed, review_notes=notes, db_path=DEFAULT_DB_PATH)
            st.rerun()
        except (ValueError, OSError, sqlite3.Error) as exc:
            show_problem("Impossibile registrare la decisione sul materiale.", exc)


def show_new_explanation(catalog: list[AdministrativeDocument]) -> None:
    by_id = {item.id: item for item in catalog if item.id is not None and item.stato_verifica != "demo" and (item.detail_url or item.fonte_url or item.download_url)}
    if not by_id:
        return
    with st.expander("Prepara una spiegazione per un documento"):
        identifier = st.selectbox("Documento della nuova scheda", list(by_id), format_func=lambda value: f"{by_id[value].ente} — {display_title(by_id[value].titolo_ufficiale, max_length=80)}", key="new_explanation_document")
        version = st.text_input("Versione iniziale della spiegazione", value="1.0", key="new_explanation_version", max_chars=80)
        reviewer = st.text_input("Autore della nuova scheda", key="new_explanation_author", max_chars=MAX_REVIEWER_NAME_LENGTH)
        access_date = st.text_input("Data del confronto con la fonte (AAAA-MM-GG)", key="new_explanation_access_date")
        st.caption("La bozza contiene soltanto i metadati già registrati. La spiegazione va scritta e revisionata da una persona.")
        if st.button("Crea prima bozza", disabled=not reviewer_name_is_valid(reviewer) or not version.strip() or not access_date.strip(), key="create_first_draft"):
            try:
                identifier = submit_explanation_draft(identifier, version.strip(), reviewer, access_date.strip(), db_path=DEFAULT_DB_PATH)
                st.session_state["pending_review_selection"] = identifier
                st.rerun()
            except (ValueError, sqlite3.Error) as exc:
                show_problem("Impossibile creare la bozza.", exc)


def show_explanation_review(catalog: list[AdministrativeDocument], explanations: list[DocumentExplanation]) -> None:
    st.header("Revisione contenuti")
    st.caption("Area editoriale locale. Il nome del revisore è una dichiarazione, non un'identità autenticata. Le spiegazioni restano separate dai metadati ufficiali.")
    explanation_tab, document_tab, resource_tab, history_tab = st.tabs(("Spiegazioni", "Documenti", "Materiali", "Storico"))
    with explanation_tab:
        show_new_explanation(catalog)
        show_explanation_editor(catalog, explanations)
    with document_tab:
        show_document_review(catalog)
    with resource_tab:
        show_resource_review()
    with history_tab:
        show_review_history()


def show_theme_selector() -> None:
    """Selettore tema locale, compatto e visibile nella barra laterale."""
    st.caption("Aspetto")
    st.html(
        """
<style>
  .burocrazia-theme-options {
    display: flex;
    gap: 1.15rem;
    align-items: center;
    margin: -.15rem 0 .7rem;
    font: inherit;
  }
  .burocrazia-theme-option {
    display: inline-flex;
    align-items: center;
    gap: .42rem;
    cursor: pointer;
    user-select: none;
    font-size: .92rem;
    line-height: 1.2;
  }
  .burocrazia-theme-option input {
    appearance: none;
    -webkit-appearance: none;
    width: .86rem;
    height: .86rem;
    margin: 0;
    border: 1.5px solid currentColor;
    border-radius: 50%;
    background: transparent;
    display: grid;
    place-content: center;
    cursor: pointer;
  }
  .burocrazia-theme-option input::before {
    content: "";
    width: .42rem;
    height: .42rem;
    border-radius: 50%;
    transform: scale(0);
    transition: transform 100ms ease-in-out;
    background: #c84646;
  }
  .burocrazia-theme-option input:checked::before { transform: scale(1); }
  .burocrazia-theme-option input:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
</style>
<div class="burocrazia-theme-options" role="radiogroup" aria-label="Aspetto">
  <label class="burocrazia-theme-option"><input type="radio" name="burocrazia-theme" value="light_theme">Chiaro</label>
  <label class="burocrazia-theme-option"><input type="radio" name="burocrazia-theme" value="dark_theme">Scuro</label>
</div>
<script>
(() => {
  const allowed = new Set(["light_theme", "dark_theme"]);
  const url = new URL(window.location.href);
  const current = url.searchParams.getAll("embed_options").find(value => allowed.has(value)) || "dark_theme";
  const inputs = document.querySelectorAll('input[name="burocrazia-theme"]');
  for (const input of inputs) {
    input.checked = input.value === current;
    input.addEventListener("change", () => {
      if (!input.checked || input.value === current) return;
      const next = new URL(window.location.href);
      const retained = next.searchParams.getAll("embed_options").filter(value => !allowed.has(value));
      next.searchParams.delete("embed_options");
      for (const value of retained) next.searchParams.append("embed_options", value);
      next.searchParams.append("embed_options", input.value);
      window.location.replace(next.href);
    });
  }
})();
</script>
        """,
        unsafe_allow_javascript=True,
    )


def show_benchmark(catalog, families):
    from src.recognize import catalog_revision
    from src.benchmark_display import headline_sections
    st.subheader("Benchmark")
    st.caption("Risultati statici; nessun test sul documento caricato.")
    summary = load_summary(Path(__file__).resolve().parent / "benchmarks/latest_summary.json")
    st.text("Stato candidata: " + str(summary.get("status", "non disponibile")))
    st.text("Esecuzione: " + str(summary.get("executed_at", "non disponibile")))
    st.text("Commit valutato: " + str(summary.get("commit", "non disponibile")))
    st.text("Catalogo testato: " + str(summary.get("catalog_semantic_sha256", "non disponibile")))
    st.text("Documenti reali nel catalogo testato: " + str(summary.get("catalog_count", "non disponibile")))
    if summary.get("catalog_semantic_sha256") != catalog_revision(catalog, families):
        st.warning("Il catalogo corrente differisce da quello valutato: i risultati non descrivono le modifiche locali.")
    labels = {"document_precision": "Precisione documento", "document_recall": "Recall documento", "document_f1": "F1 documento",
              "family_precision": "Precisione famiglia", "family_recall": "Recall famiglia", "family_f1": "F1 famiglia", "useful_coverage": "Copertura utile",
              "unknown_correct_rejection_rate": "Rifiuti corretti degli sconosciuti", "unknown_false_acceptance_rate": "False accettazioni",
              "entity_error_rate": "Errori ente", "version_year_error_rate": "Errori versione"}
    for key,section in headline_sections(summary):
        st.divider()
        st.text({'independent_holdout':'Holdout ufficiale indipendente','hard_negatives':'Hard negatives',
                 'real_ocr':'OCR reale','performance':'Performance',
                 'known_canonical':'Documenti noti — file canonici',
                 'known_robustness':'Documenti noti — rappresentazioni trasformate',
                 'filled_forms':'Moduli compilati con dati fittizi',
                 'family_identity_holdout':'Famiglie — identità escluse',
                 'unknown_official':'Documenti ufficiali sconosciuti'}[key])
        if key=='independent_holdout':st.text('Corpus richiesto: official_holdout_v2; v1 è storico e non promuove la release.')
        if section.get('status')=='not_run':
            st.text('Benchmark indipendente non ancora disponibile' if key=='independent_holdout' else 'Non eseguito')
            continue
        if isinstance(section.get('summary'),dict):
            st.text('Casi: '+str(section['summary'].get('cases','non disponibile')))
            for name,label in labels.items():st.text(label+': '+metric_label(section['summary'].get('metrics',{}).get(name)))
        if key=='real_ocr':st.text(str(section.get('result','non disponibile')))
        if key=='performance':st.text('Rapporti p50/p95: '+str(section.get('p50_ratio'))+' / '+str(section.get('p95_ratio')))
    st.text('Dettagli di sviluppo e regressione: corpus non indipendenti.')
    for evaluation in summary["evaluations"]:
        st.divider()
        st.text(str(evaluation.get("name", "Valutazione")))
        if evaluation.get("status")=="not_run":
            st.text("Non eseguito")
            continue
        result = evaluation["summary"]
        st.text("Casi: " + str(result.get("cases", "non disponibile")))
        for key, label in labels.items():
            st.text(label + ": " + metric_label(result.get("metrics", {}).get(key)))
        latency = result.get("latency_ms", {})
        st.text("Latenza p50/p95 (ms): " + str(latency.get("p50")) + " / " + str(latency.get("p95")))
    st.text("OCR reale: " + str(summary.get("ocr_status", "non eseguito")))
    st.text("Dettagli locali: docs/BENCHMARK.md; docs/COVERAGE.md; benchmarks/results/")
    st.info("Il benchmark non garantisce il risultato su ogni documento reale. I risultati valgono per i corpus e l'ambiente indicati.")


def main() -> None:
    install_network_guard()
    st.set_page_config(page_title="BurOCRazia", page_icon="📄", layout="wide", menu_items={"Get help": None, "Report a Bug": None, "About": None})
    assets = Path(__file__).resolve().parent / "assets"
    st.html(assets / "theme_start.html", unsafe_allow_javascript=True)
    st.title("BurOCRazia")
    st.write("Capire la burocrazia, più chiaramente.")
    st.caption("Progetto ideato da Luca Lullo · Applicazione locale")
    try:
        catalog, sources, explanations, families = load_application_data()
    except (OSError, sqlite3.Error, ValueError):
        st.error("Non è stato possibile inizializzare il catalogo locale. Controlla il database e le istruzioni di ripristino.")
        return

    selected_area = st.sidebar.radio("Navigazione", NAVIGATION_AREAS, format_func=lambda area: NAVIGATION_LABELS[area], key="main_navigation")
    st.sidebar.divider()
    with st.sidebar:
        show_theme_selector()
    st.sidebar.button("Cancella sessione", key="reset_session", on_click=reset_document_session, help="Rimuove il documento e il risultato corrente dalla sessione. Il catalogo non viene modificato.")
    show_catalog_state(catalog, sources)

    if st.session_state.pop("reset_completed", False):
        st.success("Sessione ripulita.")
    try:
        if selected_area == "BurOCRazia":
            show_home(catalog, explanations, families)
        elif selected_area == "Catalogo":
            show_document_catalog(catalog, families, explanations)
        elif selected_area == "Fonti":
            show_sources_registry(sources)
        elif selected_area == "Benchmark":
            show_benchmark(catalog, families)
        else:
            show_explanation_review(catalog, explanations)
    except (OSError, sqlite3.Error, ValueError) as exc:
        show_problem("Impossibile completare l'operazione sui dati locali.", exc)


if __name__ == "__main__":
    main()
