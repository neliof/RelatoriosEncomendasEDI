from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from integration_app.api.read_models import EventFilters, fetch_events, fetch_summary, fetch_suppliers, list_reports


def create_app(db_path: Path, report_dir: Path) -> FastAPI:
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

    @app.get("/suppliers")
    def suppliers() -> dict[str, object]:
        return {"items": fetch_suppliers(db_path)}

    @app.get("/reports")
    def reports() -> dict[str, object]:
        return {"items": list_reports(report_dir)}

    return app
