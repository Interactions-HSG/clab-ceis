# Use the official Python image with version 3.12
FROM python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN mkdir -p /app/clab_ceis/
# Set the working directory
WORKDIR /app
COPY . /app/

# Run uv sync during build
RUN uv sync --frozen
