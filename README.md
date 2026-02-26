# clab-prototype

Repository dedicated to prototypes for the Circular Lab. Currently it consits of two _mocks_:

- CEIS: the Circular Economy Information System
- A dashboard: it interacts with the CEIS to provide relevant information to the manufacturer
- A webshop: it interacts with the CEIS to get quote and register its orders

## How to run

All components can be run from the workspace root using `uv`:

### backend

```bash
uv run --directory clab_ceis/ceis_backend uvicorn main:app --host 0.0.0.0 --port 8052 --reload
```

### dashboard

```bash
uv run --directory clab_ceis/ceis_dashboard python main.py
```

### shop

```bash
uv run --directory clab_ceis/shop ceis-shop
```

Then connect to `http://localhost:8050` (shop) and `http://localhost:8051` (dashboard)

## Architecture

The overall idea is presented by the following diagram:

![alt text](doc/assets/overview.drawio.svg)
