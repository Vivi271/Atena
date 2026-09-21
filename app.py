"""
app.py — Punto de entrada de Atena RAG (modo ligero: delega RAG al API de FastAPI)
"""
import streamlit as st
import os
import sys
import time
import httpx

# Configuración de rutas — app.py está en la raíz del repo
ROOT = os.path.dirname(os.path.abspath(__file__))   # raíz del repo
_BACKEND_DIR = os.path.join(ROOT, "backend")
_COMPONENTS_DIR = os.path.join(ROOT, "frontend", "web")

for _p in [_BACKEND_DIR, _COMPONENTS_DIR, ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 1. Configuración de página (DEBE ser la primera instrucción de Streamlit) ──
st.set_page_config(
    page_title="Atena — Consultor IA",
    # page_icon sin emojis
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── URL del API de FastAPI (configurable via variable de entorno) ──
ATENA_API_URL = os.environ.get("ATENA_API_URL", "https://atena-vugz.onrender.com").rstrip("/")

# ── 2. Cargar y aplicar estilos CSS ──
CSS_PATH = os.path.join(ROOT, "frontend", "web", "style.css")
if os.path.exists(CSS_PATH):
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# ── Modo oscuro / claro ──
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Inyección de estilos de modo oscuro (puro CSS, confiable y directo)
if st.session_state.dark_mode:
    st.markdown("""
    <style>
    :root {
        --bg-base: #0d1117 !important;
        --bg-surface: #161b22 !important;
        --bg-card: #21262d !important;
        --bg-hover: rgba(140, 198, 63, 0.12) !important;
        --text-main: #f0f6fc !important;
        --text-muted: #8b949e !important;
        --border: #30363d !important;
        --border-accent: rgba(140, 198, 63, 0.35) !important;
    }
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    section[data-testid="stSidebar"],
    body {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
    }
    .atena-topbar {
        background: #161b22 !important;
        border-bottom: 1px solid #30363d !important;
    }
    .stButton > button {
        background-color: #21262d !important;
        color: #f0f6fc !important;
        border-color: #30363d !important;
    }
    .stButton > button:hover {
        background-color: #30363d !important;
        border-color: #8CC63F !important;
        color: #8CC63F !important;
    }
    .stButton > button[kind="primary"],
    button[data-testid*="primary"] {
        background-color: #4a235a !important;
        color: #ffffff !important;
        border-color: #6c3483 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
    }
    div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
        color: #f0f6fc !important;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox div {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border-color: #30363d !important;
    }
    div[data-testid="stExpander"] {
        background-color: #161b22 !important;
        border-color: #30363d !important;
    }
    div[data-testid="stChatMessage"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
    }
    #atena-loader {
        background: #0d1117 !important;
    }
    #atena-loader .loader-logo {
        color: #f0f6fc !important;
    }
    #atena-loader .loader-sub {
        color: #8b949e !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ── Pantalla de carga (desvanece automáticamente vía CSS en 1.2s sin bloquear) ──
_loader_dark_cls = "dark" if st.session_state.dark_mode else ""
st.markdown(f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<div id="atena-loader" class="{_loader_dark_cls}">
  <div class="loader-logo">Atena</div>
  <div class="loader-sub">Consultor de Neuroanatomia &middot; Konrad Lorenz</div>
  <div class="loader-bar"><div class="loader-bar-fill"></div></div>
</div>
""", unsafe_allow_html=True)

# ── 3. Inicialización de Estado ──
if "historial" not in st.session_state:
    st.session_state.historial = []
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "_uploader_key" not in st.session_state:
    st.session_state["_uploader_key"] = 0

try:
    from db_metrics import registrar_consulta, registrar_evaluacion
    from db_preguntas import obtener_preguntas_por_nivel
except ImportError as e:
    st.error(f"Error al importar módulos del sistema: {e}")
    st.stop()

# ── Función de consulta RAG vía API (ligero: sin cargar modelos localmente) ──
def consultar_via_api(pregunta: str, nivel: str = "Principiante", k: int = 6):
    """
    Llama al endpoint POST /api/consultar del API de FastAPI.
    Retorna (respuesta_texto, lista_fuentes) donde lista_fuentes es una lista de dicts
    con claves: fuente, pagina, fragmento.
    """
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{ATENA_API_URL}/api/consultar",
                json={
                    "pregunta": pregunta,
                    "nivel": nivel,
                    "k": k,
                    "formato_unity": False,  # Queremos Markdown, no Unity Rich Text
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("respuesta", ""), data.get("fuentes", [])
    except httpx.TimeoutException:
        return "El servidor tardó demasiado en responder. Por favor, intenta de nuevo.", []
    except Exception as exc:
        return f"Error al contactar el sistema RAG: {exc}", []

# Vector store no disponible en modo ligero (vs = None)
vs = None

# Cargar Componentes de Interfaz
from components.sidebar import render_sidebar
from config import es_consulta_saludo, NO_INFO_PHRASES, nombre_legible
import html as html_module
import re

def formatear_evidencia_limpia(texto: str) -> str:
    """Limpia saltos de línea rotos, guiones, marcas de agua y fragmentación de palabras típica de PDFs."""
    if not texto:
        return ""
    # Quitar marcas de agua comunes de libros escaneados
    t = re.sub(r'www\.freelibros\.(com|org|me)', '', texto, flags=re.IGNORECASE)
    # 1. Unir palabras partidas por guión al final de línea (ej: 'espi-\nnal' -> 'espinal')
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', t)
    t = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', t)
    # 2. Corregir errores comunes de escaneo / OCR en PDFs
    reemplazos = {
        "ga nglios": "ganglios",
        "hemisf erios": "hemisferios",
        "a pariencia": "apariencia",
        "co mplejo": "complejo",
        "sist ema": "sistema",
        "es encial": "esencial",
        "cavi-dad": "cavidad",
        "cavi dad": "cavidad",
        "aluminio cinaciones": "alucinaciones",
        "aluminio cinacion": "alucinación",
    }
    for roto, arreglado in reemplazos.items():
        t = t.replace(roto, arreglado)
    # 3. Fluir renglones rotos de columnas estrechas
    parrafos = t.split("\n\n")
    parrafos_procesados = []
    for p in parrafos:
        limpio = re.sub(r'\s*\n\s*', ' ', p.strip())
        limpio = re.sub(r'[ \t]+', ' ', limpio)
        if limpio:
            parrafos_procesados.append(limpio)
    return "<br><br>".join(parrafos_procesados)

# --- DIALOG DE AUTOEVALUACIÓN ---
@st.dialog("Autoevaluación de Neuroanatomía", width="large")
def mostrar_evaluacion(nivel):
    st.caption(f"Responde el cuestionario para evaluar tus conocimientos del nivel {nivel} basados en el material del laboratorio.")
    db_preguntas = obtener_preguntas_por_nivel(nivel)
    preguntas_quiz = []
    
    for i, q in enumerate(db_preguntas, 1):
        opciones = [
            f"A) {q['opcion_a']}",
            f"B) {q['opcion_b']}",
            f"C) {q['opcion_c']}",
            f"D) {q['opcion_d']}"
        ]
        letra_correcta = q['correcta'].upper()
        opcion_correcta = ""
        if letra_correcta == 'A': opcion_correcta = opciones[0]
        elif letra_correcta == 'B': opcion_correcta = opciones[1]
        elif letra_correcta == 'C': opcion_correcta = opciones[2]
        elif letra_correcta == 'D': opcion_correcta = opciones[3]
        
        preguntas_quiz.append({
            "id": q['id'],
            "num": i,
            "pregunta": q['pregunta'],
            "opciones": opciones,
            "correcta": opcion_correcta,
            "explicacion": q['explicacion']
        })
        
    if not preguntas_quiz:
        st.info(f"No hay preguntas de evaluación registradas para el nivel {nivel}.")
        return
        
    if "quiz_respuestas" not in st.session_state:
        st.session_state.quiz_respuestas = {}
    if "quiz_evaluado" not in st.session_state:
        st.session_state.quiz_evaluado = False
        
    form_quiz = st.form(key="evaluacion_form_dialog")
    with form_quiz:
        for p in preguntas_quiz:
            st.markdown(f"**{p['num']}. {p['pregunta']}**")
            st.session_state.quiz_respuestas[p['id']] = st.radio(
                "Selecciona una opción:",
                options=p["opciones"],
                key=f"q_dlg_{p['id']}",
                label_visibility="collapsed"
            )
            st.markdown("<br>", unsafe_allow_html=True)
            
        enviar_btn = st.form_submit_button("Enviar Respuestas")
        
    if enviar_btn:
        st.session_state.quiz_evaluado = True
        
    if st.session_state.quiz_evaluado:
        st.markdown("#### Resultados de tu evaluación")
        aciertos = 0
        for p in preguntas_quiz:
            resp_usr = st.session_state.quiz_respuestas.get(p['id'])
            if not resp_usr:
                resp_usr = p["opciones"][0]
            es_correcta = p['correcta'] in resp_usr
            if es_correcta:
                aciertos += 1
                st.success(f"**Pregunta {p['num']}:** Correcto. Tu respuesta: {resp_usr}\n\n{p['explicacion']}")
            else:
                st.error(f"**Pregunta {p['num']}:** Incorrecto. Tu respuesta: {resp_usr} (Correcta: {p['correcta']})\n\n{p['explicacion']}")
                
            if not st.session_state.get(f"dlg_q_logged_{p['id']}"):
                registrar_evaluacion(p['pregunta'], resp_usr, p['correcta'], es_correcta, p['explicacion'])
                st.session_state[f"dlg_q_logged_{p['id']}"] = True
                
        nota = (aciertos / len(preguntas_quiz)) * 5.0
        st.metric("Calificación Final", f"{nota:.2f} / 5.00", f"{aciertos} de {len(preguntas_quiz)} correctas")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("Reiniciar Examen", key="reset_quiz_dlg_btn"):
                st.session_state.quiz_evaluado = False
                for p in preguntas_quiz:
                    st.session_state.pop(f"dlg_q_logged_{p['id']}", None)
                st.rerun()
        with col_r2:
            if st.button("Cerrar Ventana", key="close_quiz_dlg_btn"):
                st.session_state.quiz_evaluado = False
                for p in preguntas_quiz:
                    st.session_state.pop(f"dlg_q_logged_{p['id']}", None)
                st.rerun()

# ── Ventanita Pequeña de Consultor IA (Modal Dialog) ─────────────────────────
@st.dialog("Consultor IA — Atena", width="large")
def _dialog_consultor_ia():
    st.caption("Nivel Avanzado — Conectado a la base de conocimientos RAG")
    if "adm_chat_msgs" not in st.session_state:
        st.session_state.adm_chat_msgs = []

    chat_box = st.container(height=380)
    with chat_box:
        if not st.session_state.adm_chat_msgs:
            st.info("Escribe tu consulta sobre neuroanatomía para interactuar con Atena.")
        for _m in st.session_state.adm_chat_msgs:
            with st.chat_message(_m["role"]):
                st.markdown(_m["content"])
                if _m.get("fuentes"):
                    with st.expander("Fuentes bibliográficas"):
                        for _i, _f in enumerate(_m["fuentes"], 1):
                            st.caption(f"[{_i}] {nombre_legible(_f.get('fuente',''))} — Pág. {_f.get('pagina','?')}")

    _q = st.chat_input("Escribe tu consulta...", key="adm_dlg_chat_input")
    if _q:
        st.session_state.adm_chat_msgs.append({"role": "user", "content": _q})
        with st.spinner("Consultando..."):
            _resp, _fuentes = consultar_via_api(_q, nivel="Avanzado", k=5)
        st.session_state.adm_chat_msgs.append({"role": "assistant", "content": _resp, "fuentes": _fuentes})
        st.rerun()


# ── Panel de Administración ───────────────────────────────────────────────────
def _render_admin_dashboard():
    """Panel de administración. Secciones: Documentos | Preguntas | Estadísticas | Sistema."""
    ATENA_API_URL = os.environ.get("ATENA_API_URL", "https://atena-vugz.onrender.com").rstrip("/")
    ADMIN_PIN_ENV = st.session_state.get("adm_pin_activo", os.environ.get("ADMIN_PIN", "12345"))

    try:
        from db_preguntas import (
            obtener_preguntas_por_nivel, agregar_pregunta,
            actualizar_pregunta, eliminar_pregunta,
            obtener_niveles, obtener_temas,
        )
        _DB_AVAILABLE = True
    except ImportError:
        _DB_AVAILABLE = False

    if "adm_seccion" not in st.session_state:
        st.session_state.adm_seccion = "documentos"

    # ── Topbar profesional ────────────────────────────────────────────────────
    st.markdown("""
    <div class="atena-topbar">
        <div style="display:flex; align-items:center; gap:12px;">
            <span style="font-family:'Outfit',sans-serif; font-size:1.35rem; font-weight:700; color:var(--text-main, #1e293b); letter-spacing:-0.5px;">Atena</span>
            <span style="color:var(--text-muted, #94a3b8); font-size:0.9rem;">|</span>
            <span style="font-size:0.85rem; font-weight:500; color:var(--text-muted, #64748b);">Panel de Administracion</span>
        </div>
        <div style="flex:1;"></div>
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:0.8rem; padding:4px 10px; border-radius:20px; background:rgba(140,198,63,0.12); color:#7ab332; font-weight:600; border:1px solid rgba(140,198,63,0.3);">
                Administrador Activo
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Barra de navegación limpia y equilibrada
    col_tabs, col_actions = st.columns([5.5, 3.5])

    with col_tabs:
        t1, t2, t3, t4 = st.columns(4)
        secciones = [
            ("documentos",   "Documentos",        t1),
            ("preguntas",    "Banco de Preguntas",t2),
            ("estadisticas", "Estadisticas",      t3),
            ("sistema",      "Sistema",           t4),
        ]
        for key, label, col in secciones:
            with col:
                tipo = "primary" if st.session_state.adm_seccion == key else "secondary"
                if st.button(label, key=f"adm_nav_{key}", use_container_width=True, type=tipo):
                    st.session_state.adm_seccion = key
                    st.rerun()

    with col_actions:
        a_chat, a_theme, a_logout = st.columns([1.2, 1.2, 1.1])
        with a_chat:
            if st.button("Consultor IA", key="btn_open_dialog_chat", use_container_width=True):
                _dialog_consultor_ia()
        with a_theme:
            modo_icon = "Modo claro" if st.session_state.dark_mode else "Modo oscuro"
            if st.button(modo_icon, key="adm_toggle_dark", use_container_width=True):
                st.session_state.dark_mode = not st.session_state.dark_mode
                st.rerun()
        with a_logout:
            if st.button("Cerrar sesion", key="adm_btn_logout_top", use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()

    st.markdown("<hr style='margin:10px 0 18px; opacity:0.15;'>", unsafe_allow_html=True)
    seccion = st.session_state.adm_seccion


    # ── DOCUMENTOS ──────────────────────────────────────────────────────────
    if seccion == "documentos":
        st.markdown("### Documentos del sistema")
        st.caption("Sube materiales al servidor. El sistema los indexa para el consultor de IA.")

        col_l, col_r = st.columns([1, 1], gap="large")

        with col_l:
            st.markdown("**Subir archivo**")
            archivos = st.file_uploader(
                "Selecciona PDF o DOCX:", type=["pdf", "docx"],
                accept_multiple_files=True, key="adm_uploader"
            )
            if archivos:
                ya_subidos = st.session_state.get("adm_uploads_ok", set())
                nuevos = [f for f in archivos if f.name not in ya_subidos]
                if nuevos:
                    if st.button(
                        f"Subir e indexar ({len(nuevos)} archivo{'s' if len(nuevos) > 1 else ''})",
                        key="adm_btn_upload", use_container_width=True, type="primary"
                    ):
                        for archivo in nuevos:
                            with st.spinner(f"Indexando {archivo.name}..."):
                                try:
                                    resp = httpx.post(
                                        f"{ATENA_API_URL}/api/admin/upload",
                                        headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                                        files={"file": (archivo.name, archivo.getvalue(), "application/octet-stream")},
                                        timeout=180.0,
                                    )
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        st.success(f"{archivo.name} indexado — {data.get('fragmentos_indexados','?')} fragmentos")
                                        ya_subidos.add(archivo.name)
                                        st.session_state.pop("adm_docs_cache", None)
                                    else:
                                        st.error(f"Error: {resp.text[:120]}")
                                except Exception as e:
                                    st.error(f"Sin conexion: {e}")
                        st.session_state["adm_uploads_ok"] = ya_subidos

        with col_r:
            st.markdown("**Archivos en el servidor**")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Actualizar lista", key="adm_refresh_docs", use_container_width=True):
                    st.session_state.pop("adm_docs_cache", None)
                    st.rerun()
            with btn_col2:
                if st.button("Reindexar todo", key="adm_rebuild", use_container_width=True, type="secondary"):
                    with st.spinner("Reconstruyendo base vectorial..."):
                        try:
                            resp = httpx.post(f"{ATENA_API_URL}/api/admin/rebuild",
                                              headers={"X-Admin-Pin": ADMIN_PIN_ENV}, timeout=120.0)
                            if resp.status_code == 200:
                                st.success(f"{resp.json().get('total_vectores','?')} vectores reconstruidos")
                            else:
                                st.error(resp.text[:120])
                        except Exception as e:
                            st.error(str(e))

            if "adm_docs_cache" not in st.session_state:
                try:
                    resp = httpx.get(f"{ATENA_API_URL}/api/admin/documents",
                                     headers={"X-Admin-Pin": ADMIN_PIN_ENV}, timeout=15.0)
                    st.session_state["adm_docs_cache"] = resp.json().get("documentos", []) if resp.status_code == 200 else []
                except Exception:
                    st.session_state["adm_docs_cache"] = []

            docs = st.session_state.get("adm_docs_cache", [])
            if docs:
                for doc in docs:
                    nombre = doc["nombre"]
                    c_n, c_d = st.columns([5, 1.5])
                    with c_n:
                        st.markdown(
                            f"<div style='padding:7px 12px; background:#f8fafc; border-radius:6px; "
                            f"border:1px solid #e2e8f0; font-size:0.85rem; margin-bottom:4px; "
                            f"overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>"
                            f"{nombre_legible(nombre)}</div>",
                            unsafe_allow_html=True
                        )
                    with c_d:
                        if st.button("Eliminar", key=f"adm_del_{nombre}", use_container_width=True, help=f"Eliminar {nombre_legible(nombre)}"):
                            st.session_state["adm_pending_del"] = nombre

                if st.session_state.get("adm_pending_del"):
                    pending = st.session_state["adm_pending_del"]
                    st.warning(f"Eliminar '{nombre_legible(pending)}' del servidor. Esta accion no se puede deshacer.")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("Eliminar", key="adm_confirm_del", use_container_width=True, type="primary"):
                            with st.spinner("Eliminando..."):
                                try:
                                    resp = httpx.delete(f"{ATENA_API_URL}/api/admin/delete/{pending}",
                                                        headers={"X-Admin-Pin": ADMIN_PIN_ENV}, timeout=30.0)
                                    if resp.status_code == 200:
                                        st.success("Eliminado.")
                                        st.session_state.pop("adm_docs_cache", None)
                                    else:
                                        st.error(resp.text[:120])
                                except Exception as e:
                                    st.error(str(e))
                            st.session_state.pop("adm_pending_del", None)
                            st.rerun()
                    with cc2:
                        if st.button("Cancelar", key="adm_cancel_del", use_container_width=True):
                            st.session_state.pop("adm_pending_del", None)
                            st.rerun()
            else:
                st.info("No hay documentos o no se pudo conectar al servidor.")

    # ── BANCO DE PREGUNTAS ───────────────────────────────────────────────────
    elif seccion == "preguntas":
        st.markdown("### Banco de Preguntas")

        if not _DB_AVAILABLE:
            st.error("No se pudo conectar a la base de datos.")
            return

        try:
            niveles_db = obtener_niveles()
            temas_db = obtener_temas()
        except Exception as e:
            st.error(f"Error Supabase: {e}")
            return

        modo_q = st.radio("", ["Ver y editar", "Nueva pregunta"],
                          horizontal=True, key="adm_modo_q", label_visibility="collapsed")
        st.markdown("---")

        if modo_q == "Ver y editar":
            col_f, col_c = st.columns([2, 1])
            with col_f:
                nivel_filtro = st.selectbox("Filtrar por nivel:", ["Todos"] + niveles_db, key="adm_filtro_nivel")
            try:
                preguntas = obtener_preguntas_por_nivel(
                    nivel=None if nivel_filtro == "Todos" else nivel_filtro, cantidad=50)
            except Exception as e:
                st.error(str(e)); preguntas = []
            with col_c:
                st.metric("Total encontradas", len(preguntas))

            for p in preguntas:
                pid = p["id"]
                resumen = p["enunciado"][:65] + "..." if len(p["enunciado"]) > 65 else p["enunciado"]
                respuestas = p.get("respuestas", [])
                textos = [r["texto"] for r in respuestas]
                while len(textos) < 4:
                    textos.append("")
                idx_cor = next((i for i, r in enumerate(respuestas) if r.get("es_correcta")), 0)
                letras = ["A", "B", "C", "D"]

                with st.expander(f"#{pid} — {resumen}"):
                    with st.form(f"adm_form_{pid}"):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            n_enun = st.text_area("Enunciado:", value=p["enunciado"],
                                                   key=f"adm_enun_{pid}", height=75)
                        with c2:
                            n_niv = st.selectbox("Nivel:", niveles_db, key=f"adm_niv_{pid}",
                                index=niveles_db.index(p["nivel"]) if p["nivel"] in niveles_db else 0)
                            n_tem = st.selectbox("Tema:", temas_db, key=f"adm_tem_{pid}",
                                index=temas_db.index(p["tema"]) if p["tema"] in temas_db else 0)
                        c_op = st.columns(2)
                        opciones = []
                        for i, l in enumerate(letras):
                            with c_op[i % 2]:
                                opciones.append(st.text_input(f"Opcion {l}:", value=textos[i],
                                                               key=f"adm_op{l}_{pid}"))
                        n_cor = st.radio("Respuesta correcta:", letras, index=idx_cor,
                                          horizontal=True, key=f"adm_cor_{pid}")
                        cg, ce = st.columns(2)
                        with cg:
                            if st.form_submit_button("Guardar cambios", use_container_width=True, type="primary"):
                                ok = actualizar_pregunta(pid, n_niv, n_tem, n_enun,
                                                          opciones[0], opciones[1], opciones[2], opciones[3], n_cor)
                                if ok:
                                    st.success("Guardado.")
                                    time.sleep(0.5); st.rerun()
                                else:
                                    st.error("Error al guardar.")
                        with ce:
                            if st.form_submit_button("Eliminar", use_container_width=True):
                                st.session_state[f"adm_cdel_{pid}"] = True

                    if st.session_state.get(f"adm_cdel_{pid}"):
                        st.warning("Confirma que deseas eliminar esta pregunta.")
                        cy, cn = st.columns(2)
                        with cy:
                            if st.button("Si, eliminar", key=f"adm_yes_{pid}", use_container_width=True, type="primary"):
                                eliminar_pregunta(pid)
                                st.session_state.pop(f"adm_cdel_{pid}", None)
                                time.sleep(0.5); st.rerun()
                        with cn:
                            if st.button("Cancelar", key=f"adm_no_{pid}", use_container_width=True):
                                st.session_state.pop(f"adm_cdel_{pid}", None)
                                st.rerun()
        else:
            st.markdown("**Nueva pregunta**")
            with st.form("adm_nueva_form", clear_on_submit=True):
                ca, cb = st.columns([3, 1])
                with ca:
                    n_enun = st.text_area("Enunciado:", height=90, key="adm_nueva_enun")
                with cb:
                    n_niv = st.selectbox("Nivel:", niveles_db, key="adm_nueva_niv")
                    n_tem = st.selectbox("Tema:", temas_db, key="adm_nueva_tem")
                c_op = st.columns(2)
                with c_op[0]:
                    op_a = st.text_input("Opcion A:", key="adm_nop_a")
                    op_c = st.text_input("Opcion C:", key="adm_nop_c")
                with c_op[1]:
                    op_b = st.text_input("Opcion B:", key="adm_nop_b")
                    op_d = st.text_input("Opcion D:", key="adm_nop_d")
                n_cor = st.radio("Respuesta correcta:", ["A", "B", "C", "D"],
                                  horizontal=True, key="adm_nueva_cor")
                if st.form_submit_button("Crear pregunta", use_container_width=True, type="primary"):
                    if not n_enun.strip():
                        st.error("El enunciado no puede estar vacio.")
                    elif not all([op_a, op_b, op_c, op_d]):
                        st.error("Completa las 4 opciones.")
                    else:
                        ok = agregar_pregunta(n_niv, n_tem, n_enun, op_a, op_b, op_c, op_d, n_cor)
                        st.success("Pregunta creada.") if ok else st.error("Error al crear.")

    # ── ESTADISTICAS ─────────────────────────────────────────────────────────
    elif seccion == "estadisticas":
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        from datetime import date, timedelta

        st.markdown("### Estadisticas de uso")

        try:
            from db_metrics import (
                obtener_metricas, obtener_preguntas_frecuentes,
                obtener_volumen_diario, obtener_distribucion_niveles,
                obtener_precision_evaluaciones, obtener_tendencia_aciertos_diaria,
                obtener_consultas_recientes,
            )
            _METRICS_OK = True
        except ImportError:
            _METRICS_OK = False

        if not _METRICS_OK:
            st.error("No se pudo conectar al modulo de metricas.")
        else:
            # ── Filtros de fecha ────────────────────────────────────────────
            fc1, fc2, fc3 = st.columns([1, 1, 1])
            with fc1:
                fecha_desde = st.date_input("Desde:", value=date.today() - timedelta(days=30), key="adm_f_desde")
            with fc2:
                fecha_hasta = st.date_input("Hasta:", value=date.today(), key="adm_f_hasta")
            with fc3:
                acceso_rapido = st.selectbox("Acceso rapido:", ["Personalizado", "Ultima semana", "Ultimo mes", "Ultimos 3 meses", "Todo el historial"], key="adm_rapido")
                if acceso_rapido != "Personalizado":
                    deltas = {"Ultima semana": 7, "Ultimo mes": 30, "Ultimos 3 meses": 90, "Todo el historial": 3650}
                    fecha_desde = date.today() - timedelta(days=deltas[acceso_rapido])
                    fecha_hasta = date.today()

            dias = max(1, (fecha_hasta - fecha_desde).days + 1)
            st.markdown("---")

            try:
                stats        = obtener_metricas()
                volumen      = obtener_volumen_diario(dias)
                frecuentes   = obtener_preguntas_frecuentes(10)
                dist_niveles = obtener_distribucion_niveles()
                precision    = obtener_precision_evaluaciones()
                tend_aciertos= obtener_tendencia_aciertos_diaria(dias)
                recientes    = obtener_consultas_recientes(20)
            except Exception as e:
                st.error(f"Error al cargar estadisticas: {e}")
                st.stop()

            # ── KPIs ────────────────────────────────────────────────────────
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Consultas totales", stats["total_consultas"])
            k2.metric("Latencia promedio", f"{stats['latencia_promedio']} s" if stats["latencia_promedio"] else "—")
            k3.metric("Evaluaciones", stats["total_evaluaciones"])
            k4.metric("Precision global", f"{stats['porcentaje_aciertos']} %" if stats["total_evaluaciones"] else "—")
            aciertos = stats.get("evaluaciones_correctas", 0)
            k5.metric("Respuestas correctas", aciertos)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── FILA 1: Volumen + Torta niveles ─────────────────────────────
            col_v, col_p = st.columns([3, 2], gap="large")

            with col_v:
                if volumen:
                    df_vol = pd.DataFrame(volumen)
                    df_vol["dia"] = pd.to_datetime(df_vol["dia"])
                    df_vol["latencia_avg"] = df_vol["latencia_avg"].apply(lambda x: round(float(x), 2) if x else 0)
                    fig_vol = px.bar(
                        df_vol, x="dia", y="total",
                        labels={"dia": "Fecha", "total": "Consultas"},
                        title="Consultas por dia",
                        color_discrete_sequence=["#8CC63F"],
                        custom_data=["latencia_avg"],
                    )
                    fig_vol.update_traces(
                        hovertemplate="<b>%{x|%d %b}</b><br>Consultas: %{y}<br>Latencia prom: %{customdata[0]} s<extra></extra>"
                    )
                    fig_vol.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter"), margin=dict(l=0, r=0, t=40, b=0),
                        height=280, title_font_size=14,
                        xaxis=dict(showgrid=False), yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
                    )
                    st.plotly_chart(fig_vol, use_container_width=True)
                else:
                    st.info("Sin datos de volumen en el periodo seleccionado.")

            with col_p:
                if dist_niveles:
                    labels = list(dist_niveles.keys())
                    values = list(dist_niveles.values())
                    fig_pie = go.Figure(go.Pie(
                        labels=labels, values=values, hole=0.5,
                        marker=dict(colors=["#4a235a", "#8CC63F", "#7ab332", "#6c3483"]),
                        textinfo="percent+label",
                    ))
                    fig_pie.update_layout(
                        title="Distribucion por nivel",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter"),
                        margin=dict(l=0, r=0, t=40, b=0),
                        height=280, showlegend=False, title_font_size=14,
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Sin datos de niveles.")

            st.markdown("---")

            # ── FILA 2: Barras frecuentes + Barras precision ─────────────────
            col_f, col_pr = st.columns([1, 1], gap="large")

            with col_f:
                if frecuentes:
                    df_freq = pd.DataFrame(frecuentes)
                    df_freq["pregunta_corta"] = df_freq["pregunta"].apply(lambda x: x[:55] + "..." if len(x) > 55 else x)
                    df_freq["lat_r"] = df_freq["latencia_avg"].apply(lambda x: round(float(x), 2) if x else 0)
                    fig_freq = px.bar(
                        df_freq, x="veces", y="pregunta_corta",
                        orientation="h",
                        labels={"veces": "Veces consultada", "pregunta_corta": ""},
                        title="Temas mas consultados",
                        color="veces",
                        color_continuous_scale=["#c7e8a0", "#4a235a"],
                        custom_data=["lat_r"],
                    )
                    fig_freq.update_traces(
                        hovertemplate="<b>%{y}</b><br>Consultas: %{x}<br>Latencia: %{customdata[0]} s<extra></extra>"
                    )
                    fig_freq.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter"), margin=dict(l=0, r=0, t=40, b=0),
                        height=340, coloraxis_showscale=False, title_font_size=14,
                        yaxis=dict(tickfont=dict(size=10)), xaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
                    )
                    st.plotly_chart(fig_freq, use_container_width=True)
                else:
                    st.info("Sin datos de frecuencia aun.")

            with col_pr:
                if precision:
                    df_prec = pd.DataFrame(precision)
                    df_prec["preg_c"] = df_prec["pregunta"].apply(lambda x: x[:50] + "..." if len(x) > 50 else x)
                    df_prec["porcentaje"] = df_prec["porcentaje"].apply(float)
                    fig_prec = px.bar(
                        df_prec, x="porcentaje", y="preg_c",
                        orientation="h",
                        labels={"porcentaje": "% Aciertos", "preg_c": ""},
                        title="Precision por pregunta",
                        color="porcentaje",
                        color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
                        range_color=[0, 100],
                        custom_data=["intentos"],
                    )
                    fig_prec.update_traces(
                        hovertemplate="<b>%{y}</b><br>Aciertos: %{x}%<br>Intentos: %{customdata[0]}<extra></extra>"
                    )
                    fig_prec.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter"), margin=dict(l=0, r=0, t=40, b=0),
                        height=340, coloraxis_showscale=False, title_font_size=14,
                        yaxis=dict(tickfont=dict(size=10)), xaxis=dict(gridcolor="rgba(0,0,0,0.06)", range=[0, 100]),
                    )
                    st.plotly_chart(fig_prec, use_container_width=True)
                else:
                    st.info("Sin datos de evaluaciones aun.")

            # ── FILA 3: Tendencia de aciertos ───────────────────────────────
            if tend_aciertos:
                st.markdown("---")
                df_tend = pd.DataFrame(tend_aciertos)
                df_tend["dia"] = pd.to_datetime(df_tend["dia"])
                df_tend["pct_aciertos"] = df_tend["pct_aciertos"].apply(float)
                fig_tend = px.line(
                    df_tend, x="dia", y="pct_aciertos",
                    labels={"dia": "Fecha", "pct_aciertos": "% Aciertos"},
                    title="Tendencia de precision en evaluaciones",
                    markers=True,
                    color_discrete_sequence=["#4a235a"],
                )
                fig_tend.add_hline(y=70, line_dash="dash", line_color="#f59e0b", annotation_text="Meta 70%")
                fig_tend.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter"), margin=dict(l=0, r=0, t=40, b=0),
                    height=260, title_font_size=14,
                    yaxis=dict(range=[0, 105], gridcolor="rgba(0,0,0,0.06)"),
                    xaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_tend, use_container_width=True)

            # ── FILA 4: Log de consultas recientes ───────────────────────────
            st.markdown("---")
            st.markdown("**Registro de consultas recientes**")
            if recientes:
                df_rec = pd.DataFrame(recientes)
                df_rec["pregunta"] = df_rec["pregunta"].apply(lambda x: x[:90] + "..." if len(x) > 90 else x)
                df_rec["fecha"] = pd.to_datetime(df_rec["fecha"]).dt.strftime("%d/%m/%Y %H:%M")
                df_rec["latencia"] = df_rec["latencia"].apply(lambda x: f"{round(float(x),2)} s" if x else "—")
                df_rec = df_rec.rename(columns={"fecha": "Fecha", "pregunta": "Consulta", "nivel": "Nivel", "latencia": "Latencia"})
                st.dataframe(
                    df_rec,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Fecha":    st.column_config.TextColumn("Fecha", width="small"),
                        "Nivel":    st.column_config.TextColumn("Nivel", width="small"),
                        "Latencia": st.column_config.TextColumn("Latencia", width="small"),
                        "Consulta": st.column_config.TextColumn("Consulta"),
                    }
                )
            else:
                st.info("No hay consultas registradas aun.")

    # ── SISTEMA ──────────────────────────────────────────────────────────────
    elif seccion == "sistema":
        st.markdown("### Sistema y Configuracion")

        col_s1, col_s2, col_s3 = st.columns(3)
        info_cards = [
            ("Servicio API", "atena-vugz.onrender.com", "#22c55e"),
            ("Modelo LLM", os.environ.get("GROQ_LLM_MODEL", "N/A"), "#1e293b"),
            ("Embeddings", os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2"), "#1e293b"),
        ]
        for col, (titulo, valor, color) in zip([col_s1, col_s2, col_s3], info_cards):
            with col:
                st.markdown(
                    f"<div style='background:#f8fafc; border-radius:8px; padding:14px 16px; border:1px solid #e2e8f0;'>"
                    f"<div style='font-size:0.72rem; color:#94a3b8; margin-bottom:4px; text-transform:uppercase; letter-spacing:.05em;'>{titulo}</div>"
                    f"<div style='font-size:0.88rem; color:{color}; font-weight:600;'>{valor}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Verificar conexion con el API", key="adm_ping"):
            try:
                resp = httpx.get(f"{ATENA_API_URL}/salud", timeout=10.0)
                data = resp.json()
                if data.get("estado") == "ok":
                    vs_ok = data.get("vector_store_listo", False)
                    st.success(f"API activo. Vector Store: {'listo' if vs_ok else 'no disponible'}")
                else:
                    st.warning(str(data))
            except Exception as e:
                st.error(f"Sin conexion: {e}")

        st.markdown("---")
        st.markdown("**Cambiar PIN de administrador**")
        st.caption("El cambio aplica para esta sesion. Para hacerlo permanente, actualiza ADMIN_PIN en las variables de entorno de Render.")
        with st.form("adm_cambiar_pin", clear_on_submit=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                pin_actual = st.text_input("PIN actual:", type="password", key="adm_pin_actual")
            with col_p2:
                pin_nuevo = st.text_input("PIN nuevo:", type="password", key="adm_pin_nuevo")
            if st.form_submit_button("Cambiar PIN", use_container_width=True, type="primary"):
                pin_real = st.session_state.get("adm_pin_activo", os.environ.get("ADMIN_PIN", "12345"))
                if pin_actual != pin_real:
                    st.error("El PIN actual es incorrecto.")
                elif len(pin_nuevo) < 4:
                    st.error("El PIN nuevo debe tener al menos 4 caracteres.")
                else:
                    st.session_state["adm_pin_activo"] = pin_nuevo
                    st.success("PIN actualizado para esta sesion.")





    
# ── 4. Enrutamiento principal: Admin vs Chat de Usuario ──────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

is_admin = st.session_state.get("is_admin", False)

if is_admin:
    # Ocultar completamente el sidebar de Streamlit en modo administrador para aprovechar el 100% del ancho
    st.markdown("""
    <style>
    section[data-testid="stSidebar"],
    div[data-testid="stSidebarCollapsedControl"],
    button[data-testid="baseButton-headerNoPadding"] {
        display: none !important;
        width: 0px !important;
        min-width: 0px !important;
    }
    .main .block-container {
        padding-top: 1.2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1400px !important;
        margin: 0 auto !important;
    }
    </style>
    """, unsafe_allow_html=True)
    _render_admin_dashboard()

else:
    # Renderizar el sidebar únicamente para usuarios normales
    with st.sidebar:
        nivel, k_chunks, is_admin_sidebar, lanzar_evaluacion, vs = render_sidebar(vs, disabled=st.session_state.is_generating)

    if is_admin_sidebar:
        st.session_state.is_admin = True
        st.rerun()

    if lanzar_evaluacion:
        mostrar_evaluacion(nivel)
    # ── Interfaz de Chat para usuarios ───────────────────────────────────────
    clase_vacio = "chat-vacio" if len(st.session_state.mensajes) == 0 else "chat-con-mensajes"
    st.markdown(f"<h2 class='main-title {clase_vacio}'>Consultor de Neuroanatomía</h2>", unsafe_allow_html=True)

    # Capturar input ANTES de renderizar historial
    pregunta_usuario = st.chat_input(
        "Escribe tu consulta sobre neuroanatomía...",
        key="chat_query",
        disabled=st.session_state.is_generating
    )

    chat_container = st.container()
    with chat_container:
        # Bienvenida si chat vacío
        if len(st.session_state.mensajes) == 0 and not pregunta_usuario and not st.session_state.get("pregunta_activa"):
            st.markdown(
                """
                <div style="text-align: center; padding: 48px 24px; max-width: 680px; margin: 20px auto;
                            background: rgba(255,255,255,0.6); border-radius: 16px;
                            border: 1px solid rgba(226,232,240,0.8); box-shadow: 0 4px 20px -2px rgba(0,0,0,0.05);">
                    <div style="margin-bottom: 14px;"><span style="font-family:'Outfit',sans-serif; font-size: 2.2rem; font-weight: 700; color: #4a235a; letter-spacing: -0.5px;">Atena</span></div>
                    <h2 style="color: #1e293b; font-size: 1.5rem; font-weight: 700; margin-bottom: 10px;">
                        Consultor Académico de Neuroanatomía
                    </h2>
                    <p style="color: #64748b; font-size: 0.95rem; line-height: 1.6; margin-bottom: 0;">
                        Formula libremente cualquier consulta conceptual, funcional o anatómica.
                        Las respuestas son sintetizadas en tiempo real a partir de la literatura científica indexada.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Historial de mensajes
        for msg in st.session_state.mensajes:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("es_respuesta_sin_info"):
                    st.markdown(
                        '<div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);'
                        'color:#10b981;padding:6px 12px;border-radius:6px;font-size:0.85rem;margin-top:8px;'
                        'display:inline-block;font-weight:500;">'
                        'Respuesta validada: El sistema reconoció el límite de su conocimiento'
                        '</div>',
                        unsafe_allow_html=True
                    )
                if msg.get("evidencia_html"):
                    with st.expander("Ver Evidencia Documental (Citas y Referencias)"):
                        st.markdown(msg["evidencia_html"], unsafe_allow_html=True)
                if msg.get("reporte"):
                    st.download_button(
                        label="Descargar Reporte",
                        data=msg["reporte"],
                        file_name="consulta_atena.txt",
                        mime="text/plain",
                        key=f"dl_{msg['id']}"
                    )

        # Nueva pregunta → activar generación
        if pregunta_usuario:
            if not pregunta_usuario.strip():
                st.warning("Por favor, escribe una pregunta válida.")
            else:
                st.session_state.pregunta_activa = pregunta_usuario
                st.session_state.is_generating = True
                st.rerun()

        # Procesar pregunta activa
        pregunta_a_procesar = st.session_state.get("pregunta_activa")
        if pregunta_a_procesar:
            st.session_state.historial.append(pregunta_a_procesar)
            st.session_state.mensajes.append({"role": "user", "content": pregunta_a_procesar, "id": str(time.time())})
            with st.chat_message("user"):
                st.markdown(pregunta_a_procesar)

            with st.chat_message("assistant"):
                try:
                    thinking_placeholder = st.empty()
                    thinking_placeholder.markdown(
                        """
                        <div style="display:flex;align-items:center;gap:8px;padding:4px 0;">
                            <div style="display:flex;gap:4px;">
                                <span style="background:#8CC63F;width:8px;height:8px;border-radius:50%;display:inline-block;animation:pulse 1.4s infinite ease-in-out both;animation-delay:-0.32s;"></span>
                                <span style="background:#8CC63F;width:8px;height:8px;border-radius:50%;display:inline-block;animation:pulse 1.4s infinite ease-in-out both;animation-delay:-0.16s;"></span>
                                <span style="background:#8CC63F;width:8px;height:8px;border-radius:50%;display:inline-block;animation:pulse 1.4s infinite ease-in-out both;"></span>
                            </div>
                            <span style="color:#64748b;font-size:0.85rem;font-style:italic;">Consultando fuentes...</span>
                        </div>
                        <style>@keyframes pulse{0%,80%,100%{transform:scale(0);opacity:0;}40%{transform:scale(1.0);opacity:1;}}</style>
                        """,
                        unsafe_allow_html=True
                    )

                    t_start = time.time()
                    respuesta_texto, fuentes = consultar_via_api(pregunta_a_procesar, nivel=nivel, k=k_chunks)
                    thinking_placeholder.empty()
                    st.markdown(respuesta_texto)
                    latencia = time.time() - t_start

                    es_respuesta_sin_info = any(p in respuesta_texto.lower() for p in NO_INFO_PHRASES)
                    es_saludo = es_consulta_saludo(pregunta_a_procesar)
                    registrar_consulta(pregunta_a_procesar, respuesta_texto, nivel.lower(), latencia)

                    if es_respuesta_sin_info:
                        st.markdown(
                            '<div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);'
                            'color:#10b981;padding:6px 12px;border-radius:6px;font-size:0.85rem;margin-top:8px;'
                            'display:inline-block;font-weight:500;">'
                            'Respuesta validada: El sistema reconoció el límite de su conocimiento'
                            '</div>',
                            unsafe_allow_html=True
                        )

                    evidencia_html = ""
                    reporte_txt = ""

                    if len(fuentes) > 0 and not es_saludo:
                        evidencias_lista = []
                        fuentes_txt_lista = []
                        for i, fuente in enumerate(fuentes, 1):
                            nombre_revista = nombre_legible(fuente.get("fuente", "desconocido"))
                            pagina = fuente.get("pagina", "?")
                            texto_escapado = html_module.escape(fuente.get("fragmento", ""))
                            texto_limpio = formatear_evidencia_limpia(texto_escapado)
                            evidencias_lista.append(
                                f"<div style='margin-bottom:14px;background:#ffffff;border:1px solid #e2e8f0;"
                                f"border-left:4px solid #8CC63F;border-radius:8px;padding:12px 16px;'>"
                                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
                                f"<span style='font-weight:600;font-size:0.88rem;color:#1e293b;'>[{i}] {nombre_revista}</span>"
                                f"<span style='background:#f1f5f9;color:#475569;font-size:0.76rem;padding:2px 8px;border-radius:10px;'>Pág. {pagina}</span>"
                                f"</div><div style='font-size:0.86rem;color:#334155;line-height:1.6;'>{texto_limpio}</div></div>"
                            )
                            fuentes_txt_lista.append(f"  [{i}] {nombre_revista} — Pág. {pagina}")

                        evidencia_html = f"<div style='max-height:380px;overflow-y:auto;padding-right:8px;margin-top:6px;'>{''.join(evidencias_lista)}</div>"
                        with st.expander("Ver Evidencia Documental (Citas y Referencias)"):
                            st.markdown(evidencia_html, unsafe_allow_html=True)

                        reporte_txt = (
                            f"=========================================\n"
                            f"CONSULTA NEUROANATÓMICA — REPORTE RAG\n"
                            f"=========================================\n\n"
                            f"PREGUNTA:\n{pregunta_a_procesar}\n\n"
                            f"RESPUESTA:\n{respuesta_texto}\n\n"
                            f"FUENTES:\n" + "\n".join(fuentes_txt_lista) + "\n\n========================================="
                        )
                        st.download_button(
                            label="Descargar Reporte",
                            data=reporte_txt,
                            file_name="consulta_atena.txt",
                            mime="text/plain",
                            key=f"dl_new_{time.time()}"
                        )

                    st.session_state.mensajes.append({
                        "role": "assistant",
                        "content": respuesta_texto,
                        "es_respuesta_sin_info": es_respuesta_sin_info,
                        "evidencia_html": evidencia_html,
                        "reporte": reporte_txt,
                        "id": str(time.time())
                    })
                    st.session_state.pregunta_activa = None
                    st.session_state.is_generating = False
                    st.rerun()
                except Exception as e:
                    st.session_state.pregunta_activa = None
                    st.session_state.is_generating = False
                    st.error(f"Error al generar respuesta: {str(e)}")


