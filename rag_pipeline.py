"""
rag_pipeline.py — Pipeline RAG para el Consultor Especialista en Neuroanatomía
Versión 4.0: HuggingFace Embeddings (en contenedor) + Groq LLM
- Embeddings: all-MiniLM-L6-v2 (sentence-transformers, sin API, sin límites)
- LLM: qwen/qwen3.6-27b (via Groq API, gratuito)
- VectorDB: ChromaDB local (SQLite)
"""

import os
import re
import shutil
import unicodedata
import difflib
from dotenv import load_dotenv

# Forzar uso de PyTorch solamente — evita conflictos con TensorFlow instalado en el sistema
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.embeddings import Embeddings
import chromadb.utils.embedding_functions as ef
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN
# ─────────────────────────────────────────────
load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError(
        "No se encontró GROQ_API_KEY en las variables de entorno. "
        "Agrégala al archivo .env como: GROQ_API_KEY=gsk_tu_clave_aqui"
    )

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR  = os.path.join(BASE_DIR, "Docs")


def _get_docs_files():
    """Lista dinámica de PDFs/DOCX en la carpeta Docs/ para capturar archivos nuevos."""
    if not os.path.exists(DOCS_DIR):
        return []
    return sorted([
        os.path.join(DOCS_DIR, f)
        for f in os.listdir(DOCS_DIR)
        if f.lower().endswith((".pdf", ".docx"))
    ])


def _load_any_document(file_path: str) -> list:
    """Carga un PDF con PyPDFLoader o un DOCX usando un parser local de XML."""
    if file_path.lower().endswith(".pdf"):
        loader = PyPDFLoader(file_path)
        return loader.load()
    elif file_path.lower().endswith(".docx"):
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(file_path) as docx:
                tree = ET.parse(docx.open("word/document.xml"))
                root = tree.getroot()
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                text = " ".join(n.text for n in root.findall(".//w:t", ns) if n.text)
            return [Document(page_content=text, metadata={"source": file_path, "page": 1})]
        except Exception as e:
            print(f"  [!] Error leyendo Word {os.path.basename(file_path)}: {e}")
            return []
    return []


PERSIST_DIR     = os.path.join(BASE_DIR, "chroma_neuro_db")
COLLECTION_NAME = "neuroanatomia_cientifica"

# Embeddings: ONNX Runtime (nativo en ChromaDB) — sin PyTorch ni Transformers
# Reduce el uso de RAM de 520MB a <150MB, garantizando compatibilidad con Render Free Tier
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

