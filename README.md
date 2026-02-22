# clab-prototype

Repository dedicated to prototypes for the Circular Lab. Currently it consits of two _mocks_:

- CEIS: the Circular Economy Information System
- A dashboard: it interacts with the CEIS to provide relevant information to the manufacturer
- A webshop: it interacts with the CEIS to get quote and register its orders

## How to run

### backend

```bash
cd clab_ceis/ceis_backend
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8052 --reload
```

### dashboard

```bash
cd clab_ceis/ceis_dashboard
uv sync
uv run python main.py
```

### shop

currently unavailable

Then connect to `http://localhost:8050` (shop) and `http://localhost:8051` (dashboard)

## Architecture

The overall idea is presented by the following diagram:

![alt text](doc/assets/overview.drawio.svg)
