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

RUN bash -c "ls /wheels/pydantic_core*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/pydantic_core*.whl || true"

# 2. Extrem feingranulare Zerstückelung (inklusive Großbuchstaben, falls ein Paket so anfängt)
RUN bash -c "ls /wheels/[a-cA-C]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[a-cA-C]*.whl || true"
RUN bash -c "ls /wheels/[d-fD-F]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[d-fD-F]*.whl || true"
RUN bash -c "ls /wheels/[g-iG-I]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[g-iG-I]*.whl || true"
RUN bash -c "ls /wheels/[j-lJ-L]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[j-lJ-L]*.whl || true"
RUN bash -c "ls /wheels/[m-oM-O]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[m-oM-O]*.whl || true"

# 'p' ist wegen pydantic, pytest etc. sehr schwer, daher spalten wir P nochmal auf:
RUN bash -c "ls /wheels/[pP]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[pP]*.whl || true"
RUN bash -c "ls /wheels/[q-sQ-S]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[q-sQ-S]*.whl || true"
RUN bash -c "ls /wheels/[t-vT-V]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[t-vT-V]*.whl || true"

# Der Rest, inklusive Zahlen
RUN bash -c "ls /wheels/[w-zW-Z0-9]*.whl >/dev/null 2>&1 && pip install --no-cache-dir /wheels/[w-zW-Z0-9]*.whl || true"

# WICHTIG: KEIN ALLGEMEINER *.whl FALLBACK LAYER MEHR! 
# Die Regex oben decken das komplette Alphabet und Zahlen ab. 

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