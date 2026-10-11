"""Deterministic extraction diagnostics; no text is persisted or cached."""
from __future__ import annotations
import re
import unicodedata


def text_quality(text: str) -> dict:
    tokens = re.findall(r"\w+", text, flags=re.UNICODE)
    visible = [c for c in text if not c.isspace()]
    printable = sum(c.isprintable() and unicodedata.category(c) not in {'Co', 'Cn'} and c != '\ufffd' for c in visible)
    printable_ratio = printable / len(visible) if visible else 0.0
    singles = sum(len(t) == 1 for t in tokens) / len(tokens) if tokens else 0.0
    # Only explicit corruption triggers OCR on a nonempty digital layer.
    unusable = bool(visible) and (printable_ratio < .8 or (len(tokens) >= 40 and singles > .85))
    return dict(extracted_chars=len(text), token_count=len(tokens), printable_ratio=round(printable_ratio, 6),
                text_order_quality='fragmented_tokens' if len(tokens) >= 40 and singles > .85 else 'not_measurable',
                usable=bool(tokens) and not unusable,
                extraction_warning='Unusable digital text layer' if unusable else None)
