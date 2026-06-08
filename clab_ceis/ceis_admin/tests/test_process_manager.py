"""Tests for ProcessManager and ManagedApp."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ceis_admin.process_manager import ManagedApp, ProcessManager


# ---------------------------------------------------------------------------
# ManagedApp
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_mock(tmp_path):
    """Return a ManagedApp pointing at a tmp work dir."""
    return ManagedApp(
        name="test_app",
        work_dir=tmp_path,
        health_url="http://localhost:9999",
    )


def test_is_healthy_true(app_mock):
    response = MagicMock()
    response.status_code = 200
    with patch("ceis_admin.process_manager.httpx.get", return_value=response):
        assert app_mock.is_healthy() is True


def test_is_healthy_false_on_request_error(app_mock):
    import httpx

    with patch(
        "ceis_admin.process_manager.httpx.get",
        side_effect=httpx.RequestError("conn refused"),
    ):
        assert app_mock.is_healthy() is False


def test_status_not_running(app_mock):
    import httpx as _httpx

    with patch(
        "ceis_admin.process_manager.httpx.get",
        side_effect=_httpx.RequestError("conn refused"),
    ):
        status = app_mock.status()
    assert status["name"] == "test_app"
    assert status["process_running"] is False
    assert status["pid"] is None


def test_stop_when_not_started(app_mock):
    """stop() should be a no-op when no process was ever started."""
    app_mock.stop()  # must not raise


def test_restart_calls_stop_then_start(app_mock, tmp_path):
    with patch("ceis_admin.process_manager.subprocess.Popen") as mock_popen:
        fake_proc = MagicMock()
        fake_proc.poll.return_value = None
        mock_popen.return_value = fake_proc

        app_mock.start()
        assert app_mock._process is fake_proc

        app_mock.restart()
        # Popen should have been called twice (start + restart)
        assert mock_popen.call_count == 2


def test_start_logs_output_to_file(app_mock):
    import httpx
    import subprocess

    with patch("ceis_admin.process_manager.subprocess.Popen") as mock_popen, \
            patch(
                "ceis_admin.process_manager.httpx.get",
                side_effect=httpx.RequestError("conn refused"),
            ):
        fake_proc = MagicMock()
        fake_proc.poll.return_value = None
        mock_popen.return_value = fake_proc

        app_mock.start()

    _, kwargs = mock_popen.call_args
    assert kwargs["stdout"].name == f"/tmp/{app_mock.name}.log"
    assert kwargs["stderr"] == subprocess.STDOUT
    kwargs["stdout"].close()


def test_stop_closes_log_handle(app_mock):
    fake_proc = MagicMock()
    fake_proc.poll.return_value = 0
    fake_log = MagicMock()
    app_mock._process = fake_proc
    app_mock._log_handle = fake_log

    app_mock.stop()

    fake_log.close.assert_called_once()
    assert app_mock._log_handle is None


# ---------------------------------------------------------------------------
# ProcessManager
# ---------------------------------------------------------------------------


def test_process_manager_has_three_apps():
    manager = ProcessManager()
    for name in ("ceis_backend", "ceis_shop", "ceis_dashboard"):
        assert manager.get(name) is not None


def test_process_manager_get_unknown_returns_none():
    manager = ProcessManager()
    assert manager.get("does_not_exist") is None


def test_all_statuses_returns_three_entries():
    import httpx as _httpx

    manager = ProcessManager()
    with patch(
        "ceis_admin.process_manager.httpx.get",
        side_effect=_httpx.RequestError("conn refused"),
    ):
        statuses = manager.all_statuses()
    assert len(statuses) == 3


def test_restart_unknown_raises_key_error():
    manager = ProcessManager()
    with pytest.raises(KeyError):
        manager.restart("nonexistent_app")


def test_start_skips_if_externally_healthy(app_mock):
    """start() must not spawn a process if the app is already responding."""
    response = MagicMock()
    response.status_code = 200
    with patch("ceis_admin.process_manager.subprocess.Popen") as mock_popen, \
            patch("ceis_admin.process_manager.httpx.get", return_value=response):
        app_mock.start()
        mock_popen.assert_not_called()


def test_start_all_starts_all_three_apps():
    manager = ProcessManager()
    with patch.object(manager._apps["ceis_backend"], "start") as mock_backend, \
            patch.object(manager._apps["ceis_backend"], "is_healthy", return_value=True), \
            patch.object(manager._apps["ceis_dashboard"], "start") as mock_dashboard, \
            patch.object(manager._apps["ceis_shop"], "start") as mock_shop:
        manager.start_all()
    mock_backend.assert_called_once()
    mock_dashboard.assert_called_once()
    mock_shop.assert_called_once()


def test_start_all_starts_backend_before_others():
    manager = ProcessManager()
    call_order = []
    with patch.object(manager._apps["ceis_backend"], "start", side_effect=lambda: call_order.append("backend")), \
            patch.object(manager._apps["ceis_backend"], "is_healthy", return_value=True), \
            patch.object(manager._apps["ceis_dashboard"], "start", side_effect=lambda: call_order.append("dashboard")), \
            patch.object(manager._apps["ceis_shop"], "start", side_effect=lambda: call_order.append("shop")):
        manager.start_all()
    assert call_order[0] == "backend"
    assert set(call_order[1:]) == {"dashboard", "shop"}
