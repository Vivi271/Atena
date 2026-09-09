"""
api.py — API REST para Atena (FastAPI)
Expone el pipeline RAG de neuroanatomía como endpoints HTTP
para ser consumidos desde Unity u otras aplicaciones externas.
"""

import os
import sys
from contextlib import asynccontextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

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

    # 3. Estilizar citas documentales y autores (Reconocedor universal robusto)
    def _estilizar_cita_fuente(match):
        fuente = match.group(1)
        pag = match.group(2) if match.group(2) else None
        if pag:
            return f'<color=#E5C07B><i>[Fuente {fuente}, pág. {pag}]</i></color>'
        return f'<color=#E5C07B><i>[Fuente {fuente}]</i></color>'

    # Captura: [Fuente X, p. Y], (Fuente X, pág. Y), (*[Fuente X], p. Y*), [Fuente X], etc.
    t = re.sub(
        r'[\(\[\*]*Fuente\s*(\d+)(?:[\]\)]?,?\s*(?:págs?\.?|pags?\.?|pp?\.?)\s*([\d\-–]+))?[\)\]\*]*',
        _estilizar_cita_fuente,
        t,
        flags=re.IGNORECASE,
    )

    # Citas con nombre de autor: (Clark, pág. 231), (*Clark, pág. 231*), (Lange, p. 195)
    def _estilizar_cita_autor(match):
        contenido = match.group(1).strip('*')
        return f'<color=#E5C07B><i>({contenido})</i></color>'

    t = re.sub(
        r'\((?:\*)?([A-ZÁÉÍÓÚ][a-záéíóúA-Z\s]+,?\s*(?:págs?\.?|pags?\.?|pp?\.?)\s*[\d\-–]+)(?:\*)?\)',
        _estilizar_cita_autor,
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

    # 8. Corregir dobles viñetas en la misma línea (ej. '• Título: • Contenido' -> '• Título: Contenido')
    t = re.sub(r'([•\-\*]\s*[^:\n]+:)\s*[•\-\*]\s*', r'\1 ', t)

    # 9. Destacar en negrita automáticamente los conceptos antes de dos puntos si el modelo los omitió
    t = re.sub(r'^[ \t]*[•\-\*]\s*(?!\<b\>)([^:\n]{3,70}:)', r'  • <b>\1</b>', t, flags=re.MULTILINE)

    # 10. Viñetas con jerarquía para móviles:
    # Sub-viñetas indentadas (con 2+ espacios): guión secundario indentado
    t = re.sub(r'^[ \t]{2,}[-*][ \t]+', '    – ', t, flags=re.MULTILINE)
    # Viñetas principales: punto limpio
    t = re.sub(r'^[ \t]*[-*][ \t]+', '  • ', t, flags=re.MULTILINE)

    # 11. Desamontonar: añadir espaciado y aire vertical entre introducciones, viñetas y conclusiones
    lineas_bloques = t.split("\n")
    resultado = []
    prev_era_item = False

    for l in lineas_bloques:
        l_strip = l.strip()
        if not l_strip:
            if resultado and resultado[-1] != "":
                resultado.append("")
            prev_era_item = False
            continue

        # Detectar si la línea actual es un elemento de lista (viñeta o numeral)
        es_item = bool(
            re.match(r'^\d+[\.\)]\s+', l_strip)
            or l_strip.startswith('•')
            or l_strip.startswith('–')
        )

        # Si inicia un ítem nuevo, o si salimos de una lista a un párrafo de texto normal (conclusión/síntesis)
        if (es_item or prev_era_item) and resultado and resultado[-1] != "":
            resultado.append("")

        resultado.append(l)
        prev_era_item = es_item

    t = "\n".join(resultado)
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


# ── Schemas de Evaluación ─────────────────────────────────────────────────────
class RespuestaEvaluacion(BaseModel):
    """Una opción de respuesta vinculada a una pregunta."""
    id: int
    texto: str
    es_correcta: bool

class PreguntaEvaluacion(BaseModel):
    """Una pregunta de autoevaluación con su tema, enunciado y lista de respuestas."""
    id: int
    enunciado: str
    tema: str
    nivel: str
    respuestas: List[RespuestaEvaluacion]

class PreguntasEvaluacionResponse(BaseModel):
    """Respuesta completa del endpoint de preguntas de evaluación."""
    nivel: str
    cantidad: int
    preguntas: List[PreguntaEvaluacion]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", tags=["Sistema"])
async def root():
    """Ruta raíz — mensaje de bienvenida, estado y acceso a la documentación."""
    return {
        "mensaje": "🧠 Atena — API de Neuroanatomía en línea",
        "servicio": "Atena API",
        "estado": "activo",
        "version": "1.0.0",
        "documentacion_swagger": "/docs",
        "endpoints": {
            "salud": "/salud",
            "info": "/info",
            "consultar_rag": "POST /consultar",
            "evaluacion_preguntas": "GET /api/evaluacion/preguntas",
        },
    }


@app.get("/salud", tags=["Sistema"])
async def salud():
    """Health check — verifica que el servidor está vivo y expone la URL pública del servicio."""
    # En Render, RENDER_EXTERNAL_URL contiene la URL pública automáticamente.
    # En local, se puede setear API_BASE_URL en el .env.
    url_publica = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("API_BASE_URL")
        or "http://localhost:8080"
    )
    return {
        "estado": "ok",
        "servicio": "Atena API",
        "version": "1.0.0",
        "vector_store_listo": vector_store is not None,
        "url_base": url_publica,
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
            "POST /consultar":                 "Consultar el asistente RAG con una pregunta",
            "GET  /api/evaluacion/preguntas":  "Generar preguntas de autoevaluación neuroanatómica",
            "GET  /salud":                     "Health check del servidor",
            "GET  /info":                      "Información del servicio y modelos activos",
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


# ── Endpoint de Evaluación ────────────────────────────────────────────────────
@app.get(
    "/api/evaluacion/preguntas",
    response_model=PreguntasEvaluacionResponse,
    tags=["Evaluación"],
)
async def obtener_preguntas_evaluacion(
    nivel: str = "avanzado",
    cantidad: Optional[int] = None,
    aleatorio: bool = False,
):
    """
    Retorna el banco de preguntas de autoevaluación neuroanatómica desde PostgreSQL (Supabase),
    cada una con su nivel, tema y sus 4 respuestas agrupadas indicando cuál es la correcta.

    Parámetros:
    - **nivel**: `basico` o `avanzado`
    - **cantidad**: número de preguntas a retornar (opcional; si se omite, devuelve todas las del nivel, ej: 15)
    - **aleatorio**: si es true, mezcla las preguntas aleatoriamente
    """
    try:
        from db_preguntas import obtener_preguntas_por_nivel
        preguntas_db = obtener_preguntas_por_nivel(nivel=nivel, cantidad=cantidad, aleatorio=aleatorio)

        preguntas = [
            PreguntaEvaluacion(
                id=p["id"],
                enunciado=p["enunciado"],
                tema=p["tema"],
                nivel=p["nivel"],
                respuestas=[
                    RespuestaEvaluacion(
                        id=r["id"],
                        texto=r["texto"],
                        es_correcta=r["es_correcta"],
                    )
                    for r in p.get("respuestas", [])
                ],
            )
            for p in preguntas_db
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener preguntas de evaluación desde la base de datos: {str(e)}",
        )

    return PreguntasEvaluacionResponse(
        nivel=nivel,
        cantidad=len(preguntas),
        preguntas=preguntas,
    )


# ── Arranque local ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
