"""
rag_pipeline.py — Pipeline RAG para el Consultor Especialista en Neuroanatomía
Versión 2.0: 100% LOCAL con Ollama (sin API keys, sin cuotas, sin internet)
- Embeddings: nomic-embed-text (via Ollama)
- LLM: llama3.2 (via Ollama)
- VectorDB: ChromaDB local (SQLite)
"""

import os
import shutil
import time
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.documents import Document

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN
# ─────────────────────────────────────────────
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "Docs")

# _get_docs_files es dinámico — se lee en cada llamada para capturar archivos nuevos (.pdf y .docx)
def _get_docs_files():
    if not os.path.exists(DOCS_DIR):
        return []
    return sorted([
        os.path.join(DOCS_DIR, f)
        for f in os.listdir(DOCS_DIR)
        if f.lower().endswith((".pdf", ".docx"))
    ])

def _load_any_document(file_path: str) -> list:
    """Carga un PDF usando PyPDFLoader o un DOCX usando un parser local de XML."""
    if file_path.lower().endswith(".pdf"):
        loader = PyPDFLoader(file_path)
        return loader.load()
    elif file_path.lower().endswith(".docx"):
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(file_path) as docx:
                tree = ET.parse(docx.open('word/document.xml'))
                root = tree.getroot()
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text = ' '.join(n.text for n in root.findall('.//w:t', ns) if n.text)
            
            # Retorna como una sola página de Documento (será fragmentada en el split)
            return [Document(page_content=text, metadata={"source": file_path, "page": 1})]
        except Exception as e:
            print(f"  [!] Error leyendo Word {os.path.basename(file_path)}: {e}")
            return []
    return []

PERSIST_DIR = os.path.join(BASE_DIR, "chroma_neuro_db")
COLLECTION_NAME = "neuroanatomia_cientifica"

# ─────────────────────────────────────────────
# 2. MODELOS — 100% LOCAL via Ollama
# ─────────────────────────────────────────────
OLLAMA_EMBED_MODEL = "nomic-embed-text"
OLLAMA_LLM_MODEL   = "llama3.2:latest"

embeddings_model = OllamaEmbeddings(
    model=OLLAMA_EMBED_MODEL,
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


# ─────────────────────────────────────────────
# 4. CONSTRUCCIÓN DE LA BASE VECTORIAL
# ─────────────────────────────────────────────
def build_vector_store(force_rebuild: bool = False) -> Chroma:
    """
    PASO 1-4 del pipeline RAG:
    Carga PDFs → Chunking → Vectorización (Embeddings locales) → ChromaDB

    Backup permanente en ~/.neuro_db_permanent/ — se restaura automáticamente
    si la DB local desaparece.
    """
    PERMANENT_BACKUP = os.path.join(os.path.expanduser("~"), ".neuro_db_permanent")

    if not force_rebuild:
        # Modo carga: SOLO cargar si existe, NUNCA reconstruir automáticamente
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
        return Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings_model,
            collection_name=COLLECTION_NAME,
        )

    # ── Construir en carpeta TEMPORAL + Backup de seguridad ──
    TEMP_DIR   = PERSIST_DIR + "_temp"
    BACKUP_DIR = PERSIST_DIR + "_backup"

    # 1. Limpiar temp anterior si existe
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)

    # 2. Hacer backup de la DB actual ANTES de tocarla
    if os.path.exists(PERSIST_DIR):
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(PERSIST_DIR, BACKUP_DIR)
        print(f"[BACKUP] DB respaldada en {os.path.basename(BACKUP_DIR)}/")

    # PASO 1 — Carga de documentos (PDF y DOCX)
    docs_files = _get_docs_files()
    print(f"\n[PASO 1] Cargando documentos de neuroanatomía... ({len(docs_files)} archivos en Docs/)")
    documents = []
    for file_path in docs_files:
        if not os.path.exists(file_path):
            print(f"  [!] Archivo no encontrado: {os.path.basename(file_path)}")
            continue
        pages = _load_any_document(file_path)
        documents.extend(pages)
        print(f"  ✔ {os.path.basename(file_path)}: {len(pages)} páginas/secciones cargadas")
    print(f"  Total de páginas/secciones cargadas: {len(documents)}")

    # PASO 2 — Chunking
    print("\n[PASO 2] Dividiendo en fragmentos (chunk_size=1800, overlap=250)...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800,
        chunk_overlap=250,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(documents)
    print(f"  Fragmentos generados: {len(chunks)}")

    # PASO 3 & 4 — Embeddings locales + ChromaDB
    # OllamaEmbeddings no tiene límite de cuota — 100% local
    print(f"\n[PASO 3 & 4] Vectorizando con Ollama ({OLLAMA_EMBED_MODEL}) — sin cuotas, 100% local...")
    print("  (lotes de 50 fragmentos)")

    BATCH_SIZE = 50
    vector_store = None

    for i in range(0, len(chunks), BATCH_SIZE):
        lote = chunks[i:i + BATCH_SIZE]
        numero_lote = i // BATCH_SIZE + 1
        total_lotes = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Lote {numero_lote}/{total_lotes}: fragmentos {i+1}–{min(i+BATCH_SIZE, len(chunks))}...")

        try:
            if vector_store is None:
                vector_store = Chroma.from_documents(
                    documents=lote,
                    embedding=embeddings_model,
                    persist_directory=TEMP_DIR,
                    collection_name=COLLECTION_NAME,
                    collection_metadata={"hnsw:space": "cosine"},
                )
            else:
                vector_store.add_documents(lote)
        except Exception as e:
            _restaurar_backup(TEMP_DIR, BACKUP_DIR, PERSIST_DIR)
            raise RuntimeError(f"Error vectorizando: {e}") from e

    # ── Swap seguro ──
    total = vector_store._collection.count()
    print(f"  ✔ {total} vectores listos. Cerrando conexión temporal...")

    try:
        vector_store._client._system.stop()
    except Exception:
        pass
    del vector_store

    # Checkpoint WAL de SQLite
    import sqlite3 as _sqlite3
    sqlite_file = os.path.join(TEMP_DIR, "chroma.sqlite3")
    if os.path.exists(sqlite_file):
        try:
            _conn = _sqlite3.connect(sqlite_file)
            _conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            _conn.close()
            print("  ✔ SQLite WAL checkpoint completado")
        except Exception as _e:
            print(f"  [WARN] No se pudo hacer checkpoint: {_e}")

    # Swap: temporal → real
    if os.path.exists(PERSIST_DIR):
        shutil.rmtree(PERSIST_DIR)
    shutil.copytree(TEMP_DIR, PERSIST_DIR)
    shutil.rmtree(TEMP_DIR)

    if os.path.exists(BACKUP_DIR):
        shutil.rmtree(BACKUP_DIR)
        print(f"  ✔ Backup eliminado — DB nueva confirmada ({total} vectores)")

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

    return Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings_model,
        collection_name=COLLECTION_NAME,
    )


