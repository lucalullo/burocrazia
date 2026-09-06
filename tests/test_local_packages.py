from __future__ import annotations

import errno
import hashlib
import json
import os
import sqlite3
import stat
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from src.database import connect_database, create_schema
from src.local_packages import PackageValidationError, catalog_state, import_local_package
from src.local_resources import list_local_resources, read_resource_text, resource_status


def package_payload():
    source = dict(key="demo-source", ente="Comune dimostrativo BurOCRazia", nome_fonte="Fonte sintetica locale", tipo_ente="demo", livello="locale", ambito="dimostrazione", metodo_acquisizione="local_package_demo", stato_verifica="demo", note="Fonte interamente sintetica; nessun ente reale.", attiva=False)
    document = dict(key="demo-document", source_key="demo-source", ente=source["ente"], codice="DEMO-PKG-01", titolo_ufficiale="Richiesta sintetica di accesso alla biblioteca dimostrativa", versione="demo-1", data_rilevazione="2026-09-05", stato_verifica="demo", parole_chiave=["biblioteca dimostrativa", "DEMO-PKG-01"])
    provenance = dict(key="demo-provenance", document_key="demo-document", source_key="demo-source", acquired_at="2026-09-05", last_seen_at="2026-09-05", acquisition_method="local_package_demo", source_status="demo")
    records = dict(sources=[source], entities=[], documents=[document], families=[], explanations=[], provenance=[provenance])
    resource = dict(path="resources/demo.txt", document_key="demo-document", source_key="demo-source", title="Esempio sintetico — non ufficiale", media_type="text/plain", provenance="Creato appositamente per dimostrare l'importazione. Nessun documento ufficiale.", acquired_at="2026-09-05", version="demo-1", reuse_conditions="Materiale sintetico riutilizzabile per prove e dimostrazioni.", verification_status="demo")
    manifest = dict(format_version=1, catalog_schema_version=1, package_id="burocrazia-demo", package_version="1.0.0", catalog_version="demo-1", created_at="2026-09-05T00:00:00+00:00", producer="BurOCRazia — esempio sintetico", demo=True, files=[], resources=[resource])
    files = {"resources/demo.txt": b"ESEMPIO SINTETICO - NON UFFICIALE\nComune dimostrativo BurOCRazia\nDEMO-PKG-01\nVersione demo-1\nRichiesta sintetica di accesso alla biblioteca dimostrativa\nNessuna procedura amministrativa reale e nessun dato personale.\n"}
    return manifest, records, files


def write_package(path, manifest=None, records=None, files=None, *, mutate_manifest=None, extra_entries=None):
    if manifest is None:
        manifest, records, files = package_payload()
    files = {**files, "records.json": json.dumps(records, ensure_ascii=False, sort_keys=True).encode()}
    manifest["files"] = [dict(path=name, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest()) for name, data in sorted(files.items())]
    if mutate_manifest:
        mutate_manifest(manifest)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode())
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
        for name, data in extra_entries or []:
            archive.writestr(name, data)
    return path


@pytest.fixture
def database(tmp_path):
    connection = connect_database(tmp_path / "catalog.db")
    create_schema(connection)
    yield connection
    connection.close()


def apply_package(database, path, root):
    preview = import_local_package(database, path, root)
    return import_local_package(database, path, root, dry_run=False, expected_sha256=preview.sha256)


