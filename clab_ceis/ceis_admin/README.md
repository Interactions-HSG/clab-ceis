# ceis_admin

Admin application that monitors and controls the three CEIS applications:
`ceis_backend`, `ceis_shop`, and `ceis_dashboard`.

## Running

```bash
uv run --directory clab_ceis/ceis_admin python main.py
```

The server starts on `http://localhost:8053` by default.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message |
| GET | `/status` | Status of all three managed apps |
| GET | `/status/{app_name}` | Status of a single app |
| POST | `/restart/{app_name}` | Restart a single app |

Valid `app_name` values: `ceis_backend`, `ceis_shop`, `ceis_dashboard`.

### Example – check all statuses

```bash
curl http://localhost:8053/status
```

```json
[
  {"name": "ceis_backend", "process_running": true, "healthy": true, "pid": 1234},
  {"name": "ceis_shop",    "process_running": true, "healthy": true, "pid": 1235},
  {"name": "ceis_dashboard","process_running": true, "healthy": true, "pid": 1236}
]
```

### Example – restart the shop

```bash
curl -X POST http://localhost:8053/restart/ceis_shop
```

## Configuration

All settings can be overridden via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CEIS_ADMIN_HOST` | `0.0.0.0` | Admin server bind host |
| `CEIS_ADMIN_PORT` | `8053` | Admin server port |
| `BACKEND_API_URL` | `http://localhost:8052` | Backend health-check URL |
| `CEIS_SHOP_URL` | `http://localhost:8050` | Shop health-check URL |
| `CEIS_DASHBOARD_URL` | `http://localhost:8051` | Dashboard health-check URL |
| `CEIS_BACKEND_DIR` | `../ceis_backend` | Working directory for backend process |
| `CEIS_SHOP_DIR` | `../ceis_shop` | Working directory for shop process |
| `CEIS_DASHBOARD_DIR` | `../ceis_dashboard` | Working directory for dashboard process |
| `UV_BIN` | `uv` | Path to the `uv` executable |
| `CEIS_RESTART_HEALTH_TIMEOUT` | `30` | Seconds to wait for a restarted app to become healthy |

## Running tests

```bash
uv run --directory clab_ceis/ceis_admin pytest
```
