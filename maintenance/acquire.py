"""Explicit source census/collection. Output is staging, never the catalog."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from maintenance.fetch import Fetcher, AcquisitionError
from maintenance.parsers import parse, discover, merge_observations
from src.importers.inps import derive_search_endpoint


def collect(source, fetcher, *, max_pages=100):
    report = dict(source_key=source["key"], ente=source["ente"], started_at=datetime.now(UTC).isoformat(),
                  coverage_status="partial", pages=[], errors=[], excluded=[], observations=[],
                  discovered=None, importable=None, duplicates=0, new=0, updated=0)
    queue = list(source["urls"])
    seen = set()
    all_items = []
    inps_page = 1
    expected_total = None
    if source["key"] == "inps":
        queue = [derive_search_endpoint(source["urls"][0]) + "?" + urlencode(dict(maxItems=200, currentPage=1, lang="it"))]
    while queue and len(seen) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            receipt = fetcher.fetch(url, source["key"])
            raw = fetcher.read(receipt)
            info = asdict(receipt)
            report["pages"].append(info)
            items, excluded = parse(raw, source, info)
            all_items.extend(items)
            report["excluded"].extend(excluded)
            if source["key"] == "inps":
                payload = json.loads(raw)
                total = payload.get("totResult", payload.get("totalItems", payload.get("total", payload.get("totalResults"))))
                if isinstance(total, int):
                    if expected_total is not None and total != expected_total:
                        raise ValueError("Totale INPS cambiato durante il censimento: ripetere in nuova sessione.")
                    expected_total = total
                raw_items = payload["items"]
                if raw_items:
                    # Repeated pages are a structural error, not exhaustion.
                    signature = hashlib.sha256(json.dumps(raw_items, sort_keys=True).encode()).hexdigest()
                    if signature in report.setdefault("batch_hashes", []):
                        raise ValueError("Paginazione INPS ripetuta: raccolta non esaurita.")
                    report["batch_hashes"].append(signature)
                    inps_page += 1
                    received = sum(p.get("item_count", 0) for p in report["pages"]) + len(raw_items)
                    if expected_total is None or received < expected_total:
                        queue.append(derive_search_endpoint(source["urls"][0]) + "?" + urlencode(dict(maxItems=200, currentPage=inps_page, lang="it")))
                    elif received == expected_total:
                        report["exhausted"] = True
                    else:
                        raise ValueError("Conteggio INPS eccede il totale dichiarato.")
                    info["item_count"] = len(raw_items)
                else:
                    if expected_total is not None and sum(p.get("item_count",0) for p in report["pages"]) != expected_total:
                        raise ValueError("Paginazione INPS esaurita prima del totale dichiarato.")
                    report["exhausted"] = True
            else:
                queue.extend(u for u in discover(raw, source, receipt.final_url) if u not in seen and u not in queue)
        except (AcquisitionError, ValueError, KeyError, UnicodeError) as exc:
            report["errors"].append(dict(url=url, error=str(exc), status=getattr(exc, "status", None), attempts=getattr(exc, "attempts", None)))
            # Respect any block for this source; no alternate path or host.
            if getattr(exc, "status", None) in {403, 429}:
                break
    items, duplicates = merge_observations(all_items)
    report.update(observations=items, discovered=len(all_items) + len(report["excluded"]), importable=len(items), duplicates=duplicates,
                  pending_pages=len(queue), finished_at=datetime.now(UTC).isoformat(), declared_total=expected_total)
    if not queue and not report["errors"] and items:
        report["coverage_status"] = "complete_for_declared_collection"
    elif not items and report["errors"]:
        report["coverage_status"] = "blocked"
    elif not items:
        report["coverage_status"] = "manual"
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--allow-network", action="store_true")
    p.add_argument("--source", help="Comma-separated source keys; default all")
    p.add_argument("--max-pages", type=int, default=300)
    p.add_argument("--use-cache", action="store_true", help="Riusa ricevute con hash; mantiene la data originale")
    p.add_argument("--output", type=Path, default=ROOT / "maintenance/staging/collection.json")
    args = p.parse_args(argv)
    if not 1 <= args.max_pages <= 500:
        p.error("--max-pages deve essere tra 1 e 500")
    plan = json.loads((ROOT / "maintenance/sources.json").read_text(encoding="utf-8"))
    selected = set(args.source.split(",")) if args.source else {s["key"] for s in plan}
    if selected - {s["key"] for s in plan}:
        p.error("Fonte sconosciuta")
    if not args.allow_network:
        print(json.dumps({"dry_run": True, "sources": [s for s in plan if s["key"] in selected]}, ensure_ascii=False, indent=2))
        return 0
    fetcher = Fetcher(ROOT / "maintenance/cache", allow_network=True, use_cache=args.use_cache)
    reports = []
    for source in plan:
        if source["key"] not in selected:
            continue
        report = collect(source, fetcher, max_pages=args.max_pages)
        reports.append(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
        print(source["key"], report["coverage_status"], report["importable"], len(report["pages"]), report["errors"][:1], flush=True)
    return int(any(r["errors"] for r in reports))


if __name__ == "__main__":
    raise SystemExit(main())
