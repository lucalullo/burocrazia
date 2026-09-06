"""Process-wide external-socket guard; only literal loopback and local IPC pass."""
from __future__ import annotations
import ipaddress
import socket
import sys

_installed = False
blocked_attempts: list[str] = []


def _is_loopback(host: object) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="replace")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def install_network_guard() -> None:
    global _installed
    if _installed:
        return

    def audit(event, args):
        host = None
        if event in {"socket.connect", "socket.bind"}:
            sock, address = args[:2]
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                host = address[0]
        elif event == "socket.getaddrinfo":
            host = args[0]
        elif event == "socket.sendto":
            sock, address = args[:2]
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                host = address[0]
        if host is not None and not _is_loopback(host):
            blocked_attempts.append(event)  # No hostname or document content is logged.
            raise PermissionError("BurOCRazia consente soltanto connessioni locali loopback.")

    sys.addaudithook(audit)
    _installed = True
