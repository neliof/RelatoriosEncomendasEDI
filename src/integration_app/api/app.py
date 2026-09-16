from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from integration_app.api.read_models import (
    EventFilters,
    fetch_connections,
    fetch_config_summary,
    fetch_event_detail,
    fetch_events,
    fetch_summary,
    fetch_suppliers,
    list_reports,
)


def create_app(db_path: Path, report_dir: Path, config_path: Path = Path("config.yaml")) -> FastAPI:
    app = FastAPI(title="Relatorios Encomendas EDI EF API")
    static_dir = Path(__file__).with_name("static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

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

    @app.get("/suppliers")
    def suppliers() -> dict[str, object]:
        return {"items": fetch_suppliers(db_path)}

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

    return app
