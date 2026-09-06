"""A03: simulated OCR isolates PDF orientation, deadlines and cleanup."""
from io import BytesIO
from tempfile import TemporaryDirectory

import fitz
from PIL import Image, ImageDraw
import pytest

from src import extract, ocr

TEXT = "INPS SR211 RINUNCIA DEI BENEFICIARI ALLA CARTA ACQUISTI"


def scanned_pdf(angle=0, pages=1):
    with Image.new("RGB", (160, 80), "white") as marker:
        ImageDraw.Draw(marker).rectangle((3, 3, 27, 27), fill="black")
        with marker.rotate(angle, expand=True) as rotated:
            stream = BytesIO()
            rotated.save(stream, format="PNG")
            with fitz.open() as pdf:
                for _ in range(pages):
                    page = pdf.new_page(width=rotated.width / 2, height=rotated.height / 2)
                    page.insert_image(page.rect, stream=stream.getvalue())
                return pdf.tobytes()


def test_a03_pdf_enables_existing_ocr_auto_orientation(monkeypatch):
    calls = []
    def read(image, **kwargs):
        calls.append(kwargs)
        return ocr.OCRResult(TEXT, "ita")
    monkeypatch.setattr(ocr, "ocr_image", read)
    result = extract.extract_pdf(scanned_pdf())
    assert calls[0].get("auto_orient") is True
    assert calls[0]["min_text_length"] == 0
    assert result.text == TEXT and result.method == "ocr"


@pytest.mark.parametrize("angle", (0, 90, 180, 270))
def test_pdf_synthetic_quarter_turns_with_simulated_ocr(monkeypatch, angle):
    class Backend:
        calls = 0
        @staticmethod
        def get_languages(**kwargs):
            return ["eng"]
        @staticmethod
        def image_to_osd(*args, **kwargs):
            raise RuntimeError("OSD intentionally unavailable in simulated fixture")
        def image_to_string(self, image, **kwargs):
            self.calls += 1
            with image.crop((0, 0, 32, 32)) as corner:
                average = sum(corner.getdata()) / (corner.width * corner.height)
            return TEXT if image.width > image.height and average < 220 else "x"
    backend = Backend()
    monkeypatch.setattr(ocr, "_configured_backend", lambda: backend)
    result = extract.extract_pdf(scanned_pdf(angle))
    assert result.text == TEXT and result.ocr_pages == 1
    assert backend.calls == 4
    assert result.warning == ocr.OCR_ENGLISH_FALLBACK_WARNING


class Clock:
    now = 0.0
    def __call__(self):
        return self.now


class TimedBackend:
    def __init__(self, clock, osd=None):
        self.clock, self.osd, self.calls = clock, osd, []
    def spend(self, operation, duration, timeout):
        self.calls.append((operation, timeout))
        self.clock.now += min(duration, timeout)
        if duration > timeout:
            raise ocr.OCRTimeoutError(ocr.OCR_TIMEOUT_MESSAGE)
    def get_languages(self, *, config, timeout):
        self.spend("language", 1, timeout)
        return ["ita"]
    def image_to_osd(self, image, *, timeout):
        self.spend("osd", 1, timeout)
        if self.osd is None:
            raise RuntimeError("OSD unavailable")
        return self.osd
    def image_to_string(self, image, *, lang, timeout):
        self.spend("ocr", 18, timeout)
        return TEXT


def test_image_orientation_attempts_share_sixty_second_budget(monkeypatch):
    clock = Clock()
    backend = TimedBackend(clock)
    monkeypatch.setattr(ocr, "monotonic", clock)
    monkeypatch.setattr(ocr, "_configured_backend", lambda: backend)
    with Image.new("RGB", (160, 80)) as image, pytest.raises(ocr.OCRTimeoutError):
        ocr.ocr_image(image, auto_orient=True)
    assert clock.now == ocr.OCR_TOTAL_TIMEOUT_SECONDS == 60
    assert [timeout for operation, timeout in backend.calls if operation == "ocr"] == [20, 20, 20, 4]


