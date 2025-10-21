import os

CEIS_SHOP_HOSTNAME = os.getenv("CEIS_SHOP_HOSTNAME", "localhost")
CEIS_SHOP_PORT = os.getenv("CEIS_SHOP_PORT", "8050")
CEIS_MONITOR_HOSTNAME = os.getenv("CEIS_MONITOR_HOSTNAME", "localhost")
CEIS_MONITOR_PORT = os.getenv("CEIS_MONITOR_PORT", "8051")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://ceis-backend:8052")