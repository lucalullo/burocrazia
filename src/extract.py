from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from io import BytesIO
import math
from pathlib import Path, PurePosixPath
from time import monotonic
from typing import BinaryIO
from xml.etree import ElementTree
from zipfile import BadZipFile, LargeZipFile, ZipFile
from zlib import error as ZlibError

import fitz
from PIL import Image
from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError

from src import ocr as local_ocr
from src.text_quality import text_quality

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_EXTRACTED_TEXT_CHARS = 1_000_000
MAX_DOCX_MEMBERS = 2_000
MAX_DOCX_MEMBER_BYTES = 10 * 1024 * 1024
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_DOCX_XML_ELEMENTS = 200_000
MAX_DOCX_COMPRESSION_RATIO = 200
MAX_EXTRACTION_SECONDS = 120
NO_TEXT_PDF_MESSAGE = local_ocr.OCR_UNAVAILABLE_MESSAGE
PDF_OCR_LIMIT_WARNING = f"L'OCR è stato limitato alle prime {local_ocr.MAX_OCR_PAGES} pagine del documento."
SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain"}, ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"}, ".png": {"image/png"},
}


class ExtractionError(ValueError):
    """A supported file cannot be read safely."""


class UnsupportedFileError(ExtractionError):
    """The uploaded format is unsupported."""


class NoTextFoundError(ExtractionError):
    """The document contains no usable text."""


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    method: str
    used_ocr: bool = False
    pages_processed: int | None = None
    warning: str | None = None
    total_pages: int | None = None
    ocr_pages: int = 0

    @property
    def ocr(self) -> bool:
        return self.used_ocr


