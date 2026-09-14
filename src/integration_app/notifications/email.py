from __future__ import annotations


class EmailNotifier:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def send(self, subject: str, body: str) -> None:
        if not self.enabled:
            return None
        raise RuntimeError("Email notifications are not configured in the MVP")
