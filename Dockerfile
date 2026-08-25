# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Atena (FastAPI + RAG + Gemini API)
# Deploy en Google Cloud Run
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

LABEL maintainer="Universidad Konrad Lorenz - Programa de Psicología"
LABEL description="Atena — Consultor RAG de Neuroanatomía (Cloud Run)"
LABEL version="3.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements_docker.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY api.py rag_pipeline.py config.py database.py ./
COPY components/ ./components/

# Copiar la ChromaDB ya indexada (corpus de neuroanatomía listo)
COPY chroma_neuro_db/ ./chroma_neuro_db/

# Copiar documentos fuente (por si se necesita re-indexar)
COPY Docs/ ./Docs/

# Exponer puerto de Cloud Run
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/salud || exit 1

# Arrancar FastAPI con uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
