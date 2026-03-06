from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
import pytest

pytestmark = pytest.mark.integration


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_backend(base_url: str, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/", timeout=1)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise TimeoutError("Backend did not become ready in time")


class _MockWiserHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status_code: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        if self.path == "/auth/token":
            self._send_json({"access_token": "ci-token"})
            return
        self._send_json({"detail": "not found"}, status_code=404)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/activity/"):
            self._send_json(
                {
                    "lcia_results": [
                        {"method": {"name": "IPCC 2021"}, "emissions": 0.2}
                    ]
                }
            )
            return
        self._send_json({"detail": "not found"}, status_code=404)

    def log_message(self, format, *args):
        return


def _start_mock_wiser(port: int) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", port), _MockWiserHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _start_backend(db_path: Path, backend_port: int, wiser_port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["CEIS_DB_PATH"] = str(db_path)
    env["CEIS_DISABLE_DISTANCE_SYNC"] = "1"
    env["WISER_AUTH_URL"] = f"http://127.0.0.1:{wiser_port}/auth/token"
    env["WISER_API_BASE_URL"] = f"http://127.0.0.1:{wiser_port}/api"

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ceis_backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(backend_port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_shop_backend_scenarios_contains_expected_content(tmp_path):
    wiser_port = _free_port()
    backend_port = _free_port()
    db_path = tmp_path / "integration_shop.db"

    mock_server, _ = _start_mock_wiser(wiser_port)
    proc = _start_backend(db_path, backend_port, wiser_port)
    base_url = f"http://127.0.0.1:{backend_port}"

    try:
        _wait_for_backend(base_url)
        response = requests.get(f"{base_url}/scenarios", timeout=10)
        assert response.status_code == 200

        scenarios = response.json()
        labels = {scenario.get("label") for scenario in scenarios}
        assert labels == {
            "Self repair (materials shipped)",
            "Repair at shop",
            "Send to manufacturer",
            "Buy New",
        }

        buy_new = next(s for s in scenarios if s.get("label") == "Buy New")
        assert buy_new["activities"]
        assert any(a.get("name") == "Garment Material" for a in buy_new["activities"])

        repair = next(s for s in scenarios if s.get("label") == "Self repair (materials shipped)")
        assert any(a.get("name") == "Fabric Block Material" for a in repair["activities"])
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        mock_server.shutdown()
        mock_server.server_close()
