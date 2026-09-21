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

# ── Persistencia de sesión admin entre recargas de página ──
if st.query_params.get("adm_ok") == "1" and not st.session_state.get("is_admin"):
    st.session_state.is_admin = True
    st.session_state.adm_pin_activo = True

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
    /* ── Todos los botones en modo oscuro ────────────────────────────── */
    button,
    .stButton > button,
    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stDownloadButton"] > button,
    div[data-testid="stBaseButton-secondary"] {
        background-color: #21262d !important;
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
    }
    button:hover,
    .stButton > button:hover {
        background-color: #30363d !important;
        border-color: #8CC63F !important;
        color: #8CC63F !important;
    }
    button[kind="primary"],
    .stButton > button[kind="primary"],
    div[data-testid="stBaseButton-primary"] > button,
    div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #4a235a, #6c3483) !important;
        color: #ffffff !important;
        border-color: #6c3483 !important;
    }
    /* ── Inputs, textareas, selects ───────────────────────────────────── */
    input, textarea,
    .stTextInput input, .stTextArea textarea,
    .stNumberInput input,
    div[data-baseweb="select"] *, div[data-baseweb="input"] * {
        background-color: #161b22 !important;
        color: #e6edf3 !important;
        border-color: #30363d !important;
    }
    /* ── Cards, containers ────────────────────────────────────────────── */
    div[data-testid="stMarkdown"] div[style*="background"] {
        filter: brightness(0.85);
    }
    div[data-testid="stExpander"] > details {
        background-color: #161b22 !important;
        border-color: #30363d !important;
    }
    div[data-testid="stExpander"] summary {
        color: #e6edf3 !important;
    }
    /* ── Radio, checkboxes ────────────────────────────────────────────── */
    div[data-testid="stRadio"] label,
    div[data-testid="stCheckbox"] label {
        color: #e6edf3 !important;
    }
    /* ── Dataframe ────────────────────────────────────────────────────── */
    div[data-testid="stDataFrame"] * {
        background-color: #161b22 !important;
        color: #e6edf3 !important;
        border-color: #30363d !important;
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
  <div class="loader-logo" translate="no"><span class="notranslate">Atena</span></div>
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
    Llama al endpoint /consultar o /api/consultar del API de FastAPI.
    Retorna (respuesta_texto, lista_fuentes) donde lista_fuentes es una lista de dicts
    con claves: fuente, pagina, fragmento.
    """
    endpoints = [
        f"{ATENA_API_URL}/consultar",
        f"{ATENA_API_URL}/api/consultar",
    ]
    for url in endpoints:
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    url,
                    json={
                        "pregunta": pregunta,
                        "nivel": nivel,
                        "k": k,
                        "formato_unity": False,
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("respuesta", ""), data.get("fuentes", [])
                elif response.status_code != 404:
                    return f"Error del servidor ({response.status_code}): {response.text[:120]}", []
        except httpx.TimeoutException:
            return "El servidor tardó demasiado en responder. Por favor, intenta de nuevo.", []
        except Exception:
            continue
    return "Error al contactar el sistema RAG. Por favor, intenta de nuevo en unos momentos.", []

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




# ── Chat Flotante Tipo Tidio (inyeccion DOM via components.html) ──────────────
def _inject_floating_chat():
    """Widget de chat flotante esquina inferior derecha."""
    import streamlit.components.v1 as components
    api_url = ATENA_API_URL
    html = f"""
    <script>
    (function() {{
        var A = '{api_url}';
        var W = window.parent, D = W.document;
        var st = W._atenaChatSt || {{}};
        var msgs = st.msgs || [], open = st.open || false, szIdx = st.szIdx || 0;
        var SZ = [
            {{w:'360px',h:'500px',lbl:'Ampliar'}},
            {{w:'540px',h:'660px',lbl:'Grande'}},
            {{w:'720px',h:'82vh', lbl:'Compacto'}}
        ];
        ['atena-cw','atena-cw-st'].forEach(function(id){{
            var e=D.getElementById(id); if(e) e.remove();
        }});
        var s=D.createElement('style'); s.id='atena-cw-st';
        s.textContent=[
            '#atena-cw{{position:fixed;bottom:20px;right:20px;z-index:2147483647;font-family:Inter,-apple-system,sans-serif;}}',
            '#a-fab{{width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#4a235a,#6c3483);border:none;cursor:pointer;box-shadow:0 4px 20px rgba(74,35,90,.5);display:flex;align-items:center;justify-content:center;color:#fff;font-size:22px;transition:transform .2s,box-shadow .2s;outline:none;}}',
            '#a-fab:hover{{transform:scale(1.1);box-shadow:0 6px 28px rgba(74,35,90,.65);}}',
            '#a-pan{{background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.22);border:1px solid #e2e8f0;display:flex;flex-direction:column;overflow:hidden;resize:both;min-width:300px;min-height:400px;max-width:calc(100vw - 40px);max-height:calc(100vh - 40px);}}',
            '#a-hdr{{background:linear-gradient(135deg,#4a235a,#6c3483);padding:12px 14px;display:flex;align-items:center;gap:10px;flex-shrink:0;}}',
            '.a-av{{width:36px;height:36px;border-radius:50%;background:#8CC63F;display:flex;align-items:center;justify-content:center;font-weight:800;color:#4a235a;font-size:1rem;flex-shrink:0;}}',
            '.a-tt{{color:#fff;font-weight:700;font-size:.93rem;margin:0;}}',
            '.a-sub{{color:rgba(255,255,255,.6);font-size:.7rem;margin:2px 0 0;}}',
            '.a-act{{margin-left:auto;display:flex;gap:6px;align-items:center;}}',
            '.a-hb{{background:rgba(255,255,255,.18);border:none;color:#fff;border-radius:6px;padding:5px 10px;cursor:pointer;font-size:.75rem;font-weight:600;transition:background .15s;outline:none;white-space:nowrap;}}',
            '.a-hb:hover{{background:rgba(255,255,255,.32);}}',
            '.a-cl{{background:rgba(255,255,255,.18);border:none;color:#fff;border-radius:6px;width:28px;height:28px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:1rem;transition:background .15s;outline:none;}}',
            '.a-cl:hover{{background:rgba(220,50,50,.5);}}',
            '#a-msgs{{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;background:#f8fafc;scroll-behavior:smooth;}}',
            '#a-msgs::-webkit-scrollbar{{width:4px;}}',
            '#a-msgs::-webkit-scrollbar-thumb{{background:#cbd5e1;border-radius:4px;}}',
            '.m-u{{background:linear-gradient(135deg,#4a235a,#6c3483);color:#fff;align-self:flex-end;padding:10px 14px;border-radius:14px 14px 4px 14px;max-width:82%;font-size:.86rem;line-height:1.5;word-break:break-word;}}',
            '.m-b{{background:#fff;color:#1e293b;align-self:flex-start;padding:10px 14px;border-radius:14px 14px 14px 4px;max-width:86%;font-size:.86rem;line-height:1.5;border:1px solid #e2e8f0;word-break:break-word;}}',
            '.m-b.tk{{color:#94a3b8;border-style:dashed;animation:aBl 1s infinite;}}',
            '@keyframes aBl{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}',
            '.m-w{{text-align:center;color:#94a3b8;font-size:.83rem;padding:24px 10px;line-height:1.6;}}',
            '#a-irow{{padding:10px 12px;border-top:1px solid #e2e8f0;display:flex;gap:8px;align-items:flex-end;background:#fff;flex-shrink:0;}}',
            '#a-inp{{flex:1;border:1.5px solid #e2e8f0;border-radius:10px;padding:9px 12px;font-size:.87rem;outline:none;font-family:inherit;background:#f8fafc;resize:none;min-height:38px;max-height:100px;line-height:1.4;transition:border-color .15s;}}',
            '#a-inp:focus{{border-color:#8CC63F;background:#fff;box-shadow:0 0 0 3px rgba(140,198,63,.15);}}',
            '#a-snd{{background:linear-gradient(135deg,#4a235a,#6c3483);color:#fff;border:none;border-radius:10px;width:40px;height:40px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:1.1rem;transition:opacity .15s;outline:none;}}',
            '#a-snd:hover{{opacity:.85;}}',
            '#a-snd:disabled{{opacity:.4;cursor:not-allowed;}}',
            '#a-ft{{text-align:center;font-size:.63rem;color:#cbd5e1;padding:4px;border-top:1px solid #f1f5f9;flex-shrink:0;background:#fff;}}'
        ].join('');
        D.head.appendChild(s);
        var root=D.createElement('div'); root.id='atena-cw';
        var fab=D.createElement('button'); fab.id='a-fab'; fab.title='Consultor IA';
        fab.innerHTML='&#x1F4AC;'; fab.style.display=open?'none':'flex';
        fab.onclick=function(){{W._atenaCW.open();}};
        root.appendChild(fab);
        var sz=SZ[szIdx];
        var pan=D.createElement('div'); pan.id='a-pan';
        pan.style.cssText='width:'+sz.w+';height:'+sz.h+';display:'+(open?'flex':'none');
        var mH=msgs.length===0
            ? '<div class="m-w">Hola, soy Atena.<br>Escribe tu consulta.</div>'
            : msgs.map(function(m){{var e=m.c.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');return '<div class="m-'+(m.r==='u'?'u':'b')+'">'+e+'</div>';}}).join('');
        pan.innerHTML='<div id="a-hdr"><div class="a-av">A</div><div><p class="a-tt" translate="no">Atena IA</p><p class="a-sub">Consultor de Neuroanatomia</p></div><div class="a-act"><button class="a-hb" id="a-sz">'+sz.lbl+'</button><button class="a-cl" id="a-cl-btn">&#x2715;</button></div></div><div id="a-msgs">'+mH+'</div><div id="a-irow"><textarea id="a-inp" placeholder="Escribe tu consulta..." rows="1"></textarea><button id="a-snd">&#x27A4;</button></div><div id="a-ft">Atena RAG &middot; Konrad Lorenz</div>';
        root.appendChild(pan); D.body.appendChild(root);
        var m=D.getElementById('a-msgs'); if(m) m.scrollTop=m.scrollHeight;
        // Bind header buttons via addEventListener (more reliable than inline onclick)
        var _szBtn=D.getElementById('a-sz'), _clBtn=D.getElementById('a-cl-btn');
        if(_szBtn) _szBtn.addEventListener('click',function(){{W._atenaCW.sz();}});
        if(_clBtn) _clBtn.addEventListener('click',function(){{W._atenaCW.close();}});
        var inp=D.getElementById('a-inp'), sb=D.getElementById('a-snd');
        if(inp){{
            inp.addEventListener('keydown',function(e){{if(e.key==='Enter'&&!e.shiftKey){{e.preventDefault();W._atenaCW.send();}}}});
            inp.addEventListener('input',function(){{this.style.height='auto';this.style.height=Math.min(this.scrollHeight,100)+'px';}});
        }}
        if(sb) sb.addEventListener('click',function(){{W._atenaCW.send();}});
        W._atenaChatSt={{msgs:msgs,open:open,szIdx:szIdx}};
        W._atenaCW={{
            open:function(){{
                open=true;W._atenaChatSt.open=true;
                var f=D.getElementById('a-fab');if(f)f.style.display='none';
                var p=D.getElementById('a-pan');if(p)p.style.display='flex';
                var i=D.getElementById('a-inp');setTimeout(function(){{if(i)i.focus();}},80);
                var ms=D.getElementById('a-msgs');if(ms)ms.scrollTop=ms.scrollHeight;
            }},
            close:function(){{
                open=false;W._atenaChatSt.open=false;
                var f=D.getElementById('a-fab');if(f)f.style.display='flex';
                var p=D.getElementById('a-pan');if(p)p.style.display='none';
            }},
            sz:function(){{
                szIdx=(szIdx+1)%3;W._atenaChatSt.szIdx=szIdx;
                var ns=SZ[szIdx];
                var p=D.getElementById('a-pan');if(p){{p.style.width=ns.w;p.style.height=ns.h;}}
                var b=D.getElementById('a-sz');if(b)b.textContent=ns.lbl;
            }},
            send:async function(){{
                var i2=D.getElementById('a-inp'),b2=D.getElementById('a-snd');
                if(!i2)return;
                var txt=i2.value.trim();if(!txt)return;
                i2.value='';i2.style.height='auto';
                if(b2)b2.disabled=true;i2.disabled=true;
                msgs.push({{r:'u',c:txt}});W._atenaChatSt.msgs=msgs;
                var mEl=D.getElementById('a-msgs');
                if(mEl){{
                    var we=mEl.querySelector('.m-w');if(we)we.remove();
                    var ud=D.createElement('div');ud.className='m-u';ud.textContent=txt;mEl.appendChild(ud);
                    var td=D.createElement('div');td.className='m-b tk';td.id='a-tk';td.textContent='Consultando fuentes...';mEl.appendChild(td);
                    mEl.scrollTop=mEl.scrollHeight;
                }}
                var bt='Error al contactar el servidor.';
                try{{
                    var urls=[A+'/api/consultar',A+'/consultar'],res=null;
                    for(var i=0;i<urls.length;i++){{
                        try{{res=await fetch(urls[i],{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{pregunta:txt,nivel:'Avanzado',k:5,formato_unity:false}})}});
                        if(res&&res.ok)break;}}catch(ex){{res=null;}}
                    }}
                    if(res&&res.ok){{var d=await res.json();bt=d.respuesta||'Sin respuesta.';}}
                }}catch(err){{bt='Error: '+(err.message||'');}}
                msgs.push({{r:'b',c:bt}});W._atenaChatSt.msgs=msgs;
                var tk=D.getElementById('a-tk');if(tk){{tk.className='m-b';tk.id='';tk.textContent=bt;}}
                if(b2)b2.disabled=false;i2.disabled=false;
                setTimeout(function(){{if(i2)i2.focus();}},50);
                var mEl2=D.getElementById('a-msgs');if(mEl2)mEl2.scrollTop=mEl2.scrollHeight;
            }}
        }};
    }})();
    </script>
    """
    components.html(html, height=0)

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
            <span translate="no" class="notranslate" style="font-family:'Outfit',sans-serif; font-size:1.35rem; font-weight:700; color:var(--text-main, #1e293b); letter-spacing:-0.5px;">Atena</span>
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

    # Barra de navegación limpia con las 4 secciones principales
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

    st.markdown(
        "<style>section[data-testid='stMain'] > div:first-child > div:first-child "
        "{animation:atenaSFade .2s ease;}"
        "@keyframes atenaSFade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}"
        "</style>", unsafe_allow_html=True
    )
    st.markdown("<hr style='margin:10px 0 18px; opacity:0.15;'>", unsafe_allow_html=True)
    # ─── Arreglo bleeding: mostrar placeholder mientras carga sección nueva ─────
    _prev_sec = st.session_state.get("_adm_last_sec")
    seccion = st.session_state.adm_seccion
    if _prev_sec != seccion:
        st.session_state["_adm_last_sec"] = seccion


    # ── DOCUMENTOS ──────────────────────────────────────────────────────────
    # ── Contenedor atómico: evita módulo anterior visible durante carga ─────
    _section_slot = st.empty()
    with _section_slot.container():
        if seccion == "documentos":
            st.markdown("### Documentos del sistema")
            st.caption("Biblioteca de literatura indexada. Sube PDF o DOCX para ampliar el conocimiento de Atena.")

            ab1, ab2, _sp = st.columns([1.2, 1.2, 7])
            with ab1:
                if st.button("Actualizar", key="adm_refresh_docs", use_container_width=True):
                    st.session_state.pop("adm_docs_cache", None)
                    st.rerun()
            with ab2:
                if st.button("Reindexar todo", key="adm_rebuild", use_container_width=True):
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

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

            if "adm_docs_cache" not in st.session_state:
                try:
                    resp = httpx.get(f"{ATENA_API_URL}/api/admin/documents",
                                     headers={"X-Admin-Pin": ADMIN_PIN_ENV}, timeout=15.0)
                    st.session_state["adm_docs_cache"] = resp.json().get("documentos", []) if resp.status_code == 200 else []
                except Exception:
                    st.session_state["adm_docs_cache"] = []

            docs = st.session_state.get("adm_docs_cache", [])
            if docs:
                st.markdown(
                    f"<p style='font-size:0.8rem;color:#94a3b8;margin-bottom:10px;'>"
                    f"{len(docs)} documento{'s' if len(docs)>1 else ''} indexado{'s' if len(docs)>1 else ''}</p>",
                    unsafe_allow_html=True
                )
                for doc in docs:
                    nombre = doc["nombre"]
                    ext = os.path.splitext(nombre)[1].upper().replace(".", "") or "DOC"
                    c_card, c_del = st.columns([8, 1])
                    with c_card:
                        st.markdown(
                            f"<div style='display:flex;align-items:center;gap:14px;padding:13px 18px;"
                            f"background:#fff;border:1px solid #e2e8f0;border-left:4px solid #8CC63F;"
                            f"border-radius:8px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.04);'>"
                            f"<span style='font-size:0.7rem;font-weight:700;background:rgba(74,35,90,.08);"
                            f"color:#4a235a;padding:4px 8px;border-radius:4px;flex-shrink:0;'>{ext}</span>"
                            f"<div style='flex:1;overflow:hidden;'>"
                            f"<div style='font-weight:600;font-size:0.92rem;color:#1e293b;"
                            f"text-overflow:ellipsis;overflow:hidden;white-space:nowrap;'>{nombre_legible(nombre)}</div>"
                            f"<div style='font-size:0.74rem;color:#94a3b8;margin-top:2px;'>Indexado en base vectorial RAG</div>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
                    with c_del:
                        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
                        if st.button("Eliminar", key=f"adm_del_{nombre}", use_container_width=True):
                            st.session_state["adm_pending_del"] = nombre

                if st.session_state.get("adm_pending_del"):
                    pending = st.session_state["adm_pending_del"]
                    st.warning(f"Confirmar: eliminar '{nombre_legible(pending)}' del servidor.")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("Si, eliminar", key="adm_confirm_del", use_container_width=True, type="primary"):
                            with st.spinner("Eliminando..."):
                                try:
                                    resp = httpx.delete(f"{ATENA_API_URL}/api/admin/delete/{pending}",
                                                        headers={"X-Admin-Pin": ADMIN_PIN_ENV}, timeout=30.0)
                                    if resp.status_code == 200:
                                        st.success("Documento eliminado.")
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
                st.info("No hay documentos registrados o no se pudo conectar al servidor.")

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            with st.expander("Subir nuevo material", expanded=False):
                st.caption("Arrastra archivos PDF o DOCX. El sistema los fragmenta y vectoriza automaticamente.")
                archivos = st.file_uploader(
                    "Selecciona archivos:", type=["pdf", "docx"],
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
                                            st.success(f"{archivo.name} indexado - {data.get('fragmentos_indexados','?')} fragmentos")
                                            ya_subidos.add(archivo.name)
                                            st.session_state.pop("adm_docs_cache", None)
                                        else:
                                            st.error(f"Error: {resp.text[:120]}")
                                    except Exception as e:
                                        st.error(f"Sin conexion: {e}")
                            st.session_state["adm_uploads_ok"] = ya_subidos
                            st.rerun()


        # ── BANCO DE PREGUNTAS ───────────────────────────────────────────────────
        elif seccion == "preguntas":
            st.markdown("### Banco de Preguntas")
            # Fix visual "do" en radio horizontal (Streamlit label truncation)
            st.markdown("""<style>
            div[data-testid="stRadio"] > div { gap: 20px !important; }
            div[data-testid="stRadio"] label > div { white-space: nowrap !important; }
            </style>""", unsafe_allow_html=True)

            if not _DB_AVAILABLE:
                st.error("No se pudo conectar a la base de datos.")
                return

            try:
                niveles_db = obtener_niveles()
                temas_db = obtener_temas()
            except Exception as e:
                st.error(f"Error Supabase: {e}")
                return

            _modo_forzar = st.session_state.pop("adm_modo_q_forzar", None)
            if _modo_forzar:
                st.session_state["adm_modo_q"] = _modo_forzar
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
                            if ok:
                                st.session_state["adm_pregunta_creada"] = True
                                st.rerun()
                            else:
                                st.error("Error al crear la pregunta.")

            # Flujo post-creación
            if st.session_state.get("adm_pregunta_creada"):
                st.session_state.pop("adm_pregunta_creada", None)
                st.markdown(
                    "<div style='background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1px solid #86efac;"
                    "border-left:4px solid #22c55e;border-radius:10px;padding:20px 24px;margin:12px 0;'>"
                    "<div style='font-weight:700;font-size:1rem;color:#166534;margin-bottom:6px;'>Pregunta creada</div>"
                    "<div style='font-size:0.85rem;color:#16a34a;'>¿Desea agregar otra pregunta?</div>"
                    "</div>", unsafe_allow_html=True
                )
                _ca, _cb = st.columns(2)
                with _ca:
                    if st.button("Si, agregar otra", key="adm_otra_si", use_container_width=True, type="primary"):
                        pass  # permanece en modo Nueva pregunta
                with _cb:
                    if st.button("No, ver lista", key="adm_otra_no", use_container_width=True):
                        st.session_state["adm_modo_q_forzar"] = "Ver y editar"
                        st.rerun()

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
                    _top_n = st.session_state.get("adm_top_n", 20)
                    recientes    = obtener_consultas_recientes(_top_n)
                except Exception as e:
                    st.error(f"Error al cargar estadisticas: {e}")
                    st.stop()

                # ── KPIs ────────────────────────────────────────────────────────
                k1, k2, k3, k4, k5 = st.columns(5)
                _kpis = [
                    ("Consultas totales", str(stats["total_consultas"]), "#4a235a"),
                    ("Latencia prom.", f"{stats['latencia_promedio']} s" if stats["latencia_promedio"] else "—", "#1e3a5f"),
                    ("Evaluaciones", str(stats["total_evaluaciones"]), "#14532d"),
                    ("Precision global", f"{stats['porcentaje_aciertos']} %" if stats["total_evaluaciones"] else "—", "#7c2d12"),
                    ("Resp. correctas", str(stats.get("evaluaciones_correctas", 0)), "#1e3a5f"),
                ]
                for _c, (_l, _v, _bg) in zip([k1,k2,k3,k4,k5], _kpis):
                    with _c:
                        st.markdown(
                            f"<div style='background:linear-gradient(135deg,{_bg}18,{_bg}05);"
                            f"border:1px solid {_bg}22;border-top:3px solid {_bg};"
                            f"border-radius:10px;padding:18px 12px;text-align:center;'>"
                            f"<div style='font-size:0.63rem;text-transform:uppercase;letter-spacing:.07em;color:#94a3b8;margin-bottom:8px;'>{_l}</div>"
                            f"<div style='font-size:1.8rem;font-weight:800;color:{_bg};line-height:1;'>{_v}</div>"
                            f"</div>", unsafe_allow_html=True
                        )
                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

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
                        st.markdown("<div style='border:2px dashed #e2e8f0;border-radius:12px;padding:36px 20px;text-align:center;background:#fafbfc;margin:8px 0;'><p style='font-weight:600;color:#6b7280;margin:0;font-size:.88rem;'>Sin consultas en este periodo</p><p style='font-size:.75rem;color:#9ca3af;margin:4px 0 0;'>Las consultas aparecerán aquí al registrarse</p></div>", unsafe_allow_html=True)

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
                        st.markdown("<div style='border:2px dashed #e2e8f0;border-radius:12px;padding:36px 20px;text-align:center;background:#fafbfc;margin:8px 0;'><p style='font-weight:600;color:#6b7280;margin:0;font-size:.88rem;'>Sin datos por nivel</p><p style='font-size:.75rem;color:#9ca3af;margin:4px 0 0;'>Aparecerá al completar evaluaciones</p></div>", unsafe_allow_html=True)

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
                        st.markdown("<div style='border:2px dashed #e2e8f0;border-radius:12px;padding:36px 20px;text-align:center;background:#fafbfc;margin:8px 0;'><p style='font-weight:600;color:#6b7280;margin:0;font-size:.88rem;'>Sin temas frecuentes aún</p><p style='font-size:.75rem;color:#9ca3af;margin:4px 0 0;'>Los temas más consultados aparecerán aquí</p></div>", unsafe_allow_html=True)

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
                        st.markdown("<div style='border:2px dashed #e2e8f0;border-radius:12px;padding:36px 20px;text-align:center;background:#fafbfc;margin:8px 0;'><p style='font-weight:600;color:#6b7280;margin:0;font-size:.88rem;'>Sin evaluaciones aún</p><p style='font-size:.75rem;color:#9ca3af;margin:4px 0 0;'>La precisión aparecerá al evaluar respuestas</p></div>", unsafe_allow_html=True)

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
                _rc1, _rc2 = st.columns([3, 1])
                with _rc1:
                    st.markdown("**Registro de consultas recientes**")
                with _rc2:
                    _top_n = st.selectbox("Mostrar:", [10, 20, 50, 100], index=1, key="adm_top_n", label_visibility="collapsed")
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
                    st.markdown("<div style='border:2px dashed #e2e8f0;border-radius:10px;padding:30px 20px;text-align:center;background:#fafbfc;margin:8px 0;'><p style='font-weight:600;color:#6b7280;margin:0;font-size:.88rem;'>Sin historial de consultas</p><p style='font-size:.75rem;color:#9ca3af;margin:4px 0 0;'>Aparecerá cuando los usuarios interactúen con Atena</p></div>", unsafe_allow_html=True)

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




# ── 4. Enrutamiento principal: Sidebar siempre presente + Admin vs Chat ───────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

with st.sidebar:
    nivel, k_chunks, is_admin_sidebar, lanzar_evaluacion, vs = render_sidebar(vs, disabled=st.session_state.is_generating)

if is_admin_sidebar != st.session_state.get("is_admin", False):
    st.session_state.is_admin = is_admin_sidebar
    st.rerun()

is_admin = st.session_state.get("is_admin", False)

if is_admin:
    _render_admin_dashboard()
    _inject_floating_chat()
else:
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


