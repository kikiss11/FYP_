# Google Trends Scraper - Multi-stage Dockerfile
# Supports: API, Scheduler, Dashboard

# ===== Base Stage =====
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY config.yaml .

# Create data directory
RUN mkdir -p data

# ===== API Stage =====
FROM base as api

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ===== Scheduler Stage =====
FROM base as scheduler

CMD ["python", "-m", "src.scraper.scheduler"]

# ===== Dashboard Stage =====
FROM base as dashboard

EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]

# ===== Development Stage =====
FROM base as dev

# Install dev dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    httpx \
    black \
    ruff

# Enable hot reload
ENV PYTHONDONTWRITEBYTECODE=0

CMD ["bash"]

