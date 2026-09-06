"""Regressioni A05: materiali isolati per catalogo, senza migrare i file v0.6.0."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from src.database import connect_database, create_schema
from src.local_packages import PackageValidationError, _database_fingerprint, _storage_key, import_local_package
from src.local_resources import RESOURCE_ROOT_KEY, list_local_resources, read_resource_text, resolve_resource_root
from src.review import submit_resource_review
from test_local_packages import write_package


@pytest.mark.parametrize("explicit_root", [True, False])
def test_same_package_is_readable_in_two_databases_with_shared_base(tmp_path, monkeypatch, explicit_root):
    package, root = write_package(tmp_path / "demo.zip"), tmp_path / "shared-resources"
    monkeypatch.setattr("src.local_resources.DEFAULT_RESOURCE_ROOT", root)
    selected_root = root if explicit_root else None
    connections = [connect_database(tmp_path / name) for name in ("first.db", "second.db")]
    try:
        paths = []
        for connection in connections:
            create_schema(connection)
            before = list(connection.iterdump())
            preview = import_local_package(connection, package, selected_root)
            assert list(connection.iterdump()) == before
            applied = import_local_package(connection, package, selected_root, dry_run=False, expected_sha256=preview.sha256)
            resource = list_local_resources(connection)[0]
            assert applied.applied and "SINTETICO" in read_resource_text(resource, root)
            paths.append(resource.relative_path)
        assert paths[0] != paths[1]
        for connection in connections:
            assert "SINTETICO" in read_resource_text(list_local_resources(connection)[0], root)
            repeated = import_local_package(connection, package, selected_root, dry_run=False, expected_sha256=preview.sha256)
            assert repeated.already_imported and not repeated.applied
            assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
            assert not connection.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        for connection in connections:
            connection.close()


def _import(connection, package, root=None):
    preview = import_local_package(connection, package, root)
    return import_local_package(connection, package, root, dry_run=False, expected_sha256=preview.sha256)


def _files(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_custom_root_persists_across_reopen_and_cli_without_repeating_option(tmp_path, monkeypatch):
    db_path, root = tmp_path / "catalog.db", tmp_path / "custom-materials"
    package = write_package(tmp_path / "demo.zip")
    with connect_database(db_path) as connection:
        create_schema(connection)
        report = _import(connection, package, root)
        original_path = list_local_resources(connection)[0].relative_path
    monkeypatch.setattr("src.local_resources.DEFAULT_RESOURCE_ROOT", tmp_path / "unrelated-default")
    with connect_database(db_path) as connection:
        resource = list_local_resources(connection)[0]
        assert resolve_resource_root(connection) == root
        assert resource.relative_path == original_path
        assert "SINTETICO" in read_resource_text(resource, connection=connection)
        assert _import(connection, package).already_imported
    result = subprocess.run([sys.executable, "scripts/import_package.py", str(package), "--db", str(db_path), "--commit", "--expected-sha256", report.sha256], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert '"already_imported": true' in result.stdout
    assert not (tmp_path / "unrelated-default").exists()


@pytest.mark.parametrize("failure_mode", ["database", "filesystem"])
def test_failed_second_database_import_cannot_touch_first_database_files(tmp_path, monkeypatch, failure_mode):
    package, root = write_package(tmp_path / "demo.zip"), tmp_path / "shared"
    with connect_database(tmp_path / "first.db") as first, connect_database(tmp_path / "second.db") as second:
        create_schema(first)
        create_schema(second)
        _import(first, package, root)
        first_dump, first_files = list(first.iterdump()), _files(root)
        if failure_mode == "database":
            second.execute("CREATE TRIGGER fail_package BEFORE INSERT ON package_imports BEGIN SELECT RAISE(ABORT, 'forced second catalog failure'); END")
            second.commit()
        else:
            monkeypatch.setattr("src.local_packages.os.replace", lambda *_: (_ for _ in ()).throw(OSError("forced second catalog failure")))
        with pytest.raises(PackageValidationError, match="forced second catalog failure"):
            _import(second, package, root)
        assert list(first.iterdump()) == first_dump and _files(root) == first_files
        assert "SINTETICO" in read_resource_text(list_local_resources(first)[0], connection=first)
        for table in ("documents", "document_provenance", "local_resources", "package_imports"):
            assert second.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert second.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_metadata'").fetchone() is None
        assert second.execute("SELECT status FROM package_import_attempts").fetchone()[0] == "rejected"


def test_changing_registered_root_is_rejected_in_preview_and_commit(tmp_path):
    package, root = write_package(tmp_path / "demo.zip"), tmp_path / "materials"
    with connect_database(tmp_path / "catalog.db") as connection:
        create_schema(connection)
        imported = _import(connection, package, root)
        before, files = list(connection.iterdump()), _files(root)
        other = tmp_path / "wrong-materials"
        with pytest.raises(PackageValidationError, match="altra cartella"):
            import_local_package(connection, package, other)
        assert list(connection.iterdump()) == before
        with pytest.raises(PackageValidationError, match="altra cartella"):
            import_local_package(connection, package, other, dry_run=False, expected_sha256=imported.sha256)
        assert resolve_resource_root(connection) == root and _files(root) == files and not other.exists()


def test_legacy_digest_paths_are_readable_and_adopted_without_moving_or_rewriting(tmp_path, monkeypatch):
    package, root = write_package(tmp_path / "demo.zip"), tmp_path / "legacy-materials"
    db_path = tmp_path / "catalog.db"
    with connect_database(db_path) as connection:
        create_schema(connection)
        report = _import(connection, package, root)
        current = list_local_resources(connection)[0]
        # Ricrea esclusivamente nel database temporaneo il layout realmente usato da v0.6.0.
        (root / current.relative_path.split("/")[0]).rename(root / report.sha256)
        legacy_path = report.sha256 + "/resources/demo.txt"
        connection.execute("UPDATE local_resources SET relative_path = ?", (legacy_path,))
        connection.execute("DELETE FROM catalog_metadata WHERE key = ?", (RESOURCE_ROOT_KEY,))
        connection.commit()
        before_files = _files(root)
        legacy_row = tuple(connection.execute("SELECT * FROM local_resources").fetchone())
        monkeypatch.setattr("src.local_resources.DEFAULT_RESOURCE_ROOT", root)
        assert "SINTETICO" in read_resource_text(list_local_resources(connection)[0], connection=connection)
        assert _import(connection, package, root).already_imported
        assert tuple(connection.execute("SELECT * FROM local_resources").fetchone()) == legacy_row
        assert _files(root) == before_files
    with connect_database(db_path) as connection:
        assert resolve_resource_root(connection) == root
        assert "SINTETICO" in read_resource_text(list_local_resources(connection)[0], connection=connection)


def test_legacy_root_is_not_adopted_when_registered_materials_are_missing(tmp_path):
    package, root = write_package(tmp_path / "demo.zip"), tmp_path / "legacy-materials"
    with connect_database(tmp_path / "catalog.db") as connection:
        create_schema(connection)
        _import(connection, package, root)
        connection.execute("DELETE FROM catalog_metadata WHERE key = ?", (RESOURCE_ROOT_KEY,))
        connection.commit()
        files = _files(root)
        with pytest.raises(PackageValidationError, match="assente"):
            _import(connection, package, tmp_path / "incorrect-legacy-root")
        assert connection.execute("SELECT value FROM catalog_metadata WHERE key = ?", (RESOURCE_ROOT_KEY,)).fetchone() is None
        assert _files(root) == files


def test_new_namespace_orphans_recovered_and_foreign_owned_folder_preserved(tmp_path):
    package, root = write_package(tmp_path / "demo.zip"), tmp_path / "shared"
    with connect_database(tmp_path / "catalog.db") as connection:
        create_schema(connection)
        preview = import_local_package(connection, package, root)
        orphan = root / _storage_key(connection, preview.sha256)
        orphan.mkdir(parents=True)
        marker = orphan / ".burocrazia-package"
        marker.write_text(json.dumps({"sha256": preview.sha256, "database": "different-owner"}))
        (orphan / "unfinished").write_text("owned by another database")
        before = _files(root)
        with pytest.raises(PackageValidationError, match="Cartella del pacchetto già presente"):
            _import(connection, package, root)
        assert _files(root) == before
        marker.write_text(json.dumps({"sha256": preview.sha256, "database": _database_fingerprint(connection)}))
        assert _import(connection, package, root).applied
        assert not (orphan / "unfinished").exists()
        assert "SINTETICO" in read_resource_text(list_local_resources(connection)[0], connection=connection)


def test_resource_review_uses_persisted_root_and_checks_bytes(tmp_path):
    db_path, root = tmp_path / "catalog.db", tmp_path / "custom-materials"
    package = write_package(tmp_path / "demo.zip")
    with connect_database(db_path) as connection:
        create_schema(connection)
        _import(connection, package, root)
        # Solo fixture: risorsa reale in attesa di revisione, senza attribuire verifiche.
        connection.execute("UPDATE local_resources SET verification_status='da_verificare'")
        connection.execute("UPDATE documents SET stato_verifica='da_verificare'")
        connection.execute("UPDATE sources SET stato_verifica='da_verificare'")
        connection.commit()
        resource = list_local_resources(connection)[0]
        data = (root / resource.relative_path).read_bytes()
        (root / resource.relative_path).write_bytes(b"x" * len(data))
    with pytest.raises(ValueError, match="impronta"):
        submit_resource_review(resource.id, "verificato", "Curatore di prova", source_confirmed=True, db_path=db_path)
    with connect_database(db_path) as connection:
        assert list_local_resources(connection)[0].verification_status == "da_verificare"
        assert connection.execute("SELECT COUNT(*) FROM review_events").fetchone()[0] == 0
    (root / resource.relative_path).write_bytes(data)
    assert submit_resource_review(resource.id, "verificato", "Curatore di prova", source_confirmed=True, db_path=db_path)


def test_memory_database_previews_but_cannot_publish_materials_or_write_attempts(tmp_path):
    package, root = write_package(tmp_path / "demo.zip"), tmp_path / "materials"
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        create_schema(connection)
        before = list(connection.iterdump())
        preview = import_local_package(connection, package, root)
        assert preview.resource_count == 1 and not preview.applied
        with pytest.raises(PackageValidationError, match="database SQLite su file"):
            import_local_package(connection, package, root, dry_run=False, expected_sha256=preview.sha256)
        assert list(connection.iterdump()) == before and not connection.in_transaction
        assert not root.exists()
    finally:
        connection.close()
