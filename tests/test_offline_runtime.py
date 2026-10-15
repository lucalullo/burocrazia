"""Meaningful regression coverage of first start and the external-network boundary."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import os
import socket
import time
import http.client

from src.bootstrap import prepare_database
from src import offline_transport

ROOT = Path(__file__).resolve().parents[1]


def test_first_start_preserves_entire_catalog_and_second_start_preserves_local_edits(tmp_path):
    path = prepare_database(tmp_path / "catalog.db")
    with sqlite3.connect(path) as db:
        manifest=json.loads((ROOT/'data/catalog_manifest.json').read_text(encoding='utf-8'))
        assert db.execute("SELECT count(*) FROM documents").fetchone()[0] == manifest['tables']['documents']
        assert db.execute("SELECT count(*) FROM entities").fetchone()[0] == 2499
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        db.execute("UPDATE documents SET categoria='modifica locale' WHERE id=1")
    prepare_database(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT categoria FROM documents WHERE id=1").fetchone()[0] == "modifica locale"


def test_external_socket_and_dns_attempts_blocked_but_loopback_works():
    code = '''
import socket
from src.offline import install_network_guard, blocked_attempts
install_network_guard()
for action in (lambda: socket.getaddrinfo('external.invalid',443), lambda: socket.socket().connect(('203.0.113.1',443))):
    try: action()
    except PermissionError: pass
    else: raise AssertionError('external network not blocked')
with socket.socket() as server:
    server.bind(('127.0.0.1',0)); server.listen()
    with socket.create_connection(server.getsockname()) as client:
        peer, address = server.accept(); peer.close()
assert len(blocked_attempts) == 2
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_old_cli_commands_cannot_start_external_acquisitions():
    for name in ("ipa", "inps", "inail", "ade", "ader", "inl", "garante", "lavoro"):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / f"import_{name}.py"), "--commit"], capture_output=True, text=True, timeout=10)
        assert result.returncode == 2
        assert "disattivata" in result.stderr


def test_historical_parser_default_transport_never_opens_socket(monkeypatch):
    import socket
    import pytest
    monkeypatch.setattr(socket, "socket", lambda *a, **kw: pytest.fail("network attempted"))
    with pytest.raises(offline_transport.RequestException, match="disattivata"):
        offline_transport.get("https://example.invalid")


def test_supported_launcher_serves_health_on_requested_loopback_port(tmp_path):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment = {**os.environ, "BUROCRAZIA_DB_PATH": str(tmp_path / "launch.db")}
    process = subprocess.Popen([sys.executable, "run.py", "--port", str(port)], cwd=ROOT, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ready, output = False, ""
    try:
        deadline = time.monotonic() + 20
        while process.poll() is None and time.monotonic() < deadline:
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=.5)
                connection.request("GET", "/_stcore/health")
                response = connection.getresponse()
                ready = response.status == 200 and response.read() == b"ok"
                connection.close()
                if ready:
                    break
            except OSError:
                time.sleep(.1)
    finally:
        process.terminate()
        try:
            output = process.communicate(timeout=8)[0]
        except subprocess.TimeoutExpired:
            process.kill()
            output = process.communicate()[0]
    assert ready, output
