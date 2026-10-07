"""
api.py — API REST para Atena (FastAPI)
Expone el pipeline RAG de neuroanatomía como endpoints HTTP
para ser consumidos desde Unity u otras aplicaciones externas.
"""

import os
import logging
import sys
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("atena.api")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, HTTPException, Query
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
    logger.info("Atena API — Cargando vector store...")
    try:
        from rag_pipeline import build_vector_store
        vector_store = build_vector_store(force_rebuild=False)
        logger.info("Vector store listo.")
    except Exception as e:
        logger.error(f"Error al cargar vector store: {e}")
    yield
    logger.info("Atena API — Cerrando.")


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

# CORS — permite llamadas desde el frontend web y Unity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

import re
from collections import deque
import time as _time
from datetime import datetime as _dt
from fastapi import Header

# ── Registro en memoria de consultas de la sesión actual ─────────────────────
# Guarda las últimas 200 consultas desde que el servidor arrancó (sin BD)
_SESSION_LOG: deque = deque(maxlen=200)
_SESSION_START = _dt.now()


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
    nivel: str = "Principiante"   # "Principiante" | "Avanzado" | "General"
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
    nivel: Optional[str] = "todos"
    cantidad: int
    preguntas: List[PreguntaEvaluacion]


class PreguntaAdminRequest(BaseModel):
    """Payload para crear o editar una pregunta de evaluación."""
    nivel: str
    tema: str
    enunciado: str
    opcion_a: str
    opcion_b: str
    opcion_c: str
    opcion_d: str
    correcta: str  # "A", "B", "C" o "D"


# ── Endpoints ──────────────────────────────────────────────────────────────────

from fastapi.responses import FileResponse as _FileResponse