class ONNXMiniLMEmbeddings(Embeddings):
    """Embeddings ultraligeros basados en ONNX Runtime nativo de ChromaDB (sin PyTorch)."""
    def __init__(self):
        self._ef = ef.ONNXMiniLM_L6_V2()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [list(map(float, v)) for v in self._ef(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(map(float, self._ef([text])[0]))

embeddings_model = ONNXMiniLMEmbeddings()

# LLM: Groq API con OpenAI GPT OSS 120B (alta precisión, sin límite para estudiantes)
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
GROQ_EMBED_MODEL = EMBED_MODEL_NAME  # referencia para compatibilidad con api.py
GEMINI_LLM_MODEL = GROQ_LLM_MODEL   # compatibilidad hacia atrás con sidebar y UI
GEMINI_EMBED_MODEL = EMBED_MODEL_NAME

from config import nombre_legible

# ─────────────────────────────────────────────
# 3. SYSTEM PROMPT — Identidad del consultor (Estilo Claude / ChatGPT)
# ─────────────────────────────────────────────
SYSTEM_INSTRUCTION_BASICO = """Eres Atena, un asistente y tutor inteligente especialista en neuroanatomía de la Fundación Universitaria Konrad Lorenz.
Tu misión es guiar al estudiante con la calidez pedagógica, claridad conceptual, dinamismo y estructura impecable que caracterizan a asistentes de IA avanzados como Claude o ChatGPT en una app de chat móvil.

ESTILO PEDAGÓGICO Y PAUTAS DE COMUNICACIÓN (NIVEL BÁSICO):
1. Tono y Apertura: Inicia directamente con una respuesta fluida y cercana que aborde la consulta. NO repitas la pregunta ni pongas títulos de encabezado como '# Funciones de...' al inicio de la respuesta.
2. Estructura Compacta para Chat Móvil:
   - Mantén la respuesta ágil, compacta y agradable de leer en una pantalla móvil.
   - Usa numerales destacados (ej. 1. **Concepto clave:** breve explicación) para los puntos centrales.
   - Si necesitas desglosar detalles dentro de un punto, usa viñetas cortas.
   - Resalta los términos anatómicos fundamentales y conceptos clave en **negrita**.
   - PROHIBIDO usar tablas Markdown ('|') ni líneas divisorias ('---').
3. Citas Académicas Limpias:
   - Apoya los conceptos clave citando sobria y limpiamente la fuente al final de la frase relevante: [Fuente X, pág. Y].
4. Cero Alucinación: Basa tus explicaciones EXCLUSIVAMENTE en la información de las fuentes provistas. Si los fragmentos no contienen información sobre un aspecto consultado, dilo amablemente: "Lo siento, no cuento con información suficiente sobre ese aspecto en la literatura disponible."
5. Cierre Didáctico: Concluye con una breve frase integradora que resuma la importancia funcional de la estructura estudiada."""

SYSTEM_INSTRUCTION_AVANZADO = """Eres Atena, un consultor de élite y especialista en neuroanatomía clínica y funcional de la Fundación Universitaria Konrad Lorenz.
Tu objetivo es responder con la máxima profundidad conceptual, rigor terminológico, estructura analítica y fluidez expositiva propias de asistentes de investigación como Claude o GPT-4.

ESTILO Y PAUTAS DE COMUNICACIÓN (NIVEL AVANZADO):
1. Tono Especializado: Inicia con una explicación directa y científica que aborde de inmediato la pregunta sin rodeos ni títulos redundantes al inicio.
2. Estructura Analítica Limpia (Formato Chat Móvil):
   - Desglosa la respuesta con numerales (1. **Estructura/Vía:** detalle científico).
   - Destaca núcleos, fascículos, surcos, giros o áreas de Brodmann en **negrita**.
   - PROHIBIDO usar tablas Markdown ('|') ni líneas divisorias ('---').
   - Usa párrafos concisos y viñetas solo para listas secundarias.
3. Citas Sobrias y Rigurosas: Fundamenta afirmaciones anatómicas con citas bibliográficas limpias: [Fuente X, pág. Y].
4. Cero Alucinación: Cíñete estrictamente a las fuentes documentales. Si un aspecto no está reportado en los textos, indícalo con rigor académico.
5. Integración Funcional: Explica cómo la anatomía sustenta los procesos funcionales o clínicos según la literatura."""

PROMPT_TEMPLATE = """FUENTES DOCUMENTALES DE REFERENCIA (extraídas de la literatura de neuroanatomía):
{context}

PREGUNTA: {question}

Instrucciones de respuesta:
- Responde con formato de chat conversacional ágil y compacto (estilo Claude / ChatGPT).
- NO agregues títulos de encabezado repetitivos al inicio (ej. '# Funciones de...'). Empieza de una vez con la explicación.
- Usa puntos numerados claros con el concepto en **negrita** (ej. 1. **Nombre:** explicación).
- Explica los conceptos clave usando ÚNICAMENTE las fuentes provistas.
- Cita de manera limpia como [Fuente X, pág. Y].
- NO uses tablas ('|') ni líneas horizontales ('---').
- Si ninguna fuente contiene datos para responder a la pregunta, di: "Lo siento, no cuento con esa información en la literatura disponible."

Respuesta:"""


# ─────────────────────────────────────────────
# 3.5. HELPER — Restaurar backup si el rebuild falla
# ─────────────────────────────────────────────
def _restaurar_backup(temp_dir: str, backup_dir: str, persist_dir: str) -> None:
    """Limpia carpeta temporal y restaura el backup si existe."""
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(backup_dir):
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)
        shutil.copytree(backup_dir, persist_dir)
        shutil.rmtree(backup_dir)
        print("[RESTORE] ✅ Base de datos anterior restaurada exitosamente.")
    else:
        print("[RESTORE] ⚠️ No se encontró backup para restaurar.")


import chromadb


def _get_or_create_vector_store(persist_dir: str = PERSIST_DIR) -> Chroma:
    """
    Crea siempre un ChromaDB PersistentClient NUEVO para evitar usar clientes
    obsoletos del caché de Streamlit que pueden apuntar a un SQLite ya borrado
    o cuyo singleton interno fue detenido.
    """
    os.makedirs(persist_dir, exist_ok=True)
    # Forzar la creación de un cliente completamente nuevo en cada llamada
    client = chromadb.PersistentClient(path=persist_dir)
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings_model,
        collection_metadata={"hnsw:space": "cosine"},
    )


