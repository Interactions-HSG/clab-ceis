#!/bin/bash
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${WORKSPACE_DIR}/.devcontainer/codespaces.env"

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    . "$ENV_FILE"
fi

# Refresh the Wiser emission cache timestamps so entries don't expire between
# dev sessions. The emission factors themselves are still valid; only the TTL
# clock needs resetting so the backend can serve /garment-designer without
# waiting on live Wiser API calls.
DB_PATH="${CEIS_DB_PATH:-${WORKSPACE_DIR}/clab_ceis/ceis_backend/ceis_backend.db}"
export DB_PATH
python3 - <<'PYEOF'
import os, sqlite3, time
db = os.environ.get("DB_PATH", "")
if db and os.path.exists(db):
    with sqlite3.connect(db) as conn:
        result = conn.execute("UPDATE activity_emission_cache SET cached_at = ?", (time.time(),))
        if result.rowcount:
            print(f"Refreshed {result.rowcount} Wiser emission cache entries.")
PYEOF

ADMIN_PORT="${CEIS_ADMIN_PORT:-8053}"

start_if_not_running() {
    local name="$1"
    local port="$2"
    local dir="$3"
    local cmd="$4"
    local log="/tmp/${name}.log"

    if ! curl -s --max-time 1 "http://127.0.0.1:${port}" >/dev/null 2>&1; then
        echo "Starting ${name} on port ${port}..."
        # shellcheck disable=SC2086
        nohup uv run --directory "${dir}" ${cmd} >> "${log}" 2>&1 &
        disown
    else
        echo "${name} already running on port ${port}."
    fi
}

wait_for_port() {
    local name="$1"
    local port="$2"
    local timeout="${3:-30}"
    local elapsed=0

    echo "Waiting for ${name} on port ${port}..."
    while ! curl -s --max-time 1 "http://127.0.0.1:${port}" >/dev/null 2>&1; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ "$elapsed" -ge "$timeout" ]; then
            echo "WARNING: ${name} did not become ready within ${timeout}s."
            return 1
        fi
    done
    echo "${name} is ready."
}

# ceis_admin starts first and owns the lifecycle of the other services.
start_if_not_running "ceis_admin" "$ADMIN_PORT" \
    "${WORKSPACE_DIR}/clab_ceis/ceis_admin" "python main.py"
wait_for_port "ceis_admin" "$ADMIN_PORT"
