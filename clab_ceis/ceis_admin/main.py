"""CEIS Admin – FastAPI application.

Endpoints
---------
GET  /                    – health check / welcome message
GET  /status              – status of all three managed apps
GET  /status/{app_name}   – status of a single managed app
POST /restart/{app_name}  – restart a single managed app
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException

from ceis_admin import config
from ceis_admin.process_manager import ProcessManager

_VALID_APPS = ("ceis_backend", "ceis_shop", "ceis_dashboard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Attach a shared ProcessManager and clean up on shutdown."""
    manager = ProcessManager()
    app.state.manager = manager
    yield
    manager.stop_all()


app = FastAPI(
    title="CEIS Admin",
    description="Monitor and control the CEIS backend, shop, and dashboard applications.",
    lifespan=lifespan,
)


def _get_manager() -> ProcessManager:
    return app.state.manager


def _validate_app_name(app_name: str) -> None:
    if app_name not in _VALID_APPS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown app '{app_name}'. Valid apps: {list(_VALID_APPS)}",
        )


@app.get("/")
def read_root():
    return {"message": "CEIS Admin is running", "managed_apps": list(_VALID_APPS)}


@app.get("/status")
def get_all_statuses():
    """Return the health status of all three managed applications."""
    return _get_manager().all_statuses()


@app.get("/status/{app_name}")
def get_app_status(app_name: str):
    """Return the health status of a single application."""
    _validate_app_name(app_name)
    managed = _get_manager().get(app_name)
    return managed.status()


@app.post("/restart/{app_name}")
def restart_app(app_name: str):
    """Restart a single application and return its updated status."""
    _validate_app_name(app_name)
    return _get_manager().restart(app_name)


def main():
    uvicorn.run(
        "ceis_admin.main:app",
        host=config.ADMIN_HOST,
        port=config.ADMIN_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