def test_pdf_pages_share_whole_document_budget(monkeypatch):
    clock = Clock()
    backend = TimedBackend(clock, "Rotate: 90\nOrientation confidence: 12.5\n")
    monkeypatch.setattr(extract, "monotonic", clock)
    monkeypatch.setattr(ocr, "monotonic", clock)
    monkeypatch.setattr(ocr, "_configured_backend", lambda: backend)
    with pytest.raises(extract.ExtractionError, match="Tempo massimo"):
        extract.extract_pdf(scanned_pdf(pages=5))
    assert clock.now == extract.MAX_EXTRACTION_SECONDS == 120
    assert [timeout for operation, timeout in backend.calls if operation == "ocr"] == [20] * 6 + [4]


@pytest.mark.parametrize("stage", ("language", "osd", "ocr"))
def test_near_expired_pdf_budget_bounds_every_native_command(monkeypatch, stage):
    clock = Clock()
    backend = TimedBackend(clock, "Rotate: 90\nOrientation confidence: 12.5\n")
    monkeypatch.setattr(extract, "monotonic", clock)
    monkeypatch.setattr(ocr, "monotonic", clock)
    monkeypatch.setattr(ocr, "_configured_backend", lambda: backend)
    original = extract._pdf_page_image
    def slow_render(page):
        clock.now = {"language": 119.5, "osd": 118.5, "ocr": 117.5}[stage]
        return original(page)
    monkeypatch.setattr(extract, "_pdf_page_image", slow_render)
    with pytest.raises(extract.ExtractionError, match="Tempo massimo OCR"):
        extract.extract_pdf(scanned_pdf())
    assert clock.now == 120
    assert backend.calls[-1] == (stage, 0.5)


@pytest.mark.parametrize("text", ("", "abc", "    "))
def test_all_scanned_pdf_rejects_insufficient_text_after_orientation(monkeypatch, text):
    class Backend:
        @staticmethod
        def get_languages(**kwargs):
            return ["ita"]
        @staticmethod
        def image_to_string(*args, **kwargs):
            return text
    monkeypatch.setattr(ocr, "_configured_backend", lambda: Backend())
    with pytest.raises(extract.NoTextFoundError, match="abbastanza testo"):
        extract.extract_pdf(scanned_pdf())


def test_textual_pdf_still_bypasses_ocr(monkeypatch):
    monkeypatch.setattr(ocr, "_configured_backend", lambda: pytest.fail("Digital PDF must bypass all OCR"))
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((30, 40), TEXT)
        result = extract.extract_pdf(pdf.tobytes())
    assert result.text == TEXT and result.method == "pdf_text"
    assert not result.used_ocr and result.ocr_pages == 0


def test_pdf_orientation_timeout_closes_rotations_and_native_temporaries(tmp_path, monkeypatch):
    images = []
    original_rotate = ocr._rotate_clockwise
    def track_rotation(image, angle):
        rotated = original_rotate(image, angle)
        images.append(rotated)
        return rotated
    backend = ocr._LocalTesseractBackend("local-test-command")
    monkeypatch.setattr(backend, "get_languages", lambda **kwargs: ["ita"])
    monkeypatch.setattr(backend, "image_to_osd", lambda *args, **kwargs: "")
    def timeout(*args, **kwargs):
        raise ocr.OCRTimeoutError(ocr.OCR_TIMEOUT_MESSAGE)
    monkeypatch.setattr(backend, "_run", timeout)
    monkeypatch.setattr(ocr, "_configured_backend", lambda: backend)
    monkeypatch.setattr(ocr, "_rotate_clockwise", track_rotation)
    monkeypatch.setattr(ocr, "TemporaryDirectory", lambda **kwargs: TemporaryDirectory(dir=tmp_path, **kwargs))
    with pytest.raises(extract.ExtractionError, match="Tempo massimo OCR"):
        extract.extract_pdf(scanned_pdf())
    assert len(images) == 4
    assert list(tmp_path.iterdir()) == []
    for image in images:
        with pytest.raises(ValueError, match="closed"):
            image.getpixel((0, 0))
