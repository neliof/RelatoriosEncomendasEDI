#!/usr/bin/env python
from pathlib import Path
from integration_app.storage.sqlite_store import SQLiteStore

db_path = Path('data') / 'integration.db'
store = SQLiteStore(db_path)

for row in store.report_rows()[-3:]:
    print(f"{row.get('connection_name')}: {row.get('status')} - {row.get('error_message')}")
