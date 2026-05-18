"""Configuration module for CEIS admin."""

import os
from pathlib import Path

ADMIN_HOST = os.getenv("CEIS_ADMIN_HOST", "0.0.0.0")
ADMIN_PORT = int(os.getenv("CEIS_ADMIN_PORT", "8053"))

# Base URLs used to health-check each managed app
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8052")
SHOP_URL = os.getenv("CEIS_SHOP_URL", "http://localhost:8050")
DASHBOARD_URL = os.getenv("CEIS_DASHBOARD_URL", "http://localhost:8051")

# Working directories for each app (resolved relative to this file's location
# so the admin app works regardless of CWD).
_HERE = Path(__file__).resolve().parent
_CLAB_ROOT = _HERE.parent

BACKEND_DIR = Path(os.getenv("CEIS_BACKEND_DIR", str(_CLAB_ROOT / "ceis_backend")))
SHOP_DIR = Path(os.getenv("CEIS_SHOP_DIR", str(_CLAB_ROOT / "ceis_shop")))
DASHBOARD_DIR = Path(os.getenv("CEIS_DASHBOARD_DIR", str(_CLAB_ROOT / "ceis_dashboard")))

# uv executable (must be on PATH or overridden via env)
UV_BIN = os.getenv("UV_BIN", "uv")

# Seconds to wait for a restarted app to become healthy before giving up
RESTART_HEALTH_TIMEOUT = int(os.getenv("CEIS_RESTART_HEALTH_TIMEOUT", "30"))
