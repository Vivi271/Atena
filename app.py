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

# ── Función: Panel Admin Dashboard (vista completa, ancho total) ──────────────
def _render_admin_dashboard():
    """
    Panel de administración profesional que ocupa el área principal.
    Se muestra cuando el admin está logueado en lugar del chat.
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

    # ── Header del admin ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px; padding: 24px 32px; margin-bottom: 24px;
        border: 1px solid rgba(139,198,63,0.3);
        box-shadow: 0 4px 24px rgba(0,0,0,0.15);
        display: flex; align-items: center; gap: 16px;
    ">
        <div style="font-size: 2.5rem;">🛡️</div>
        <div>
            <h1 style="margin:0; color:#f8fafc; font-size:1.6rem; font-weight:700;">
                Panel de Administración — Atena
            </h1>
            <p style="margin:4px 0 0; color:#94a3b8; font-size:0.9rem;">
                Gestión de documentos, banco de preguntas y configuración del sistema
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs principales ──────────────────────────────────────────────────────
    tab_docs, tab_preguntas, tab_chat, tab_motor = st.tabs([
        "📚 Documentos",
        "📋 Banco de Preguntas",
        "💬 Consultor IA",
        "⚙️ Sistema",
    ])

    # ── TAB 1: DOCUMENTOS ─────────────────────────────────────────────────────
    with tab_docs:
        st.markdown("### 📚 Gestión de Documentos")
        st.caption("Sube PDFs al servidor para indexarlos en la base vectorial del sistema RAG.")

        col_upload, col_list = st.columns([1, 1], gap="large")

        with col_upload:
            st.markdown("#### ⬆️ Subir nuevo documento")
            archivos = st.file_uploader(
                "Selecciona PDF o DOCX:",
                type=["pdf", "docx"],
                accept_multiple_files=True,
                key="admin_uploader_main"
            )
            if archivos:
                ya_subidos = st.session_state.get("_admin_uploads_ok", set())
                nuevos = [f for f in archivos if f.name not in ya_subidos]
                if nuevos:
                    if st.button(f"⬆️ Subir {len(nuevos)} archivo(s) e indexar", key="btn_upload_docs", use_container_width=True, type="primary"):
                        for archivo in nuevos:
                            with st.spinner(f"Procesando '{archivo.name}'..."):
                                try:
                                    resp = httpx.post(
                                        f"{ATENA_API_URL}/api/admin/upload",
                                        headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                                        files={"file": (archivo.name, archivo.getvalue(), "application/octet-stream")},
                                        timeout=180.0,
                                    )
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        st.success(f"✅ '{archivo.name}' — {data.get('fragmentos_indexados','?')} fragmentos indexados")
                                        ya_subidos.add(archivo.name)
                                        st.session_state.pop("_docs_lista_cache", None)
                                    else:
                                        st.error(f"Error {resp.status_code}: {resp.text[:150]}")
                                except Exception as e:
                                    st.error(f"❌ Error de conexión: {e}")
                        st.session_state["_admin_uploads_ok"] = ya_subidos

        with col_list:
            st.markdown("#### 📄 Documentos en el servidor")
            col_r, col_rebuild = st.columns([1,1])
            with col_r:
                if st.button("🔄 Actualizar lista", key="refresh_docs_main"):
                    st.session_state.pop("_docs_lista_cache", None)
            with col_rebuild:
                if st.button("♻️ Reindexar todo", key="rebuild_main", type="secondary"):
                    with st.spinner("Reconstruyendo vectores..."):
                        try:
                            resp = httpx.post(
                                f"{ATENA_API_URL}/api/admin/rebuild",
                                headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                                timeout=120.0,
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                st.success(f"✅ {data.get('total_vectores','?')} vectores reconstruidos")
                            else:
                                st.error(f"Error: {resp.text[:150]}")
                        except Exception as e:
                            st.error(f"❌ {e}")

            # Cargar lista
            if "_docs_lista_cache" not in st.session_state:
                try:
                    resp = httpx.get(
                        f"{ATENA_API_URL}/api/admin/documents",
                        headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                        timeout=15.0,
                    )
                    if resp.status_code == 200:
                        st.session_state["_docs_lista_cache"] = resp.json().get("documentos", [])
                    else:
                        st.session_state["_docs_lista_cache"] = []
                except Exception:
                    st.session_state["_docs_lista_cache"] = []

            docs = st.session_state.get("_docs_lista_cache", [])
            if docs:
                for doc in docs:
                    nombre = doc["nombre"]
                    nombre_display = nombre_legible(nombre)
                    col_n, col_d = st.columns([6, 1])
                    with col_n:
                        st.markdown(
                            f"<div style='padding:8px 12px; background:rgba(255,255,255,0.05); "
                            f"border-radius:8px; border:1px solid rgba(255,255,255,0.1); "
                            f"font-size:0.87rem; color:#e2e8f0; margin-bottom:6px;'>"
                            f"📄 {nombre_display}</div>",
                            unsafe_allow_html=True
                        )
                    with col_d:
                        if st.button("🗑️", key=f"del_main_{nombre}", help=f"Eliminar {nombre}"):
                            st.session_state["_pending_del_doc"] = nombre
                # Confirmación eliminación
                if st.session_state.get("_pending_del_doc"):
                    pending = st.session_state["_pending_del_doc"]
                    st.warning(f"⚠️ ¿Eliminar **{nombre_legible(pending)}** del servidor y de la base vectorial?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Sí, eliminar", key="confirm_del_doc", use_container_width=True, type="primary"):
                            with st.spinner("Eliminando..."):
                                try:
                                    resp = httpx.delete(
                                        f"{ATENA_API_URL}/api/admin/delete/{pending}",
                                        headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                                        timeout=30.0,
                                    )
                                    if resp.status_code == 200:
                                        st.success(f"✅ '{pending}' eliminado.")
                                        st.session_state.pop("_docs_lista_cache", None)
                                    else:
                                        st.error(f"Error: {resp.text[:150]}")
                                except Exception as e:
                                    st.error(f"❌ {e}")
                            st.session_state.pop("_pending_del_doc", None)
                            st.rerun()
                    with c2:
                        if st.button("Cancelar", key="cancel_del_doc", use_container_width=True):
                            st.session_state.pop("_pending_del_doc", None)
                            st.rerun()
            else:
                st.info("No se encontraron documentos o no se pudo conectar al servidor.")

    # ── TAB 2: BANCO DE PREGUNTAS ─────────────────────────────────────────────
    with tab_preguntas:
        st.markdown("### 📋 Banco de Preguntas de Evaluación")
        if not _DB_AVAILABLE:
            st.error("❌ No se pudo conectar a la base de datos de preguntas.")
        else:
            try:
                niveles_db = obtener_niveles()
                temas_db = obtener_temas()
            except Exception as e:
                st.error(f"Error al conectar con Supabase: {e}")
                niveles_db, temas_db = [], []

            sub_ver, sub_nueva = st.tabs(["📖 Ver y Editar Preguntas", "➕ Agregar Nueva Pregunta"])

            with sub_ver:
                col_filtro, col_count = st.columns([2, 1])
                with col_filtro:
                    nivel_filtro = st.selectbox("Filtrar por nivel:", ["todos"] + niveles_db, key="crud_nivel")
                try:
                    preguntas = obtener_preguntas_por_nivel(
                        nivel=None if nivel_filtro == "todos" else nivel_filtro,
                        cantidad=50
                    )
                except Exception as e:
                    st.error(f"Error al cargar preguntas: {e}")
                    preguntas = []
                with col_count:
                    st.metric("Preguntas encontradas", len(preguntas))

                if preguntas:
                    for p in preguntas:
                        pid = p["id"]
                        enunciado_corto = p["enunciado"][:70] + "..." if len(p["enunciado"]) > 70 else p["enunciado"]
                        respuestas = p.get("respuestas", [])
                        textos = [r["texto"] for r in respuestas]
                        while len(textos) < 4: textos.append("")
                        idx_correcta = next((i for i, r in enumerate(respuestas) if r.get("es_correcta")), 0)
                        letras = ["A", "B", "C", "D"]

                        with st.expander(f"#{pid} — {enunciado_corto}"):
                            with st.form(f"edit_{pid}"):
                                col_e1, col_e2 = st.columns([3, 1])
                                with col_e1:
                                    nuevo_enunciado = st.text_area("Enunciado:", value=p["enunciado"], key=f"enun_{pid}", height=80)
                                with col_e2:
                                    nuevo_nivel = st.selectbox("Nivel:", niveles_db,
                                        index=niveles_db.index(p["nivel"]) if p["nivel"] in niveles_db else 0,
                                        key=f"niv_{pid}")
                                    nuevo_tema = st.selectbox("Tema:", temas_db,
                                        index=temas_db.index(p["tema"]) if p["tema"] in temas_db else 0,
                                        key=f"tem_{pid}")
                                cols = st.columns(2)
                                nuevas_opciones = []
                                for i, letra in enumerate(letras):
                                    with cols[i % 2]:
                                        nuevas_opciones.append(st.text_input(f"Opción {letra}:", value=textos[i] if i < len(textos) else "", key=f"op{letra}_{pid}"))
                                nueva_correcta = st.radio("Respuesta correcta:", letras, index=idx_correcta, horizontal=True, key=f"cor_{pid}")
                                col_g, col_e = st.columns(2)
                                with col_g:
                                    if st.form_submit_button("💾 Guardar cambios", use_container_width=True, type="primary"):
                                        ok = actualizar_pregunta(pid, nuevo_nivel, nuevo_tema, nuevo_enunciado,
                                                                  nuevas_opciones[0], nuevas_opciones[1],
                                                                  nuevas_opciones[2], nuevas_opciones[3], nueva_correcta)
                                        if ok:
                                            st.success("✅ Actualizada correctamente.")
                                            time.sleep(0.5)
                                            st.rerun()
                                        else:
                                            st.error("Error al actualizar.")
                                with col_e:
                                    if st.form_submit_button("🗑️ Eliminar", use_container_width=True):
                                        st.session_state[f"_confirm_del_{pid}"] = True
                            if st.session_state.get(f"_confirm_del_{pid}"):
                                st.warning("¿Seguro que quieres eliminar esta pregunta?")
                                cc1, cc2 = st.columns(2)
                                with cc1:
                                    if st.button("Sí, eliminar", key=f"yes_{pid}", use_container_width=True, type="primary"):
                                        eliminar_pregunta(pid)
                                        st.session_state.pop(f"_confirm_del_{pid}", None)
                                        st.success("🗑️ Eliminada.")
                                        time.sleep(0.5)
                                        st.rerun()
                                with cc2:
                                    if st.button("Cancelar", key=f"no_{pid}", use_container_width=True):
                                        st.session_state.pop(f"_confirm_del_{pid}", None)
                                        st.rerun()
                else:
                    st.info("No hay preguntas para este nivel.")

            with sub_nueva:
                st.markdown("#### Crear nueva pregunta")
                with st.form("nueva_pregunta_main", clear_on_submit=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        nuevo_enunciado = st.text_area("Enunciado de la pregunta:", height=100)
                    with col_b:
                        nuevo_nivel = st.selectbox("Nivel:", niveles_db, key="nueva_niv_main")
                        nuevo_tema = st.selectbox("Tema:", temas_db, key="nueva_tem_main")
                    st.markdown("**Opciones de respuesta:**")
                    cols2 = st.columns(2)
                    with cols2[0]:
                        op_a = st.text_input("Opción A:")
                        op_c = st.text_input("Opción C:")
                    with cols2[1]:
                        op_b = st.text_input("Opción B:")
                        op_d = st.text_input("Opción D:")
                    correcta_nueva = st.radio("Respuesta correcta:", ["A", "B", "C", "D"], horizontal=True, key="nueva_cor_main")
                    if st.form_submit_button("✅ Crear Pregunta", use_container_width=True, type="primary"):
                        if not nuevo_enunciado.strip():
                            st.error("El enunciado no puede estar vacío.")
                        elif not all([op_a, op_b, op_c, op_d]):
                            st.error("Debes llenar las 4 opciones.")
                        else:
                            ok = agregar_pregunta(nuevo_nivel, nuevo_tema, nuevo_enunciado, op_a, op_b, op_c, op_d, correcta_nueva)
                            if ok:
                                st.success("✅ Pregunta creada exitosamente.")
                            else:
                                st.error("Error al crear. Verifica que el nivel y tema existan en la BD.")

    # ── TAB 3: CONSULTOR IA (chat disponible también para admin) ──────────────
    with tab_chat:
        st.markdown("### 💬 Consultor IA de Neuroanatomía")
        st.caption("Prueba el sistema RAG directamente desde el panel de administración.")
        _render_chat_interface(nivel="Avanzado", k_chunks=6)

    # ── TAB 4: SISTEMA ─────────────────────────────────────────────────────────
    with tab_motor:
        st.markdown("### ⚙️ Estado del Sistema")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown("""
            <div style="background:rgba(255,255,255,0.05); border-radius:12px; padding:16px; border:1px solid rgba(255,255,255,0.1);">
                <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:4px;">SERVICIO API</div>
                <div style="font-size:1rem; color:#22c55e; font-weight:600;">🟢 atena-vugz.onrender.com</div>
            </div>""", unsafe_allow_html=True)
        with col_s2:
            groq_model = os.environ.get("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05); border-radius:12px; padding:16px; border:1px solid rgba(255,255,255,0.1);">
                <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:4px;">MODELO LLM</div>
                <div style="font-size:0.9rem; color:#e2e8f0; font-weight:600;">🧠 {groq_model}</div>
            </div>""", unsafe_allow_html=True)
        with col_s3:
            embed_model = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05); border-radius:12px; padding:16px; border:1px solid rgba(255,255,255,0.1);">
                <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:4px;">EMBEDDINGS</div>
                <div style="font-size:0.9rem; color:#e2e8f0; font-weight:600;">🔢 {embed_model}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Verificar estado del API")
        if st.button("🔍 Ping al API", key="ping_api_btn"):
            try:
                resp = httpx.get(f"{ATENA_API_URL}/salud", timeout=10.0)
                data = resp.json()
                if data.get("estado") == "ok":
                    st.success(f"✅ API activo — Vector Store listo: {data.get('vector_store_listo', '?')}")
                else:
                    st.warning(f"⚠️ {data}")
            except Exception as e:
                st.error(f"❌ No se pudo conectar: {e}")


