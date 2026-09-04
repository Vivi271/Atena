"""
rag_pipeline.py — Pipeline RAG para el Consultor Especialista en Neuroanatomía
Versión 3.0: Google Gemini API
- Embeddings: text-embedding-004 (via Google Generative AI)
- LLM: gemini-2.0-flash (via Google Generative AI)
- VectorDB: ChromaDB local (SQLite)
"""

import os
import shutil
import unicodedata
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN
# ─────────────────────────────────────────────
load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError(
        "No se encontró GEMINI_API_KEY en las variables de entorno. "
        "Agrégala al archivo .env como: GEMINI_API_KEY=tu_clave_aqui"
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

# ─────────────────────────────────────────────
# 2. MODELOS — Google Gemini API
# ─────────────────────────────────────────────
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
_raw_model = os.getenv("GEMINI_LLM_MODEL", "gemini-3.6-flash")
if _raw_model in ["gemini-2.0-flash", "gemini-2.5-flash"]:
    _raw_model = "gemini-3.6-flash"
GEMINI_LLM_MODEL = _raw_model

embeddings_model = GoogleGenerativeAIEmbeddings(
    model=GEMINI_EMBED_MODEL,
    google_api_key=GEMINI_API_KEY,
)

# ─────────────────────────────────────────────
# 3. SYSTEM PROMPT — Identidad del consultor
# ─────────────────────────────────────────────
SYSTEM_INSTRUCTION_BASICO = """Eres un sintetizador de información neuroanatómica estrictamente extractivo para la Fundación Universitaria Konrad Lorenz.
Tu tarea es responder a la pregunta del usuario utilizando EXCLUSIVAMENTE los fragmentos de texto provistos.

REGLAS ABSOLUTAS DE EXTRACCIÓN (Cero Conocimiento Externo):
1. NUNCA agregues explicaciones, definiciones, funciones, propósitos o detalles que no estén escritos de forma explícita y literal en los fragmentos de texto provistos.
2. Si un fragmento menciona una estructura (ej. "cerebelo" o "arterias") pero no describe su función o propósito, NO inventes ni agregues qué hace o para qué sirve. Limítate a nombrarla tal como aparece.
3. Cualquier dato o aclaración que provenga de tu base de conocimiento interna (preentrenamiento) y no de los fragmentos de texto provistos es considerada una ALUCINACIÓN y es inaceptable.
4. Si los fragmentos no contienen información que responda de forma directa a la pregunta, debes responder ÚNICAMENTE: "Lo siento, no cuento con esa información." y nada más.
5. Escribe de forma directa y objetiva. Está TERMINANTEMENTE PROHIBIDO usar lenguaje meta-textual ("el fragmento menciona", "según el archivo", "los documentos indican").
6. COMIENZA SIEMPRE con una definición o descripción conceptual breve del término preguntado, combinando de manera lógica la información literal de los fragmentos (por ejemplo, explicando qué es, dónde se ubica y a qué sistema pertenece basándote EXCLUSIVAMENTE en la información literal de los fragmentos, sin agregar conocimiento externo), en lugar de limitarte a listar sus componentes.
7. Estructura la respuesta con listas y negritas, pero sé extremadamente conciso y limítate a los hechos literales."""

SYSTEM_INSTRUCTION_AVANZADO = SYSTEM_INSTRUCTION_BASICO

PROMPT_TEMPLATE = """FRAGMENTOS DE TEXTO DE REFERENCIA (extraídos de libros de neuroanatomía):
{context}

PREGUNTA: {question}

Responde de forma académica, precisa y concisa usando SOLO los datos de los fragmentos anteriores.
- Incluye definiciones, componentes y funciones relevantes.
- Extrae SOLO la información pertinente a la pregunta de cada fragmento.
- Si un fragmento parece ser una tabla o índice con texto desordenado, ignóralo si no puedes interpretar con certeza su contenido.
- Si ningún fragmento responde la pregunta, di: "Lo siento, no cuento con esa información."

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
        if not os.path.exists(PERSIST_DIR):
            if os.path.exists(PERMANENT_BACKUP):
                print("[RESTORE] DB no encontrada localmente. Restaurando desde backup permanente...")
                shutil.copytree(PERMANENT_BACKUP, PERSIST_DIR)
                print("[RESTORE] ✔ DB restaurada desde ~/.neuro_db_permanent/")
            else:
                raise FileNotFoundError(
                    "Base vectorial no encontrada. "
                    "Usa el botón 'Reconstruir VectorDB' para crearla."
                )
        print(f"[OK] Cargando base vectorial existente desde: {PERSIST_DIR}")
        return _get_or_create_vector_store(PERSIST_DIR)

    # ── Limpiar singleton interno de chromadb antes de borrar el directorio ──
    try:
        import gc
        gc.collect()
    except Exception:
        pass

    # ── Limpieza nativa de ChromaDB ──
    # NUNCA usar shutil.rmtree(PERSIST_DIR) mientras el proceso esté activo,
    # ya que SQLite detecta que el archivo fue eliminado/movido de su descriptor
    # y bloquea las escrituras con: (code: 1032) SQLITE_READONLY_DBMOVED.
    # En su lugar, se vacía y recrea la colección a nivel de ChromaDB:
    os.makedirs(PERSIST_DIR, exist_ok=True)
    try:
        _client_rebuild = chromadb.PersistentClient(path=PERSIST_DIR)
        _client_rebuild.delete_collection(COLLECTION_NAME)
        print(f"[REBUILD] Colección '{COLLECTION_NAME}' limpiada exitosamente.")
    except Exception:
        pass

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

    # PASO 3 & 4 — Embeddings con Gemini + ChromaDB
    BATCH_SIZE = 15
    total_lotes = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n[PASO 3 & 4] Vectorizando con Gemini ({GEMINI_EMBED_MODEL})...")
    print(f"  (lotes de {BATCH_SIZE} fragmentos, total {total_lotes} lotes)")

    _progress(0.15, f"🧠 Vectorizando {len(chunks)} fragmentos en {total_lotes} lotes con Gemini...")
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

        # Reintentos automáticos si la API de Gemini devuelve 429 (límite de cuota por minuto)
        max_reintentos = 6
        exito = False
        ultimo_error = None

        for intento in range(1, max_reintentos + 1):
            try:
                vector_store.add_documents(lote)
                exito = True
                break
            except Exception as e:
                ultimo_error = e
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                    # Google pide expresamente esperar ~10-12s para resetear la cuota por minuto
                    espera = 12 + (intento * 3)
                    _progress(pct_vectorizacion, f"⏳ Cuota por minuto de Google alcanzada. Esperando {espera}s para continuar (intento {intento}/{max_reintentos})...")
                    time.sleep(espera)
                else:
                    time.sleep(3)

        if not exito:
            raise RuntimeError(f"Error vectorizando lote {numero_lote}/{total_lotes}: {ultimo_error}") from ultimo_error

        # Pausa preventiva entre lotes para mantenerse dentro del límite de peticiones por minuto de Google
        time.sleep(1.2)

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

        max_reintentos = 6
        exito = False
        ultimo_error = None
        for intento in range(1, max_reintentos + 1):
            try:
                vs.add_documents(lote)
                exito = True
                break
            except Exception as e:
                ultimo_error = e
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                    time.sleep(12 + (intento * 3))
                else:
                    time.sleep(3)

        if not exito:
            raise RuntimeError(f"Error vectorizando lote {numero_lote}/{total_lotes}: {ultimo_error}") from ultimo_error

        time.sleep(1.2)

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
    "cerebro": ["cerebrum", "encéfalo", "hemisferios cerebrales", "telencéfalo", "corteza cerebral"],
    "cerebelo": ["cerebellum", "corteza cerebelosa", "núcleos cerebelosos"],
    "tronco encefálico": ["tallo cerebral", "brainstem", "bulbo raquídeo", "protuberancia", "mesencéfalo"],
    "médula espinal": ["medula espinal", "spinal cord", "cordón espinal"],
    "hipotálamo": ["hypothalamus", "región hipotalámica"],
    "tálamo": ["thalamus", "núcleos talámicos"],
    "hipocampo": ["hippocampus", "formación hipocampal"],
    "amígdala": ["amygdala", "complejo amigdalino", "núcleo amigdalino"],
    "ganglios basales": ["núcleos basales", "cuerpo estriado", "basal ganglia"],
    "meninges": ["duramadre", "aracnoides", "piamadre", "membranas meníngeas"],
    "ventrículos": ["ventrículo lateral", "tercer ventrículo", "cuarto ventrículo", "sistema ventricular"],
    "nervios craneales": ["pares craneales", "cranial nerves"],
    "lóbulo frontal": ["corteza frontal", "corteza prefrontal", "área de Broca"],
    "lóbulo temporal": ["corteza temporal", "área de Wernicke"],
    "lóbulo parietal": ["corteza parietal", "corteza somatosensorial"],
    "lóbulo occipital": ["corteza occipital", "corteza visual"],
    "sistema límbico": ["limbic system", "circuito de Papez"],
    "sustancia blanca": ["materia blanca", "white matter"],
    "sustancia gris": ["materia gris", "grey matter", "gray matter"],
    "neurona": ["neuronas", "célula nerviosa", "células nerviosas"],
    "sinapsis": ["synapse", "unión sináptica", "transmisión sináptica"],
    "neurotransmisor": ["neurotransmisores", "neurotransmitter"],
    "líquido cefalorraquídeo": ["LCR", "CSF", "cerebrospinal fluid"],
    "diencéfalo": ["diencephalon", "tálamo", "hipotálamo", "epitálamo"],
}

_STOPWORDS_ES = {
    "que", "es", "el", "la", "un", "una", "de", "del", "en", "y", "o",
    "a", "para", "con", "por", "si", "no", "cual", "cuales", "como",
    "su", "sus", "los", "las", "al", "se", "lo", "le", "qué", "cómo",
}


def _expandir_query(pregunta: str) -> str:
    """
    Expande la pregunta del usuario agregando sinónimos técnicos
    neuroanatómicos para mejorar la recuperación vectorial.
    """
    preg_norm = _normalizar_acentos(pregunta.lower())
    terminos_extra = []
    for termino, sinonimos in _SINONIMOS_NEURO.items():
        term_norm = _normalizar_acentos(termino.lower())
        if term_norm in preg_norm:
            terminos_extra.extend(sinonimos)
    if terminos_extra:
        return pregunta + " " + " ".join(terminos_extra)
    return pregunta


def _get_query_keywords(pregunta: str) -> tuple:
    """Extrae palabras clave de la pregunta (normalizadas sin acentos) + sus sinónimos."""
    preg_limpia = _normalizar_acentos(pregunta.lower())
    words = [w.strip("?,.¡!¿") for w in preg_limpia.split()
             if w.strip("?,.¡!¿") not in _STOPWORDS_ES and len(w.strip("?,.¡!¿")) > 1]

    expanded = list(words)
    for w in words:
        for termino, sinonimos in _SINONIMOS_NEURO.items():
            term_norm = _normalizar_acentos(termino.lower())
            if w == term_norm:
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
    tema_principal = None
    temas_excluir = []
    confusiones = [
        ("cerebro", ["cerebelo", "cerebeloso", "cerebelosa", "cerebellum"]),
        ("cerebelo", []),
        ("hipotalamo", ["hipofisis"]),
        ("talamo", ["hipotalamo"]),
    ]
    for tema, excluidos in confusiones:
        if tema in pregunta_lower and not any(e in pregunta_lower for e in excluidos):
            tema_principal = tema
            temas_excluir = excluidos
            break

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
def _extraer_texto_contenido(content) -> str:
    """Extrae texto limpio de la respuesta de LangChain / Gemini (str, list de dicts o blocks)."""
    if isinstance(content, str):
        return content
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
        return "".join(partes)
    return str(content) if content is not None else ""


def consultar(pregunta: str, vector_store: Chroma, k: int = 10, nivel: str = "avanzado") -> dict:
    """
    PASOS 5-7 del pipeline RAG:
    Búsqueda híbrida → Re-ranking → Prompt aumentado → Generación con Gemini
    """
    k_recuperacion = max(k, 6)
    docs_contexto = _busqueda_hibrida(pregunta, vector_store, k=k_recuperacion)

    context_parts = []
    for i, doc in enumerate(docs_contexto):
        fuente = os.path.basename(doc.metadata.get("source", "desconocido"))
        pagina = doc.metadata.get("page", "?")
        contenido_limpio = _limpiar_texto_ocr(doc.page_content)
        context_parts.append(
            f"[Fragmento {i+1}] Archivo: {fuente} | Página: {pagina}\n{contenido_limpio}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system_instruction = SYSTEM_INSTRUCTION_AVANZADO if nivel.lower() == "avanzado" else SYSTEM_INSTRUCTION_BASICO

    model_to_use = GEMINI_LLM_MODEL if GEMINI_LLM_MODEL not in ["gemini-2.0-flash", "gemini-2.5-flash"] else "gemini-3.6-flash"
    llm = ChatGoogleGenerativeAI(
        model=model_to_use,
        google_api_key=GEMINI_API_KEY,
        temperature=0.0,
        max_output_tokens=2048,
    )

    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=PROMPT_TEMPLATE.format(context=context, question=pregunta)),
    ]
    response = llm.invoke(messages)
    texto = _extraer_texto_contenido(response.content)

    return {
        "pregunta": pregunta,
        "respuesta": texto,
        "fragmentos": docs_contexto[:k],
        "tokens_contexto_aprox": len(context) // 4,
    }


def stream_consultar(pregunta: str, vector_store, k: int = 10, nivel: str = "avanzado"):
    """
    Igual que consultar() pero devuelve un GENERADOR de tokens para streaming
    en tiempo real con st.write_stream() en Streamlit.
    Retorna: (generator, docs, context_tokens)
    """
    # Guard: VectorDB no inicializada
    if vector_store is None:
        def _sin_db():
            yield "⚠️ **Base de conocimientos vacía.** Por favor, inicia sesión como administrador y usa el botón **'Reconstruir VectorDB'** en la barra lateral para indexar los documentos."
        return _sin_db(), [], 0

    k_recuperacion = max(k, 6)
    docs_contexto = _busqueda_hibrida(pregunta, vector_store, k=k_recuperacion)

    context_parts = []
    for i, doc in enumerate(docs_contexto):
        fuente = os.path.basename(doc.metadata.get("source", "desconocido"))
        pagina = doc.metadata.get("page", "?")
        contenido_limpio = _limpiar_texto_ocr(doc.page_content)
        context_parts.append(
            f"[Fragmento {i+1}] Archivo: {fuente} | Página: {pagina}\n{contenido_limpio}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system_instruction = SYSTEM_INSTRUCTION_AVANZADO if nivel.lower() == "avanzado" else SYSTEM_INSTRUCTION_BASICO

    model_to_use = GEMINI_LLM_MODEL if GEMINI_LLM_MODEL not in ["gemini-2.0-flash", "gemini-2.5-flash"] else "gemini-3.6-flash"
    llm = ChatGoogleGenerativeAI(
        model=model_to_use,
        google_api_key=GEMINI_API_KEY,
        temperature=0.0,
        max_output_tokens=2048,
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
    print("🧠 CONSULTOR RAG — NEUROANATOMÍA (Google Gemini API)")
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