# ─────────────────────────────────────────────
# 4. CONSTRUCCIÓN DE LA BASE VECTORIAL
# ─────────────────────────────────────────────
def build_vector_store(force_rebuild: bool = False, on_progress=None) -> Chroma:
    """
    PASO 1-4 del pipeline RAG:
    Carga PDFs → Chunking → Vectorización (Gemini Embeddings) → ChromaDB

    Backup permanente en ~/.neuro_db_permanent/ — se restaura automáticamente
    si la DB local desaparece.

    Args:
        force_rebuild: Si True, borra y reconstruye la base completa.
        on_progress: Callback opcional (pct: float 0-1, msg: str) que se llama
                     después de cada lote para reportar progreso al frontend.
    """
    def _progress(pct: float, msg: str):
        if on_progress:
            try:
                on_progress(pct, msg)
            except Exception:
                pass

    PERMANENT_BACKUP = os.path.join(os.path.expanduser("~"), ".neuro_db_permanent")

    if not force_rebuild:
        if os.path.exists(PERSIST_DIR):
            try:
                vs = _get_or_create_vector_store(PERSIST_DIR)
                count = vs._collection.count()
                if count > 0:
                    print(f"[OK] Cargando base vectorial existente desde: {PERSIST_DIR} ({count} fragmentos)")
                    return vs
                print("[INFO] Base vectorial existe pero está vacía. Construyendo automáticamente desde Docs/...")
            except Exception as e:
                print(f"[WARN] Error al verificar base existente ({e}). Reconstruyendo...")
        elif os.path.exists(PERMANENT_BACKUP):
            print("[RESTORE] DB no encontrada localmente. Restaurando desde backup permanente...")
            shutil.copytree(PERMANENT_BACKUP, PERSIST_DIR)
            print("[RESTORE] ✔ DB restaurada desde ~/.neuro_db_permanent/")
            return _get_or_create_vector_store(PERSIST_DIR)
        else:
            print("[INFO] Base vectorial no encontrada. Construyendo automáticamente desde Docs/...")

    # ── Limpiar singleton interno de chromadb antes de borrar el directorio ──
    try:
        import gc
        gc.collect()
    except Exception:
        pass

    # ── Directorio de persistencia asegurado ──
    os.makedirs(PERSIST_DIR, exist_ok=True)

    # PASO 1 — Carga de documentos (PDF y DOCX)
    docs_files = _get_docs_files()
    total_archivos = len(docs_files)
    print(f"\n[PASO 1] Cargando documentos de neuroanatomía... ({total_archivos} archivos en Docs/)")
    _progress(0.02, f"📂 Leyendo {total_archivos} documento(s)...")
    documents = []
    for idx, file_path in enumerate(docs_files):
        nombre = os.path.basename(file_path)
        if not os.path.exists(file_path):
            print(f"  [!] Archivo no encontrado: {nombre}")
            continue
        _progress(0.02 + 0.08 * (idx / total_archivos), f"📄 Leyendo: {nombre}")
        pages = _load_any_document(file_path)
        documents.extend(pages)
        print(f"  ✔ {nombre}: {len(pages)} páginas/secciones cargadas")
    print(f"  Total de páginas/secciones cargadas: {len(documents)}")

    # PASO 2 — Chunking
    _progress(0.12, f"✂️ Dividiendo en fragmentos ({len(documents)} páginas)...")
    print("\n[PASO 2] Dividiendo en fragmentos (chunk_size=1800, overlap=250)...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800,
        chunk_overlap=250,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(documents)
    print(f"  Fragmentos generados: {len(chunks)}")

    # PASO 3 & 4 — Embeddings con Groq + ChromaDB
    BATCH_SIZE = 96  # Groq soporta hasta 96 textos por petición
    total_lotes = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n[PASO 3 & 4] Vectorizando con Groq ({GROQ_EMBED_MODEL})...")
    print(f"  (lotes de {BATCH_SIZE} fragmentos, total {total_lotes} lotes)")

    _progress(0.15, f"🧠 Vectorizando {len(chunks)} fragmentos en {total_lotes} lotes con ONNX...")
    if force_rebuild:
        try:
            _c = chromadb.PersistentClient(path=PERSIST_DIR)
            _c.delete_collection(COLLECTION_NAME)
            print(f"[REBUILD] Colección '{COLLECTION_NAME}' renovada para inserción atómica.")
        except Exception:
            pass
    vector_store = _get_or_create_vector_store(PERSIST_DIR)

    import time
    for i in range(0, len(chunks), BATCH_SIZE):
        lote = chunks[i:i + BATCH_SIZE]
        numero_lote = i // BATCH_SIZE + 1
        pct_vectorizacion = 0.15 + 0.80 * (numero_lote / total_lotes)
        msg = (
            f"🧠 Lote {numero_lote}/{total_lotes} — "
            f"fragmentos {i+1}–{min(i+BATCH_SIZE, len(chunks))} de {len(chunks)} "
            f"({int(pct_vectorizacion * 100)}%)"
        )
        _progress(pct_vectorizacion, msg)
        print(f"  Lote {numero_lote}/{total_lotes}: fragmentos {i+1}–{min(i+BATCH_SIZE, len(chunks))}...")

        max_reintentos = 3
        exito = False
        ultimo_error = None

        for intento in range(1, max_reintentos + 1):
            try:
                vector_store.add_documents(lote)
                exito = True
                break
            except Exception as e:
                ultimo_error = e
                time.sleep(2 * intento)

        if not exito:
            raise RuntimeError(f"Error vectorizando lote {numero_lote}/{total_lotes}: {ultimo_error}") from ultimo_error

    total = vector_store._collection.count() if vector_store is not None else 0
    print(f"  ✔ DB actualizada en {os.path.basename(PERSIST_DIR)}/ — {total} vectores indexados")

    # Backup permanente en home
    try:
        PERMANENT_BACKUP = os.path.join(os.path.expanduser("~"), ".neuro_db_permanent")
        if os.path.exists(PERMANENT_BACKUP):
            shutil.rmtree(PERMANENT_BACKUP)
        shutil.copytree(PERSIST_DIR, PERMANENT_BACKUP)
        print(f"  ✔ Backup permanente guardado en ~/.neuro_db_permanent/ ({total} vectores)")
    except Exception as _e:
        print(f"  [WARN] No se pudo guardar backup permanente: {_e}")

    return vector_store


# ─────────────────────────────────────────────
# 4a. ELIMINAR VECTORES DE UN PDF ESPECÍFICO
# ─────────────────────────────────────────────
def remove_documents_from_store(pdf_filename: str, vs_existente=None):
    """
    Elimina de ChromaDB todos los vectores que provienen del PDF indicado.
    Siempre crea un cliente fresco para evitar usar referencias obsoletas del caché.
    """
    # SIEMPRE usar un cliente fresco, ignorar vs_existente para evitar el error
    # 'default_tenant does not exist' causado por clientes obsoletos del caché de Streamlit
    if not os.path.exists(PERSIST_DIR):
        return None, 0
    vs = _get_or_create_vector_store(PERSIST_DIR)

    todos = vs._collection.get(include=["metadatas"])
    ids_a_borrar = [
        doc_id
        for doc_id, meta in zip(todos["ids"], todos["metadatas"])
        if meta and pdf_filename in (meta.get("source", ""))
    ]

    if ids_a_borrar:
        vs._collection.delete(ids=ids_a_borrar)
        print(f"  ✔ {len(ids_a_borrar)} vectores eliminados de '{pdf_filename}'")
    else:
        print(f"  [!] No se encontraron vectores para '{pdf_filename}'")

    total = vs._collection.count()
    print(f"  ✔ DB ahora tiene {total} vectores totales")
    return vs, len(ids_a_borrar)


# ─────────────────────────────────────────────
# 4b. INDEXACIÓN INCREMENTAL — solo archivos nuevos
# ─────────────────────────────────────────────
def add_documents_incremental(new_pdf_paths: list, vs_existente=None):
    """
    Agrega solo los archivos nuevos a la base vectorial existente.
    IMPORTANTE: Siempre crea un cliente ChromaDB fresco para evitar el error
    'default_tenant does not exist' causado por clientes obsoletos en el caché
    de Streamlit (@st.cache_resource) que pueden apuntar a un SQLite inválido.
    """
    BATCH_SIZE = 50

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "],
    )

    documents = []
    for doc_path in new_pdf_paths:
        if not os.path.exists(doc_path):
            print(f"  [!] No encontrado: {os.path.basename(doc_path)}")
            continue
        pages = _load_any_document(doc_path)
        documents.extend(pages)
        print(f"  ✔ {os.path.basename(doc_path)}: {len(pages)} páginas/secciones cargadas")

    if not documents:
        raise ValueError("No se pudo cargar ningún documento de los archivos dados.")

    chunks = splitter.split_documents(documents)
    print(f"  Fragmentos nuevos: {len(chunks)}")

    # SIEMPRE crear un cliente fresco — ignorar vs_existente para evitar referencias
    # obsoletas del caché de Streamlit que causan 'default_tenant does not exist'
    vs = _get_or_create_vector_store(PERSIST_DIR)

    import time
    for i in range(0, len(chunks), BATCH_SIZE):
        lote = chunks[i:i + BATCH_SIZE]
        numero_lote = i // BATCH_SIZE + 1
        total_lotes = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Lote {numero_lote}/{total_lotes}: fragmentos {i+1}–{min(i+BATCH_SIZE, len(chunks))}...")

        max_reintentos = 3
        exito = False
        ultimo_error = None
        for intento in range(1, max_reintentos + 1):
            try:
                vs.add_documents(lote)
                exito = True
                break
            except Exception as e:
                ultimo_error = e
                time.sleep(2 * intento)

        if not exito:
            raise RuntimeError(f"Error vectorizando lote {numero_lote}/{total_lotes}: {ultimo_error}") from ultimo_error

    total = vs._collection.count()
    print(f"  ✔ DB ahora tiene {total} vectores totales")
    return vs