def _render_chat_interface(nivel="Principiante", k_chunks=5):
    """Renderiza la interfaz de chat (usada tanto por usuarios como por admin desde su tab)."""
    if "mensajes_admin" not in st.session_state:
        st.session_state.mensajes_admin = []

    pregunta = st.chat_input("Escribe tu consulta...", key="admin_chat_input")

    for msg in st.session_state.mensajes_admin:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if pregunta:
        st.session_state.mensajes_admin.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Consultando fuentes..."):
                respuesta_texto, fuentes = consultar_via_api(pregunta, nivel=nivel, k=k_chunks)
            st.markdown(respuesta_texto)
            if fuentes:
                with st.expander("Ver fuentes"):
                    for i, f in enumerate(fuentes, 1):
                        st.markdown(f"**[{i}] {nombre_legible(f.get('fuente',''))}** — Pág. {f.get('pagina','?')}")
                        st.caption(f.get("fragmento", "")[:200])
        st.session_state.mensajes_admin.append({"role": "assistant", "content": respuesta_texto})
        st.rerun()


# ── 4. Renderizar Componentes de UI ──

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

with st.sidebar:
    nivel, k_chunks, is_admin, lanzar_evaluacion, vs = render_sidebar(vs, disabled=st.session_state.is_generating)

# Activar dialog de autoevaluación si se pulsó el botón
if lanzar_evaluacion:
    mostrar_evaluacion(nivel)

