from pathlib import Path

from integration_app.api.__main__ import build_parser


def test_api_cli_defaults_to_local_paths():
    parser = build_parser()

    args = parser.parse_args([])

    assert args.db == Path("data/integration.db")
    assert args.reports == Path("reports")
    assert args.host == "127.0.0.1"
    assert args.port == 8000