def _limpiar_texto_ocr(texto: str) -> str:
    """Corrige errores comunes de extracción de PDF (OCR) para ayudar al modelo."""
    if not texto:
        return texto
    texto = texto.replace("-\n", "").replace("- \n", "")
    reemplazos = {
        "co mplejo": "complejo",
        "neur ociencia": "neurociencia",
        "neur oanatomía": "neuroanatomía",
        "sist ema": "sistema",
        "es encial": "esencial",
        "cavi-dad": "cavidad",
        "cavi- dad": "cavidad",
        "cavi dad": "cavidad",
        "aluminio cinaciones": "alucinaciones",
        "aluminio cinacion": "alucinación",
    }
    for roto, corregido in reemplazos.items():
        texto = texto.replace(roto, corregido)
    return texto


# ─────────────────────────────────────────────
# 5. SINÓNIMOS NEUROANATÓMICOS PARA EXPANSIÓN DE QUERY
# ─────────────────────────────────────────────
def _normalizar_acentos(texto: str) -> str:
    """Elimina acentos y diacríticos del texto para búsquedas insensibles a tildes."""
    if not texto:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )

_SINONIMOS_NEURO = {
    "cerebro": ["cerebrum", "encéfalo", "hemisferios cerebrales", "telencéfalo", "corteza cerebral", "prosencéfalo"],
    "cerebelo": ["cerebellum", "corteza cerebelosa", "núcleos cerebelosos", "vermis"],
    "tronco encefálico": ["tallo cerebral", "brainstem", "bulbo raquídeo", "protuberancia", "mesencéfalo", "puente"],
    "médula espinal": ["medula espinal", "spinal cord", "cordón espinal"],
    "hipotálamo": ["hypothalamus", "región hipotalámica"],
    "tálamo": ["thalamus", "núcleos talámicos"],
    "hipocampo": ["hippocampus", "formación hipocampal", "circunvolución dentada", "subículo"],
    "amígdala": ["amygdala", "complejo amigdalino", "núcleo amigdalino"],
    "ganglios basales": ["núcleos basales", "cuerpo estriado", "basal ganglia", "putamen", "globo pálido"],
    "meninges": ["duramadre", "aracnoides", "piamadre", "membranas meníngeas"],
    "ventrículos": ["ventrículo lateral", "tercer ventrículo", "cuarto ventrículo", "sistema ventricular"],
    "nervios craneales": ["pares craneales", "cranial nerves"],
    "lóbulo frontal": ["corteza frontal", "corteza prefrontal", "área de Broca"],
    "lóbulo temporal": ["corteza temporal", "área de Wernicke"],
    "lóbulo parietal": ["corteza parietal", "corteza somatosensorial"],
    "lóbulo occipital": ["corteza occipital", "corteza visual"],
    "sistema límbico": ["limbic system", "circuito de Papez"],
    "sustancia blanca": ["materia blanca", "white matter", "fibras mielinizadas"],
    "sustancia gris": ["materia gris", "grey matter", "gray matter", "somas"],
    "neurona": ["neuronas", "célula nerviosa", "células nerviosas", "axón", "dendrita"],
    "sinapsis": ["synapse", "unión sináptica", "transmisión sináptica", "hendidura sináptica"],
    "neurotransmisor": ["neurotransmisores", "neurotransmitter", "dopamina", "serotonina", "acetilcolina", "GABA"],
    "líquido cefalorraquídeo": ["LCR", "CSF", "cerebrospinal fluid"],
    "diencéfalo": ["diencephalon", "tálamo", "hipotálamo", "epitálamo"],
    "cuerpo calloso": ["corpus callosum", "comisura interhemisférica"],
    "sustancia negra": ["substantia nigra", "complejo nigral", "vía dopaminérgica"],
    "glía": ["neuroglía", "astrocitos", "microglía", "oligodendrocitos"],
}

