# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Atena (FastAPI + RAG Pipeline + Frontend Web)
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

LABEL maintainer="Universidad Konrad Lorenz - Programa de Psicología"
LABEL description="Atena — Consultor RAG de Neuroanatomía"
LABEL version="3.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libsqlite3-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar backend completo (código, persistencia y base vectorial) y documentos
COPY backend/ ./backend/
COPY Docs/ ./Docs/
# Copiar frontend web estático (servido por FastAPI en /)
COPY frontend/web/static/ ./frontend/web/static/

# Exponer puerto por defecto
EXPOSE 8080

# Arrancar FastAPI con el puerto dinámico de Render/Cloud
CMD ["sh", "-c", "PYTHONPATH=/app/backend uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
