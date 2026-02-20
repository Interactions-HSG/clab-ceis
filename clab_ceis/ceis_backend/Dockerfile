# Use official Python image
FROM python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy only project files first (improves caching)
COPY pyproject.toml uv.lock /app/

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy the FastAPI application files
COPY . /app/

# Expose FastAPI port
EXPOSE 8052

# Default command to run FastAPI with uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8052", "--reload"]
