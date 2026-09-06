from __future__ import annotations

from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageDraw
import pytest

from src import ocr
from src.extract import (
    ExtractionError,
    NoTextFoundError,
    PDF_OCR_LIMIT_WARNING,
    extract_document,
)
from src.models import AdministrativeDocument
from src.recognize import recognize_document


OCR_TEXT = "SR211 RINUNCIA DEI BENEFICIARI ALLA CARTA ACQUISTI"


def image_bytes(format_name: str = "PNG", *, exif=None) -> bytes:
    image = Image.new("RGB", (120, 60), "white")
    buffer = BytesIO()
    save_options = {"exif": exif} if exif is not None else {}
    image.save(buffer, format=format_name, **save_options)
    return buffer.getvalue()


def oriented_marker_bytes(angle: int, format_name: str) -> bytes:
    image = Image.new("RGB", (160, 80), "white")
    ImageDraw.Draw(image).rectangle((3, 3, 27, 27), fill="black")
    rotated = image.rotate(angle, expand=True)
    buffer = BytesIO()
    rotated.save(buffer, format=format_name)
    return buffer.getvalue()


class OrientationBackend:
    def __init__(self, osd: str | None = None) -> None:
        self.osd = osd
        self.ocr_calls = 0

    @staticmethod
    def get_languages(config: str = "", *, timeout: float) -> list[str]:
        return ["ita"]

    def image_to_osd(self, _image: Image.Image, *, timeout: float) -> str:
        if self.osd is None:
            raise RuntimeError("OSD non disponibile nella fixture")
        return self.osd

    def image_to_string(self, image: Image.Image, *, lang: str, timeout: float) -> str:
        self.ocr_calls += 1
        corner = image.crop((0, 0, 32, 32))
        average = sum(corner.getdata()) / (corner.width * corner.height)
        return OCR_TEXT if average < 220 else "x"


def blank_pdf(page_count: int = 1) -> bytes:
    document = fitz.open()
    for _ in range(page_count):
        document.new_page(width=120, height=80)
    content = document.tobytes()
    document.close()
    return content


@pytest.mark.parametrize(
    ("filename", "format_name"),
    [("foto.jpg", "JPEG"), ("foto.JPEG", "JPEG"), ("foto.png", "PNG")],
)
def test_supported_image_extensions_are_accepted(
    monkeypatch,
    filename: str,
    format_name: str,
) -> None:
    monkeypatch.setattr(
        "src.extract.local_ocr.ocr_image_bytes",
        lambda _content: ocr.OCRResult(OCR_TEXT, "ita"),
    )

    result = extract_document(image_bytes(format_name), filename)

    assert result.text == OCR_TEXT
    assert result.used_ocr
    assert result.pages_processed == 1


def test_valid_image_is_loaded_and_preprocessed() -> None:
    loaded = ocr.load_image(image_bytes())
    prepared = ocr.prepare_image(loaded)

    assert loaded.size == (120, 60)
    assert prepared.mode == "L"


def test_corrupt_image_is_reported_safely() -> None:
    with pytest.raises(ExtractionError, match="immagine non è valida"):
        extract_document(b"not an image", "foto.png")


def test_image_extraction_calls_the_ocr_function(monkeypatch) -> None:
    calls: list[bytes] = []

    def fake_ocr(content: bytes) -> ocr.OCRResult:
        calls.append(content)
        return ocr.OCRResult(OCR_TEXT, "ita")

    monkeypatch.setattr("src.extract.local_ocr.ocr_image_bytes", fake_ocr)
    content = image_bytes()

    extract_document(content, "foto.png")

    assert calls == [content]


def test_tesseract_unavailable_has_the_required_message(monkeypatch) -> None:
    monkeypatch.setattr(ocr, "pytesseract", None)

    with pytest.raises(ExtractionError) as exc_info:
        extract_document(image_bytes(), "foto.png")

    assert str(exc_info.value) == ocr.OCR_UNAVAILABLE_MESSAGE


def test_insufficient_ocr_text_is_rejected(monkeypatch) -> None:
    class ShortTextBackend:
        @staticmethod
        def get_languages(config: str = "", *, timeout: float) -> list[str]:
            return ["ita"]

        @staticmethod
        def image_to_string(_image, *, lang: str, timeout: float) -> str:
            return "abc"

    monkeypatch.delenv(ocr.TESSERACT_COMMAND_ENV, raising=False)
    monkeypatch.setattr(ocr, "_configured_backend", lambda: ShortTextBackend())

    with pytest.raises(NoTextFoundError) as exc_info:
        extract_document(image_bytes(), "foto.png")

    assert "Non sono riuscito a leggere abbastanza testo" in str(exc_info.value)
    assert "foto più nitida" in str(exc_info.value)


def test_textual_pdf_does_not_call_ocr(monkeypatch) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Documento amministrativo con testo digitale")
    content = document.tobytes()
    document.close()

    def unexpected_ocr(*_args, **_kwargs):
        raise AssertionError("OCR non deve essere usato per un PDF testuale")

    monkeypatch.setattr("src.extract.local_ocr.ocr_image", unexpected_ocr)

    result = extract_document(content, "documento.pdf")

    assert result.method == "pdf_text"
    assert not result.used_ocr