def test_preview_has_no_catalog_or_filesystem_writes_and_commit_is_idempotent(database, tmp_path):
    path, root = write_package(tmp_path / "demo.zip"), tmp_path / "resources"
    before = list(database.iterdump())
    preview = import_local_package(database, path, root)
    assert preview.new_records["documents"] == preview.new_records["provenance"] == 1
    assert not preview.applied and not root.exists()
    assert list(database.iterdump()) == before
    result = import_local_package(database, path, root, dry_run=False, expected_sha256=preview.sha256)
    assert result.applied and result.demo
    resources = list_local_resources(database)
    assert len(resources) == 1 and "SINTETICO" in read_resource_text(resources[0], root)
    assert "dimostrativo" in resource_status(database, resources[0].document_id)
    assert catalog_state(database)["catalog_version"] == "demo-1"
    again = import_local_package(database, path, root, dry_run=False, expected_sha256=preview.sha256)
    assert again.already_imported and not again.applied and again.new_records["documents"] == 0
    assert database.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert database.execute("SELECT COUNT(*) FROM package_imports").fetchone()[0] == 1
    assert not database.execute("PRAGMA foreign_key_check").fetchall()


def test_commit_requires_exact_preview_hash_and_rejects_replaced_archive(database, tmp_path):
    path = write_package(tmp_path / "demo.zip")
    preview = import_local_package(database, path)
    with pytest.raises(PackageValidationError, match="anteprima"):
        import_local_package(database, path, dry_run=False)
    manifest, records, files = package_payload()
    manifest["producer"] = "Produttore cambiato dopo l'anteprima"
    write_package(path, manifest, records, files)
    with pytest.raises(PackageValidationError, match="cambiato"):
        import_local_package(database, path, dry_run=False, expected_sha256=preview.sha256)
    assert database.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    assert database.execute("SELECT status FROM package_import_attempts").fetchone()[0] == "rejected"


@pytest.mark.parametrize("name", ["../outside.txt", "/absolute.txt", "resources/../../outside.txt", "resources\\outside.txt", "resources/CON.txt"])
def test_rejects_unsafe_zip_paths_before_writing(database, tmp_path, name):
    path = write_package(tmp_path / "unsafe.zip", extra_entries=[(name, b"payload")])
    with pytest.raises(PackageValidationError):
        import_local_package(database, path, tmp_path / "resources")
    assert not (tmp_path / "outside.txt").exists()


def test_rejects_symlink_duplicate_unlisted_and_compression_bomb(database, tmp_path):
    cases = []
    symlink = zipfile.ZipInfo("resources/link.txt")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    cases.append([(symlink, b"../../outside")])
    cases.append([("resources/demo.txt", b"duplicate")])
    cases.append([("script.py", b"print('never executed')")])
    cases.append([("resources/bomb.txt", b"a" * 300_000)])
    for index, entries in enumerate(cases):
        with pytest.warns(UserWarning) if index == 1 else __import__("contextlib").nullcontext():
            path = write_package(tmp_path / f"unsafe{index}.zip", extra_entries=entries)
        with pytest.raises(PackageValidationError):
            import_local_package(database, path)


def test_rejects_bad_hash_schema_and_relations(database, tmp_path):
    path = write_package(tmp_path / "hash.zip", mutate_manifest=lambda manifest: manifest["files"][0].update(sha256="0" * 64))
    with pytest.raises(PackageValidationError, match="Impronta"):
        import_local_package(database, path)
    manifest, records, files = package_payload()
    records["documents"][0]["source_key"] = "missing-source"
    path = write_package(tmp_path / "relation.zip", manifest, records, files)
    with pytest.raises(PackageValidationError, match="Relazione inesistente"):
        import_local_package(database, path)
    records["documents"][0]["execute"] = "anything"
    write_package(path, manifest, records, files)
    with pytest.raises(PackageValidationError, match="Schema"):
        import_local_package(database, path)


def test_new_document_without_provenance_is_rejected(database, tmp_path):
    manifest, records, files = package_payload()
    records["provenance"] = []
    path = write_package(tmp_path / "missing.zip", manifest, records, files)
    with pytest.raises(PackageValidationError, match="provenienza"):
        import_local_package(database, path)


