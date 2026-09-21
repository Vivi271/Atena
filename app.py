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
    page_title="Atena",
    page_icon="🧠",
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

# ── Viewport meta tag for proper mobile rendering ──
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
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
        return "⏳ El servidor tardó demasiado en responder. Por favor, intenta de nuevo.", []
    except Exception as exc:
        return f"❌ Error al contactar el sistema RAG: {exc}", []

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

# ── Función: Panel Admin Dashboard (limpio, sin tabs anidados) ────────────────
def _render_admin_dashboard():
    """
    Panel de administración profesional. Navegación simple sin tabs anidados.
    Todas las keys tienen prefijo 'adm_' para evitar conflictos con el sidebar.
    """
    ATENA_API_URL = os.environ.get("ATENA_API_URL", "https://atena-vugz.onrender.com").rstrip("/")
    ADMIN_PIN_ENV = os.environ.get("ADMIN_PIN", "12345")

    try:
        from db_preguntas import (
            obtener_preguntas_por_nivel, agregar_pregunta,
            actualizar_pregunta, eliminar_pregunta,
            obtener_niveles, obtener_temas,
        )
        _DB_AVAILABLE = True
    except ImportError:
        _DB_AVAILABLE = False

    # ── Navegación por sección ────────────────────────────────────────────────
    if "adm_seccion" not in st.session_state:
        st.session_state.adm_seccion = "documentos"

    # Botones de navegación en la parte superior
    nav_cols = st.columns(4)
    secciones = [
        ("documentos", "📚 Documentos"),
        ("preguntas",  "📋 Preguntas"),
        ("consultor",  "💬 Consultor IA"),
        ("sistema",    "⚙️ Sistema"),
    ]
    for col, (key, label) in zip(nav_cols, secciones):
        with col:
            activo = st.session_state.adm_seccion == key
            tipo = "primary" if activo else "secondary"
            if st.button(label, key=f"adm_nav_{key}", use_container_width=True, type=tipo):
                st.session_state.adm_seccion = key
                st.rerun()

    st.markdown("<hr style='margin:12px 0 20px; border-color:rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    seccion = st.session_state.adm_seccion

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: DOCUMENTOS
    # ══════════════════════════════════════════════════════════════════════════
    if seccion == "documentos":
        st.markdown("## 📚 Documentos del sistema")
        st.caption("Sube libros y materiales al servidor. El sistema los indexa automáticamente para el consultor de IA.")

        col_l, col_r = st.columns([1, 1], gap="large")

        # Columna izquierda: subir
        with col_l:
            st.markdown("#### Subir nuevo archivo")
            archivos = st.file_uploader(
                "PDF o DOCX:", type=["pdf", "docx"],
                accept_multiple_files=True, key="adm_uploader"
            )
            if archivos:
                ya_subidos = st.session_state.get("adm_uploads_ok", set())
                nuevos = [f for f in archivos if f.name not in ya_subidos]
                if nuevos:
                    if st.button(f"⬆️ Subir e indexar ({len(nuevos)} archivo{'s' if len(nuevos)>1 else ''})",
                                 key="adm_btn_upload", use_container_width=True, type="primary"):
                        for archivo in nuevos:
                            with st.spinner(f"Indexando '{archivo.name}'..."):
                                try:
                                    resp = httpx.post(
                                        f"{ATENA_API_URL}/api/admin/upload",
                                        headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                                        files={"file": (archivo.name, archivo.getvalue(), "application/octet-stream")},
                                        timeout=180.0,
                                    )
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        st.success(f"✅ {archivo.name} — {data.get('fragmentos_indexados','?')} fragmentos")
                                        ya_subidos.add(archivo.name)
                                        st.session_state.pop("adm_docs_cache", None)
                                    else:
                                        st.error(f"Error: {resp.text[:120]}")
                                except Exception as e:
                                    st.error(f"Sin conexión: {e}")
                        st.session_state["adm_uploads_ok"] = ya_subidos

        # Columna derecha: lista + acciones
        with col_r:
            st.markdown("#### Archivos en el servidor")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🔄 Actualizar", key="adm_refresh_docs", use_container_width=True):
                    st.session_state.pop("adm_docs_cache", None)
                    st.rerun()
            with btn_col2:
                if st.button("♻️ Reindexar todo", key="adm_rebuild", use_container_width=True, type="secondary"):
                    with st.spinner("Reconstruyendo base vectorial..."):
                        try:
                            resp = httpx.post(f"{ATENA_API_URL}/api/admin/rebuild",
                                              headers={"X-Admin-Pin": ADMIN_PIN_ENV}, timeout=120.0)
                            if resp.status_code == 200:
                                st.success(f"✅ {resp.json().get('total_vectores','?')} vectores listos")
                            else:
                                st.error(resp.text[:120])
                        except Exception as e:
                            st.error(str(e))

            # Cargar lista de documentos
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
                    c_n, c_d = st.columns([7, 1])
                    with c_n:
                        st.markdown(
                            f"<div style='padding:8px 12px; background:rgba(255,255,255,0.05); border-radius:8px; "
                            f"border:1px solid rgba(255,255,255,0.08); font-size:0.86rem; margin-bottom:5px; "
                            f"color:#e2e8f0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>"
                            f"📄 {nombre_legible(nombre)}</div>",
                            unsafe_allow_html=True
                        )
                    with c_d:
                        if st.button("🗑️", key=f"adm_del_{nombre}", help="Eliminar"):
                            st.session_state["adm_pending_del"] = nombre

                if st.session_state.get("adm_pending_del"):
                    pending = st.session_state["adm_pending_del"]
                    st.warning(f"⚠️ ¿Eliminar **{nombre_legible(pending)}** del servidor?")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("Sí, eliminar", key="adm_confirm_del", use_container_width=True, type="primary"):
                            with st.spinner("Eliminando..."):
                                try:
                                    resp = httpx.delete(f"{ATENA_API_URL}/api/admin/delete/{pending}",
                                                        headers={"X-Admin-Pin": ADMIN_PIN_ENV}, timeout=30.0)
                                    if resp.status_code == 200:
                                        st.success("✅ Eliminado.")
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

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: BANCO DE PREGUNTAS
    # ══════════════════════════════════════════════════════════════════════════
    elif seccion == "preguntas":
        st.markdown("## 📋 Banco de Preguntas de Evaluación")

        if not _DB_AVAILABLE:
            st.error("❌ No se pudo conectar a Supabase.")
            return

        try:
            niveles_db = obtener_niveles()
            temas_db = obtener_temas()
        except Exception as e:
            st.error(f"Error Supabase: {e}")
            return

        # Sub-navegación: Ver/Editar o Nueva
        modo_q = st.radio("", ["📖 Ver y editar", "➕ Nueva pregunta"],
                          horizontal=True, key="adm_modo_q", label_visibility="collapsed")
        st.markdown("---")

        if modo_q == "📖 Ver y editar":
            col_f, col_c = st.columns([2, 1])
            with col_f:
                nivel_filtro = st.selectbox("Nivel:", ["todos"] + niveles_db, key="adm_filtro_nivel")
            try:
                preguntas = obtener_preguntas_por_nivel(
                    nivel=None if nivel_filtro == "todos" else nivel_filtro, cantidad=50)
            except Exception as e:
                st.error(str(e)); preguntas = []
            with col_c:
                st.metric("Total", len(preguntas))

            for p in preguntas:
                pid = p["id"]
                resumen = p["enunciado"][:65] + "…" if len(p["enunciado"]) > 65 else p["enunciado"]
                respuestas = p.get("respuestas", [])
                textos = [r["texto"] for r in respuestas]
                while len(textos) < 4: textos.append("")
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
                                opciones.append(st.text_input(f"Opción {l}:", value=textos[i],
                                                               key=f"adm_op{l}_{pid}"))
                        n_cor = st.radio("Respuesta correcta:", letras, index=idx_cor,
                                          horizontal=True, key=f"adm_cor_{pid}")
                        cg, ce = st.columns(2)
                        with cg:
                            if st.form_submit_button("💾 Guardar", use_container_width=True, type="primary"):
                                ok = actualizar_pregunta(pid, n_niv, n_tem, n_enun,
                                                          opciones[0], opciones[1], opciones[2], opciones[3], n_cor)
                                if ok:
                                    st.success("✅ Guardado.")
                                    time.sleep(0.5); st.rerun()
                                else:
                                    st.error("Error al guardar.")
                        with ce:
                            if st.form_submit_button("🗑️ Eliminar", use_container_width=True):
                                st.session_state[f"adm_cdel_{pid}"] = True

                    if st.session_state.get(f"adm_cdel_{pid}"):
                        st.warning("¿Eliminar esta pregunta?")
                        cy, cn = st.columns(2)
                        with cy:
                            if st.button("Sí", key=f"adm_yes_{pid}", use_container_width=True, type="primary"):
                                eliminar_pregunta(pid)
                                st.session_state.pop(f"adm_cdel_{pid}", None)
                                time.sleep(0.5); st.rerun()
                        with cn:
                            if st.button("No", key=f"adm_no_{pid}", use_container_width=True):
                                st.session_state.pop(f"adm_cdel_{pid}", None)
                                st.rerun()
        else:
            # Nueva pregunta
            with st.form("adm_nueva_form", clear_on_submit=True):
                ca, cb = st.columns([3, 1])
                with ca:
                    n_enun = st.text_area("Enunciado:", height=90, key="adm_nueva_enun")
                with cb:
                    n_niv = st.selectbox("Nivel:", niveles_db, key="adm_nueva_niv")
                    n_tem = st.selectbox("Tema:", temas_db, key="adm_nueva_tem")
                c_op = st.columns(2)
                with c_op[0]:
                    op_a = st.text_input("Opción A:", key="adm_nop_a")
                    op_c = st.text_input("Opción C:", key="adm_nop_c")
                with c_op[1]:
                    op_b = st.text_input("Opción B:", key="adm_nop_b")
                    op_d = st.text_input("Opción D:", key="adm_nop_d")
                n_cor = st.radio("Respuesta correcta:", ["A", "B", "C", "D"],
                                  horizontal=True, key="adm_nueva_cor")
                if st.form_submit_button("✅ Crear Pregunta", use_container_width=True, type="primary"):
                    if not n_enun.strip():
                        st.error("El enunciado no puede estar vacío.")
                    elif not all([op_a, op_b, op_c, op_d]):
                        st.error("Completa las 4 opciones.")
                    else:
                        ok = agregar_pregunta(n_niv, n_tem, n_enun, op_a, op_b, op_c, op_d, n_cor)
                        st.success("✅ Creada.") if ok else st.error("Error. Verifica nivel y tema en Supabase.")

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: CONSULTOR IA
    # ══════════════════════════════════════════════════════════════════════════
    elif seccion == "consultor":
        st.markdown("## 💬 Consultor IA")
        st.caption("Prueba el sistema RAG con nivel Avanzado.")
        _render_chat_interface(nivel="Avanzado", k_chunks=6)

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 4: SISTEMA
    # ══════════════════════════════════════════════════════════════════════════
    elif seccion == "sistema":
        st.markdown("## ⚙️ Estado del Sistema")

        col_s1, col_s2, col_s3 = st.columns(3)
        info_cards = [
            ("SERVICIO API", "🟢 atena-vugz.onrender.com", "#22c55e"),
            ("MODELO LLM", f"🧠 {os.environ.get('GROQ_LLM_MODEL','N/A')}", "#e2e8f0"),
            ("EMBEDDINGS", f"🔢 {os.environ.get('EMBED_MODEL','all-MiniLM-L6-v2')}", "#e2e8f0"),
        ]
        for col, (titulo, valor, color) in zip([col_s1, col_s2, col_s3], info_cards):
            with col:
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.05); border-radius:12px; padding:16px; "
                    f"border:1px solid rgba(255,255,255,0.1);'>"
                    f"<div style='font-size:0.72rem; color:#94a3b8; margin-bottom:6px; letter-spacing:.05em;'>{titulo}</div>"
                    f"<div style='font-size:0.88rem; color:{color}; font-weight:600;'>{valor}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Verificar estado del API", key="adm_ping", use_container_width=False):
            try:
                resp = httpx.get(f"{ATENA_API_URL}/salud", timeout=10.0)
                data = resp.json()
                if data.get("estado") == "ok":
                    vs_ok = data.get("vector_store_listo", False)
                    st.success(f"✅ API activo — Vector Store: {'✅ listo' if vs_ok else '⚠️ no disponible'}")
                else:
                    st.warning(str(data))
            except Exception as e:
                st.error(f"Sin conexión: {e}")


