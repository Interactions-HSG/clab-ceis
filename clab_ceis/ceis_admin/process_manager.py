"""Process manager for the three CEIS applications.

Each application is launched via ``uv run python main.py`` inside its own
working directory, mirroring the manual start commands documented in the
project README.  The manager tracks the live :class:`subprocess.Popen`
handle for every app and can stop / restart it on demand.
"""

import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx

from ceis_admin import config


class ManagedApp:
    """Represents one managed sub-process."""

    def __init__(self, name: str, work_dir: Path, health_url: str) -> None:
        self.name = name
        self.work_dir = work_dir
        self.health_url = health_url
        self._process: Optional[subprocess.Popen] = None

    # ------------------------------------------------------------------
    # Process control
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the app if it is not already running."""
        if self._process is not None and self._process.poll() is None:
            return  # already running
        self._process = subprocess.Popen(
            [config.UV_BIN, "run", "python", "main.py"],
            cwd=self.work_dir,
        )

    def stop(self) -> None:
        """Terminate the app and wait for it to exit."""
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        self._process = None

    def restart(self) -> None:
        """Stop the app and start it again."""
        self.stop()
        self.start()

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        """Return *True* if the app answers HTTP requests on its health URL."""
        try:
            response = httpx.get(self.health_url, timeout=3.0)
            return response.status_code < 500
        except httpx.RequestError:
            return False

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return a status dictionary for this app."""
        process_running = (
            self._process is not None and self._process.poll() is None
        )
        healthy = self.is_healthy()
        return {
            "name": self.name,
            "process_running": process_running,
            "healthy": healthy,
            "pid": self._process.pid if process_running else None,
        }


class ProcessManager:
    """Manages the three CEIS applications."""

    APP_NAMES = ("ceis_backend", "ceis_shop", "ceis_dashboard")

    def __init__(self) -> None:
        self._apps: dict[str, ManagedApp] = {
            "ceis_backend": ManagedApp(
                name="ceis_backend",
                work_dir=config.BACKEND_DIR,
                health_url=config.BACKEND_URL,
            ),
            "ceis_shop": ManagedApp(
                name="ceis_shop",
                work_dir=config.SHOP_DIR,
                health_url=config.SHOP_URL,
            ),
            "ceis_dashboard": ManagedApp(
                name="ceis_dashboard",
                work_dir=config.DASHBOARD_DIR,
                health_url=config.DASHBOARD_URL,
            ),
        }

    def get(self, name: str) -> Optional[ManagedApp]:
        return self._apps.get(name)

    def all_statuses(self) -> list[dict]:
        return [app.status() for app in self._apps.values()]

    def restart(self, name: str) -> dict:
        """Restart a named app and wait until it becomes healthy (or times out).

        Returns a status dictionary for the restarted app.
        """
        app = self._apps[name]
        app.restart()

        deadline = time.monotonic() + config.RESTART_HEALTH_TIMEOUT
        while time.monotonic() < deadline:
            if app.is_healthy():
                break
            time.sleep(1)

        return app.status()

    def stop_all(self) -> None:
        for app in self._apps.values():
            app.stop()
