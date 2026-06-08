#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/codespaces.env"

if [ -n "$CODESPACES" ]; then
    cat > "$ENV_FILE" <<EOF
export CEIS_BACKEND_LINK_URL="https://${CODESPACE_NAME}-8052.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/"
export CEIS_SHOP_LINK_URL="https://${CODESPACE_NAME}-8050.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/"
export CEIS_DASHBOARD_LINK_URL="https://${CODESPACE_NAME}-8051.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/"
EOF
else
    rm -f "$ENV_FILE"
fi

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
