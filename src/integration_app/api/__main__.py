from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from integration_app.api.app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="integration-api")
    parser.add_argument("--db", type=Path, default=Path("data/integration.db"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = create_app(args.db, args.reports)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
