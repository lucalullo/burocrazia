"""Tests run without external network; fixture parsers remain entirely local."""
from src.offline import install_network_guard


def pytest_configure(config):
    install_network_guard()
