"""Institutional URL policy; no I/O, discovery never grants trust."""
from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit, urlunsplit

from src.official_urls import OFFICIAL_DOMAIN_ALLOWLIST

# Additions have institutional evidence recorded in docs/SOURCES.md.
DOMAINS = {
    **OFFICIAL_DOMAIN_ALLOWLIST,
    "aci": ("aci.it", "aci.gov.it", "t-acigov.serviziaci.it"),
    "interno": ("interno.gov.it",),
    "giustizia": ("giustizia.it",),
    "salute": ("salute.gov.it",),
    "mimit": ("mimit.gov.it",),
    "mit": ("mit.gov.it", "ilportaledellautomobilista.it"),
    "adm": ("adm.gov.it",),
    "mef": ("mef.gov.it",),
    "anac": ("anticorruzione.it",),
    "agid": ("agid.gov.it",),
    "polizia": ("poliziadistato.it",),
    "unioncamere": ("unioncamere.gov.it",),
    "registro_imprese": ("registroimprese.it",),
}


def canonical_url(url: str) -> str:
    try:
        p = urlsplit(url)
        host = (p.hostname or "").lower().rstrip(".")
        if (p.scheme != "https" or not host or p.username is not None
                or p.password is not None or p.port not in (None, 443)
                or any(c.isspace() or ord(c) < 32 for c in url) or "\\" in url):
            raise ValueError("URL HTTPS istituzionale non valida.")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("Indirizzi IP non ammessi come fonti.")
        return urlunsplit(("https", host, p.path or "/", p.query, ""))
    except (ValueError, AttributeError) as exc:
        raise ValueError("URL HTTPS istituzionale non valida.") from exc


def validate_url(url: str, source_key: str, *, ipa_site: str | None = None) -> str:
    canonical = canonical_url(url)
    if source_key == "ipa_territorial":
        if not ipa_site:
            raise ValueError("Il dominio territoriale richiede il sito IPA.")
        site = urlsplit(ipa_site)
        if site.scheme not in {"http", "https"} or site.username or site.password:
            raise ValueError("Sito IPA non valido.")
        domain = (site.hostname or "").lower().rstrip(".").removeprefix("www.")
        if "." not in domain:
            raise ValueError("Sito IPA non valido.")
        domains = (domain,)
    else:
        domains = DOMAINS.get(source_key, ())
    host = urlsplit(canonical).hostname
    if not any(host == d or host.endswith("." + d) for d in domains):
        raise ValueError("Dominio fuori dalla policy istituzionale della fonte.")
    return canonical
