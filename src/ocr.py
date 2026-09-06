from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from io import BytesIO
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

try:  # The import remains optional so a missing local component is user-friendly.
    import pytesseract
except ImportError:  # pragma: no cover - depends on the local installation
    pytesseract = None  # type: ignore[assignment]


MAX_OCR_PAGES = 5
MIN_OCR_TEXT_LENGTH = 20
MAX_OCR_IMAGE_PIXELS = 16_000_000
MAX_INPUT_IMAGE_PIXELS = 50_000_000
TESSERACT_COMMAND_ENV = "BUROCRAZIA_TESSERACT_CMD"
ORIENTATION_ANGLES = (0, 90, 180, 270)
MIN_OSD_CONFIDENCE = 5.0
OCR_TIMEOUT_SECONDS = 20
OCR_TOTAL_TIMEOUT_SECONDS = 60
OCR_PROBE_TIMEOUT_SECONDS = 5
MAX_OCR_TEXT_CHARS = 1_000_000
MAX_OCR_OUTPUT_BYTES = 4 * MAX_OCR_TEXT_CHARS
MAX_INPUT_IMAGE_BYTES = 20 * 1024 * 1024
OCR_TIMEOUT_MESSAGE = "Tempo massimo OCR superato. Prova con un’immagine più piccola o un documento più breve."

OCR_UNAVAILABLE_MESSAGE = (
    "Il riconoscimento delle immagini richiede il componente OCR locale "
    "Tesseract, che non risulta installato o configurato."
)
OCR_INSUFFICIENT_TEXT_MESSAGE = (
    "Non sono riuscito a leggere abbastanza testo da questa immagine. "
    "Prova a scattare una foto più nitida, ben illuminata e senza tagliare "
    "il documento."
)
INVALID_IMAGE_MESSAGE = "L'immagine non è valida o non può essere letta."
IMAGE_TOO_LARGE_MESSAGE = (
    "L'immagine è troppo grande per essere elaborata in modo sicuro. "
    "Prova a ridurne la risoluzione e caricala di nuovo."
)
OCR_LANGUAGE_MISSING_MESSAGE = (
    "Tesseract non dispone dei pacchetti lingua italiano o inglese necessari "
    "per leggere il documento."
)
OCR_ENGLISH_FALLBACK_WARNING = (
    "Il pacchetto lingua italiano di Tesseract non è disponibile: il testo "
    "è stato letto usando il pacchetto inglese."
)


class OCRError(ValueError):
    """Base error for safe, local OCR failures."""


class OCRTimeoutError(OCRError):
    """The bounded local OCR operation exceeded its deadline."""


class OCRUnavailableError(OCRError):
    """Raised when pytesseract or the Tesseract executable is unavailable."""


class InvalidImageError(OCRError):
    """Raised when uploaded bytes are not a readable image."""


class ImageTooLargeError(OCRError):
    """Raised before decoding an image that is unreasonably large."""


class OCRLanguageError(OCRError):
    """Raised when neither the Italian nor English language pack is present."""


class InsufficientOCRTextError(OCRError):
    """Raised when OCR output is too short to feed the recognizer safely."""


@dataclass(frozen=True)
class OCRResult:
    text: str
    language: str
    warning: str | None = None
    rotation: int = 0


def _remaining_timeout(deadline: float, maximum: float) -> float:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise OCRTimeoutError(OCR_TIMEOUT_MESSAGE)
    return min(maximum, remaining)


