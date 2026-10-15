from __future__ import annotations

from urllib.parse import urlsplit


OFFICIAL_DOMAIN_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "ipa": ("indicepa.gov.it",),
    "inps": ("inps.it",),
    "ader": ("agenziaentrateriscossione.gov.it",),
    "inail": ("inail.it",),
    "ade": ("agenziaentrate.gov.it",),
    "lavoro": ("lavoro.gov.it",),
    "inl": ("ispettorato.gov.it",),
    "mit": ("mit.gov.it",),
    "funzione_pubblica": ("funzionepubblica.gov.it",),
    "aci": ("aci.it", "aci.gov.it", "t-acigov.serviziaci.it"),
    "garante_privacy": ("garanteprivacy.it",),
    "interno": ("interno.gov.it",),
    "giustizia": ("giustizia.it",),
    "salute": ("salute.gov.it",),
    "mimit": ("mimit.gov.it",),
    "mef": ("mef.gov.it",),
    "anac": ("anticorruzione.it",),
    "agid": ("agid.gov.it",),
    "unioncamere": ("unioncamere.gov.it",),
    "polizia": ("poliziadistato.it",),
}

SOURCE_KEY_BY_ENTITY = {
    "indice delle pubbliche amministrazioni (ipa)": "ipa",
    "inps": "inps",
    "inail": "inail",
    "agenzia delle entrate-riscossione": "ader",
    "agenzia delle entrate": "ade",
    "ministero del lavoro": "lavoro",
    "ispettorato nazionale del lavoro": "inl",
    "ministero delle infrastrutture e dei trasporti": "mit",
    "dipartimento della funzione pubblica": "funzione_pubblica",
    "aci / pra": "aci",
    "garante per la protezione dei dati personali": "garante_privacy",
    "ministero dell'interno": "interno",
    "ministero della giustizia": "giustizia",
    "tribunale di venezia": "giustizia",
    "ministero della salute": "salute",
    "ministero delle imprese e del made in italy": "mimit",
    "ministero dell'economia e delle finanze / rgs": "mef",
    "autorità nazionale anticorruzione": "anac",
    "agenzia per l'italia digitale": "agid",
    "unioncamere": "unioncamere",
    "polizia di stato": "polizia",
}


def is_official_url(url: str | None, source_key: str) -> bool:
    if not url or source_key not in OFFICIAL_DOMAIN_ALLOWLIST:
        return False
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    hostname = (parsed.hostname or "").casefold().rstrip(".")
    allowed_domains = OFFICIAL_DOMAIN_ALLOWLIST[source_key]
    domain_allowed = any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in allowed_domains
    )
    return (
        parsed.scheme.casefold() == "https"
        and bool(hostname)
        and domain_allowed
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
    )


def is_official_entity_url(url: str | None, entity: str) -> bool:
    source_key = SOURCE_KEY_BY_ENTITY.get(entity.casefold().strip())
    return bool(source_key) and is_official_url(url, source_key)


def is_official_inps_url(url: str | None) -> bool:
    return is_official_url(url, "inps")


def is_official_ader_url(url: str | None) -> bool:
    return is_official_url(url, "ader")


def is_official_ipa_url(url: str | None) -> bool:
    return is_official_url(url, "ipa")


def is_official_inail_url(url: str | None) -> bool:
    return is_official_url(url, "inail")


def is_official_ade_url(url: str | None) -> bool:
    return is_official_url(url, "ade")


def is_official_lavoro_url(url: str | None) -> bool:
    return is_official_url(url, "lavoro")


def is_official_inl_url(url: str | None) -> bool:
    return is_official_url(url, "inl")


def is_official_garante_url(url: str | None) -> bool:
    return is_official_url(url, "garante_privacy")
