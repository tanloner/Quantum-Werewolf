# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY quantumwerewolf/ ./quantumwerewolf/
COPY web/server/requirements.txt ./web_requirements.txt

# Statt direkt zu installieren, bauen wir Wheels (gepackte Archive)
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r web_requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir=/wheels .

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kopiere die Wheels (das ist temporär und bläht das finale Image nicht auf, wenn wir sie danach löschen)
COPY --from=builder /wheels /wheels

# Layer aufteilen: Wir installieren die Abhängigkeiten in mehreren Schritten.
# Zuerst die Standard-Requirements
RUN pip install --no-cache-dir /wheels/uvicorn*.whl /wheels/fastapi*.whl || true
# Dann den Rest der externen Bibliotheken
RUN pip install --no-cache-dir /wheels/*.whl 

# Danach räumen wir den Wheel-Ordner auf, um Platz zu sparen
RUN rm -rf /wheels

COPY quantumwerewolf/ ./quantumwerewolf/
COPY web/server/ ./server/
COPY web/static/ ./static/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    CORS_ORIGINS="*" \
    DEBUG=false

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

EXPOSE 8000
ENV PYTHONPATH=/app
WORKDIR /app/server
CMD ["python", "-m", "uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "8000"]