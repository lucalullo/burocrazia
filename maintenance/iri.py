"""IRI to ASCII URI conversion before the unchanged institutional URL policy."""
from __future__ import annotations
import re
from urllib.parse import quote, urlsplit, urlunsplit


def iri_to_uri(value: str) -> str:
    if not isinstance(value,str) or not value or len(value)>16_384 or '\\' in value or any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError('IRI non valida.')
    p=urlsplit(value)
    if p.scheme!='https' or not p.hostname or p.username is not None or p.password is not None:
        raise ValueError('IRI HTTPS senza credenziali richiesta.')
    if any(c.isspace() for c in p.hostname) or '%' in p.hostname:
        raise ValueError('Host IRI non valido.')
    host=p.hostname.encode('idna').decode('ascii').lower().rstrip('.')
    if ':' in host:host='['+host+']'
    port=p.port
    authority=host+(f':{port}' if port is not None else '')
    def encode(part,safe):
        # Keep valid escapes exactly once, including their original case.
        part=re.sub(r'%(?![0-9A-Fa-f]{2})','%25',part)
        return quote(part,safe=safe+'%',encoding='utf-8',errors='strict')
    return urlunsplit(('https',authority,encode(p.path or '/',"/:@!$&'()*+,;=-._~"),
                       encode(p.query,"/?@:!$&'()*+,;=-._~"),encode(p.fragment,"/?@:!$&'()*+,;=-._~")))
