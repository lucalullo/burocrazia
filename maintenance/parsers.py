"""Offline parsers: metadata observations are proposals, never human reviews."""
from __future__ import annotations

from dataclasses import asdict
import json
import re
from urllib.parse import urljoin, urlsplit

from lxml import html

from maintenance.policy import validate_url
from src.importers.inps import parse_inps_json
from src.importers.lavoro import parse_lavoro_html
from src.recognize import normalize_text

FILES = re.compile(r"\.(pdf|docx?|odt|rtf|xlsx?)(?:[/?#]|$)", re.I)
EXCLUDED = re.compile(r"\b(faq|domande frequenti|manuale|manuali|istruzioni|guida|guide|tutorial|circolare|regolamento|normativa|comunicato|informativa|specifiche tecniche|accordo|decreto|direttiva|elenco nazionale|tabella|glossario)\b", re.I)
FORM = re.compile(r"\b(modul\w*|modell\w*|istanza|domanda|richiesta|dichiarazione|certificat\w*|delega|autocertificaz\w*|scia|cila|denuncia|comunicazione|allegato)\b", re.I)


def clean(text):
    return " ".join((text or "").split()).strip()


def classify(title, *, collection_is_forms=False):
    if EXCLUDED.search(title):
        return "instructions" if re.search(r"istruzioni|guida|tutorial", title, re.I) else "other"
    if re.search(r"dichiarazione|autocertificazione", title, re.I):
        return "declaration"
    if re.search(r"certificato|certificazione", title, re.I):
        return "certificate"
    if re.search(r"istanza|domanda|richiesta", title, re.I):
        return "application"
    return "form" if FORM.search(title) or collection_is_forms else "other"


def identity(observation):
    """Formats are resources; versions, issuers and official codes stay distinct."""
    return (normalize_text(observation["ente"]), normalize_text(observation["titolo_ufficiale"]),
            normalize_text(observation.get("codice") or ""), observation.get("versione"))


def observation(module, source, receipt):
    d = asdict(module) if not isinstance(module, dict) else module
    title = clean(d["titolo_ufficiale"])
    download = d.get("download_url") or d.get("model_url")
    return dict(ente=source["ente"], titolo_ufficiale=title, codice=d.get("codice"),
                categoria=d.get("categoria") or d.get("area"), descrizione_ufficiale=d.get("descrizione_ufficiale"),
                versione=d.get("versione"), data_pubblicazione=d.get("data_pubblicazione"),
                fonte_url=receipt["final_url"], detail_url=d.get("detail_url"), download_url=download,
                source_key=source["key"], acquired_at=receipt["acquired_at"],
                response_sha256=receipt["sha256"], kind=classify(title, collection_is_forms=True),
                resources=[dict(url=download, language=None)] if download else [])


