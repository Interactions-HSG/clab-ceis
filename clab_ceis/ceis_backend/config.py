"""Configuration module for CEIS backend."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from ceis_backend/.env.secrets, regardless of CWD
load_dotenv(BASE_DIR / ".env.secrets", override=True)

# Database path - ensures DB is always created in the ceis_backend directory
DB_PATH = str(BASE_DIR / "ceis_backend.db")

# Backend server configuration
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8052"))

# WISER API configuration
WISER_SP3_API_USER = os.getenv("WISER_SP3_API_USER", "")
WISER_SP3_API_KEY = os.getenv("WISER_SP3_API_KEY", "")
WISER_AUTH_URL = os.getenv(
    "WISER_AUTH_URL",
    "https://auth.wiser.ehealth.hevs.ch/realms/wiser/protocol/openid-connect/token",
)
WISER_API_BASE_URL = os.getenv(
    "WISER_API_BASE_URL",
    "https://api.wiser.ehealth.hevs.ch/ecoinvent/3.12-cutoff",
)
