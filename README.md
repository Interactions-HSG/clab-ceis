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

Then connect to `http://localhost:8050` (shop) and `http://localhost:8051` (dashboard)

### Running with the Devcontainer

The `.devcontainer/post-create.sh` script installs dependencies for all components on container creation. If the environment variable `CLAB_RUN_CEIS` is set, it also starts the backend, dashboard, and shop in the background automatically.

## How to run tests

### backend

```bash
uv run --directory clab_ceis/ceis_backend pytest
```

To run tests with verbose output:

```bash
uv run --directory clab_ceis/ceis_backend pytest -v
```
