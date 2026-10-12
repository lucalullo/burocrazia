"""Keep SQLite references alive so Windows handle leaks cannot hide behind GC."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from scripts import benchmark
from src import database


@pytest.fixture
def tracked_connections(monkeypatch):
    original_connect = sqlite3.connect
    state = SimpleNamespace(connections=[], fail_backup=False, bad_integrity=False, fail_target=False, read=original_connect)

    class Cursor(sqlite3.Cursor):
        def execute(self, sql, parameters=()):
            if state.bad_integrity and sql == "PRAGMA integrity_check":
                return super().execute("SELECT 'not ok'")
            return super().execute(sql, parameters)

    class Connection(sqlite3.Connection):
        closed = False

        def cursor(self, *args, **kwargs):
            return super().cursor(factory=Cursor)

        def close(self):
            super().close()
            self.closed = True

        def backup(self, target, **kwargs):
            if state.fail_backup:
                raise sqlite3.DatabaseError("synthetic backup failure")
            return super().backup(target, **kwargs)

        def execute(self, sql, parameters=()):
            return self.cursor().execute(sql, parameters)

    def connect(path, *args, **kwargs):
        if state.fail_target and not kwargs.get("uri"):
            raise sqlite3.OperationalError("synthetic target open failure")
        connection = original_connect(path, *args, factory=Connection, **kwargs)
        state.connections.append(connection)
        return connection

    def assert_closed():
        assert state.connections, "No SQLite connection exercised"
        for connection in state.connections:
            assert connection.closed, "SQLite connection remains open while the owning operation has finished"
            with pytest.raises(sqlite3.ProgrammingError, match="closed"):
                connection.execute("SELECT 1")

    state.assert_closed = assert_closed
    monkeypatch.setattr(sqlite3, "connect", connect)
    yield state
    for connection in state.connections:
        if not connection.closed:
            connection.close()


def test_initialize_database_closes_connection_and_preserves_committed_seed(tracked_connections, tmp_path):
    state, path = tracked_connections, tmp_path / "initialize.db"
    assert database.initialize_database(path) == 10
    state.assert_closed()
    with closing(state.read(path)) as connection, closing(connection.cursor()) as cursor:
        assert cursor.execute("SELECT count(*) FROM documents").fetchone()[0] == 10
        assert cursor.execute("PRAGMA user_version").fetchone()[0] == database.SCHEMA_VERSION
        assert cursor.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_initialize_database_rolls_back_pending_writes_and_closes_on_error(tracked_connections, tmp_path, monkeypatch):
    state, path = tracked_connections, tmp_path / "failed-initialize.db"

    def fail_during_seed(connection):
        connection.execute("CREATE TABLE lifecycle_probe (value TEXT)").close()
        connection.execute("INSERT INTO lifecycle_probe VALUES ('must roll back')").close()
        raise sqlite3.DatabaseError("synthetic seeding failure")

    monkeypatch.setattr(database, "seed_initial_sources", fail_during_seed)
    with pytest.raises(sqlite3.DatabaseError, match="synthetic seeding failure"):
        database.initialize_database(path)
    state.assert_closed()
    with closing(state.read(path)) as connection, closing(connection.cursor()) as cursor:
        assert cursor.execute("SELECT * FROM lifecycle_probe").fetchall() == []


@pytest.mark.parametrize("failure", [None, "backup", "integrity", "target_connect"])
def test_migration_backup_closes_owned_handles_and_leaves_caller_usable(tracked_connections, tmp_path, failure):
    state, path = tracked_connections, tmp_path / "old.db"
    with closing(state.read(path)) as caller, caller:
        caller.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, title TEXT)").close()
        caller.execute("INSERT INTO documents VALUES (1, 'preserved record')").close()
        caller.commit()
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        state.fail_backup, state.bad_integrity, state.fail_target = failure == "backup", failure == "integrity", failure == "target_connect"
        if failure:
            error = RuntimeError if failure == "integrity" else sqlite3.DatabaseError
            with pytest.raises(error, match="integrità" if failure == "integrity" else "synthetic"):
                database._backup_before_migration(caller)
        else:
            backup = database._backup_before_migration(caller)
            with closing(state.read(backup)) as copied, closing(copied.cursor()) as cursor:
                assert cursor.execute("SELECT * FROM documents").fetchall() == [(1, "preserved record")]
                assert cursor.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        state.assert_closed()
        with closing(caller.cursor()) as cursor:
            assert cursor.execute("SELECT * FROM documents").fetchall() == [(1, "preserved record")]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("alternate_catalog", [False, True])
@pytest.mark.parametrize("read_error", [False, True])
def test_benchmark_closes_all_handles_before_temporary_cleanup(tracked_connections, tmp_path, monkeypatch, alternate_catalog, read_error):
    state = tracked_connections
    original_temporary = benchmark.tempfile.TemporaryDirectory
    cleaned = []

    class CheckedTemporaryDirectory(original_temporary):
        def __exit__(self, *args):
            state.assert_closed()
            result = super().__exit__(*args)
            assert not Path(self.name).exists()
            cleaned.append(self.name)
            return result

    def fail_read(connection):
        return connection.execute("SELECT * FROM deliberately_absent_lifecycle_table").fetchall()

    monkeypatch.setattr(benchmark.tempfile, "TemporaryDirectory", CheckedTemporaryDirectory)
    if read_error:
        monkeypatch.setattr(benchmark, "list_documents", fail_read)
    catalog = None
    if alternate_catalog:
        catalog = tmp_path / "alternate.db"
        shutil.copyfile(database.PROJECT_ROOT / "data/catalog_seed.sqlite3", catalog)
        before = hashlib.sha256(catalog.read_bytes()).hexdigest()
    if read_error:
        with pytest.raises(sqlite3.OperationalError, match="deliberately_absent_lifecycle_table"):
            benchmark.run_benchmark(catalog_path=catalog)
    else:
        report = benchmark.run_benchmark(catalog_path=catalog)
        # The immutable v1 corpus has two unversioned positives contradicted
        # by v2. R9 refuses both; the handle lifecycle must still be correct.
        failures = {c['id']: c for c in report['cases'] if not c['correct']}
        assert set(failures) == {'EX02', 'EX03'} and report['summary']['failed'] == 2
        assert all(c['observed']['match_type'] == 'NO_MATCH' for c in failures.values())
        manifest=json.loads((database.PROJECT_ROOT/'data/catalog_manifest.json').read_text(encoding='utf-8'))
        assert report["catalog"] == {"documents_real": manifest['real_documents'], "documents_demo": 10, "families": 16}
    state.assert_closed()
    assert len(cleaned) == 1
    if alternate_catalog:
        assert hashlib.sha256(catalog.read_bytes()).hexdigest() == before


def test_benchmark_closes_alternate_source_if_copy_cannot_open(tracked_connections, tmp_path):
    state = tracked_connections
    path = tmp_path / "alternate.db"
    shutil.copyfile(database.PROJECT_ROOT / "data/catalog_seed.sqlite3", path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    state.fail_target = True
    with pytest.raises(sqlite3.OperationalError, match="synthetic target open failure"):
        benchmark.run_benchmark(catalog_path=path)
    state.assert_closed()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