def _read_bytes(source: bytes | bytearray | BinaryIO) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        if len(source) > MAX_UPLOAD_BYTES:
            raise ExtractionError("Il file supera il limite di 20 MiB per caricamento.")
        content = bytes(source)
    else:
        try:
            content = source.read(MAX_UPLOAD_BYTES + 1)
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise ExtractionError("Non è stato possibile leggere il file caricato.") from exc
    if not isinstance(content, bytes):
        raise ExtractionError("Il contenuto del file non è in formato binario valido.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ExtractionError("Il file supera il limite di 20 MiB per caricamento.")
    if not content:
        raise ExtractionError("Il file caricato è vuoto.")
    return content


def _normalize_extracted_text(text: str) -> str:
    if len(text) > MAX_EXTRACTED_TEXT_CHARS:
        raise ExtractionError("Il testo estratto supera il limite di 1.000.000 di caratteri.")
    return local_ocr.normalize_ocr_text(text)


def _check_deadline(started: float) -> None:
    if monotonic() - started > MAX_EXTRACTION_SECONDS:
        raise ExtractionError("Tempo massimo di estrazione superato. Carica un documento più breve.")


def _combine_warnings(warnings: list[str]) -> str | None:
    unique = list(dict.fromkeys(warning for warning in warnings if warning))
    return " ".join(unique) if unique else None


def _raise_safe_ocr_error(exc: local_ocr.OCRError) -> None:
    if isinstance(exc, local_ocr.InsufficientOCRTextError):
        raise NoTextFoundError(str(exc)) from exc
    raise ExtractionError(str(exc)) from exc


def _pdf_page_image(page) -> Image.Image:
    width, height = page.rect.width, page.rect.height
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise ExtractionError("La pagina PDF ha dimensioni non valide.")
    scale = min(2.0, math.sqrt(local_ocr.MAX_OCR_IMAGE_PIXELS / (width * height)))
    # Check rounded output dimensions before allocating the native raster.
    if math.ceil(width * scale) * math.ceil(height * scale) > local_ocr.MAX_OCR_IMAGE_PIXELS:
        scale *= 0.99
    raster_width, raster_height = math.ceil(width * scale), math.ceil(height * scale)
    if max(raster_width, raster_height) > 32_768 or raster_width * raster_height > local_ocr.MAX_OCR_IMAGE_PIXELS:
        raise ExtractionError("La pagina PDF è troppo grande per l'OCR.")
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def extract_pdf(source: bytes | bytearray | BinaryIO) -> ExtractionResult:
    content = _read_bytes(source)
    if not content.startswith(b"%PDF-"):
        raise ExtractionError("Il PDF non è valido o non può essere letto.")
    started = monotonic()
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        raise ExtractionError("Il PDF non è valido o non può essere letto.") from exc
    with pdf:
        if pdf.needs_pass:
            raise ExtractionError("Il PDF è protetto da password. Carica una copia sbloccata.")
        if pdf.page_count > MAX_PDF_PAGES:
            raise ExtractionError(f"Il PDF supera il limite di {MAX_PDF_PAGES} pagine.")
        if not pdf.page_count:
            raise NoTextFoundError("Il PDF non contiene pagine leggibili.")
        page_texts: list[str] = []
        warnings: list[str] = []
        text_chars = direct_pages = ocr_pages = 0
        unread_pages: list[int] = []
        unavailable: local_ocr.OCRUnavailableError | None = None
        try:
            for page_number in range(pdf.page_count):
                _check_deadline(started)
                page = pdf.load_page(page_number)
                text = _normalize_extracted_text(page.get_text("text"))
                if text and not text_quality(text)['usable']:
                    warnings.append('Text layer PDF non utilizzabile: tentativo OCR entro i limiti esistenti.')
                    text = ''
                if text:
                    direct_pages += 1
                elif page_number >= local_ocr.MAX_OCR_PAGES:
                    unread_pages.append(page_number + 1)
                    warnings.append(PDF_OCR_LIMIT_WARNING)
                elif unavailable is not None:
                    unread_pages.append(page_number + 1)
                else:
                    try:
                        with closing(_pdf_page_image(page)) as image:
                            result = local_ocr.ocr_image(image, min_text_length=0, auto_orient=True, deadline=started + MAX_EXTRACTION_SECONDS)
                        ocr_pages += 1
                        text = result.text
                        if result.warning:
                            warnings.append(result.warning)
                        if not text:
                            unread_pages.append(page_number + 1)
                    except local_ocr.OCRUnavailableError as exc:
                        unavailable = exc
                        unread_pages.append(page_number + 1)
                    except local_ocr.OCRError as exc:
                        _raise_safe_ocr_error(exc)
                text_chars += len(text) + bool(page_texts and text)
                if text_chars > MAX_EXTRACTED_TEXT_CHARS:
                    raise ExtractionError("Il testo estratto supera il limite di 1.000.000 di caratteri.")
                if text:
                    page_texts.append(text)
                _check_deadline(started)
        except (ExtractionError, NoTextFoundError):
            raise
        except (RuntimeError, ValueError, OSError, OverflowError) as exc:
            raise ExtractionError("Il PDF non è valido o non può essere elaborato in modo sicuro.") from exc
        if unavailable is not None:
            if not page_texts:
                raise NoTextFoundError(NO_TEXT_PDF_MESSAGE) from unavailable
            warnings.append(NO_TEXT_PDF_MESSAGE)
        text = _normalize_extracted_text("\n".join(page_texts))
        if not direct_pages:
            try:
                text = local_ocr.validate_ocr_text(text)
            except local_ocr.OCRError as exc:
                _raise_safe_ocr_error(exc)
        # The usual all-scanned limit keeps its established warning; other partial
        # results explicitly identify the pages missing usable text.
        if unread_pages and (direct_pages or not all(page > local_ocr.MAX_OCR_PAGES for page in unread_pages)):
            warnings.append("Testo non acquisito dalle pagine: " + ", ".join(map(str, unread_pages)) + ".")
        return ExtractionResult(
            text=text, method="pdf_mixed" if direct_pages and ocr_pages else "pdf_text" if direct_pages else "ocr",
            used_ocr=bool(ocr_pages), pages_processed=direct_pages + ocr_pages,
            warning=_combine_warnings(warnings), total_pages=pdf.page_count, ocr_pages=ocr_pages,
        )


def extract_pdf_text(source: bytes | bytearray | BinaryIO) -> str:
    return extract_pdf(source).text


def _validate_docx_archive(content: bytes, started: float) -> None:
    try:
        with ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > MAX_DOCX_MEMBERS:
                raise ExtractionError("Il DOCX contiene troppi elementi nell'archivio.")
            if sum(info.file_size for info in members) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise ExtractionError("Il DOCX supera il limite di 50 MiB decompressi.")
            names: set[str] = set()
            elements = 0
            for info in members:
                _check_deadline(started)
                path = PurePosixPath(info.filename)
                # ZipInfo normalizes backslashes on Windows even when reading a raw archive.
                if info.filename in names or path.is_absolute() or ".." in path.parts or "\\" in info.filename or "\\" in info.orig_filename or ":" in info.filename:
                    raise ExtractionError("Il DOCX contiene percorsi non validi o elementi duplicati.")
                names.add(info.filename)
                if info.flag_bits & 1:
                    raise ExtractionError("Il DOCX contiene elementi protetti da password.")
                if info.file_size > MAX_DOCX_MEMBER_BYTES or info.file_size > MAX_DOCX_COMPRESSION_RATIO * max(1, info.compress_size):
                    raise ExtractionError("Il DOCX contiene un elemento troppo grande o eccessivamente compresso.")
                payload = archive.read(info)  # CRC and declared sizes are validated without extracting to disk.
                if len(payload) != info.file_size:
                    raise ExtractionError("Il DOCX contiene dimensioni non valide.")
                if info.filename.endswith((".xml", ".rels")):
                    xml_markers = payload.replace(b"\x00", b"").upper()
                    if b"<!DOCTYPE" in xml_markers or b"<!ENTITY" in xml_markers:
                        raise ExtractionError("Il DOCX contiene dichiarazioni XML non consentite.")
                    root = ElementTree.fromstring(payload)
                    elements += sum(1 for _ in root.iter())
                    if elements > MAX_DOCX_XML_ELEMENTS:
                        raise ExtractionError("Il DOCX contiene troppi elementi XML.")
            if not {"[Content_Types].xml", "word/document.xml", "_rels/.rels"} <= names:
                raise ExtractionError("Il file DOCX non è valido o non può essere letto.")
            types = ElementTree.fromstring(archive.read("[Content_Types].xml"))
            expected = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
            if not any(node.attrib.get("PartName") == "/word/document.xml" and node.attrib.get("ContentType") == expected for node in types):
                raise ExtractionError("Il formato interno del DOCX non è supportato.")
    except ExtractionError:
        raise
    except (BadZipFile, LargeZipFile, RuntimeError, ValueError, OSError, NotImplementedError, ElementTree.ParseError, ZlibError) as exc:
        raise ExtractionError("Il file DOCX non è valido o non può essere letto.") from exc


def extract_docx_text(source: bytes | bytearray | BinaryIO) -> str:
    content = _read_bytes(source)
    started = monotonic()
    if not content.startswith(b"PK\x03\x04"):
        raise ExtractionError("Il file DOCX non è valido o non può essere letto.")
    _validate_docx_archive(content, started)
    try:
        document = DocxDocument(BytesIO(content))
        paragraphs: list[str] = []
        text_chars = 0
        # Body order includes paragraphs in table cells and nested tables.
        for element in document.element.body.iter(qn("w:p")):
            _check_deadline(started)
            text = Paragraph(element, document).text.strip()
            text_chars += len(text) + bool(paragraphs and text)
            if text_chars > MAX_EXTRACTED_TEXT_CHARS:
                raise ExtractionError("Il testo estratto supera il limite di 1.000.000 di caratteri.")
            if text:
                paragraphs.append(text)
        text = _normalize_extracted_text("\n".join(paragraphs))
    except ExtractionError:
        raise
    except (ValueError, KeyError, OSError, BadZipFile, XMLSyntaxError) as exc:
        raise ExtractionError("Il file DOCX non è valido o non può essere letto.") from exc
    if not text:
        raise NoTextFoundError("Il documento DOCX non contiene testo estraibile.")
    return text


def extract_txt_text(source: bytes | bytearray | BinaryIO) -> str:
    content = _read_bytes(source)
    if content.startswith((b"%PDF-", b"PK\x03\x04", b"\x89PNG", b"\xff\xd8\xff")) or any(byte < 32 and byte not in (9, 10, 12, 13) for byte in content):
        raise ExtractionError("Il file TXT non sembra contenere testo valido.")
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = _normalize_extracted_text(content.decode(encoding))
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - latin-1 decodes every byte sequence
        raise ExtractionError("Non è stato possibile decodificare il file TXT.")
    if not text:
        raise NoTextFoundError("Il file TXT non contiene testo.")
    return text


def extract_image(source: bytes | bytearray | BinaryIO) -> ExtractionResult:
    content = _read_bytes(source)
    try:
        result = local_ocr.ocr_image_bytes(content)
    except local_ocr.OCRError as exc:
        _raise_safe_ocr_error(exc)
    return ExtractionResult(_normalize_extracted_text(result.text), method="ocr", used_ocr=True, pages_processed=1, warning=result.warning, total_pages=1, ocr_pages=1)


def extract_image_text(source: bytes | bytearray | BinaryIO) -> str:
    return extract_image(source).text


def extract_document(source: bytes | bytearray | BinaryIO, filename: str, mime_type: str | None = None) -> ExtractionResult:
    extension = Path(filename).suffix.casefold()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError("Formato non supportato. Carica un file PDF, DOCX, TXT, JPG, JPEG o PNG.")
    if mime_type and mime_type.split(";", 1)[0].strip().casefold() not in MIME_TYPES[extension] | {"application/octet-stream"}:
        raise ExtractionError("Il tipo MIME dichiarato non corrisponde al formato del file.")
    content = _read_bytes(source)
    if extension == ".pdf":
        return extract_pdf(content)
    if extension == ".docx":
        return ExtractionResult(extract_docx_text(content), method="docx")
    if extension == ".txt":
        return ExtractionResult(extract_txt_text(content), method="txt")
    expected_magic = b"\x89PNG\r\n\x1a\n" if extension == ".png" else b"\xff\xd8\xff"
    if not content.startswith(expected_magic):
        raise ExtractionError(local_ocr.INVALID_IMAGE_MESSAGE)
    return extract_image(content)


def extract_text(source: bytes | bytearray | BinaryIO, filename: str) -> str:
    """Backward-compatible text-only extraction API."""
    return extract_document(source, filename).text
