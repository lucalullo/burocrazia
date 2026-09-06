"""Exercise SQLite handle lifetime with real databases, on every platform."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from src import bootstrap


@pytest.fixture
def tracked_bootstrap(tmp_path, monkeypatch):
    real_connect, real_link, real_unlink = sqlite3.connect, bootstrap.os.link, Path.unlink
    project = tmp_path / "public"
    (project / "data").mkdir(parents=True)
    seed = project / "data/catalog_seed.sqlite3"
    with closing(real_connect(seed)) as connection, connection:
        connection.execute("CREATE TABLE example (value TEXT)").close()
        connection.execute("INSERT INTO example VALUES ('catalogo completo')").close()
    digest = hashlib.sha256(seed.read_bytes()).hexdigest()
    (project / "data/catalog_manifest.json").write_text(json.dumps({"sha256": digest, "catalog_version": "test"}), encoding="utf-8")
    state = SimpleNamespace(failure=None, connections=[], cursors=[], published=[], cleaned=[], initialized=[],
                            path=tmp_path / "catalog.db", seed=seed, digest=digest, metadata_at_cleanup=None)

    class TrackedCursor(sqlite3.Cursor):
        closed = False

        def execute(self, sql, parameters=()):
            if state.failure == "integrity" and sql == "PRAGMA integrity_check":
                return super().execute("SELECT 'not ok'")
            return super().execute(sql, parameters)

        def executemany(self, sql, parameters):
            if state.failure == "metadata":
                super().executemany(sql, list(parameters)[:1])
                raise sqlite3.DatabaseError("synthetic metadata failure")
            return super().executemany(sql, parameters)

        def close(self):
            super().close()
            self.closed = True

    class TrackedConnection(sqlite3.Connection):
        closed = False

        def cursor(self, *args, **kwargs):
            cursor = super().cursor(factory=TrackedCursor)
            state.cursors.append(cursor)
            return cursor

        def execute(self, sql, parameters=()):
            return self.cursor().execute(sql, parameters)

        def executemany(self, sql, parameters):
            return self.cursor().executemany(sql, parameters)

        def backup(self, target, **kwargs):
            if state.failure == "backup":
                raise sqlite3.DatabaseError("synthetic backup failure")
            return super().backup(target, **kwargs)

        def close(self):
            super().close()
            self.closed = True

    def connect(database, *args, **kwargs):
        if state.failure == "target_connect" and not kwargs.get("uri"):
            raise sqlite3.OperationalError("synthetic target open failure")
        connection = real_connect(database, *args, factory=TrackedConnection, **kwargs)
        state.connections.append(connection)
        return connection

    def handles_closed():
        assert all(cursor.closed for cursor in state.cursors), "SQLite cursor still open"
        assert all(connection.closed for connection in state.connections), "SQLite connection still open"

    def publish(source, target):
        handles_closed()
        state.published.append(Path(target))
        if state.failure == "publish":
            raise PermissionError("synthetic publication failure")
        if state.failure == "race":
            with closing(real_connect(target)) as connection, connection:
                connection.execute("CREATE TABLE winner (value TEXT)").close()
                connection.execute("INSERT INTO winner VALUES ('primo avvio concorrente')").close()
        return real_link(source, target)

    def unlink(path, *args, **kwargs):
        if path.name.startswith(".catalog-"):
            handles_closed()
            state.cleaned.append(path)
            if state.failure == "metadata":
                with closing(real_connect(path)) as connection, closing(connection.cursor()) as cursor:
                    state.metadata_at_cleanup = cursor.execute("SELECT * FROM catalog_metadata").fetchall()
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(bootstrap, "PROJECT_ROOT", project)
    monkeypatch.setattr(bootstrap.sqlite3, "connect", connect)
    monkeypatch.setattr(bootstrap.os, "link", publish)
    monkeypatch.setattr(Path, "unlink", unlink)
    monkeypatch.setattr(bootstrap, "initialize_database", lambda path, **kwargs: state.initialized.append(path))
    state.read = real_connect
    yield state
    # A failing regression must not itself leave Windows handles open.
    for cursor in state.cursors:
        if not cursor.closed:
            try:
                cursor.close()
            except sqlite3.ProgrammingError:
                pass
    for connection in state.connections:
        if not connection.closed:
            connection.close()


def test_bootstrap_closes_handles_before_publication_and_commits_metadata(tracked_bootstrap):
    state = tracked_bootstrap
    assert bootstrap.prepare_database(state.path) == state.path
    assert len(state.connections) == 2
    assert state.published == state.initialized == [state.path]
    assert len(state.cleaned) == 1 and not list(state.path.parent.glob(".catalog-*"))
    with closing(state.read(state.path)) as connection, closing(connection.cursor()) as cursor:
        assert cursor.execute("SELECT value FROM example").fetchone() == ("catalogo completo",)
        metadata = dict(cursor.execute("SELECT * FROM catalog_metadata").fetchall())
        assert metadata["seed_sha256"] == state.digest and metadata["seed_version"] == "test"
        assert metadata["initialized_at"]
    assert hashlib.sha256(state.seed.read_bytes()).hexdigest() == state.digest


@pytest.mark.parametrize("failure, error", [
    ("target_connect", sqlite3.OperationalError), ("backup", sqlite3.DatabaseError),
    ("integrity", ValueError), ("metadata", sqlite3.DatabaseError), ("publish", PermissionError),
])
def test_bootstrap_closes_handles_and_removes_temporary_on_failure(tracked_bootstrap, failure, error):
    state = tracked_bootstrap
    state.failure = failure
    with pytest.raises(error, match="non integro" if failure == "integrity" else "synthetic"):
        bootstrap.prepare_database(state.path)
    assert not state.path.exists() and not state.initialized
    assert len(state.cleaned) == 1 and not list(state.path.parent.glob(".catalog-*"))
    assert all(connection.closed for connection in state.connections)
    assert all(cursor.closed for cursor in state.cursors)
    if failure == "metadata":
        assert state.metadata_at_cleanup == [], "A failed metadata transaction must roll back"
    assert hashlib.sha256(state.seed.read_bytes()).hexdigest() == state.digest


def test_bootstrap_preserves_concurrent_winner_and_cleans_own_temporary(tracked_bootstrap):
    state = tracked_bootstrap
    state.failure = "race"
    assert bootstrap.prepare_database(state.path) == state.path
    assert state.initialized == [state.path]
    assert len(state.cleaned) == 1 and not list(state.path.parent.glob(".catalog-*"))
    with closing(state.read(state.path)) as connection, closing(connection.cursor()) as cursor:
        assert cursor.execute("SELECT * FROM winner").fetchall() == [("primo avvio concorrente",)]
        assert cursor.execute("SELECT name FROM sqlite_master WHERE name='example'").fetchall() == []


def test_existing_database_does_not_open_seed_or_change_bytes(tracked_bootstrap):
    state = tracked_bootstrap
    state.path.write_bytes(b"existing database is handled by initialize_database")
    before = state.path.read_bytes()
    assert bootstrap.prepare_database(state.path) == state.path
    assert state.path.read_bytes() == before and state.initialized == [state.path]
    assert state.connections == state.published == state.cleaned == []


def test_invalid_seed_hash_does_not_open_connections_or_publish(tracked_bootstrap):
    state = tracked_bootstrap
    state.seed.write_bytes(b"synthetic corrupted seed")
    with pytest.raises(ValueError, match="impronta"):
        bootstrap.prepare_database(state.path)
    assert state.connections == state.published == state.cleaned == state.initialized == []
    assert not state.path.exists() and not list(state.path.parent.glob(".catalog-*"))