def _render_chat_interface(nivel="Principiante", k_chunks=5):
    """Interfaz de chat para el tab Consultor IA del admin."""
    if "adm_mensajes" not in st.session_state:
        st.session_state.adm_mensajes = []

    pregunta = st.chat_input("Escribe tu consulta...", key="adm_chat_input")

    for msg in st.session_state.adm_mensajes:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if pregunta:
        st.session_state.adm_mensajes.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Consultando fuentes..."):
                respuesta_texto, fuentes = consultar_via_api(pregunta, nivel=nivel, k=k_chunks)
            st.markdown(respuesta_texto)
            if fuentes:
                with st.expander("Ver fuentes documentales"):
                    for i, f in enumerate(fuentes, 1):
                        st.markdown(f"**[{i}] {nombre_legible(f.get('fuente',''))}** — Pág. {f.get('pagina','?')}")
                        st.caption(f.get("fragmento","")[:200])
        st.session_state.adm_mensajes.append({"role": "assistant", "content": respuesta_texto})
        st.rerun()



    
# ── 4. Renderizar Componentes de UI ──

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

with st.sidebar:
    nivel, k_chunks, is_admin, lanzar_evaluacion, vs = render_sidebar(vs, disabled=st.session_state.is_generating)

# Activar dialog de autoevaluación si se pulsó el botón
if lanzar_evaluacion:
    mostrar_evaluacion(nivel)

# ── Enrutamiento principal: Admin vs Chat ────────────────────────────────────
if is_admin:
    _render_admin_dashboard()

else:
    # ── Interfaz de Chat para usuarios ───────────────────────────────────────
    clase_vacio = "chat-vacio" if len(st.session_state.mensajes) == 0 else "chat-con-mensajes"
    st.markdown(f"<h2 class='main-title {clase_vacio}'>Consultor IA Neuroanatomía</h2>", unsafe_allow_html=True)

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
                    <div style="font-size: 3rem; margin-bottom: 16px;">🧠</div>
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
                        label="📥 Descargar Reporte",
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
                                f"<span style='font-weight:600;font-size:0.88rem;color:#1e293b;'>📖 [{i}] {nombre_revista}</span>"
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
                            label="📥 Descargar Reporte",
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