_STOPWORDS_ES = {
    "que", "es", "el", "la", "un", "una", "de", "del", "en", "y", "o",
    "a", "para", "con", "por", "si", "no", "cual", "cuales", "como",
    "su", "sus", "los", "las", "al", "se", "lo", "le", "qué", "cómo",
}


def _detectar_terminos_clave(pregunta: str) -> list:
    """Detecta términos neuroanatómicos en la pregunta, tolerando acentos y errores ortográficos comunes."""
    preg_norm = _normalizar_acentos(pregunta.lower())
    words = [w.strip("?,.¡!¿:;()\"'") for w in preg_norm.split() if w.strip("?,.¡!¿:;()\"'")]

    vocabulario_norm = {_normalizar_acentos(k.lower()): (k, v) for k, v in _SINONIMOS_NEURO.items()}
    terminos_detectados = []

    # 1. Búsqueda exacta de términos simples o compuestos
    for term_norm, (term_orig, sinonimos) in vocabulario_norm.items():
        if term_norm in preg_norm:
            terminos_detectados.append((term_orig, sinonimos))

    # 2. Tolerancia a errores ortográficos / tipográficos comunes (fuzzy matching con difflib)
    for w in words:
        if len(w) >= 4 and w not in _STOPWORDS_ES:
            matches = difflib.get_close_matches(w, list(vocabulario_norm.keys()), n=1, cutoff=0.72)
            if matches:
                matched_key = matches[0]
                term_orig, sinonimos = vocabulario_norm[matched_key]
                if (term_orig, sinonimos) not in terminos_detectados:
                    terminos_detectados.append((term_orig, sinonimos))

    return terminos_detectados


