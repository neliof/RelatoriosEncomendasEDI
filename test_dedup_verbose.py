#!/usr/bin/env python
from pathlib import Path
from integration_app.config import load_config
from integration_app.storage.sqlite_store import SQLiteStore
from integration_app.core.runner import run_once
import logging

logging.basicConfig(level=logging.DEBUG)

config = load_config(Path("config.yaml"))
db_path = Path("data") / "integration.db"
store = SQLiteStore(db_path)
store.initialize()

result = run_once(config, store)
print(f"Run result: processed={result.processed}, sent={result.sent}, failed={result.failed}, skipped_unstable={result.skipped_unstable}")

# Check state
for conn in config.connections:
    if conn.protocol == "local":
        mtime = store.get_generix_last_mtime(conn.name)
        print(f"{conn.name}: last_mtime={mtime}")

# Show all errors
print("\nAll events:")
for row in store.report_rows():
    if row.get('connection_name') == 'generix_received':
        print(f"  {row.get('status')}: {row.get('error_message')}")
