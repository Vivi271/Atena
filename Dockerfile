# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Atena (FastAPI + RAG + Gemini API)
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
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements_docker.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fuente y documentos
COPY api.py rag_pipeline.py config.py database.py ./
COPY components/ ./components/
COPY Docs/ ./Docs/

# Crear carpeta para ChromaDB
RUN mkdir -p chroma_neuro_db

# Exponer puerto por defecto
EXPOSE 8080

# Arrancar FastAPI con el puerto dinámico de Render/Cloud
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080}"]
