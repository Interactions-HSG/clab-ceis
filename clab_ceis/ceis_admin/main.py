"""CEIS Admin – FastAPI application.

Endpoints
---------
GET  /                    – health check / welcome message
GET  /ui                  – minimal web UI (HTML)
GET  /status              – status of all three managed apps
GET  /status/{app_name}   – status of a single managed app
POST /restart             – restart all managed apps
POST /restart/{app_name}  – restart a single managed app
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from ceis_admin import config
from ceis_admin.process_manager import ProcessManager

_VALID_APPS = ("ceis_backend", "ceis_shop", "ceis_dashboard")

_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CEIS Admin</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, sans-serif;
      background: #f4f6f8;
      color: #1a1a2e;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1rem;
    }
    h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
    .subtitle { color: #666; font-size: 0.9rem; margin-bottom: 2rem; }
    .card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1.25rem;
      width: 100%;
      max-width: 900px;
    }
    .card {
      background: #fff;
      border-radius: 10px;
      padding: 1.25rem 1.5rem;
      box-shadow: 0 2px 8px rgba(0,0,0,.08);
      display: flex;
      flex-direction: column;
      gap: .75rem;
    }
    .card-title {
      font-weight: 600;
      font-size: 1rem;
      display: flex;
      align-items: center;
      gap: .5rem;
    }
    .badge {
      display: inline-block;
      padding: .2rem .55rem;
      border-radius: 999px;
      font-size: .72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .05em;
    }
    .badge-up   { background: #d1fae5; color: #065f46; }
    .badge-down { background: #fee2e2; color: #991b1b; }
    .badge-wait { background: #fef9c3; color: #92400e; }
    .meta { font-size: .8rem; color: #555; }
    .btn {
      cursor: pointer;
      border: none;
      border-radius: 6px;
      padding: .45rem .9rem;
      font-size: .85rem;
      font-weight: 600;
      transition: opacity .15s;
    }
    .btn:hover { opacity: .82; }
    .btn:disabled { opacity: .45; cursor: not-allowed; }
    .btn-restart { background: #3b82f6; color: #fff; }
    .btn-restart-all { background: #6366f1; color: #fff; width: 100%; max-width: 900px; padding: .65rem; font-size: .95rem; margin-bottom: 1.5rem; border-radius: 8px; }
    .status-row { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
    .refresh-note { margin-top: 1.5rem; font-size: .75rem; color: #999; }
    #last-updated { font-size: .75rem; color: #888; margin-bottom: 1.25rem; }
  </style>
</head>
<body>
  <h1>CEIS Admin</h1>
  <p class="subtitle">Monitor &amp; control the CEIS stack</p>
  <div id="last-updated">Loading…</div>
  <button class="btn btn-restart-all" onclick="restartAll(this)">⟳ Restart All</button>
  <div class="card-grid" id="cards"></div>
  <p class="refresh-note">Status refreshes automatically every 4 seconds.</p>

  <script>
    const APPS = ["ceis_backend", "ceis_shop", "ceis_dashboard"];

    function badgeHtml(status) {
      if (status.healthy) return '<span class="badge badge-up">up</span>';
      if (status.process_running) return '<span class="badge badge-wait">starting</span>';
      return '<span class="badge badge-down">down</span>';
    }

    function renderCards(statuses) {
      const grid = document.getElementById("cards");
      grid.innerHTML = "";
      for (const s of statuses) {
        const card = document.createElement("div");
        card.className = "card";
        card.id = "card-" + s.name;
        card.innerHTML = `
          <div class="card-title">
            ${badgeHtml(s)}
            <span>${s.name}</span>
          </div>
          <div class="status-row meta">
            <span>Process: ${s.process_running ? "running (PID " + s.pid + ")" : "not running"}</span>
          </div>
          <button class="btn btn-restart" onclick="restartApp('${s.name}', this)">⟳ Restart</button>
        `;
        grid.appendChild(card);
      }
    }

    async function fetchStatus() {
      try {
        const resp = await fetch("/status");
        if (!resp.ok) return;
        const data = await resp.json();
        renderCards(data);
        document.getElementById("last-updated").textContent =
          "Last updated: " + new Date().toLocaleTimeString();
      } catch (_) {}
    }

    async function restartApp(name, btn) {
      btn.disabled = true;
      btn.textContent = "Restarting…";
      try {
        await fetch("/restart/" + name, { method: "POST" });
        await fetchStatus();
      } finally {
        btn.disabled = false;
        btn.textContent = "⟳ Restart";
      }
    }

    async function restartAll(btn) {
      btn.disabled = true;
      btn.textContent = "Restarting all…";
      try {
        await fetch("/restart", { method: "POST" });
        await fetchStatus();
      } finally {
        btn.disabled = false;
        btn.textContent = "⟳ Restart All";
      }
    }

    fetchStatus();
    setInterval(fetchStatus, 4000);
  </script>
</body>
</html>"""


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


@app.get("/ui", response_class=HTMLResponse)
def get_ui():
    """Serve the minimal web UI."""
    return HTMLResponse(content=_UI_HTML)


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


@app.post("/restart")
def restart_all_apps():
    """Restart all managed applications and return their updated statuses."""
    manager = _get_manager()
    results = []
    for name in _VALID_APPS:
        results.append(manager.restart(name))
    return results


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
