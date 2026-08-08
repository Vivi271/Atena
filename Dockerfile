# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Consultor IA en Neuroanatomía (100% Local con Ollama)
# Universidad Konrad Lorenz · Programa de Psicología · Laboratorio de Neurociencias
# ─────────────────────────────────────────────────────────────────────────────
#
# NOTA: Este Dockerfile empaqueta SOLO la app Streamlit.
# Ollama debe correr en el HOST (PC del laboratorio), no dentro del contenedor.
#
# INSTRUCCIONES DE USO:
#
# 1. En el PC del laboratorio, tener Ollama corriendo con los modelos:
#    ollama pull nomic-embed-text
#    ollama pull llama3.2
#
# 2. Construir la imagen (desde la carpeta del proyecto):
#    docker build -t consultor-neuroanatomia .
#
# 3. Correr el contenedor:
#    docker run -p 8501:8501 \
#      -v "$(pwd)/Docs:/app/Docs" \
#      -v "$(pwd)/chroma_neuro_db:/app/chroma_neuro_db" \
#      --add-host=host.docker.internal:host-gateway \
#      -e OLLAMA_HOST=http://host.docker.internal:11434 \
#      consultor-neuroanatomia
#
# 4. Abrir en el navegador: http://localhost:8501
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Metadatos
LABEL maintainer="Universidad Konrad Lorenz - Programa de Psicología"
LABEL description="Consultor IA en Neuroanatomía - Sistema RAG 100% local"
LABEL version="2.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    OLLAMA_HOST=http://host.docker.internal:11434

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (aprovechar caché de Docker)
COPY requirements_docker.txt ./requirements.txt

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY app.py rag_pipeline.py config.py database.py style.css ./
COPY components/ ./components/

# Copiar configuración de Streamlit
COPY .streamlit/ ./.streamlit/

# Crear carpetas necesarias (Docs y chroma_neuro_db se montan como volúmenes)
RUN mkdir -p Docs chroma_neuro_db

# Exponer el puerto de Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Comando de inicio
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
