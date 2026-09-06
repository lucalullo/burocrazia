from __future__ import annotations

import json
from pathlib import Path

from src.database import connect_database, initialize_database


PLAN = Path(__file__).parents[1] / "data" / "acquisition_plan.json"


def test_acquisition_plan_covers_every_registered_source(tmp_path) -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    db_path = tmp_path / "sources.db"
    initialize_database(db_path, seed_demo=True)
    with connect_database(db_path) as connection:
        sources = {
            int(row["id"]): str(row["ente"])
            for row in connection.execute("SELECT id, ente FROM sources").fetchall()
        }

    assert len(plan) == len(sources) == 15
    assert {item["ente"] for item in plan} == set(sources.values())
    assert len({item["source_id"] for item in plan}) == 15
    assert all(isinstance(item["source_id"], int) and item["source_id"] > 0 for item in plan)
    assert all(
        {
            "ente",
            "source_id",
            "classificazione",
            "metodo",
            "priorità",
            "stato",
            "note",
            "importatore_esistente",
        }
        <= item.keys()
        for item in plan
    )


def test_acquisition_plan_uses_only_controlled_methods_and_states() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    allowed_methods = {
        "api",
        "xlsx",
        "csv",
        "pagina_html",
        "pagina_html_manuale",
        "da_studiare",
    }
    allowed_classes = {"FACILE", "MEDIO", "MANUALE", "BLOCCATO"}

    assert {item["metodo"] for item in plan} <= allowed_methods
    assert {item["classificazione"] for item in plan} <= allowed_classes
    ader = next(
        item for item in plan if item["ente"] == "Agenzia delle Entrate-Riscossione"
    )
    assert ader["classificazione"] == "BLOCCATO"
    assert ader["metodo"] == "pagina_html_manuale"
    assert ader["importatore_esistente"] is True
