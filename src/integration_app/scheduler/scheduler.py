from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from integration_app.core.runner import run_once
from integration_app.models import AppConfig
from integration_app.storage.sqlite_store import SQLiteStore


class IntegrationScheduler:
    def __init__(self, config: AppConfig, store: SQLiteStore):
        self.config = config
        self.store = store
        self.scheduler = BackgroundScheduler()

    def start(self) -> None:
        enabled_connections = [c for c in self.config.connections if c.enabled and c.schedule_enabled]

        for connection in enabled_connections:
            self._schedule_connection(connection)

        self.scheduler.start()

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()

    def _schedule_connection(self, connection) -> None:
        job_id = f"run_once_{connection.name}"

        if connection.schedule_frequency == "daily":
            trigger = CronTrigger(
                hour=connection.schedule_hour,
                minute=connection.schedule_minute,
            )
        elif connection.schedule_frequency == "hourly":
            trigger = IntervalTrigger(hours=connection.schedule_interval)
        elif connection.schedule_frequency == "every_x_hours":
            trigger = IntervalTrigger(hours=connection.schedule_interval)
        elif connection.schedule_frequency == "every_x_minutes":
            trigger = IntervalTrigger(minutes=connection.schedule_interval)
        else:
            trigger = IntervalTrigger(hours=1)

        self.scheduler.add_job(
            self._run_connection,
            trigger,
            id=job_id,
            name=f"Process {connection.name}",
            args=(connection.name,),
            replace_existing=True,
        )

    def _run_connection(self, connection_name: str) -> None:
        connection = next((c for c in self.config.connections if c.name == connection_name), None)
        if connection is None:
            return

        try:
            run_once(self.config, self.store)
        except Exception:
            pass
