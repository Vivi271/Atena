"""
app.py — Punto de entrada limpio del Consultor de Neuroanatomía RAG
"""
import streamlit as st
import os
import time

# ── 1. Configuración de página (DEBE ser la primera instrucción de Streamlit) ──
st.set_page_config(
    page_title="Consultor Neuroanatomía",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 2. Cargar y aplicar estilos CSS desde style.css ──
CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
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

import urllib.request as _urllib_request
import os as _os

_ollama_host = _os.environ.get("OLLAMA_HOST", "http://localhost:11434")
if not _ollama_host.startswith("http"):
    _ollama_host = f"http://{_ollama_host}"

try:
    _urllib_request.urlopen(f"{_ollama_host}/api/tags", timeout=3)
except Exception:
    st.error("Ollama no está corriendo. Inicia Ollama en tu PC y recarga la página.")
    st.info(f"Asegúrate de que Ollama esté activo en: {_ollama_host}\n\nEn macOS abre la aplicación Ollama o ejecuta `ollama serve` en la terminal.")
    st.stop()

try:
    from rag_pipeline import build_vector_store, consultar, stream_consultar
    from database import registrar_consulta, registrar_evaluacion, obtener_preguntas_por_nivel
except ImportError as e:
    st.error(f"Error al importar módulos del sistema: {e}")
    st.stop()

# Carga del vector store (cacheado globalmente)
@st.cache_resource
def get_vector_store():
    try:
        return build_vector_store(force_rebuild=False)
    except Exception as e:
        err = str(e).lower()
        if "default_tenant" in err and "does not exist" in err:
            import shutil as _sh
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_neuro_db")
            if os.path.exists(db_path):
                _sh.rmtree(db_path)
        return None

vs = get_vector_store()

# Auto-detección de base vacía al arrancar
try:
    _count = vs._collection.count() if vs is not None else 0
except Exception:
    _count = 0

if _count == 0:
    st.warning("Base de datos de conocimiento vacía.")
    st.info("Inicia sesión como administrador en la barra lateral y haz clic en 'Reconstruir VectorDB' para indexar tus archivos PDFs.")
    # Permitir que renderice de todos modos para que el admin pueda ingresar el PIN
    
# Cargar Componentes de Interfaz
from components.sidebar import render_sidebar
from components.admin_panel import render_admin_panel
from config import EJEMPLOS_CONSULTA, SALUDOS, NO_INFO_PHRASES, nombre_legible
import html as html_module

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

# ── 4. Renderizar Componentes de UI ──
# Título minimalista en lugar de un gran header

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

clase_vacio = "chat-vacio" if len(st.session_state.mensajes) == 0 else "chat-con-mensajes"
st.markdown(f"<h2 class='main-title {clase_vacio}'>Consultor IA Neuroanatomía</h2>", unsafe_allow_html=True)

with st.sidebar:
    nivel, k_chunks, is_admin, lanzar_evaluacion, vs = render_sidebar(vs, disabled=st.session_state.is_generating)

# Activar dialog de autoevaluación si se pulsó el botón
if lanzar_evaluacion:
    mostrar_evaluacion(nivel)

# Panel de administración (pestañas RAGAS y preguntas)
if is_admin:
    render_admin_panel()

# --- 5. Interfaz tipo Chat (Gemini / ChatGPT) ---
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Capturar input del usuario ANTES de renderizar
pregunta_usuario = st.chat_input("Escribe tu consulta sobre neuroanatomía...", key="chat_query", disabled=st.session_state.is_generating)

# Revisar si se hizo clic en un ejemplo
if st.session_state.get("pregunta_ejemplo"):
    pregunta_usuario = st.session_state.pregunta_ejemplo
    st.session_state.pregunta_ejemplo = None

# Contenedor principal del chat — todo dentro de un solo container
chat_container = st.container()

with chat_container:
    # Si el chat está vacío y no hay consultas en curso, mostrar los ejemplos en el centro
    if len(st.session_state.mensajes) == 0 and not pregunta_usuario and not st.session_state.get("pregunta_activa"):
        st.markdown("<h3 style='text-align:center; color:#64748b; font-weight:400; font-size: 1.2rem; margin-bottom: 2rem;'>¿En qué te puedo ayudar hoy?</h3>", unsafe_allow_html=True)
        
        st.markdown("<h4 style='text-align:center; color:#8CC63F; font-size: 0.9rem; font-weight: 600; margin-bottom: 1.5rem; letter-spacing: 0.8px;'>PREGUNTAS SUGERIDAS DE EJEMPLO</h4>", unsafe_allow_html=True)
        
        cols = st.columns(min(3, len(EJEMPLOS_CONSULTA)))
        for i, (ej, tooltip) in enumerate(EJEMPLOS_CONSULTA):
            with cols[i % 3]:
                if st.button(ej, help=tooltip, use_container_width=True, key=f"ej_{i}"):
                    st.session_state.pregunta_ejemplo = ej
                    st.rerun()

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
                    file_name="consulta_neuroanatomia.txt",
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
                    token_gen, docs, ctx_tokens = stream_consultar(pregunta_a_procesar, vs, k=k_chunks, nivel=nivel)
                    
                    # Envolver generador para quitar los puntos al primer token
                    def _stream_with_clear():
                        first = True
                        for token in token_gen:
                            if first:
                                thinking_placeholder.empty()
                                first = False
                            yield token
                    
                    # Streaming token por token (como ChatGPT/Gemini)
                    respuesta_texto = st.write_stream(_stream_with_clear())
                    latencia = time.time() - t_start
                    
                    es_respuesta_sin_info = any(p in respuesta_texto.lower() for p in NO_INFO_PHRASES)
                    es_saludo = any(s in pregunta_a_procesar.strip().lower() for s in SALUDOS)
                    
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
                    
                    mostrar_evidencia = len(docs) > 0 and not es_saludo
                    if mostrar_evidencia:
                        evidencias_lista = []
                        for i, doc in enumerate(docs, 1):
                            file_name = os.path.basename(doc.metadata.get("source", "desconocido"))
                            nombre_revista = nombre_legible(file_name)
                            pagina = doc.metadata.get("page", "?")
                            
                            evidencias_lista.append(f"**Fragmento {i} — {nombre_revista} (Pág. {pagina})**\n<div style='background: #f8fafc; border: 1px solid rgba(74, 35, 90, 0.1); padding: 12px; border-radius: 8px; font-size: 0.9rem; color: #334155; margin-bottom: 12px; line-height: 1.5; white-space: pre-wrap;'>{html_module.escape(doc.page_content)}</div>")
                            
                        evidencia_html = "\n\n".join(evidencias_lista)
                        
                        with st.expander("Ver Evidencia Documental (Citas y Referencias)"):
                            st.markdown(evidencia_html, unsafe_allow_html=True)
                            
                        # Generar archivo descargable
                        fuentes_txt = "\n".join([f"  [{i+1}] {nombre_legible(os.path.basename(d.metadata.get('source','?')))} — Pág. {d.metadata.get('page','?')}" for i, d in enumerate(docs)])
                        
                        reporte_txt = f"=========================================\nCONSULTA NEUROANATÓMICA — REPORTE RAG\n=========================================\n\nPREGUNTA:\n{pregunta_a_procesar}\n\nRESPUESTA:\n{respuesta_texto}\n\nFUENTES BASADAS EN LITERATURA:\n{fuentes_txt}\n\n========================================="
                        
                        st.download_button(
                            label="📥 Descargar Reporte PDF/TXT",
                            data=reporte_txt,
                            file_name="consulta_neuroanatomia.txt",
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
                    st.session_state.pregunta_ejemplo = None
                    st.session_state.is_generating = False
                    # Forzar re-render limpio para eliminar fantasmas
                    st.rerun()
            except Exception as e:
                st.session_state.pregunta_activa = None
                st.session_state.pregunta_ejemplo = None
                st.session_state.is_generating = False
                st.error(f"Error al generar respuesta: {str(e)}")