def normalize_ocr_text(text: str) -> str:
    """Normalize layout noise without guessing or correcting OCR words."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in normalized.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def validate_ocr_text(
    text: str,
    *,
    min_text_length: int = MIN_OCR_TEXT_LENGTH,
) -> str:
    if len(text) > MAX_OCR_TEXT_CHARS:
        raise OCRError("Il testo OCR supera il limite di 1.000.000 di caratteri.")
    normalized = normalize_ocr_text(text)
    readable_characters = sum(character.isalnum() for character in normalized)
    if readable_characters < min_text_length:
        raise InsufficientOCRTextError(OCR_INSUFFICIENT_TEXT_MESSAGE)
    return normalized


def load_image(content: bytes) -> Image.Image:
    """Decode and EXIF-orient an image entirely in memory."""
    if not content:
        raise InvalidImageError(INVALID_IMAGE_MESSAGE)
    if len(content) > MAX_INPUT_IMAGE_BYTES:
        raise ImageTooLargeError(IMAGE_TOO_LARGE_MESSAGE)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as opened:
                if opened.format not in {"JPEG", "PNG"}:
                    raise InvalidImageError(INVALID_IMAGE_MESSAGE)
                width, height = opened.size
                if width <= 0 or height <= 0:
                    raise InvalidImageError(INVALID_IMAGE_MESSAGE)
                if width * height > MAX_INPUT_IMAGE_PIXELS:
                    raise ImageTooLargeError(IMAGE_TOO_LARGE_MESSAGE)
                opened.load()
                return ImageOps.exif_transpose(opened)
    except (ImageTooLargeError, InvalidImageError):
        raise
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise InvalidImageError(INVALID_IMAGE_MESSAGE) from exc


def prepare_image(image: Image.Image) -> Image.Image:
    """Apply conservative preprocessing within explicit pixel limits."""
    pixels = image.width * image.height
    if pixels <= 0 or pixels > MAX_INPUT_IMAGE_PIXELS:
        raise ImageTooLargeError(IMAGE_TOO_LARGE_MESSAGE)
    oriented = grayscale = None
    try:
        oriented = ImageOps.exif_transpose(image)
        grayscale = ImageOps.grayscale(oriented)
        processed = ImageOps.autocontrast(grayscale, cutoff=1)
        if pixels > MAX_OCR_IMAGE_PIXELS:
            scale = (MAX_OCR_IMAGE_PIXELS / pixels) ** 0.5
            resized = processed.resize((max(1, int(processed.width * scale)), max(1, int(processed.height * scale))), Image.Resampling.LANCZOS)
            processed.close()
            processed = resized
        return processed
    except (OSError, ValueError) as exc:
        raise InvalidImageError(INVALID_IMAGE_MESSAGE) from exc
    finally:
        if grayscale is not None:
            grayscale.close()
        if oriented is not None and oriented is not image:
            oriented.close()


class _LocalTesseractBackend:
    """Bound every native command and confine input/output to one private directory.

    pytesseract's language probe has no timeout. Its configured executable is
    retained, while the command boundary uses subprocess for uniform deadlines.
    """
    def __init__(self, command: str):
        self.command = command
        self.last_confidence: float | None = None

    def _run(self, args: list[str], *, timeout: float, cwd: str | None = None) -> str:
        try:
            result = subprocess.run([self.command, *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout, check=False, cwd=cwd)
        except subprocess.TimeoutExpired as exc:
            raise OCRTimeoutError(OCR_TIMEOUT_MESSAGE) from exc
        except OSError as exc:
            raise OCRUnavailableError(OCR_UNAVAILABLE_MESSAGE) from exc
        if result.returncode:
            raise OCRError("Il componente OCR locale non riesce a elaborare questa immagine.")
        if len(result.stdout) > MAX_OCR_OUTPUT_BYTES:
            raise OCRError("Il testo OCR supera il limite consentito.")
        return result.stdout.decode("utf-8", errors="replace")

    def get_languages(self, config: str = "", *, timeout: float = OCR_PROBE_TIMEOUT_SECONDS) -> list[str]:
        return [line.strip() for line in self._run(["--list-langs"], timeout=timeout).splitlines() if re.fullmatch(r"[a-zA-Z_+-]+", line.strip())]

    def _read_image(self, image: Image.Image, *, lang: str, timeout: float, osd: bool = False) -> str:
        # TemporaryDirectory uses restrictive permissions and removes all files in
        # its finally path, including failures, timeouts and KeyboardInterrupt.
        deadline = monotonic() + timeout
        with TemporaryDirectory(prefix="burocrazia-ocr-") as temporary:
            input_path = Path(temporary) / "input.png"
            output_path = Path(temporary) / "result"
            image.save(input_path, format="PNG")
            args = [str(input_path), str(output_path), "-l", lang]
            args.extend(["--psm", "0"] if osd else ["txt", "tsv"])
            self._run(args, timeout=_remaining_timeout(deadline, timeout), cwd=temporary)
            result_path = output_path.with_suffix(".osd" if osd else ".txt")
            try:
                if result_path.stat().st_size > MAX_OCR_OUTPUT_BYTES:
                    raise OCRError("Il testo OCR supera il limite consentito.")
                text = result_path.read_text(encoding="utf-8", errors="replace")
                if not osd:
                    tsv_path = output_path.with_suffix(".tsv")
                    if tsv_path.stat().st_size > MAX_OCR_OUTPUT_BYTES:
                        raise OCRError("I dati OCR superano il limite consentito.")
                    weighted_confidence = weight = 0.0
                    for row in tsv_path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
                        fields = row.split("\t", 11)
                        if len(fields) != 12 or not fields[11].strip():
                            continue
                        try:
                            confidence = float(fields[10])
                        except ValueError:
                            continue
                        if 0 <= confidence <= 100:
                            word_weight = len(fields[11].strip())
                            weighted_confidence += confidence * word_weight
                            weight += word_weight
                    self.last_confidence = weighted_confidence / max(1.0, weight)
                return text
            except OSError as exc:
                raise OCRError("Il componente OCR locale non ha prodotto testo leggibile.") from exc

    def image_to_string(self, image: Image.Image, *, lang: str, timeout: float) -> str:
        return self._read_image(image, lang=lang, timeout=timeout)

    def image_to_osd(self, image: Image.Image, *, timeout: float) -> str:
        return self._read_image(image, lang="osd", timeout=timeout, osd=True)


def _configured_backend():
    if pytesseract is None:
        raise OCRUnavailableError(OCR_UNAVAILABLE_MESSAGE)
    command = os.getenv(TESSERACT_COMMAND_ENV) or pytesseract.pytesseract.tesseract_cmd
    return _LocalTesseractBackend(command)


def select_ocr_language(*, deadline: float | None = None) -> tuple[str, str | None]:
    backend = _configured_backend()
    deadline = monotonic() + OCR_PROBE_TIMEOUT_SECONDS if deadline is None else deadline
    try:
        available = {language.casefold() for language in backend.get_languages(config="", timeout=_remaining_timeout(deadline, OCR_PROBE_TIMEOUT_SECONDS))}
    except OCRTimeoutError:
        raise
    except Exception as exc:  # backend-specific failures become safe messages
        raise OCRUnavailableError(OCR_UNAVAILABLE_MESSAGE) from exc

    if "ita" in available and "eng" in available:
        return "ita+eng", None
    if "ita" in available:
        return "ita", None
    if "eng" in available:
        return "eng", OCR_ENGLISH_FALLBACK_WARNING
    raise OCRLanguageError(OCR_LANGUAGE_MISSING_MESSAGE)


def _orientation_from_osd(backend, image: Image.Image, *, deadline: float) -> int | None:
    try:
        osd = backend.image_to_osd(image, timeout=_remaining_timeout(deadline, OCR_PROBE_TIMEOUT_SECONDS))
    except OCRTimeoutError:
        raise
    except Exception:
        return None

    rotation_match = re.search(r"(?im)^\s*rotate\s*:\s*(\d+)\s*$", osd)
    confidence_match = re.search(
        r"(?im)^\s*orientation confidence\s*:\s*([\d.]+)\s*$", osd
    )
    if rotation_match is None or confidence_match is None:
        return None
    try:
        rotation = int(rotation_match.group(1)) % 360
        confidence = float(confidence_match.group(1))
    except ValueError:
        return None
    if rotation not in ORIENTATION_ANGLES or confidence < MIN_OSD_CONFIDENCE:
        return None
    return rotation


def _rotate_clockwise(image: Image.Image, angle: int) -> Image.Image:
    if angle == 0:
        return image
    return image.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)


def _ocr_text_quality(text: str) -> tuple[int, int, int]:
    """Rank OCR alternatives by deterministic readable-text evidence."""
    normalized = normalize_ocr_text(text)
    words = re.findall(r"\b\w{2,}\b", normalized, flags=re.UNICODE)
    alphanumeric = sum(character.isalnum() for character in normalized)
    non_space = sum(not character.isspace() for character in normalized)
    readable_ratio = round(1000 * alphanumeric / max(1, non_space))
    return len(words), alphanumeric, readable_ratio


def _orientation_candidates(
    backend,
    prepared: Image.Image,
    *,
    auto_orient: bool,
    deadline: float,
) -> tuple[tuple[int, Image.Image], ...]:
    if not auto_orient:
        return ((0, prepared),)

    osd_rotation = _orientation_from_osd(backend, prepared, deadline=deadline)
    if osd_rotation == 0:
        angles = (0,)
    elif osd_rotation is not None:
        angles = (osd_rotation, 0)
    else:
        angles = ORIENTATION_ANGLES
    return tuple((angle, _rotate_clockwise(prepared, angle)) for angle in angles)


def ocr_image(
    image: Image.Image,
    *,
    min_text_length: int = MIN_OCR_TEXT_LENGTH,
    auto_orient: bool = False,
    deadline: float | None = None,
) -> OCRResult:
    """Read locally within the image budget and any parent extraction deadline."""
    started = monotonic()
    deadline = min(started + OCR_TOTAL_TIMEOUT_SECONDS, deadline) if deadline is not None else started + OCR_TOTAL_TIMEOUT_SECONDS
    backend = _configured_backend()
    language, warning = select_ocr_language(deadline=deadline)
    with closing(prepare_image(image)) as prepared:
        candidates = _orientation_candidates(backend, prepared, auto_orient=auto_orient, deadline=deadline)
        alternatives: list[tuple[int, str, float | None]] = []
        try:
            for angle, candidate in candidates:
                raw_text = backend.image_to_string(candidate, lang=language, timeout=_remaining_timeout(deadline, OCR_TIMEOUT_SECONDS))
                if len(raw_text) > MAX_OCR_TEXT_CHARS:
                    raise OCRError("Il testo OCR supera il limite di 1.000.000 di caratteri.")
                alternatives.append((angle, raw_text, getattr(backend, "last_confidence", None)))
        except OCRError:
            raise
        except Exception as exc:
            raise OCRUnavailableError(OCR_UNAVAILABLE_MESSAGE) from exc
        finally:
            for _, candidate in candidates:
                if candidate is not prepared:
                    candidate.close()
    rotation, raw_text, _confidence = max(alternatives, key=lambda item: (item[2] if item[2] is not None else -1, _ocr_text_quality(item[1])))
    text = validate_ocr_text(raw_text, min_text_length=min_text_length)
    _remaining_timeout(deadline, OCR_TIMEOUT_SECONDS)
    return OCRResult(text=text, language=language, warning=warning, rotation=rotation)


def ocr_image_bytes(
    content: bytes,
    *,
    min_text_length: int = MIN_OCR_TEXT_LENGTH,
) -> OCRResult:
    with load_image(content) as image:
        return ocr_image(image, min_text_length=min_text_length, auto_orient=True)