def _expandir_query(pregunta: str) -> str:
    """
    Expande la pregunta del usuario agregando términos corregidos y sinónimos
    técnicos neuroanatómicos para asegurar una recuperación vectorial óptima.
    """
    terminos = _detectar_terminos_clave(pregunta)
    terminos_extra = []
    for term_orig, sinonimos in terminos:
        terminos_extra.append(term_orig)
        terminos_extra.extend(sinonimos)
    if terminos_extra:
        return pregunta + " " + " ".join(terminos_extra)
    return pregunta


def _get_query_keywords(pregunta: str) -> tuple:
    """Extrae palabras clave de la pregunta + términos corregidos y sinónimos."""
    preg_limpia = _normalizar_acentos(pregunta.lower())
    words = [w.strip("?,.¡!¿") for w in preg_limpia.split()
             if w.strip("?,.¡!¿") not in _STOPWORDS_ES and len(w.strip("?,.¡!¿")) > 1]

    expanded = list(words)
    terminos = _detectar_terminos_clave(pregunta)
    for term_orig, sinonimos in terminos:
        expanded.append(_normalizar_acentos(term_orig.lower()))
        for s in sinonimos:
            expanded.append(_normalizar_acentos(s.lower()))

    return words, list(set(expanded))


def _reranking_por_relevancia(pregunta: str, docs_con_score: list, top_n: int = 6) -> list:
    """
    Re-ranking de fragmentos recuperados.
    Penaliza fragmentos que mencionan el término buscado solo de pasada
    pero cuyo contenido principal es sobre otro tema.
    """
    pregunta_lower = _normalizar_acentos(pregunta.lower())
    terminos_detectados = _detectar_terminos_clave(pregunta)
    nombres_detectados = [_normalizar_acentos(t[0].lower()) for t in terminos_detectados]

    tema_principal = None
    temas_excluir = []
    confusiones = [
        ("cerebro", ["cerebelo", "cerebeloso", "cerebelosa", "cerebellum"]),
        ("cerebelo", []),
        ("hipotalamo", ["hipofisis"]),
        ("talamo", ["hipotalamo"]),
        ("hipocampo", []),
    ]
    for tema, excluidos in confusiones:
        if (tema in pregunta_lower or tema in nombres_detectados) and not any(e in pregunta_lower for e in excluidos):
            tema_principal = tema
            temas_excluir = excluidos
            break

    if not tema_principal and nombres_detectados:
        tema_principal = nombres_detectados[0]

    if not tema_principal:
        return [doc for doc, _score in docs_con_score[:top_n]]

    scored = []
    for doc, sim_score in docs_con_score:
        contenido_lower = _normalizar_acentos(doc.page_content.lower())
        menciones_tema = contenido_lower.count(tema_principal)
        menciones_excl = sum(contenido_lower.count(e) for e in temas_excluir)

        if menciones_tema > 0 and menciones_excl == 0:
            bonus = 0.10
        elif menciones_tema > menciones_excl:
            bonus = 0.05
        elif menciones_tema > 0 and menciones_excl > 0:
            bonus = -0.05
        elif menciones_tema == 0 and menciones_excl > 0:
            bonus = -0.15
        else:
            bonus = 0.0
        scored.append((doc, sim_score + bonus))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _score in scored[:top_n]]


