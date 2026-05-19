"""Tests for the CEIS Admin FastAPI application."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ceis_admin.main import app


@pytest.fixture()
def client():
    """Return a TestClient with a mocked ProcessManager attached to app state."""
    manager = MagicMock()
    manager.all_statuses.return_value = [
        {"name": "ceis_backend", "process_running": True, "healthy": True, "pid": 1},
        {"name": "ceis_shop", "process_running": False, "healthy": False, "pid": None},
        {"name": "ceis_dashboard", "process_running": True, "healthy": True, "pid": 2},
    ]
    manager.get.side_effect = lambda name: _make_app_mock(name)
    manager.restart.side_effect = lambda name: {
        "name": name,
        "process_running": True,
        "healthy": True,
        "pid": 99,
    }

    with TestClient(app) as c:
        app.state.manager = manager
        yield c


def _make_app_mock(name: str) -> MagicMock:
    mock = MagicMock()
    mock.status.return_value = {
        "name": name,
        "process_running": True,
        "healthy": True,
        "pid": 42,
    }
    return mock


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "CEIS Admin is running"
    assert "ceis_backend" in data["managed_apps"]
    assert "ceis_shop" in data["managed_apps"]
    assert "ceis_dashboard" in data["managed_apps"]


def test_get_all_statuses(client):
    response = client.get("/status")
    assert response.status_code == 200
    statuses = response.json()
    assert isinstance(statuses, list)
    assert len(statuses) == 3
    names = {s["name"] for s in statuses}
    assert names == {"ceis_backend", "ceis_shop", "ceis_dashboard"}


def test_get_single_app_status(client):
    response = client.get("/status/ceis_backend")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ceis_backend"


def test_get_status_unknown_app(client):
    response = client.get("/status/unknown_app")
    assert response.status_code == 404


def test_restart_app(client):
    response = client.post("/restart/ceis_shop")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ceis_shop"
    assert data["process_running"] is True


def test_restart_unknown_app(client):
    response = client.post("/restart/nonexistent")
    assert response.status_code == 404


def test_ui_returns_html(client):
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CEIS Admin" in response.text
    assert "Restart All" in response.text


def test_restart_all_apps(client):
    response = client.post("/restart")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 3
    names = {r["name"] for r in results}
    assert names == {"ceis_backend", "ceis_shop", "ceis_dashboard"}
