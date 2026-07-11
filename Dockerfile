# Stage 1: Builder (Bleibt gleich, hier wird nur gebaut, nicht das finale Image erzeugt)
FROM python:3.11-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY quantumwerewolf/ ./quantumwerewolf/
COPY web/server/requirements.txt ./web_requirements.txt

# Alle Abhängigkeiten als gepackte Archive (Wheels) vorbereiten
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r web_requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir=/wheels .


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Wir holen uns die gebauten Wheels aus der Builder-Stage
COPY --from=builder /wheels /wheels

# EXTREM ZERSTÜCKELT: Wir erzwingen viele kleine Layer, indem wir nach dem Alphabet installieren.
# Jedes RUN ist ein eigener Layer, der einzeln über das Netzwerk zu Nexus geschoben wird.
RUN bash -c "ls /wheels/[a-e]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[a-e]*.whl || true"
RUN bash -c "ls /wheels/[f-j]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[f-j]*.whl || true"
RUN bash -c "ls /wheels/[k-o]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[k-o]*.whl || true"
RUN bash -c "ls /wheels/[p-t]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[p-t]*.whl || true"
RUN bash -c "ls /wheels/[u-z]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[u-z]*.whl || true"

# Fallback-Layer für alles, was übrig bleibt (z.B. Dateien die mit Zahlen oder Großbuchstaben anfangen)
RUN pip install --no-cache-dir /wheels/*.whl || true

# Den temporären Ordner wieder löschen
RUN rm -rf /wheels

# Der Code wird auch einzeln kopiert (3 separate Layer)
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