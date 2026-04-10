from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests
import pytest

from callbacks import api

pytestmark = pytest.mark.integration


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_backend(base_url: str, timeout_s: float = 25.0) -> None:
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


def _start_backend(db_path: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["CEIS_DB_PATH"] = str(db_path)
    env["CEIS_DISABLE_DISTANCE_SYNC"] = "1"

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ceis_backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_dashboard_api_reads_seeded_backend_data(tmp_path):
    db_path = tmp_path / "integration_dashboard.db"
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    proc = _start_backend(db_path, port)
    try:
        _wait_for_backend(base_url)
        api.config.BACKEND_API_URL = base_url

        garment_types = api.fetch_garment_types()
        assert any("Crop Top" in item["name"] for item in garment_types)

        fabric_block_types = requests.get(f"{base_url}/fabric-block-types", timeout=5)
        assert fabric_block_types.status_code == 200
        first_type = fabric_block_types.json()[0]
        first_fb_type_id = first_type["id"]
        first_fb_type_name = first_type["name"]

        process_types = requests.get(f"{base_url}/process-types", timeout=5)
        assert process_types.status_code == 200
        sewing_process_id = next(
            p["id"] for p in process_types.json() if p["name"] == "sewing"
        )

        locations = requests.get(f"{base_url}/locations", timeout=5)
        assert locations.status_code == 200
        st_gallen_location_id = next(
            l["id"] for l in locations.json() if l["name"] == "St. Gallen"
        )

        baseline_blocks = api.fetch_fabric_blocks()

        create_response = requests.post(
            f"{base_url}/fabric-blocks",
            json={
                "type_id": first_fb_type_id,
                "location_id": st_gallen_location_id,
                "processes": [{"process_id": sewing_process_id, "amount": 0.5}],
            },
            timeout=5,
        )
        assert create_response.status_code == 200

        blocks = api.fetch_fabric_blocks()
        assert len(blocks) == len(baseline_blocks) + 1

        matching_blocks = [
            block
            for block in blocks
            if block["type"] == first_fb_type_name
            and "sewing(0.5)" in block["processes"]
        ]
        assert matching_blocks
    finally:
        proc.terminate()
        proc.wait(timeout=10)