def _busqueda_hibrida(pregunta: str, vector_store: Chroma, k: int = 10) -> list:
    """
    Búsqueda híbrida: combina similitud vectorial con coincidencia
    de palabras clave para recuperar fragmentos que la búsqueda
    puramente semántica podría no encontrar (ej. 'cerebrum', 'encéfalo').
    """
    words_orig, expanded_words = _get_query_keywords(pregunta)
    query_expandida = _expandir_query(pregunta)

    # 1. Búsqueda vectorial
    docs_vector = vector_store.similarity_search_with_relevance_scores(
        query_expandida, k=100
    )
    vector_scores = {doc.page_content: score for doc, score in docs_vector}

    # 2. Escaneo de toda la base por keywords
    all_data = vector_store._collection.get(include=["documents", "metadatas"])

    anatomical_keywords = set()
    for termino in _SINONIMOS_NEURO.keys():
        anatomical_keywords.add(_normalizar_acentos(termino.lower()))
    for sinonimos in _SINONIMOS_NEURO.values():
        for s in sinonimos:
            anatomical_keywords.add(_normalizar_acentos(s.lower()))

    scored_docs = []
    for doc_content, meta in zip(all_data["documents"], all_data["metadatas"]):
        doc_lower = _normalizar_acentos(doc_content.lower())
        palabras_doc = set(w.strip(".,;:()[]{}-\"'/¿?¡!_") for w in doc_lower.split() if w.strip(".,;:()[]{}-\"'/¿?¡!_"))

        keyword_score = 0.0
        for word in expanded_words:
            if word in palabras_doc:
                weight = 3.0 if word in anatomical_keywords else 0.5
                if word in words_orig:
                    weight *= 2.0
                keyword_score += weight

        doc_len = len(doc_lower.split())
        keyword_score = keyword_score / (1 + 0.001 * doc_len) if doc_len > 0 else 0
        vec_score = vector_scores.get(doc_content, 0.0)

        # Penalizar fragmentos de baja calidad (tablas, índices, bibliografías)
        lines = doc_content.strip().split("\n")
        num_lines = len(lines)
        avg_words_per_line = doc_len / num_lines if num_lines > 0 else doc_len
        page_num = meta.get("page", 0)
        prose_penalty = 1.0
        if avg_words_per_line < 4 and num_lines > 5:
            prose_penalty = 0.3
        src = meta.get("source", "")
        if "Lange" in src and isinstance(page_num, int) and page_num > 350:
            prose_penalty = 0.1

        hybrid_score = (0.3 * vec_score + 0.7 * keyword_score) * prose_penalty

        if vec_score > 0 or keyword_score > 0:
            doc = Document(page_content=doc_content, metadata=meta)
            scored_docs.append((doc, hybrid_score))

    scored_docs.sort(key=lambda x: x[1], reverse=True)

    # 3. Re-ranking temático
    return _reranking_por_relevancia(pregunta, scored_docs, top_n=k)


# ─────────────────────────────────────────────
# 5b. CONSULTA RAG — Google Gemini API
# ─────────────────────────────────────────────
def _extraer_texto_contenido(content, strip: bool = False) -> str:
    """Extrae texto limpio de la respuesta del LLM, eliminando bloques <think> si existen."""
    if isinstance(content, str):
        texto = content
    elif isinstance(content, list):
        partes = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                partes.append(part["text"])
            elif isinstance(part, str):
                partes.append(part)
            elif hasattr(part, "text"):
                partes.append(getattr(part, "text"))
            else:
                partes.append(str(part))
        texto = "".join(partes)
    else:
        texto = str(content) if content is not None else ""

    # Limpiar bloques de pensamiento <think>...</think> emitidos por modelos de razonamiento
    if "<think>" in texto and "</think>" in texto:
        texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL)

    if strip:
        texto = texto.strip()
    return texto



