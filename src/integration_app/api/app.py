from __future__ import annotations

import os
from pathlib import Path

from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from integration_app.api.config_management import (
    ConfigUpdateError,
    add_connection_config,
    delete_connection_config,
    update_app_config,
    update_connection_config,
    update_connection_credentials,
    update_connection_schedule,
)
from integration_app.api.read_models import (
    EventFilters,
    fetch_clients,
    fetch_connections,
    fetch_config_summary,
    fetch_event_detail,
    fetch_events,
    fetch_summary,
    fetch_suppliers,
    list_reports,
)
from integration_app.config import load_config
from integration_app.scheduler import IntegrationScheduler
from integration_app.storage.sqlite_store import SQLiteStore


def create_app(db_path: Path, report_dir: Path, config_path: Path = Path("config.yaml")) -> FastAPI:
    app = FastAPI(title="Relatorios Encomendas EDI API")
    static_dir = Path(__file__).with_name("static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    scheduler: IntegrationScheduler | None = None

    @app.on_event("startup")
    def startup_scheduler() -> None:
        nonlocal scheduler
        try:
            config = load_config(config_path)
            store = SQLiteStore(db_path)
            store.initialize()
            scheduler = IntegrationScheduler(config, store)
            scheduler.start()
        except Exception:
            pass

    @app.on_event("shutdown")
    def shutdown_scheduler() -> None:
        nonlocal scheduler
        if scheduler:
            scheduler.stop()

    @app.get("/")
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "dashboard.html")

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "database_exists": db_path.exists()}

    @app.get("/summary")
    def summary() -> dict[str, object]:
        return fetch_summary(db_path)

    @app.get("/events")
    def events(
        status: str | None = None,
        connection_name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = Query(100, ge=1, le=500),
    ) -> dict[str, object]:
        filters = EventFilters(
            status=status,
            connection_name=connection_name,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        return {"items": fetch_events(db_path, filters)}

    @app.get("/events/{event_id}")
    def event_detail(event_id: int) -> dict[str, object]:
        detail = fetch_event_detail(db_path, event_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return detail

    @app.get("/connections")
    def connections() -> dict[str, object]:
        return {"items": fetch_connections(db_path)}

    @app.get("/config/summary")
    def config_summary() -> dict[str, object]:
        return fetch_config_summary(config_path)

    @app.patch("/config/app")
    def update_config_app(
        updates: dict[str, object] = Body(...),
    ) -> dict[str, object]:
        return update_app_config(config_path, updates)

    @app.patch("/config/connections/{connection_name}")
    def update_config_connection(
        connection_name: str,
        updates: dict[str, object] = Body(...),
    ) -> dict[str, object]:
        try:
            return update_connection_config(config_path, connection_name, updates)
        except ConfigUpdateError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    @app.patch("/config/connections/{connection_name}/credentials")
    def update_credentials(
        connection_name: str,
        credentials: dict[str, object] = Body(...),
    ) -> dict[str, object]:
        try:
            return update_connection_credentials(config_path, connection_name, credentials)
        except ConfigUpdateError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    @app.patch("/config/connections/{connection_name}/schedule")
    def update_schedule(
        connection_name: str,
        schedule: dict[str, object] = Body(...),
    ) -> dict[str, object]:
        try:
            return update_connection_schedule(config_path, connection_name, schedule)
        except ConfigUpdateError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    @app.post("/config/connections")
    def create_config_connection(
        connection: dict[str, object] = Body(...),
        x_admin_password: str | None = Header(default=None),
    ) -> dict[str, object]:
        _require_admin_password(x_admin_password)
        try:
            return add_connection_config(config_path, connection)
        except ConfigUpdateError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    @app.delete("/config/connections/{connection_name}")
    def delete_config_connection(
        connection_name: str,
        confirmation: dict[str, object] = Body(...),
        x_admin_password: str | None = Header(default=None),
    ) -> dict[str, object]:
        _require_admin_password(x_admin_password)
        if confirmation.get("confirm_name") != connection_name:
            raise HTTPException(status_code=400, detail="Connection name confirmation does not match")
        try:
            return delete_connection_config(config_path, connection_name)
        except ConfigUpdateError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    @app.get("/suppliers")
    def suppliers() -> dict[str, object]:
        return {"items": fetch_suppliers(db_path)}

    @app.get("/clients")
    def clients() -> dict[str, object]:
        return {"items": fetch_clients(db_path)}

    @app.get("/reports")
    def reports() -> dict[str, object]:
        return {"items": list_reports(report_dir)}

    @app.get("/reports/{report_name:path}")
    def report_file(report_name: str) -> FileResponse:
        root = report_dir.resolve()
        candidate = (root / report_name).resolve()
        if root not in candidate.parents or not candidate.is_file():
            raise HTTPException(status_code=404, detail="Report not found")
        return FileResponse(candidate, filename=candidate.name)

    @app.delete("/config/database")
    def delete_database(
        confirmation: dict[str, object] = Body(...),
        x_admin_password: str | None = Header(default=None),
    ) -> dict[str, object]:
        _require_admin_password(x_admin_password)
        if confirmation.get("confirm") != "DELETE_ALL_DATA":
            raise HTTPException(status_code=400, detail="Confirmation phrase incorrect")

        try:
            import sqlite3
            database_path = Path(db_path)
            if database_path.exists():
                try:
                    sqlite3.connect(database_path).close()
                except Exception:
                    pass
                import time
                time.sleep(0.5)
                database_path.unlink()
            store = SQLiteStore(database_path)
            store.initialize()
            return {"database_deleted": True, "message": "Base de dados apagada e reinicializada com sucesso"}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Erro ao apagar BD: {str(exc)}") from exc

    return app


def _require_admin_password(provided_password: str | None) -> None:
    expected_password = os.environ.get("INTEGRATION_ADMIN_PASSWORD")
    if not expected_password:
        raise HTTPException(status_code=403, detail="Admin password is not configured")
    if provided_password != expected_password:
        raise HTTPException(status_code=401, detail="Invalid admin password")
