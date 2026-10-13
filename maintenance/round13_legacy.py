"""Deterministic maintenance derivation; never imported by the application."""
from contextlib import closing
import hashlib
from io import BytesIO
import pymupdf
from pypdf import PdfReader, PdfWriter

from maintenance.legacy_convert import convert_official, profile_xml
from src.fingerprint_v3 import page_record, sketch
from src.fingerprint_pages import image_signature
from src.extract import _pdf_page_image

METHOD = 'libreoffice-pdf-normalized-v1'
MIMES = {'.doc': 'application/msword', '.rtf': 'application/rtf', '.xls': 'application/vnd.ms-excel',
         '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.odt': 'application/vnd.oasis.opendocument.text'}


def normalize_pdf(raw):
    """Remove producer timestamps, XMP and trailer IDs, preserving page content."""
    with pymupdf.open(stream=raw, filetype='pdf') as pdf:
        pdf.set_metadata({})
        pdf.del_xml_metadata()
        pdf.xref_set_key(-1, 'ID', 'null')
        cleaned = pdf.tobytes(garbage=4, deflate=True, no_new_id=True)
    # LibreOffice also varies allocation order of font objects. Clone the
    # reachable page graph in page/resource order, rather than xref order.
    reader = PdfReader(BytesIO(cleaned))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def derive_twice(raw, suffix, work):
    first, a = convert_official(raw, suffix, work)
    second, b = convert_official(raw, suffix, work)
    first, second = normalize_pdf(first), normalize_pdf(second)
    if first != second:
        raise ValueError('normalized_legacy_conversion_not_reproducible')
    return first, dict(original_sha256=hashlib.sha256(raw).hexdigest(), derived_sha256=hashlib.sha256(first).hexdigest(),
                       raw_conversion_sha256=[a['derived_sha256'], b['derived_sha256']],
                       original_format=suffix, original_mime_type=MIMES[suffix], derived_mime_type='application/pdf',
                       conversion_method=METHOD, deterministic_conversion=True,
                       converter_sha256=a['converter_executable_sha256'], profile_sha256=hashlib.sha256(profile_xml().encode()).hexdigest(),
                       full_derived_pages=a['pages'], derived_size_bytes=len(first))


def fingerprint_pdf(raw):
    """First five pages, the unchanged runtime page-query bound; digital+layout."""
    pages = []
    with pymupdf.open(stream=raw, filetype='pdf') as pdf:
        for i in range(min(len(pdf), 5)):
            page = pdf[i]
            with closing(_pdf_page_image(page)) as image:
                visual = image_signature(image)
            pages.append(page_record(i + 1, page.get_text(), '', visual,
                                     ocr_status='not_requested_maintenance_digital_only'))
    return dict(pages=pages, field_set=[], aggregate=sketch({int(h, 16) for p in pages for h in p['digital']}, 192))
