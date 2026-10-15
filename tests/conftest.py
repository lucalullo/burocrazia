"""Tests run without external network; fixture parsers remain entirely local."""
from src.offline import install_network_guard
import hashlib
import json
import os
from pathlib import Path


def pytest_configure(config):
    # Historical tests need the original source proofs even in a clean clone
    # whose branch history differs from the research checkout. Never import
    # objects into .git or weaken a historical byte/AST assertion.
    fixture = Path(__file__).parent / 'fixtures/historical_git_objects'
    manifest = json.loads((fixture / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((fixture / name).read_bytes()).hexdigest() == expected['sha256']
    previous = os.environ.get('GIT_ALTERNATE_OBJECT_DIRECTORIES')
    lookup = str((fixture / 'objects').resolve())
    os.environ['GIT_ALTERNATE_OBJECT_DIRECTORIES'] = lookup + (os.pathsep + previous if previous else '')
    install_network_guard()
