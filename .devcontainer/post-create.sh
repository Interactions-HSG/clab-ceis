#!/bin/bash
pipx install uv
uv sync --directory /workspaces/clab-ceis/clab_ceis/ceis_dashboard
uv sync --directory /workspaces/clab-ceis/clab_ceis/ceis_backend
uv sync --directory /workspaces/clab-ceis/clab_ceis/ceis_shop

if [ -n "$CLAB_RUN_CEIS" ]; then
    uv run --directory /workspaces/clab-ceis/clab_ceis/ceis_backend python main.py &
    uv run --directory /workspaces/clab-ceis/clab_ceis/ceis_dashboard python main.py &
    uv run --directory /workspaces/clab-ceis/clab_ceis/ceis_shop main.py &
fi
