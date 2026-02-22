#!/bin/bash
pipx install uv
uv sync --directory /workspaces/clab-ceis/clab_ceis/ceis_dashboard
uv sync --directory /workspaces/clab-ceis/clab_ceis/ceis_backend