def test_verified_existing_document_is_preserved_and_conflict_rejected(database, tmp_path):
    path, root = write_package(tmp_path / "demo.zip"), tmp_path / "resources"
    apply_package(database, path, root)
    database.execute("UPDATE documents SET stato_verifica='verificato'")
    database.commit()
    before = tuple(database.execute("SELECT * FROM documents").fetchone())
    manifest, records, files = package_payload()
    manifest["package_version"] = "2.0.0"
    records["documents"][0]["titolo_ufficiale"] = "Titolo sostituito"
    write_package(path, manifest, records, files)
    with pytest.raises(PackageValidationError, match="Conflitto"):
        import_local_package(database, path)
    assert tuple(database.execute("SELECT * FROM documents").fetchone()) == before


def test_same_package_version_with_other_bytes_is_rejected(database, tmp_path):
    path, root = write_package(tmp_path / "demo.zip"), tmp_path / "resources"
    apply_package(database, path, root)
    manifest, records, files = package_payload()
    manifest["producer"] = "Differente produttore"
    write_package(path, manifest, records, files)
    with pytest.raises(PackageValidationError, match="byte differenti"):
        import_local_package(database, path)


def test_rollback_cleans_published_files_and_catalog_on_database_error(database, tmp_path):
    path, root = write_package(tmp_path / "demo.zip"), tmp_path / "resources"
    preview = import_local_package(database, path, root)
    database.execute("CREATE TRIGGER fail_package BEFORE INSERT ON package_imports BEGIN SELECT RAISE(ABORT, 'forced commit failure'); END")
    database.commit()
    with pytest.raises(PackageValidationError, match="forced commit failure"):
        import_local_package(database, path, root, dry_run=False, expected_sha256=preview.sha256)
    assert database.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    assert database.execute("SELECT COUNT(*) FROM document_provenance").fetchone()[0] == 0
    assert database.execute("SELECT COUNT(*) FROM local_resources").fetchone()[0] == 0
    assert database.execute("SELECT COUNT(*) FROM package_imports").fetchone()[0] == 0
    assert not list(root.iterdir())
    assert database.execute("SELECT status FROM package_import_attempts").fetchone()[0] == "rejected"


def test_rollback_on_file_write_failure_keeps_catalog_unchanged(database, tmp_path, monkeypatch):
    path, root = write_package(tmp_path / "demo.zip"), tmp_path / "resources"
    preview = import_local_package(database, path, root)
    monkeypatch.setattr("src.local_packages.os.replace", lambda *_: (_ for _ in ()).throw(OSError("forced file failure")))
    with pytest.raises(PackageValidationError, match="forced file failure"):
        import_local_package(database, path, root, dry_run=False, expected_sha256=preview.sha256)
    assert database.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    assert not list(root.iterdir())


def test_missing_material_is_declared_and_existing_catalog_is_not_deleted(database, tmp_path):
    first, root = write_package(tmp_path / "first.zip"), tmp_path / "resources"
    apply_package(database, first, root)
    manifest, records, files = package_payload()
    manifest.update(package_id="burocrazia-second", package_version="2.0.0", resources=[])
    records["documents"][0].update(codice="DEMO-PKG-02", titolo_ufficiale="Altro documento sintetico")
    second = write_package(tmp_path / "second.zip", manifest, records, {})
    preview = import_local_package(database, second, root)
    assert preview.missing_resources == ("Altro documento sintetico",)
    import_local_package(database, second, root, dry_run=False, expected_sha256=preview.sha256)
    assert database.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2


def test_text_material_is_inert_and_tampering_is_rejected(database, tmp_path):
    manifest, records, files = package_payload()
    payload = '<script src="https://example.invalid/remote.js"></script> https://example.invalid/'
    files["resources/demo.txt"] = payload.encode()
    path, root = write_package(tmp_path / "text.zip", manifest, records, files), tmp_path / "resources"
    apply_package(database, path, root)
    resource = list_local_resources(database)[0]
    assert read_resource_text(resource, root) == payload
    actual = root / resource.relative_path
    actual.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError):
        read_resource_text(resource, root)