def test_pdf_without_text_uses_ocr_fallback(monkeypatch) -> None:
    calls: list[tuple[Image.Image, int]] = []

    def fake_ocr(image: Image.Image, *, min_text_length: int, auto_orient: bool, deadline: float) -> ocr.OCRResult:
        calls.append((image, min_text_length))
        assert auto_orient is True and deadline > 0
        return ocr.OCRResult(OCR_TEXT, "ita")

    monkeypatch.setattr("src.extract.local_ocr.ocr_image", fake_ocr)

    result = extract_document(blank_pdf(), "scansione.pdf")

    assert len(calls) == 1
    assert calls[0][1] == 0
    assert result.method == "ocr"
    assert result.text == OCR_TEXT


def test_pdf_ocr_is_limited_to_five_pages(monkeypatch) -> None:
    calls = 0

    def fake_ocr(_image: Image.Image, *, min_text_length: int, auto_orient: bool, deadline: float) -> ocr.OCRResult:
        nonlocal calls
        assert auto_orient is True and deadline > 0
        calls += 1
        return ocr.OCRResult(f"{OCR_TEXT} pagina {calls}", "ita")

    monkeypatch.setattr("src.extract.local_ocr.ocr_image", fake_ocr)

    result = extract_document(blank_pdf(7), "scansione.pdf")

    assert calls == ocr.MAX_OCR_PAGES == 5
    assert result.pages_processed == 5
    assert result.warning == PDF_OCR_LIMIT_WARNING


def test_exif_orientation_is_applied() -> None:
    exif = Image.Exif()
    exif[274] = 6
    source = Image.new("RGB", (40, 20), "white")
    buffer = BytesIO()
    source.save(buffer, format="JPEG", exif=exif)

    loaded = ocr.load_image(buffer.getvalue())

    assert loaded.size == (20, 40)


@pytest.mark.parametrize(
    ("angle", "format_name"),
    ((0, "PNG"), (90, "JPEG"), (180, "PNG"), (270, "JPEG")),
)
def test_image_ocr_fallback_selects_the_best_quarter_turn(
    monkeypatch,
    angle: int,
    format_name: str,
) -> None:
    backend = OrientationBackend()
    monkeypatch.delenv(ocr.TESSERACT_COMMAND_ENV, raising=False)
    monkeypatch.setattr(ocr, "_configured_backend", lambda: backend)

    result = ocr.ocr_image_bytes(oriented_marker_bytes(angle, format_name))

    assert result.text == OCR_TEXT
    assert result.rotation == angle
    assert backend.ocr_calls == 4


def test_image_ocr_prefers_reliable_tesseract_osd(monkeypatch) -> None:
    backend = OrientationBackend(
        "Orientation in degrees: 270\n"
        "Rotate: 90\n"
        "Orientation confidence: 12.50\n"
    )
    monkeypatch.delenv(ocr.TESSERACT_COMMAND_ENV, raising=False)
    monkeypatch.setattr(ocr, "_configured_backend", lambda: backend)

    result = ocr.ocr_image_bytes(oriented_marker_bytes(90, "PNG"))

    assert result.text == OCR_TEXT
    assert result.rotation == 90
    assert backend.ocr_calls == 2


def test_ocr_text_is_passed_to_the_existing_recognizer(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.extract.local_ocr.ocr_image_bytes",
        lambda _content: ocr.OCRResult(OCR_TEXT, "ita"),
    )
    catalog = [
        AdministrativeDocument(
            ente="INPS",
            codice="SR211",
            titolo_ufficiale="RINUNCIA DEI BENEFICIARI ALLA CARTA ACQUISTI",
            categoria="prestazioni",
            descrizione_ufficiale=None,
            significato_semplice=None,
            versione="test",
            data_rilevazione="2026-08-05",
            stato_verifica="demo",
        )
    ]

    extraction = extract_document(image_bytes(), "foto.png")
    recognition = recognize_document(extraction.text, catalog)

    assert recognition.recognized
    assert recognition.document is not None
    assert recognition.document.codice == "SR211"


def test_uploaded_image_is_not_saved_permanently(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.extract.local_ocr.ocr_image_bytes",
        lambda _content: ocr.OCRResult(OCR_TEXT, "ita"),
    )

    before = list(tmp_path.iterdir())
    extract_document(image_bytes(), "foto.png")

    assert list(tmp_path.iterdir()) == before == []


def test_ocr_warning_is_available_to_the_ui(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.extract.local_ocr.ocr_image_bytes",
        lambda _content: ocr.OCRResult(
            OCR_TEXT,
            "eng",
            ocr.OCR_ENGLISH_FALLBACK_WARNING,
        ),
    )

    result = extract_document(image_bytes(), "foto.png")

    assert result.warning == ocr.OCR_ENGLISH_FALLBACK_WARNING


def test_english_language_is_a_controlled_fallback(monkeypatch) -> None:
    class EnglishBackend:
        @staticmethod
        def get_languages(config: str = "", *, timeout: float) -> list[str]:
            return ["eng"]

    monkeypatch.delenv(ocr.TESSERACT_COMMAND_ENV, raising=False)
    monkeypatch.setattr(ocr, "_configured_backend", lambda: EnglishBackend())

    language, warning = ocr.select_ocr_language()

    assert language == "eng"
    assert warning == ocr.OCR_ENGLISH_FALLBACK_WARNING


def test_oversized_image_is_rejected_without_crashing(monkeypatch) -> None:
    monkeypatch.setattr(ocr, "MAX_INPUT_IMAGE_PIXELS", 100)

    with pytest.raises(ExtractionError, match="troppo grande"):
        extract_document(image_bytes(), "foto.png")
