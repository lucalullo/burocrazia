"""Compatibility boundary for historical parsers: no HTTP transport exists here.

Historical tests inject local fixture readers. Production callers fail before
opening any socket. Original acquisition code remains in Git history.
"""
from __future__ import annotations
import json


class RequestException(RuntimeError):
    """External acquisition is unavailable in the offline distribution."""


class exceptions:
    JSONDecodeError = json.JSONDecodeError


def get(*args, **kwargs):
    raise RequestException("Acquisizione esterna disattivata: importa un pacchetto locale verificabile.")
