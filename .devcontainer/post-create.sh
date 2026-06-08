#!/bin/bash
pipx install uv
uv sync --directory ../clab-ceis/clab_ceis/ceis_dashboard
uv sync --directory ../clab-ceis/clab_ceis/ceis_backend
uv sync --directory ../clab-ceis/clab_ceis/ceis_shop
uv sync --directory ../clab-ceis/clab_ceis/ceis_admin

if [ "$CLAB_CEIS_RUN" = "S" ]; then
    BACKEND_PORT="${BACKEND_PORT:-8052}"

    wait_for_backend() {
        local port="$1"

        echo "Waiting for CEIS backend on port ${port}..."
        while ! curl -s --max-time 1 "http://127.0.0.1:${port}" >/dev/null 2>&1; do
            sleep 1
        done
        echo "CEIS backend is reachable on port ${port}."
    }

    echo "Running CEIS services..."
    uv run --directory ../clab-ceis/clab_ceis/ceis_backend python main.py &
    wait_for_backend "$BACKEND_PORT"
    uv run --directory ../clab-ceis/clab_ceis/ceis_dashboard python main.py &
    uv run --directory ../clab-ceis/clab_ceis/ceis_shop main.py &
    uv run --directory ../clab-ceis/clab_ceis/ceis_admin python main.py &
fi
