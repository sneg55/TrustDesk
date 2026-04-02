FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --no-dev

# Copy application code
COPY src/ src/
COPY scripts/ scripts/

# Expose the FastAPI port
EXPOSE 8000

# Start the trading desk
CMD ["uv", "run", "python", "scripts/run_desk.py"]
