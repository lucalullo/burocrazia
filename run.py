"""Supported local launcher: python run.py [--port 8501]."""
from __future__ import annotations
import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Avvia BurOCRazia solo su questo computer.")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("La porta deve essere compresa tra 1024 e 65535.")
    root = Path(__file__).resolve().parent
    os.chdir(root)
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    from src.offline import install_network_guard
    install_network_guard()
    from src.bootstrap import prepare_database
    prepare_database()
    from streamlit.web import bootstrap
    flags = {
        "server.address": "127.0.0.1", "server.port": args.port,
        "server.headless": True, "server.fileWatcherType": "none",
        "server.maxUploadSize": 20, "browser.gatherUsageStats": False,
        "browser.serverAddress": "127.0.0.1", "client.toolbarMode": "minimal",
    }
    bootstrap.load_config_options(flags)
    print(f"Apri BurOCRazia: http://127.0.0.1:{args.port}/", flush=True)
    bootstrap.run(str(root / "app.py"), False, [], flags)


if __name__ == "__main__":
    main()
