# clab-prototype

Repository dedicated to prototypes for the Circular Lab. Currently it consits of two _mocks_:

- CEIS: the Circular Economy Information System
- A dashboard: it interacts with the CEIS to provide relevant information to the manufacturer
- A webshop: it interacts with the CEIS to get quote and register its orders

## Architecture

The overall idea is presented by the following diagram:

![alt text](doc/assets/overview.drawio.svg)


## How to run

All components can be run from the workspace root using `uv`:

### backend

```bash
uv run --directory clab_ceis/ceis_backend python main.py
```

### dashboard

```bash
uv run --directory clab_ceis/ceis_dashboard python main.py
```

### shop

```bash
uv run --directory clab_ceis/ceis_shop main.py
```

Then connect to `http://localhost:8050` (shop), `http://localhost:8051` (dashboard), and `http://localhost:8053` (admin)

### admin

```bash
uv run --directory clab_ceis/ceis_admin python main.py
```

Connect to `http://localhost:8053` to reach the admin API.

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | **Web UI** – status dashboard with restart buttons |
| `/ui` | GET | **Web UI alias** (same dashboard) |
| `/status` | GET | Health status of all three apps (JSON) |
| `/status/{app_name}` | GET | Health status of a single app (JSON) |
| `/restart` | POST | Restart all apps |
| `/restart/{app_name}` | POST | Restart a single app |

Valid `app_name` values: `ceis_backend`, `ceis_shop`, `ceis_dashboard`.

### Running with the Devcontainer

The `.devcontainer/post-create.sh` script installs dependencies for all components on container creation. In GitHub Codespaces it also prepares the admin UI hyperlinks to use Codespaces port-forwarding URLs instead of `localhost`. If the environment variable `CLAB_CEIS_RUN` is set, it also starts the backend, dashboard, and shop in the background automatically.

When the admin tool starts or restarts CEIS services, it writes their output to `/tmp/ceis_backend.log`, `/tmp/ceis_dashboard.log`, and `/tmp/ceis_shop.log`. The admin service itself logs to `/tmp/ceis_admin.log`.

## How to run tests

### backend

```bash
uv run --directory clab_ceis/ceis_backend pytest
```

To run tests with verbose output:

```bash
uv run --directory clab_ceis/ceis_backend pytest -v
```
