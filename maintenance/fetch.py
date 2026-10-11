"""Bounded sequential HTTPS acquisition, opt-in, outside src and app."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import re
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from maintenance.policy import validate_url

USER_AGENT = "BurOCRazia-maintenance/0.7 (sequential official metadata; github.com/lucalullo/burocrazia)"
MAX_BYTES = 8 * 1024 * 1024
MAX_REQUESTS = 400
MAX_REDIRECTS = 5


class AcquisitionError(ValueError):
    def __init__(self, message, *, url=None, status=None, attempts=0):
        super().__init__(message)
        self.url, self.status, self.attempts = url, status, attempts


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Fetched:
    requested_url: str
    final_url: str
    acquired_at: str
    sha256: str
    content_type: str
    size: int
    status: int
    redirects: tuple[str, ...]
    attempts: int


class Fetcher:
    def __init__(self, cache: Path, *, allow_network=False, interval=1.0,
                 timeout=12, opener=None, sleeper=time.sleep, use_cache=False):
        self.cache, self.allow_network = Path(cache), allow_network
        if any(p.is_symlink() or p.is_junction() for p in [self.cache, *self.cache.parents]):
            raise AcquisitionError('Radice cache con collegamenti rifiutata.')
        self.interval, self.timeout = max(1.0, interval), min(30, max(1, timeout))
        self.opener = opener or build_opener(_NoRedirect())
        self.sleep = sleeper
        self.robots = {}
        self.blocked = set()
        self.requests = 0
        self.last_request = 0.0
        self.cached = {}
        if use_cache and self.cache.is_dir():
            for path in sorted(self.cache.glob("*.json")):
                if path.is_symlink() or path.stat().st_size > 32_000:
                    continue
                try:
                    item = Fetched(**json.loads(path.read_text(encoding="utf-8")))
                    self.cached[item.requested_url] = item
                except (ValueError, TypeError, OSError):
                    continue

    def _request(self, url, source_key, ipa_site, *, check_robots=True):
        chain = []
        attempts = 0
        for _ in range(MAX_REDIRECTS + 1):
            url = validate_url(url, source_key, ipa_site=ipa_site)
            host = urlsplit(url).netloc
            if host in self.blocked:
                raise AcquisitionError("Fonte già bloccata in questa sessione.", url=url)
            if check_robots:
                self._robots(url, source_key, ipa_site)
            for attempt in range(2):
                if self.requests >= MAX_REQUESTS:
                    raise AcquisitionError("Limite richieste della sessione raggiunto.", url=url)
                self.sleep(max(0, self.interval - (time.monotonic() - self.last_request)))
                self.requests += 1
                attempts += 1
                self.last_request = time.monotonic()
                try:
                    response = self.opener.open(Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json,application/pdf"}), timeout=self.timeout)
                except HTTPError as exc:
                    status = exc.code
                    location = exc.headers.get("Location")
                    exc.close()
                    if status in {301, 302, 303, 307, 308} and location:
                        url = validate_url(urljoin(url, location), source_key, ipa_site=ipa_site)
                        chain.append(url)
                        break
                    if status in {403, 429}:
                        self.blocked.add(host)
                    raise AcquisitionError(f"HTTP {status}; nessun aggiramento.", url=url, status=status, attempts=attempts) from exc
                except (URLError, TimeoutError, OSError) as exc:
                    if attempt == 0:
                        self.sleep(2)
                        continue
                    raise AcquisitionError(str(exc), url=url, attempts=attempts) from exc
                else:
                    with response:
                        final = validate_url(response.url, source_key, ipa_site=ipa_site)
                        raw = response.read(MAX_BYTES + 1)
                        if len(raw) > MAX_BYTES:
                            raise AcquisitionError("Risposta oltre 8 MiB.", url=url, attempts=attempts)
                        return raw, final, response.headers.get("Content-Type", ""), response.status, tuple(chain), attempts
            else:
                raise AcquisitionError("Richiesta non conclusa.", url=url, attempts=attempts)
        raise AcquisitionError("Troppi redirect.", url=url, attempts=attempts)

    def _robots(self, url, source_key, ipa_site):
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self.robots:
            try:
                raw, *_ = self._request(origin + "/robots.txt", source_key, ipa_site, check_robots=False)
            except AcquisitionError as exc:
                if exc.status not in {404, 410}:
                    raise
                raw = b""
            robot = RobotFileParser()
            robot.parse(raw.decode("utf-8", errors="replace").splitlines())
            delay = robot.crawl_delay(USER_AGENT) or robot.crawl_delay("*") or 1
            if delay > 60:
                raise AcquisitionError("robots richiede attesa oltre il limite della sessione.", url=url)
            self.interval = max(self.interval, delay)
            self.robots[origin] = robot
        if not self.robots[origin].can_fetch(USER_AGENT, url):
            raise AcquisitionError("robots: percorso non consentito.", url=url)

    def fetch(self, url, source_key, *, ipa_site=None) -> Fetched:
        url = validate_url(url, source_key, ipa_site=ipa_site)
        if url in self.cached:
            item = self.cached[url]
            validate_url(item.final_url, source_key, ipa_site=ipa_site)
            for redirected in item.redirects:
                validate_url(redirected, source_key, ipa_site=ipa_site)
            self.read(item)
            return item
        if not self.allow_network:
            raise AcquisitionError("Rete disabilitata: serve --allow-network.", url=url)
        raw, final, mime, status, chain, attempts = self._request(url, source_key, ipa_site)
        item = Fetched(url, final, datetime.now(UTC).isoformat(), hashlib.sha256(raw).hexdigest(), mime, len(raw), status, chain, attempts)
        self.cache.mkdir(parents=True, exist_ok=True)
        body, receipt = self.cache / (item.sha256 + ".body"), self.cache / (item.sha256 + ".json")
        if body.is_symlink() or receipt.is_symlink():
            raise AcquisitionError("Cache con collegamento simbolico rifiutata.")
        body.write_bytes(raw)
        receipt.write_text(json.dumps(asdict(item), ensure_ascii=False, indent=2), encoding="utf-8")
        return item

    def read(self, item: Fetched) -> bytes:
        if not isinstance(item.sha256,str) or not re.fullmatch(r"[a-f0-9]{64}", item.sha256) or type(item.size) is not int or not 0 <= item.size <= MAX_BYTES:
            raise AcquisitionError("Ricevuta cache non valida.")
        path = self.cache / (item.sha256 + ".body")
        if path.is_symlink() or path.stat().st_size > MAX_BYTES:
            raise AcquisitionError("Cache non valida.")
        raw = path.read_bytes()
        if len(raw) != item.size or hashlib.sha256(raw).hexdigest() != item.sha256:
            raise AcquisitionError("Hash della cache non corrispondente.")
        return raw
