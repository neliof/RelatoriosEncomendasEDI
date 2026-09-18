from __future__ import annotations

import shutil
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from integration_app.models import ConnectionConfig


def discover_files(connection: ConnectionConfig) -> list[Path]:
    source_dir = connection.source_dir
    if not source_dir.exists():
        return []
    excluded = {connection.sent_dir.lower(), connection.error_dir.lower()}
    files = [
        path
        for path in source_dir.glob(connection.file_pattern)
        if path.is_file() and not any(part.lower() in excluded for part in path.relative_to(source_dir).parts[:-1])
    ]
    return sorted(files)


def is_stable(path: Path, stable_after_seconds: int, now: datetime | None = None) -> bool:
    current_time = now or datetime.now(UTC)
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return (current_time - modified).total_seconds() >= stable_after_seconds


def move_to_status_dir(path: Path, status_dir_name: str) -> Path:
    target_dir = path.parent / status_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    if target.exists():
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        target = target_dir / f"{path.stem}_{timestamp}{path.suffix}"
        counter = 1
        while target.exists():
            target = target_dir / f"{path.stem}_{timestamp}_{counter}{path.suffix}"
            counter += 1
    if target.exists():
        raise FileExistsError(f"Status target already exists: {target}")

    for attempt in range(3):
        try:
            shutil.move(str(path), str(target))
            return target
        except OSError as exc:
            if attempt < 2:
                time.sleep(0.1)
            else:
                raise exc


def remote_path_for(connection: ConnectionConfig, local_path: Path) -> str:
    remote_dir = connection.remote_dir.replace("\\", "/")
    return str(PurePosixPath(remote_dir) / local_path.name)
