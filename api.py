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
        "Expone el pipeline RAG con Groq para ser consumido desde Unity u otros clientes."
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


import re

# ── Formateador de texto para Unity (Rich Text) ────────────────────────────────
def formatear_para_unity(texto: str) -> str:
    """
    Convierte formato Markdown a Unity Rich Text (TextMeshPro / UI Text):
    - Convierte tablas Markdown a viñetas legibles en móvil
    - Elimina líneas divisorias '---'
    - **negrita** -> <b>negrita</b>
    - *cursiva* -> <i>cursiva</i>
    - viñetas con guión -> viñetas limpias '• '
    - Citas bibliográficas estilizadas en tono suave (<color=#E5C07B>)
    - Espaciado visual limpio y fluido estilo Claude / ChatGPT.
    """
    if not texto:
        return ""

    t = texto.replace("\r\n", "\n")

    # 1. Eliminar encabezados vacíos o símbolos markdown huérfanos tipo '###'
    t = re.sub(r'^\s*#{1,6}\s*$', '', t, flags=re.MULTILINE)

    # 2. Convertir tablas Markdown a viñetas limpias para interfaces móviles
    lineas = t.split("\n")
    nuevas_lineas = []
    en_tabla = False

    for linea in lineas:
        l_strip = linea.strip()
        # Ignorar divisores de tabla |---|---|
        if re.match(r"^\|?\s*:?-+:?\s*(\|?\s*:?-+:?\s*)+\|?$", l_strip):
            continue

        # Detectar fila de tabla con pipes | celda | celda |
        if l_strip.startswith("|") and l_strip.endswith("|") and l_strip.count("|") >= 2:
            celdas = [c.strip() for c in l_strip.strip("|").split("|")]
            if not en_tabla:
                en_tabla = True
                continue
            else:
                if len(celdas) >= 2:
                    primer_campo = celdas[0]
                    resto = [c for c in celdas[1:] if c]
                    nuevas_lineas.append(f"  • <b>{primer_campo}:</b> " + " — ".join(resto))
                elif celdas:
                    nuevas_lineas.append(f"  • {celdas[0]}")
                continue
        else:
            en_tabla = False

        # Eliminar líneas divisorias tipo --- o ***
        if re.match(r"^-{3,}$", l_strip) or re.match(r"^\*{3,}$", l_strip):
            continue

        nuevas_lineas.append(linea)

    t = "\n".join(nuevas_lineas)

    # 3. Estilizar citas documentales: [Fuente X, pág. Y], (Fuente X, pág. Y), (*[Fuente X]*)
    def _estilizar_cita_fuente(match):
        fuente = match.group(1)
        pag = match.group(2) if match.group(2) else None
        if pag:
            return f'<color=#E5C07B><i>[Fuente {fuente}, pág. {pag}]</i></color>'
        return f'<color=#E5C07B><i>[Fuente {fuente}]</i></color>'

    t = re.sub(
        r'[\(\[]\*?Fuente\s*(\d+)(?:,?\s*pág\.?\s*(\d+))?\*?[\)\]]',
        _estilizar_cita_fuente,
        t,
        flags=re.IGNORECASE,
    )

    # Citas con nombre de autor: (*Clark, pág. 231*) -> <color=#E5C07B><i>(Clark, pág. 231)</i></color>
    t = re.sub(
        r'\(\*([^*]+(?:pág\.?|p\.)[^*]+)\*\)',
        r'<color=#E5C07B><i>(\1)</i></color>',
        t,
    )

    # 4. Negrita y cursiva combinadas: ***texto*** -> <b><i>texto</i></b>
    t = re.sub(r'\*\*\*([^\*\n]+)\*\*\*', r'<b><i>\1</i></b>', t)

    # 5. Negrita: **texto** -> <b>texto</b>
    t = re.sub(r'\*\*([^\*\n]+)\*\*', r'<b>\1</b>', t)

    # 6. Cursiva restante: *texto* -> <i>texto</i> (sin romper etiquetas ya generadas)
    t = re.sub(r'(?<![<\w\*])\*([^\*\n]+)\*(?![>\w\*])', r'<i>\1</i>', t)

    # 7. Encabezados markdown (# Titulo, ## Titulo) -> <b>Titulo</b>
    t = re.sub(r'^#{1,4}\s+(.+)$', r'<b>\1</b>', t, flags=re.MULTILINE)

    # 8. Viñetas con jerarquía para móviles:
    # Sub-viñetas indentadas (con espacios): guión secundario indentado
    t = re.sub(r'^[ \t]{2,}[-*][ \t]+', '    – ', t, flags=re.MULTILINE)
    # Viñetas principales: punto limpio
    t = re.sub(r'^[ \t]*[-*][ \t]+', '  • ', t, flags=re.MULTILINE)

    # 9. Espaciado limpio entre secciones numeradas para que respire en pantallas móviles
    t = re.sub(r'\n(?=\d+\.\s+)', r'\n\n', t)
    t = re.sub(r'\n{3,}', '\n\n', t)

    return t.strip()


# ── Schemas ────────────────────────────────────────────────────────────────────
class ConsultaRequest(BaseModel):
    pregunta: str
    nivel: str = "avanzado"   # "basico" | "avanzado"
    k: int = 6
    formato_unity: bool = True  # Convierte Markdown a Rich Text para Unity

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
    from rag_pipeline import GROQ_LLM_MODEL, GROQ_EMBED_MODEL
    return {
        "nombre": "Atena — Consultor RAG de Neuroanatomía",
        "modelo_llm": GROQ_LLM_MODEL,
        "modelo_embeddings": GROQ_EMBED_MODEL,
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
    from config import nombre_legible
    for f in resultado.get("fuentes", []):
        raw_pag = f.get("pagina")
        pag_int = None
        try:
            if raw_pag is not None and str(raw_pag).isdigit():
                pag_int = int(raw_pag)
        except Exception:
            pag_int = None

        fuentes.append(FuenteResponse(
            fuente=nombre_legible(f.get("fuente", "Desconocida")),
            pagina=pag_int,
            fragmento=f.get("fragmento", ""),
        ))

    texto_respuesta = resultado.get("respuesta", "")
    if body.formato_unity:
        texto_respuesta = formatear_para_unity(texto_respuesta)

    return ConsultaResponse(
        respuesta=texto_respuesta,
        fuentes=fuentes,
        nivel=body.nivel,
    )


# ── Arranque local ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
