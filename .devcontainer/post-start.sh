#!/bin/bash
# Start ceis_admin if it is not already listening on its port.
ADMIN_PORT="${CEIS_ADMIN_PORT:-8053}"

if ! curl -s --max-time 1 "http://127.0.0.1:${ADMIN_PORT}" >/dev/null 2>&1; then
    echo "Starting ceis_admin on port ${ADMIN_PORT}..."
    uv run --directory /workspaces/clab-ceis/clab_ceis/ceis_admin python main.py &
else
    echo "ceis_admin already running on port ${ADMIN_PORT}."
fi
