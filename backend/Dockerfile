# Multi-stage build for the backend FastAPI app.
# Stage 1 builds a wheel cache from requirements.txt; stage 2 is a slim
# runtime that only carries the installed packages and app source.

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# System deps needed at *build* time: pdfplumber pulls in cryptography and a
# few wheels still need a compiler on 3.12.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip wheel --wheel-dir /wheels -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Tooling needed at runtime by pdfplumber/pypdf2 (libxml/libjpeg) — slim enough
# that we don't bother trimming further.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libxml2 libjpeg62-turbo \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 1000 app

COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# Application source.
COPY backend ./backend

RUN mkdir -p /data/chroma /data/uploads /data/temp /app/logs \
 && chown -R app:app /data /app

USER app

ENV CHROMA_PERSIST_DIRECTORY=/data/chroma \
    UPLOAD_DIR=/data/uploads \
    TEMP_DIR=/data/temp \
    DOCUMENT_DB_PATH=/data/documents.sqlite \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/health', timeout=3); sys.exit(0)" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
