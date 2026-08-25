"""
api.py — API REST para Atena (FastAPI)
Expone el pipeline RAG de neuroanatomía como endpoints HTTP
para ser consumidos desde Unity u otras aplicaciones externas.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from dotenv import load_dotenv
load_dotenv()

# ── Lifespan: cargar el vector store una sola vez al arrancar ──────────────────
vector_store = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store
    print("🧠 Atena API — Cargando vector store...")
    try:
        from rag_pipeline import build_vector_store
        vector_store = build_vector_store(force_rebuild=False)
        print("✅ Vector store listo.")
    except Exception as e:
        print(f"❌ Error al cargar vector store: {e}")
    yield
    print("🔴 Atena API — Cerrando.")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Atena — API de Neuroanatomía",
    description=(
        "API REST del Consultor Especialista en Neuroanatomía (RAG). "
        "Expone el pipeline RAG con Gemini para ser consumido desde Unity u otros clientes."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — permite llamadas desde Unity (cualquier origen)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Schemas ────────────────────────────────────────────────────────────────────
class ConsultaRequest(BaseModel):
    pregunta: str
    nivel: str = "avanzado"   # "basico" | "avanzado"
    k: int = 6

class FuenteResponse(BaseModel):
    fuente: str
    pagina: Optional[int] = None
    fragmento: str

class ConsultaResponse(BaseModel):
    respuesta: str
    fuentes: List[FuenteResponse]
    nivel: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/salud", tags=["Sistema"])
async def salud():
    """Health check — verifica que el servidor está vivo."""
    return {
        "estado": "ok",
        "servicio": "Atena API",
        "version": "1.0.0",
        "vector_store_listo": vector_store is not None,
    }


@app.get("/info", tags=["Sistema"])
async def info():
    """Información general del servicio."""
    return {
        "nombre": "Atena — Consultor RAG de Neuroanatomía",
        "modelo_llm": "gemini-2.5-flash",
        "modelo_embeddings": "gemini-embedding-001",
        "endpoints": {
            "POST /consultar": "Enviar pregunta y recibir respuesta con fuentes",
            "GET  /salud":     "Health check",
            "GET  /info":      "Información del servicio",
        },
    }


@app.post("/consultar", response_model=ConsultaResponse, tags=["RAG"])
async def consultar_endpoint(body: ConsultaRequest):
    """
    Endpoint principal — recibe una pregunta y devuelve respuesta del RAG.

    Ejemplo JSON para Unity:
        { "pregunta": "¿Qué es el hipocampo?", "nivel": "basico" }
    """
    if vector_store is None:
        raise HTTPException(
            status_code=503,
            detail="El vector store no está disponible. El servidor puede estar iniciando.",
        )

    if not body.pregunta or not body.pregunta.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    try:
        from rag_pipeline import consultar
        resultado = consultar(
            pregunta=body.pregunta.strip(),
            vector_store=vector_store,
            k=body.k,
            nivel=body.nivel,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el pipeline RAG: {str(e)}")

    fuentes = []
    for f in resultado.get("fuentes", []):
        fuentes.append(FuenteResponse(
            fuente=f.get("fuente", "Desconocida"),
            pagina=f.get("pagina"),
            fragmento=f.get("fragmento", ""),
        ))

    return ConsultaResponse(
        respuesta=resultado.get("respuesta", ""),
        fuentes=fuentes,
        nivel=body.nivel,
    )


# ── Arranque local ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
