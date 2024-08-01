FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY core/requirements.txt /app/core/requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/core/requirements.txt


COPY core /app/core
COPY models /app/models
COPY config /app/config


ENV PYTHONPATH=/app:$PYTHONPATH