def test_imported_resource_symlinks_are_rejected(database, tmp_path):
    path, root = write_package(tmp_path / "text.zip"), tmp_path / "resources"
    apply_package(database, path, root)
    resource = list_local_resources(database)[0]
    actual = root / resource.relative_path
    actual.unlink()
    try:
        actual.symlink_to(path)
    except NotImplementedError:
        pytest.skip("Creazione di collegamenti simbolici non disponibile su questa piattaforma.")
    except OSError as exc:
        unavailable = {errno.EPERM, errno.EACCES, errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP}
        if exc.errno not in unavailable and getattr(exc, "winerror", None) not in {1, 50, 1314}:
            raise
        pytest.skip(f"Creazione di collegamenti simbolici non consentita o non supportata: {exc}")
    assert actual.is_symlink()
    with pytest.raises(ValueError, match="simbolico"):
        read_resource_text(resource, root)


def test_crash_orphan_is_recovered_before_retry(database, tmp_path):
    path, root = write_package(tmp_path / "demo.zip"), tmp_path / "resources"
    preview = import_local_package(database, path, root)
    orphan = root / preview.sha256
    orphan.mkdir(parents=True)
    from src.local_packages import _database_fingerprint
    (orphan / ".burocrazia-package").write_text(json.dumps({"sha256": preview.sha256, "database": _database_fingerprint(database)}))
    (orphan / "unfinished").write_text("not visible in catalog")
    result = import_local_package(database, path, root, dry_run=False, expected_sha256=preview.sha256)
    assert result.applied and not (orphan / "unfinished").exists()
    assert len(list_local_resources(database)) == 1


def test_existing_reference_adds_resource_without_modifying_document(database, tmp_path):
    manifest, records, files = package_payload()
    manifest["resources"] = []
    first, root = write_package(tmp_path / "first.zip", manifest, records, {}), tmp_path / "resources"
    apply_package(database, first, root)
    document = database.execute("SELECT * FROM documents").fetchone()
    source_id = database.execute("SELECT id FROM sources").fetchone()[0]
    manifest, records, files = package_payload()
    manifest.update(package_id="burocrazia-resource", package_version="2.0.0")
    records.update(sources=[dict(key="demo-source", existing_id=source_id)], documents=[dict(key="demo-document", existing_id=document["id"])], provenance=[])
    second = write_package(tmp_path / "second.zip", manifest, records, files)
    apply_package(database, second, root)
    assert tuple(database.execute("SELECT * FROM documents").fetchone()) == tuple(document)
    assert len(list_local_resources(database)) == 1


def test_corrupt_deflate_stream_is_a_safe_validation_error(database, tmp_path):
    path = write_package(tmp_path / "corrupt.zip")
    with zipfile.ZipFile(path) as archive:
        entry = archive.infolist()[0]
    raw = bytearray(path.read_bytes())
    header = struct.unpack_from("<4s5H3I2H", raw, entry.header_offset)
    offset = entry.header_offset + 30 + header[-2] + header[-1]
    raw[offset:offset + 4] = b"\xff" * 4
    path.write_bytes(raw)
    with pytest.raises(PackageValidationError, match="ZIP rifiutato"):
        import_local_package(database, path)


def test_final_resource_path_is_validated_in_preview(database, tmp_path):
    manifest, records, files = package_payload()
    old_name = manifest["resources"][0]["path"]
    new_name = "resources/" + "a" * 100 + "/" + "b" * 80 + ".txt"
    manifest["resources"][0]["path"] = new_name
    files[new_name] = files.pop(old_name)
    path = write_package(tmp_path / "long-path.zip", manifest, records, files)
    with pytest.raises(PackageValidationError, match="Percorso"):
        import_local_package(database, path)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO non disponibile su questa piattaforma")