# ── Enrutamiento principal: Admin Dashboard vs Chat ──────────────────────────
if is_admin:
    _render_admin_dashboard()
else:

    # --- 5. Interfaz tipo Chat ---
    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    # Capturar input del usuario ANTES de renderizar
    pregunta_usuario = st.chat_input("Escribe tu consulta sobre neuroanatomía...", key="chat_query", disabled=st.session_state.is_generating)

# Contenedor principal del chat — todo dentro de un solo container
chat_container = st.container()

with chat_container:
    # Si el chat está vacío y no hay consultas en curso, mostrar mensaje de bienvenida limpio
    if len(st.session_state.mensajes) == 0 and not pregunta_usuario and not st.session_state.get("pregunta_activa"):
        st.markdown(
            """
            <div style="text-align: center; padding: 48px 24px; max-width: 680px; margin: 20px auto; background: rgba(255, 255, 255, 0.6); border-radius: 16px; border: 1px solid rgba(226, 232, 240, 0.8); box-shadow: 0 4px 20px -2px rgba(0,0,0,0.05);">
                <div style="font-size: 3rem; margin-bottom: 16px;">🧠</div>
                <h2 style="color: #1e293b; font-size: 1.5rem; font-weight: 700; margin-bottom: 10px;">
                    Consultor Académico de Neuroanatomía
                </h2>
                <p style="color: #64748b; font-size: 0.95rem; line-height: 1.6; margin-bottom: 0;">
                    Formula libremente cualquier consulta conceptual, funcional o anatómica. Las respuestas son sintetizadas en tiempo real a partir de la literatura científica indexada en la base de conocimiento.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Mostrar el historial de mensajes del chat
    for msg in st.session_state.mensajes:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Mostrar badge de sin alucinación si aplica
            if msg.get("es_respuesta_sin_info"):
                st.markdown(
                    '<div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); '
                    'color: #10b981; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; margin-top: 8px; '
                    'display: inline-block; font-weight: 500;">'
                    'Respuesta validada: El sistema reconoció el límite de su conocimiento'
                    '</div>',
                    unsafe_allow_html=True
                )

            # Mostrar evidencia si existe
            if msg.get("evidencia_html"):
                with st.expander("Ver Evidencia Documental (Citas y Referencias)"):
                    st.markdown(msg["evidencia_html"], unsafe_allow_html=True)
                    
            # Mostrar botón de descarga si existe reporte
            if msg.get("reporte"):
                st.download_button(
                    label="📥 Descargar Reporte PDF/TXT",
                    data=msg["reporte"],
                    file_name="consulta_atena.txt",
                    mime="text/plain",
                    key=f"dl_{msg['id']}"
                )

    # Guardar en estado y re-ejecutar para desactivar controles en el sidebar antes de procesar
    if pregunta_usuario:
        if not pregunta_usuario.strip():
            st.warning("Por favor, escribe una pregunta válida.")
        else:
            st.session_state.pregunta_activa = pregunta_usuario
            st.session_state.is_generating = True
            st.rerun()

    # Procesar nueva pregunta en la ejecución deshabilitada
    pregunta_a_procesar = st.session_state.get("pregunta_activa")
    if pregunta_a_procesar:
        st.session_state.historial.append(pregunta_a_procesar)
        
        # Guardar y mostrar el mensaje del usuario
        st.session_state.mensajes.append({"role": "user", "content": pregunta_a_procesar, "id": str(time.time())})
        with st.chat_message("user"):
            st.markdown(pregunta_a_procesar)
            
        # Preparar contenedor del asistente con streaming
        with st.chat_message("assistant"):
            try:
                    # Mostrar puntos suspensivos animados mientras piensa
                    thinking_placeholder = st.empty()
                    thinking_placeholder.markdown(
                        """
                        <div style="display:flex; align-items:center; gap:8px; padding:4px 0;">
                            <div style="display:flex; gap:4px;">
                                <span style="background:#8CC63F;width:8px;height:8px;border-radius:50%;display:inline-block;animation:pulse 1.4s infinite ease-in-out both;animation-delay:-0.32s;"></span>
                                <span style="background:#8CC63F;width:8px;height:8px;border-radius:50%;display:inline-block;animation:pulse 1.4s infinite ease-in-out both;animation-delay:-0.16s;"></span>
                                <span style="background:#8CC63F;width:8px;height:8px;border-radius:50%;display:inline-block;animation:pulse 1.4s infinite ease-in-out both;"></span>
                            </div>
                            <span style="color:#64748b; font-size:0.85rem; font-style:italic;">Consultando fuentes...</span>
                        </div>
                        <style>
                        @keyframes pulse {
                            0%, 80%, 100% { transform: scale(0); opacity: 0; }
                            40% { transform: scale(1.0); opacity: 1; }
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    t_start = time.time()
                    # Consultar vía API de FastAPI (modo ligero, sin cargar modelos localmente)
                    respuesta_texto, fuentes = consultar_via_api(
                        pregunta_a_procesar, nivel=nivel, k=k_chunks
                    )
                    thinking_placeholder.empty()
                    st.markdown(respuesta_texto)
                    latencia = time.time() - t_start

                    es_respuesta_sin_info = any(p in respuesta_texto.lower() for p in NO_INFO_PHRASES)
                    es_saludo = es_consulta_saludo(pregunta_a_procesar)

                    registrar_consulta(pregunta_a_procesar, respuesta_texto, nivel.lower(), latencia)

                    if es_respuesta_sin_info:
                        st.markdown(
                            '<div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); '
                            'color: #10b981; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; margin-top: 8px; '
                            'display: inline-block; font-weight: 500;">'
                            'Respuesta validada: El sistema reconoció el límite de su conocimiento'
                            '</div>',
                            unsafe_allow_html=True
                        )

                    evidencia_html = ""
                    reporte_txt = ""

                    mostrar_evidencia = len(fuentes) > 0 and not es_saludo
                    if mostrar_evidencia:
                        evidencias_lista = []
                        fuentes_txt_lista = []
                        for i, fuente in enumerate(fuentes, 1):
                            nombre_revista = nombre_legible(fuente.get("fuente", "desconocido"))
                            pagina = fuente.get("pagina", "?")
                            texto_escapado = html_module.escape(fuente.get("fragmento", ""))
                            texto_limpio = formatear_evidencia_limpia(texto_escapado)

                            evidencias_lista.append(
                                f"<div style='margin-bottom: 14px; background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #8CC63F; border-radius: 8px; padding: 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);'>"
                                f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>"
                                f"<span style='font-weight: 600; font-size: 0.88rem; color: #1e293b;'>📖 [Fuente {i}] {nombre_revista}</span>"
                                f"<span style='background: #f1f5f9; color: #475569; font-size: 0.76rem; padding: 2px 8px; border-radius: 10px; font-weight: 500;'>Pág. {pagina}</span>"
                                f"</div>"
                                f"<div style='font-size: 0.86rem; color: #334155; line-height: 1.6;'>{texto_limpio}</div>"
                                f"</div>"
                            )
                            fuentes_txt_lista.append(f"  [{i}] {nombre_revista} — Pág. {pagina}")

                        evidencia_html = f"<div style='max-height: 380px; overflow-y: auto; padding-right: 8px; margin-top: 6px;'>{''.join(evidencias_lista)}</div>"

                        with st.expander("Ver Evidencia Documental (Citas y Referencias)"):
                            st.markdown(evidencia_html, unsafe_allow_html=True)

                        reporte_txt = (
                            f"=========================================\n"
                            f"CONSULTA NEUROANATÓMICA — REPORTE RAG\n"
                            f"=========================================\n\n"
                            f"PREGUNTA:\n{pregunta_a_procesar}\n\n"
                            f"RESPUESTA:\n{respuesta_texto}\n\n"
                            f"FUENTES BASADAS EN LITERATURA:\n" + "\n".join(fuentes_txt_lista) +
                            "\n\n========================================="
                        )

                        st.download_button(
                            label="📥 Descargar Reporte PDF/TXT",
                            data=reporte_txt,
                            file_name="consulta_atena.txt",
                            mime="text/plain",
                            key=f"dl_new_{time.time()}"
                        )

                    # Guardar en el historial
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
                    # Forzar re-render limpio para eliminar fantasmas
                    st.rerun()
            except Exception as e:
                st.session_state.pregunta_activa = None
                st.session_state.is_generating = False
                st.error(f"Error al generar respuesta: {str(e)}")