def consultar(pregunta: str, vector_store: Chroma, k: int = 10, nivel: str = "avanzado") -> dict:
    """
    PASOS 5-7 del pipeline RAG:
    Búsqueda híbrida → Re-ranking → Prompt aumentado → Generación con Groq
    """
    from config import obtener_respuesta_cortesia
    resp_cortesia = obtener_respuesta_cortesia(pregunta)
    if resp_cortesia:
        return {
            "pregunta": pregunta,
            "respuesta": resp_cortesia,
            "fragmentos": [],
            "fuentes": [],
            "tokens_contexto_aprox": 0,
        }

    docs_contexto = _busqueda_hibrida(pregunta, vector_store, k=k)

    context_parts = []
    for i, doc in enumerate(docs_contexto):
        fuente = os.path.basename(doc.metadata.get("source", "desconocido"))
        nombre = nombre_legible(fuente)
        pagina = doc.metadata.get("page", "?")
        contenido_limpio = _limpiar_texto_ocr(doc.page_content)
        context_parts.append(
            f"[Fuente {i+1}] {nombre} | Página: {pagina}\n{contenido_limpio}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system_instruction = SYSTEM_INSTRUCTION_AVANZADO if nivel.lower() == "avanzado" else SYSTEM_INSTRUCTION_BASICO

    llm = ChatGroq(
        model=GROQ_LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.0,
        max_tokens=800,
        reasoning_effort="low",
    )

    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=PROMPT_TEMPLATE.format(context=context, question=pregunta)),
    ]
    response = llm.invoke(messages)
    texto = _extraer_texto_contenido(response.content, strip=True)

    fuentes = [
        {
            "fuente": os.path.basename(doc.metadata.get("source", "desconocido")),
            "pagina": doc.metadata.get("page"),
            "fragmento": doc.page_content[:300],
        }
        for doc in docs_contexto[:k]
    ]

    return {
        "pregunta": pregunta,
        "respuesta": texto,
        "fragmentos": docs_contexto[:k],
        "fuentes": fuentes,
        "tokens_contexto_aprox": len(context) // 4,
    }


def stream_consultar(pregunta: str, vector_store, k: int = 10, nivel: str = "avanzado"):
    """
    Igual que consultar() pero devuelve un GENERADOR de tokens para streaming
    en tiempo real con st.write_stream() en Streamlit.
    Retorna: (generator, docs, context_tokens)
    """
    from config import obtener_respuesta_cortesia
    resp_cortesia = obtener_respuesta_cortesia(pregunta)
    if resp_cortesia:
        def _gen_cortesia():
            yield resp_cortesia
        return _gen_cortesia(), [], 0

    # Guard: VectorDB no inicializada
    if vector_store is None:
        def _sin_db():
            yield "⚠️ **Base de conocimientos vacía.** Por favor, inicia sesión como administrador y usa el botón **'Reconstruir VectorDB'** en la barra lateral para indexar los documentos."
        return _sin_db(), [], 0

    docs_contexto = _busqueda_hibrida(pregunta, vector_store, k=k)

    context_parts = []
    for i, doc in enumerate(docs_contexto):
        fuente = os.path.basename(doc.metadata.get("source", "desconocido"))
        nombre = nombre_legible(fuente)
        pagina = doc.metadata.get("page", "?")
        contenido_limpio = _limpiar_texto_ocr(doc.page_content)
        context_parts.append(
            f"[Fuente {i+1}] {nombre} | Página: {pagina}\n{contenido_limpio}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system_instruction = SYSTEM_INSTRUCTION_AVANZADO if nivel.lower() == "avanzado" else SYSTEM_INSTRUCTION_BASICO

    llm = ChatGroq(
        model=GROQ_LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.0,
        max_tokens=800,
        reasoning_effort="low",
    )

    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=PROMPT_TEMPLATE.format(context=context, question=pregunta)),
    ]

    def _token_generator():
        for chunk in llm.stream(messages):
            if chunk.content:
                yield _extraer_texto_contenido(chunk.content)

    return _token_generator(), docs_contexto[:k], len(context) // 4


# ─────────────────────────────────────────────
# 6. EJECUCIÓN DIRECTA (modo script / prueba)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("🧠 CONSULTOR RAG — NEUROANATOMÍA (Groq API)")
    print("=" * 65)

    vs = build_vector_store(force_rebuild=False)

    preguntas_prueba = [
        "¿Cuáles son las principales estructuras neuroanatómicas descritas?",
        "¿Qué hallazgos morfológicos o histológicos se reportan?",
        "¿Es útil usar tecnología 3D para estudiar el cerebro?",
        "¿Cuál es la dosis de anestesia recomendada para una cirugía de columna?",
    ]

    for pregunta in preguntas_prueba:
        print(f"\n{'─'*65}")
        print(f"❓ {pregunta}")
        resultado = consultar(pregunta, vs)
        print(f"\n🤖 {resultado['respuesta']}")
        print(f"\n   [~{resultado['tokens_contexto_aprox']} tokens | "
              f"{len(resultado['fragmentos'])} fragmentos recuperados]")

    print(f"\n{'='*65}")
    print("Sistema listo.")
