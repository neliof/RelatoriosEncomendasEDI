import logging
from pathlib import Path

from integration_app.logging_setup import configure_json_logging


class TrackingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.closed_by_configure = False

    def emit(self, record: logging.LogRecord) -> None:
        return None

    def close(self) -> None:
        self.closed_by_configure = True
        super().close()


def test_configure_json_logging_closes_existing_handlers(tmp_path: Path):
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    tracking_handler = TrackingHandler()
    root.handlers.clear()
    root.addHandler(tracking_handler)

    try:
        configure_json_logging(tmp_path / "logs")
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers.clear()
        for handler in original_handlers:
            root.addHandler(handler)

    assert tracking_handler.closed_by_configure is True