# ─────────────────────────────────────────────
# 4a. ELIMINAR VECTORES DE UN PDF ESPECÍFICO
# ─────────────────────────────────────────────
def remove_documents_from_store(pdf_filename: str, vs_existente=None):
    """
    Elimina de ChromaDB todos los vectores que provienen del PDF indicado.
    """
    vs = vs_existente
    if vs is None:
        if not os.path.exists(PERSIST_DIR):
            return None, 0
        vs = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings_model,
            collection_name=COLLECTION_NAME,
        )

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

    vs = vs_existente
    if vs is None and os.path.exists(PERSIST_DIR):
        vs = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings_model,
            collection_name=COLLECTION_NAME,
            collection_metadata={"hnsw:space": "cosine"},
        )

    for i in range(0, len(chunks), BATCH_SIZE):
        lote = chunks[i:i + BATCH_SIZE]
        numero_lote = i // BATCH_SIZE + 1
        total_lotes = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Lote {numero_lote}/{total_lotes}: fragmentos {i+1}–{min(i+BATCH_SIZE, len(chunks))}...")

        try:
            if vs is None:
                vs = Chroma.from_documents(
                    documents=lote,
                    embedding=embeddings_model,
                    persist_directory=PERSIST_DIR,
                    collection_name=COLLECTION_NAME,
                    collection_metadata={"hnsw:space": "cosine"},
                )
            else:
                vs.add_documents(lote)
        except Exception as e:
            raise RuntimeError(f"Error vectorizando: {e}") from e

    total = vs._collection.count()
    print(f"  ✔ DB ahora tiene {total} vectores totales")
    return vs


def _limpiar_texto_ocr(texto: str) -> str:
    """Corrige errores comunes de extracción de PDF (OCR) para ayudar al modelo."""
    if not texto:
        return texto
    # Corregir saltos de línea con guiones
    texto = texto.replace("-\n", "").replace("- \n", "")
    # Corregir espaciados rotos y typos del OCR
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
# Cada clave es un término coloquial/común, y los valores son sinónimos
# técnicos que aparecen en los libros de texto pero que el estudiante
# probablemente no escribirá en su consulta.
import unicodedata

