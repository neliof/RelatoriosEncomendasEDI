#!/usr/bin/env python
"""Entry point for RelatoriosEncomendasEDI — Desktop/Windows Service executable.

Usage:
    python start_api.py                    # Start API on 127.0.0.1:8000
    python start_api.py --port 8001        # Custom port
    python start_api.py --host 0.0.0.0     # Listen on all interfaces
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from integration_app.api.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