def parse(raw: bytes, source: dict, receipt: dict):
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Input parser oltre 8 MiB.")
    key, url = source["key"], receipt["final_url"]
    validate_url(url, key)
    text = raw.decode("utf-8-sig", errors="strict")
    if re.search(r"<title>\s*(?:Gcore|Just a moment|Access denied|Attention Required)[^<]*</title>|cf-chl-|gcore.*captcha", text, re.I):
        raise ValueError("Pagina di blocco/challenge HTTP 200: contenuto non acquisibile, nessun aggiramento.")
    if key == "inps" and urlsplit(url).path.endswith(".json"):
        payload = json.loads(text)
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("Struttura INPS cambiata: items assente.")
        batch = parse_inps_json(payload, source["urls"][0], limit=200)
        return [observation(m, source, receipt) for m in batch.modules], []
    if key == "lavoro":
        batch = parse_lavoro_html(text, url, limit=500)
        return [observation(m, source, receipt) for m in batch.modules], []
    if key == "inl" and "/servizio/" not in urlsplit(url).path:
        # A service listing does not establish a downloadable form identity.
        return [], []
    tree = html.fromstring(text)
    # Some institutional templates wrap content in nav; do not discard it.
    for element in tree.xpath('//script|//style|//header|//footer'):
        element.drop_tree()
    main = tree.xpath('//main|//*[@id="interna-webcontent"]|//*[@id="main-page"]|//*[@id="content"]')
    container = main[0] if main else tree
    output, excluded = [], []
    for anchor in container.xpath('.//a[@href]'):
        raw_url = anchor.get("href")
        procedural = key == "mef" and "/area-privata/moduli/" in raw_url
        privacy_download = key == "garante_privacy" and "/garante/document?" in raw_url
        if not FILES.search(raw_url) and not procedural and not privacy_download:
            continue
        target = urljoin(url, raw_url)
        label = clean(anchor.text_content())
        title_attr = clean(anchor.get("title"))
        title = title_attr if title_attr.lower().startswith("scarica file") else label or title_attr
        # Judicial downloads have empty anchors; use the official table cell.
        row = anchor.xpath('ancestor::tr[1]')
        if source.get("parser") == "judicial" and row:
            cells = row[0].xpath('./td')
            if len(cells) >= 3:
                title = clean(cells[0].text_content())
        title = re.sub(r"^Scarica file\s*[:\-]\s*", "", title, flags=re.I)
        title = re.sub(r"\s+Formato\s+(?:PDF|DOCX?).*$", "", title, flags=re.I)
        title = re.sub(r"\.(pdf|docx?|odt|rtf)\b.*$", "", title, flags=re.I)
        title = re.sub(r"\s*[-–]\s*editabile\s*$", "", title, flags=re.I).strip()
        title = re.sub(r"\s*(?:PDF|DOCX?)\s*[,\-–]?\s*\d+(?:[.,]\d+)?\s*(?:KB|MB)\s*$", "", title, flags=re.I).strip()
        title = re.sub(r"^ModuloINL\b", "Modulo INL", title, flags=re.I)
        kind = classify(title, collection_is_forms=source.get("forms_collection", False))
        if re.fullmatch(r"(?:allegato|modulo|modello)(?:\s+(?:\d+|[a-z]|aggiornato|scaricabile|ed|editabile))*", title, re.I):
            kind = "other"
        try:
            validate_url(target, key)
        except ValueError:
            excluded.append(dict(url=target, title=title, reason="external_url"))
            continue
        if not title or title.casefold() in {"pdf", "doc", "docx", "scarica", "download"} or kind not in {"form", "application", "declaration", "certificate"}:
            excluded.append(dict(url=target, title=title, reason="not_identifiable_form", kind=kind))
            continue
        heading = anchor.xpath('preceding::h2[1]|preceding::h3[1]')
        category = clean(heading[-1].text_content()) if heading else None
        code = re.search(r"\b(?:INL[\s-]*\d+(?:[.\-]\d+)*(?:-R)?|NP[23][CD]|TT\s*\d{4}|(?:RL|TR|MB)-\s*(?:\d{2}|AE))\b", title, re.I)
        code_value = re.sub(r"^INL[\s-]*", "INL ", code.group(0), flags=re.I) if code else None
        # A law's year is not a form version.
        year = re.findall(r"\b(?:versione|edizione|annualit[àa]|anno)\s*[:\-]?\s*((?:19|20)\d{2})\b", title, re.I)
        item = observation(dict(titolo_ufficiale=title, codice=code_value,
                                categoria=None, versione=year[0] if len(set(year)) == 1 else None,
                                detail_url=target if procedural else url, download_url=None if procedural else target), source, receipt)
        item["kind"] = kind
        item["derived_section_label"] = category
        if key == "inl":
            language = re.search(r"\b(inglese|francese|romeno|cinese|arabo|bengalese|punjabi|urdu|ucraino|russo)\b", title.replace("-", " "), re.I)
            if language:
                item["resources"][0]["language"] = language.group(1).lower()
        output.append(item)
    return output, excluded


def discover(raw: bytes, source: dict, base_url: str):
    """Only declared collections and explicit next-page links, never a site crawl."""
    tree = html.fromstring(raw.decode("utf-8-sig"))
    urls = []
    for anchor in tree.xpath('//a[@href]'):
        raw_url = anchor.get("href")
        if raw_url.startswith(("#", "mailto:", "javascript:")):
            continue
        url = urljoin(base_url, raw_url)
        try:
            url = validate_url(url, source["key"])
        except ValueError:
            continue
        if FILES.search(url):
            continue
        path = urlsplit(url).path
        if any(path.startswith(prefix) for prefix in source.get("path_prefixes", [])):
            urls.append(url)
    return sorted(set(urls))


def merge_observations(items):
    merged = {}
    resource_keys = {}
    duplicates = 0
    for item in items:
        key = identity(item)
        # Two labels pointing at the same file do not establish two identities.
        resource = (normalize_text(item["ente"]), item.get("download_url"), item.get("versione"), normalize_text(item.get("codice") or item["titolo_ufficiale"]))
        if resource[1] and resource in resource_keys:
            key = resource_keys[resource]
        if item["source_key"] == "inl" and item.get("codice"):
            key = (normalize_text(item["ente"]), normalize_text(item["codice"]), item.get("versione"))
        if key in merged:
            duplicates += 1
            urls = {r["url"] for r in merged[key]["resources"]}
            merged[key]["resources"].extend(r for r in item["resources"] if r["url"] not in urls)
        else:
            merged[key] = item
        if resource[1]:
            resource_keys[resource] = key
    return list(merged.values()), duplicates
