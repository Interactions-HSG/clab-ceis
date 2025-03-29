# Use official Python image
FROM python:3.12.2

# Install Poetry globally
RUN pip install --no-cache-dir poetry

# Set working directory
WORKDIR /app

# Copy only Poetry files first (improves caching)
COPY pyproject.toml poetry.lock /app/

# Install dependencies
RUN poetry install --no-root --no-interaction

# Copy the FastAPI application files
COPY . /app/

# Expose FastAPI port
EXPOSE 8052

# Default command to run FastAPI with Poetry
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