def _normalizar_acentos(texto: str) -> str:
    """Elimina acentos y diacríticos del texto para búsquedas insensibles a tildes."""
    if not texto:
        return ""
    # Normalizar a NFKD y filtrar caracteres de combinación diacrítica (tildes, etc.)
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
    # Usamos términos normalizados sin acentos para las comparaciones
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
    vector_scores = {}
    for doc, score in docs_vector:
        vector_scores[doc.page_content] = score

    # 2. Escaneo de toda la base por keywords
    all_data = vector_store._collection.get(include=["documents", "metadatas"])

    # Palabras clave anatómicas técnicas conocidas normalizadas
    anatomical_keywords = set()
    for termino in _SINONIMOS_NEURO.keys():
        anatomical_keywords.add(_normalizar_acentos(termino.lower()))
    for sinonimos in _SINONIMOS_NEURO.values():
        for s in sinonimos:
            anatomical_keywords.add(_normalizar_acentos(s.lower()))

    scored_docs = []
    for doc_content, meta in zip(all_data["documents"], all_data["metadatas"]):
        # Normalizamos el contenido del documento para buscar keywords de forma insensible a tildes
        doc_lower = _normalizar_acentos(doc_content.lower())
        
        # Coincidencia por palabra completa limpiando puntuación (evita falsos positivos como "encefalo" en "mesencefalo")
        palabras_doc = set(w.strip(".,;:()[]{}-\"'/¿?¡!_") for w in doc_lower.split() if w.strip(".,;:()[]{}-\"'/¿?¡!_"))
        
        keyword_score = 0.0
        for word in expanded_words:
            if word in palabras_doc:
                weight = 3.0 if word in anatomical_keywords else 0.5
                if word in words_orig:
                    weight *= 2.0
                keyword_score += weight

        doc_len = len(doc_lower.split())
        # Penalización por longitud más suave (0.001 en lugar de 0.005) para no descartar párrafos definitorios largos
        keyword_score = keyword_score / (1 + 0.001 * doc_len) if doc_len > 0 else 0
        vec_score = vector_scores.get(doc_content, 0.0)

        # Penalizar fragmentos de baja calidad (tablas, índices, bibliografías)
        lines = doc_content.strip().split("\n")
        num_lines = len(lines)
        if num_lines > 0:
            avg_words_per_line = doc_len / num_lines
        else:
            avg_words_per_line = doc_len
        page_num = meta.get("page", 0)
        prose_penalty = 1.0
        # Fragmentos con líneas muy cortas = tabla/diagrama/índice
        if avg_words_per_line < 4 and num_lines > 5:
            prose_penalty = 0.3
        # Páginas de índice/bibliografía (Lange > p.350)
        src = meta.get("source", "")
        if "Lange" in src and isinstance(page_num, int) and page_num > 350:
            prose_penalty = 0.1

        hybrid_score = (0.3 * vec_score + 0.7 * keyword_score) * prose_penalty

        if vec_score > 0 or keyword_score > 0:
            doc = Document(page_content=doc_content, metadata=meta)
            scored_docs.append((doc, hybrid_score))

    scored_docs.sort(key=lambda x: x[1], reverse=True)

    # 3. Re-ranking temático (eliminar cerebelo cuando preguntan por cerebro, etc.)
    return _reranking_por_relevancia(pregunta, scored_docs, top_n=k)


# ─────────────────────────────────────────────
# 5b. CONSULTA RAG — 100% LOCAL con Ollama LLM
# ─────────────────────────────────────────────
def consultar(pregunta: str, vector_store: Chroma, k: int = 10, nivel: str = "avanzado") -> dict:
    """
    PASOS 5-7 del pipeline RAG:
    Búsqueda híbrida → Re-ranking → Prompt aumentado → Generación local
    """
    # PASO 5 — Búsqueda híbrida con mínimo 6 fragmentos (óptimo para modelo 3B)
    k_recuperacion = max(k, 6)
    docs_contexto = _busqueda_hibrida(pregunta, vector_store, k=k_recuperacion)

    # PASO 6 — Construcción del prompt aumentado con citas reales del metadata
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

    # PASO 7 — Generación LOCAL con Ollama sin repeat_penalty para términos científicos precisos
    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=0.0,
        num_predict=800,
        num_ctx=4096,
    )

    # pyrefly: ignore [missing-import]
    from langchain_core.messages import HumanMessage, SystemMessage
    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=PROMPT_TEMPLATE.format(context=context, question=pregunta)),
    ]
    response = llm.invoke(messages)
    texto = response.content

    return {
        "pregunta": pregunta,
        "respuesta": texto,
        "fragmentos": docs_contexto[:k],  # Devolvemos exactamente k fragmentos al solicitante
        "tokens_contexto_aprox": len(context) // 4,
    }


def stream_consultar(pregunta: str, vector_store, k: int = 10, nivel: str = "avanzado"):
    """
    Igual que consultar() pero devuelve un GENERADOR de tokens.
    Se usa con st.write_stream() en Streamlit para streaming en tiempo real.
    Retorna: (generator, docs, context_tokens)
    """
    # Búsqueda híbrida con mínimo 6 fragmentos (óptimo para modelo 3B)
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

    # pyrefly: ignore [missing-import]
    from langchain_core.messages import HumanMessage, SystemMessage
    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=0.0,
        num_predict=800,
        num_ctx=4096,
    )
    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=PROMPT_TEMPLATE.format(context=context, question=pregunta)),
    ]

    def _token_generator():
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content

    return _token_generator(), docs_contexto[:k], len(context) // 4


# ─────────────────────────────────────────────
# 6. EJECUCIÓN DIRECTA (modo script / prueba)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("🧠 CONSULTOR RAG — NEUROANATOMÍA (100% LOCAL con Ollama)")
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