def test_replaced_resource_fifo_does_not_block_reader(tmp_path):
    os.mkfifo(tmp_path / "fifo.txt")
    code = """import sys
from src.local_resources import LocalResource, read_resource_text
resource = LocalResource(id=1, document_id=1, source_id=1, title='Synthetic', relative_path='fifo.txt', media_type='text/plain', size_bytes=0, sha256='', provenance='Synthetic', acquired_at='2026-09-05', version=None, reuse_conditions='Synthetic', verification_status='da_verificare', package_id='test')
try:
    read_resource_text(resource, sys.argv[1])
except ValueError:
    raise SystemExit(0)
raise SystemExit(1)
"""
    completed = subprocess.run([sys.executable, "-c", code, str(tmp_path)], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=3)
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO non disponibile su questa piattaforma")
def test_package_fifo_does_not_block_validation(tmp_path):
    fifo = tmp_path / "package.zip"
    os.mkfifo(fifo)
    code = """import sys
from src.database import connect_database, create_schema
from src.local_packages import import_local_package, PackageValidationError
connection = connect_database(sys.argv[2])
create_schema(connection)
try:
    import_local_package(connection, sys.argv[1])
except PackageValidationError:
    raise SystemExit(0)
raise SystemExit(1)
"""
    completed = subprocess.run([sys.executable, "-c", code, str(fifo), str(tmp_path / "fifo.db")], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=3)
    assert completed.returncode == 0, completed.stderr


def test_orphan_cleanup_does_not_remove_files_of_another_catalog(database, tmp_path):
    path, root = write_package(tmp_path / "demo.zip"), tmp_path / "resources"
    foreign = root / ("0" * 64)
    foreign.mkdir(parents=True)
    (foreign / ".burocrazia-package").write_text(json.dumps({"sha256": "0" * 64, "database": "foreign-database"}))
    (foreign / "owned.txt").write_text("Do not remove")
    apply_package(database, path, root)
    assert (foreign / "owned.txt").read_text() == "Do not remove"


def test_no_package_can_mark_content_verified(database, tmp_path):
    manifest, records, files = package_payload()
    records["documents"][0]["stato_verifica"] = "verificato"
    path = write_package(tmp_path / "false-review.zip", manifest, records, files)
    with pytest.raises(PackageValidationError, match="automaticamente"):
        import_local_package(database, path)


def test_cli_dry_run_leaves_database_unchanged(database, tmp_path, capsys):
    from scripts.import_package import main
    path = write_package(tmp_path / "demo.zip")
    db_path = next(row[2] for row in database.execute("PRAGMA database_list") if row[1] == "main")
    before = list(database.iterdump())
    assert main([str(path), "--db", db_path, "--resource-root", str(tmp_path / "resources")]) == 0
    assert "Anteprima: nessuna scrittura" in capsys.readouterr().out
    assert before == list(database.iterdump())


def test_imported_explanation_obeys_editor_source_and_notes_validation(database, tmp_path):
    manifest, records, files = package_payload()
    manifest.update(demo=False, resources=[])
    records["sources"][0].update(ente="INPS", stato_verifica="da_verificare")
    records["documents"][0].update(ente="INPS", stato_verifica="rilevato")
    records["explanations"] = [dict(key="explanation", document_key="demo-document", source_url="https://unsupported.invalid/source", source_access_date="2026-09-05", verification_status="bozza", version="1", created_at="2026-09-05T00:00:00", updated_at="2026-09-05T00:00:00", facts_from_source=["Fatto di prova da sottoporre a revisione."], simple_explanation="Bozza di prova.")]
    path = write_package(tmp_path / "editor.zip", manifest, records, {})
    with pytest.raises(PackageValidationError, match="fonte"):
        import_local_package(database, path)
    records["explanations"][0].update(source_url="https://www.inps.it/it/it/moduli.html", review_notes="n" * 1001)
    write_package(path, manifest, records, {})
    with pytest.raises(PackageValidationError, match="note"):
        import_local_package(database, path)
    records["explanations"][0]["review_notes"] = "Da controllare manualmente."
    write_package(path, manifest, records, {})
    assert import_local_package(database, path).new_records["explanations"] == 1