@app.get("/", tags=["Sistema"], include_in_schema=False)
async def root():
    """Sirve el frontend web (index.html). Documentación de la API en /docs."""
    static_index = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "web", "static", "index.html"
    )
    if os.path.isfile(static_index):
        return _FileResponse(static_index)
    # Fallback JSON si el frontend no está presente
    return {
        "mensaje": "🧠 Atena — API de Neuroanatomía en línea",
        "documentacion": "/docs",
        "salud": "/salud",
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
    try:
        from rag_pipeline import GROQ_LLM_MODEL, GROQ_EMBED_MODEL
        llm_model = GROQ_LLM_MODEL
        embed_model = GROQ_EMBED_MODEL
    except ImportError:
        llm_model = os.environ.get("GROQ_LLM_MODEL", "(no disponible en dev local)")
        embed_model = os.environ.get("EMBED_MODEL", "(no disponible en dev local)")
    return {
        "nombre": "Atena — Consultor RAG de Neuroanatomía",
        "modelo_llm": llm_model,
        "modelo_embeddings": embed_model,
        "endpoints": {
            "POST /consultar":                 "Consultar el asistente RAG con una pregunta",
            "GET  /api/evaluacion/preguntas":  "Generar preguntas de autoevaluación neuroanatómica",
            "GET  /salud":                     "Health check del servidor",
            "GET  /info":                      "Información del servicio y modelos activos",
        },
    }


@app.post("/consultar", response_model=ConsultaResponse, tags=["RAG"])
@app.post("/api/consultar", response_model=ConsultaResponse, tags=["RAG"])
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
        t0 = _time.time()
        resultado = consultar(
            pregunta=body.pregunta.strip(),
            vector_store=vector_store,
            k=body.k,
            nivel=body.nivel,
        )
        latencia = round(_time.time() - t0, 2)
        # Registrar en log de sesión (en memoria, instantáneo, sin BD)
        _SESSION_LOG.append({
            "fecha": _dt.now().isoformat(timespec='seconds'),
            "pregunta": body.pregunta.strip()[:120],
            "nivel": body.nivel,
            "latencia": latencia,
        })
        # Intentar guardar en Supabase (si está disponible) sin bloquear
        try:
            from db_metrics import registrar_consulta
            registrar_consulta(
                pregunta=body.pregunta.strip(),
                respuesta=resultado.get("respuesta", ""),
                nivel=body.nivel,
                latencia=latencia,
            )
        except Exception:
            pass  # Supabase no disponible, no es crítico
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
    nivel: Optional[str] = Query(
        None,
        description="Nivel a consultar exactamente como está en Supabase: 'Principiante', 'Avanzado' o 'General' (o 'todos' / omitir para traer las 45 preguntas).",
        examples=["Principiante", "Avanzado", "General"]
    ),
    cantidad: Optional[int] = Query(None, description="Número de preguntas a retornar (ej: 5 o 15). Si se omite, retorna todas las del nivel."),
    aleatorio: bool = Query(True, description="Mezcla las preguntas aleatoriamente si es true."),
):
    """
    Retorna el banco de preguntas de autoevaluación neuroanatómica desde PostgreSQL (Supabase),
    cada una con su nivel, tema y sus 4 respuestas agrupadas indicando cuál es la correcta.

    Parámetros:
    - **nivel**: `Principiante`, `Avanzado` o `General` (exactamente como está en Supabase, opcional; si se omite devuelve todas las preguntas)
    - **cantidad**: número de preguntas a retornar (opcional; si se omite, devuelve todas las disponibles)
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
        nivel=nivel or "todos",
        cantidad=len(preguntas),
        preguntas=preguntas,
    )


# ── Admin: autenticación por PIN (PIN se lee de Supabase, cambiable desde el panel) ──
from fastapi import Header, UploadFile, File

def _verificar_pin(x_admin_pin: str = Header(..., alias="X-Admin-Pin")):
    """Verifica el PIN contra el valor guardado en Supabase (o env var como fallback)."""
    try:
        from db_metrics import get_pin
        pin_correcto = get_pin()
    except Exception:
        pin_correcto = os.environ.get("ADMIN_PIN", "12345")
    if x_admin_pin != pin_correcto:
        raise HTTPException(status_code=403, detail="PIN de administrador incorrecto.")


# ── Endpoints de Administración de Documentos ─────────────────────────────────

@app.get("/api/admin/documents", tags=["Admin"])
async def listar_documentos(x_admin_pin: str = Header(..., alias="X-Admin-Pin")):
    """Lista los documentos PDF/DOCX disponibles en la carpeta Docs/."""
    _verificar_pin(x_admin_pin)
    try:
        try:
            from rag_pipeline import DOCS_DIR
        except ImportError:
            # En entorno local sin dependencias de RAG instaladas, usar ruta relativa
            DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Docs")
        os.makedirs(DOCS_DIR, exist_ok=True)
        archivos = sorted([
            f for f in os.listdir(DOCS_DIR)
            if f.lower().endswith((".pdf", ".docx"))
        ])
        docs_info = [{"nombre": archivo} for archivo in archivos]
        return {"documentos": docs_info, "total": len(docs_info)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar documentos: {e}")


@app.post("/api/admin/upload", tags=["Admin"])
async def subir_documento(
    file: UploadFile = File(...),
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """Sube un PDF/DOCX, lo guarda en Docs/ y lo indexa incrementalmente en ChromaDB."""
    _verificar_pin(x_admin_pin)
    global vector_store

    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF o DOCX.")

    try:
        from rag_pipeline import DOCS_DIR, add_documents_incremental

        os.makedirs(DOCS_DIR, exist_ok=True)
        destino = os.path.join(DOCS_DIR, file.filename)

        # Guardar archivo
        contenido = await file.read()
        with open(destino, "wb") as f:
            f.write(contenido)

        # Indexar incrementalmente
        vs_nuevo, n_chunks = add_documents_incremental([destino], vs_existente=vector_store)
        if vs_nuevo is not None:
            vector_store = vs_nuevo

        return {
            "mensaje": f"✅ '{file.filename}' subido e indexado correctamente.",
            "archivo": file.filename,
            "fragmentos_indexados": n_chunks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir documento: {e}")


# ── Publicar documentos a GitHub (persistencia permanente en Render) ──────────

@app.post("/api/admin/publicar", tags=["Admin"])
async def publicar_a_github(x_admin_pin: str = Header(..., alias="X-Admin-Pin")):
    """
    Hace commit + push de Docs/ y chroma_neuro_db/ a GitHub.
    Requiere la variable de entorno GITHUB_TOKEN configurada en Render.
    Al actualizarse GitHub, Render redespliega automáticamente y los documentos
    quedan permanentemente disponibles aunque el servidor se reinicie.
    """
    _verificar_pin(x_admin_pin)

    import subprocess

    token = os.environ.get("GITHUB_TOKEN", "")
    repo_url = os.environ.get("GITHUB_REPO_URL", "")  # ej: https://github.com/Vivi271/Atena.git

    if not token:
        raise HTTPException(
            status_code=503,
            detail="GITHUB_TOKEN no está configurado en las variables de entorno del servidor."
        )

    try:
        # Configurar git con el token de autenticación
        remote_with_token = repo_url.replace("https://", f"https://x-token:{token}@")

        env = {**os.environ, "GIT_AUTHOR_NAME": "Atena Admin", "GIT_AUTHOR_EMAIL": "atena@konradlorenz.edu.co",
               "GIT_COMMITTER_NAME": "Atena Admin", "GIT_COMMITTER_EMAIL": "atena@konradlorenz.edu.co"}

        base = "/app"  # ruta en Docker; en local usar os.getcwd()
        if not os.path.exists(os.path.join(base, ".git")):
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        def run(cmd):
            r = subprocess.run(cmd, cwd=base, capture_output=True, text=True, env=env)
            if r.returncode != 0:
                raise RuntimeError(r.stderr or r.stdout)
            return r.stdout.strip()

        run(["git", "config", "user.email", "atena@konradlorenz.edu.co"])
        run(["git", "config", "user.name", "Atena Admin"])
        run(["git", "add", "Docs/", "backend/chroma_neuro_db/", "chroma_neuro_db/"])
        status = run(["git", "status", "--porcelain"])

        if not status:
            return {"ok": True, "mensaje": "No hay cambios nuevos para publicar. Los documentos ya están sincronizados."}

        run(["git", "commit", "-m", "docs(lab): actualizar documentos y base vectorial desde panel admin"])
        run(["git", "remote", "set-url", "origin", remote_with_token])
        run(["git", "push", "origin", "main"])
        run(["git", "remote", "set-url", "origin", repo_url])  # limpiar token de la url

        logger.info("Documentos publicados exitosamente en GitHub desde el panel admin.")
        return {
            "ok": True,
            "mensaje": "Documentos publicados en GitHub. Render redesplegará en ~2 minutos y los cambios serán permanentes."
        }

    except Exception as e:
        logger.error(f"Error al publicar en GitHub: {e}")
        raise HTTPException(status_code=500, detail=f"Error al publicar: {str(e)[:200]}")


@app.delete("/api/admin/delete/{filename}", tags=["Admin"])
async def eliminar_documento(
    filename: str,
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """Elimina un documento de Docs/ y remueve sus vectores de ChromaDB."""
    _verificar_pin(x_admin_pin)
    global vector_store

    try:
        from rag_pipeline import DOCS_DIR, remove_documents_from_store

        ruta_archivo = os.path.join(DOCS_DIR, filename)

        # Eliminar de ChromaDB
        vs_nuevo, n_eliminados = remove_documents_from_store(filename, vs_existente=vector_store)
        if vs_nuevo is not None:
            vector_store = vs_nuevo

        # Eliminar archivo físico
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)

        return {
            "mensaje": f"✅ '{filename}' eliminado.",
            "vectores_eliminados": n_eliminados,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar documento: {e}")


@app.post("/api/admin/rebuild", tags=["Admin"])
async def reconstruir_vectorstore(
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """Reconstruye completamente el vector store desde todos los documentos en Docs/."""
    _verificar_pin(x_admin_pin)
    global vector_store

    try:
        from rag_pipeline import build_vector_store
        vector_store = build_vector_store(force_rebuild=True)
        count = vector_store._collection.count() if vector_store else 0
        return {
            "mensaje": "✅ Vector store reconstruido.",
            "total_vectores": count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reconstruir: {e}")



# ── Estadísticas persistentes (Supabase) con fallback a sesión en RAM ────────

@app.get("/api/admin/stats_sesion", tags=["Admin"])
async def stats_sesion(x_admin_pin: str = Header(..., alias="X-Admin-Pin")):
    """
    Estadísticas de uso leídas desde Supabase (persistentes entre reinicios).
    Si Supabase no está disponible, devuelve los datos de la sesión en RAM.
    """
    _verificar_pin(x_admin_pin)

    # ── Intenta leer de Supabase ─────────────────────────────────────────────
    try:
        from db_metrics import (
            _get_conn,
            obtener_distribucion_niveles,
            obtener_metricas,
        )
        import psycopg2.extras

        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Total y latencia promedio
            cur.execute("SELECT COUNT(*) AS total, AVG(latencia) AS lat_prom FROM consultas")
            row = cur.fetchone()
            total    = int(row["total"]) if row else 0
            lat_prom = round(float(row["lat_prom"]), 2) if row and row["lat_prom"] else None

            # Distribución por nivel
            cur.execute("SELECT nivel, COUNT(*) AS cnt FROM consultas GROUP BY nivel ORDER BY cnt DESC")
            por_nivel = {r["nivel"]: int(r["cnt"]) for r in cur.fetchall()}

            # Palabras clave más frecuentes
            cur.execute("SELECT pregunta FROM consultas ORDER BY fecha DESC LIMIT 500")
            from collections import Counter
            stop = {"qué","que","cual","cuál","como","cómo","es","son","de","del","en",
                    "la","el","los","las","un","una","por","y","a","se","su","con",
                    "para","al","lo","hay","sobre","me","mi","tiene","tienen"}
            word_freq: Counter = Counter()
            for r in cur.fetchall():
                words = [w.lower().strip("¿?.,;:()") for w in r["pregunta"].split()]
                word_freq.update(w for w in words if len(w) > 4 and w not in stop)
            temas_frecuentes = [{"tema": w, "veces": c} for w, c in word_freq.most_common(8)]

            # Últimas 200 consultas
            cur.execute(
                "SELECT fecha, pregunta, nivel, latencia FROM consultas ORDER BY fecha DESC LIMIT 200"
            )
            recientes = []
            for r in cur.fetchall():
                d = dict(r)
                if d.get("fecha"):
                    d["fecha"] = d["fecha"].isoformat()
                recientes.append(d)

        conn.close()
        return {
            "fuente": "supabase",
            "total_consultas": total,
            "lat_prom": lat_prom,
            "por_nivel": por_nivel,
            "temas_frecuentes": temas_frecuentes,
            "recientes": recientes,
        }

    except Exception as db_err:
        logger.warning(f"Supabase no disponible para stats, usando RAM: {db_err}")

    # ── Fallback: datos de la sesión actual (RAM) ────────────────────────────
    logs = list(_SESSION_LOG)
    total = len(logs)
    niveles: dict = {}
    for e in logs:
        n = e.get("nivel", "—")
        niveles[n] = niveles.get(n, 0) + 1
    lats = [e["latencia"] for e in logs if e.get("latencia") is not None]
    lat_prom = round(sum(lats) / len(lats), 2) if lats else None
    from collections import Counter
    stop = {"qué","que","cual","cuál","como","cómo","es","son","de","del","en",
            "la","el","los","las","un","una","por","y","a","se","su","con",
            "para","al","lo","hay","sobre","me","mi","tiene","tienen"}
    word_freq2: Counter = Counter()
    for e in logs:
        words = [w.lower().strip("¿?.,;:()") for w in e.get("pregunta","").split()]
        word_freq2.update(w for w in words if len(w) > 4 and w not in stop)
    return {
        "fuente": "ram",
        "total_consultas": total,
        "lat_prom": lat_prom,
        "por_nivel": niveles,
        "temas_frecuentes": [{"tema": w, "veces": c} for w, c in word_freq2.most_common(8)],
        "recientes": list(reversed(logs)),
    }


# ── Cambio de PIN desde el panel (persiste en Supabase) ──────────────────────

class CambiarPinRequest(BaseModel):
    pin_actual: str
    pin_nuevo: str

@app.post("/api/admin/cambiar-pin", tags=["Admin"])
async def cambiar_pin(
    body: CambiarPinRequest,
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """Cambia el PIN de administrador. El nuevo PIN se guarda en Supabase."""
    _verificar_pin(x_admin_pin)
    if len(body.pin_nuevo) < 4:
        raise HTTPException(status_code=400, detail="El PIN debe tener al menos 4 caracteres.")
    try:
        from db_metrics import set_pin
        set_pin(body.pin_nuevo)
        return {"ok": True, "mensaje": "PIN actualizado correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el PIN: {e}")


@app.get("/diagnostico/db", tags=["Admin"])
async def diagnostico_db(x_admin_pin: str = Header(..., alias="X-Admin-Pin")):
    """Verifica conectividad con Supabase y cuenta preguntas por nivel."""
    _verificar_pin(x_admin_pin)
    try:
        from db_preguntas import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT n.nombre, COUNT(p.id) FROM niveles n "
            "LEFT JOIN preguntas p ON p.nivel_id = n.id "
            "GROUP BY n.nombre ORDER BY n.nombre"
        )
        rows = cur.fetchall()
        conn.close()
        return {"conexion": "ok", "niveles": {r[0]: r[1] for r in rows}}
    except Exception as e:
        return {"conexion": "error", "detalle": str(e)[:120]}


# ── Endpoints de Métricas y Registro (para frontend web) ──────────────────────


class RegistrarEvaluacionRequest(BaseModel):
    pregunta: str
    respuesta_usuario: str
    respuesta_correcta: str
    es_correcta: bool
    explicacion: str


@app.get("/api/admin/metricas", tags=["Admin"])
async def obtener_metricas_panel(
    dias: int = Query(30, description="Días de historial para volumen y tendencia"),
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """
    Devuelve todas las métricas del panel de administración en un solo request:
    KPIs generales, volumen diario, distribución por nivel, preguntas frecuentes,
    consultas recientes y tendencia de aciertos.
    """
    _verificar_pin(x_admin_pin)
    try:
        from db_metrics import (
            obtener_metricas,
            obtener_consultas_recientes,
            obtener_preguntas_frecuentes,
            obtener_volumen_diario,
            obtener_distribucion_niveles,
            obtener_precision_evaluaciones,
            obtener_tendencia_aciertos_diaria,
        )
        return {
            "kpis":              obtener_metricas(),
            "volumen_diario":    obtener_volumen_diario(dias),
            "distribucion":      obtener_distribucion_niveles(),
            "frecuentes":        obtener_preguntas_frecuentes(10),
            "recientes":         obtener_consultas_recientes(20),
            "tendencia":         obtener_tendencia_aciertos_diaria(dias),
            "precision":         obtener_precision_evaluaciones(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener métricas: {e}")


@app.post("/api/admin/evaluacion/registrar", tags=["Admin"])
async def registrar_respuesta_evaluacion(
    body: RegistrarEvaluacionRequest,
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """Registra la respuesta de un usuario a una pregunta del quiz de autoevaluación."""
    _verificar_pin(x_admin_pin)
    try:
        from db_metrics import registrar_evaluacion
        registrar_evaluacion(
            pregunta=body.pregunta,
            respuesta_usuario=body.respuesta_usuario,
            respuesta_correcta=body.respuesta_correcta,
            es_correcta=body.es_correcta,
            explicacion=body.explicacion,
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar evaluación: {e}")


# ── Admin: CRUD de Preguntas de Evaluación ────────────────────────────────────

@app.post("/api/admin/preguntas", tags=["Admin"])
async def crear_pregunta_admin(
    body: PreguntaAdminRequest,
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """Crea una nueva pregunta de evaluación en la base de datos."""
    _verificar_pin(x_admin_pin)
    try:
        from db_preguntas import agregar_pregunta
        ok = agregar_pregunta(
            nivel=body.nivel,
            tema=body.tema,
            enunciado=body.enunciado,
            opcion_a=body.opcion_a,
            opcion_b=body.opcion_b,
            opcion_c=body.opcion_c,
            opcion_d=body.opcion_d,
            correcta=body.correcta,
        )
        if not ok:
            raise HTTPException(status_code=400, detail="Nivel o tema no encontrado en la base de datos.")
        return {"ok": True, "mensaje": "Pregunta creada correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear pregunta: {e}")


@app.put("/api/admin/preguntas/{pregunta_id}", tags=["Admin"])
async def actualizar_pregunta_admin(
    pregunta_id: int,
    body: PreguntaAdminRequest,
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """Actualiza una pregunta de evaluación existente."""
    _verificar_pin(x_admin_pin)
    try:
        from db_preguntas import actualizar_pregunta
        ok = actualizar_pregunta(
            pregunta_id=pregunta_id,
            nivel=body.nivel,
            tema=body.tema,
            enunciado=body.enunciado,
            opcion_a=body.opcion_a,
            opcion_b=body.opcion_b,
            opcion_c=body.opcion_c,
            opcion_d=body.opcion_d,
            correcta=body.correcta,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Pregunta o nivel/tema no encontrado.")
        return {"ok": True, "mensaje": "Pregunta actualizada correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar pregunta: {e}")


@app.delete("/api/admin/preguntas/{pregunta_id}", tags=["Admin"])
async def eliminar_pregunta_admin(
    pregunta_id: int,
    x_admin_pin: str = Header(..., alias="X-Admin-Pin"),
):
    """Elimina una pregunta de evaluación y sus respuestas asociadas."""
    _verificar_pin(x_admin_pin)
    try:
        from db_preguntas import eliminar_pregunta
        ok = eliminar_pregunta(pregunta_id)
        if not ok:
            raise HTTPException(status_code=500, detail="No se pudo eliminar la pregunta.")
        return {"ok": True, "mensaje": "Pregunta eliminada correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar pregunta: {e}")


# ── Frontend estático (debe ir al final, después de todos los endpoints API) ───
# Sirve la carpeta frontend/web/static/ como raíz del sitio web.
# Render/Docker: la ruta es relativa al WORKDIR=/app, los archivos quedan en /app/frontend/web/static/
from fastapi.staticfiles import StaticFiles
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "web", "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="frontend")
