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

# Panel de administración (no disponible en modo web ligero — usa la consola del API)
if is_admin:
    st.info("ℹ️ El panel de administración (carga de PDFs / reconstrucción de VectorDB) se gestiona directamente desde la consola del API en Render.")

# --- 5. Interfaz tipo Chat (Gemini / ChatGPT) ---
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


