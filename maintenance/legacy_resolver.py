"""Maintenance-only legacy format capability probe, no execution or runtime import.

No conversion is claimed without a local isolated converter and inspected output.
OLE magic cannot distinguish Word from Excel reliably; extensions are hints only.
"""
import shutil

def inspect_legacy(raw):
    if len(raw)>20*1024*1024:raise ValueError('Legacy resource exceeds byte limit')
    kind='rtf' if raw.lstrip().startswith(b'{\\rtf') else 'ole_compound_doc_or_xls' if raw.startswith(b'\xd0\xcf\x11\xe0') else 'not_legacy'
    converter=shutil.which('soffice') or shutil.which('libreoffice')
    return dict(format=kind,converter_available=bool(converter),conversion_performed=False,reason='not_legacy' if kind=='not_legacy' else 'unsupported_no_local_converter' if not converter else 'requires_isolated_converter_validation')
