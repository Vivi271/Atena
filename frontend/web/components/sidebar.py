"""
sidebar.py — Panel lateral de Atena RAG
Modo admin: solo muestra logo + logout + acceso para usuarios normales
El panel admin completo está en el área principal (app.py)
"""
import streamlit as st
import os
import html as html_module

def render_sidebar(vs, disabled=False):
    """
    Renderiza la barra lateral.
    Cuando el admin está activo, el sidebar es mínimo (el panel admin está en el área principal).
    """
    # ── Intentar importar módulos locales
    try:
        from config import ADMIN_PIN, nombre_legible
    except ImportError:
        ADMIN_PIN = os.environ.get("ADMIN_PIN", "12345")
        def nombre_legible(nombre):
            return os.path.splitext(nombre)[0].replace("_", " ").replace("-", " ").title()

    try:
        from db_preguntas import obtener_niveles
        _DB_AVAILABLE = True
    except ImportError:
        _DB_AVAILABLE = False
        obtener_niveles = None

    is_admin = st.session_state.is_admin

    # ── Logo Konrad Lorenz ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 16px;">
        <img src="https://colombiaestudia.com/wp-content/uploads/2021/06/logo_Konrad.png"
             alt="Konrad Lorenz"
             style="max-width: 160px; width: 100%;">
    </div>
    """, unsafe_allow_html=True)

    if disabled:
        st.info("Consulta en progreso...")

    # ══════════════════════════════════════════════════════════════
    # MODO ADMIN: sidebar mínimo — solo estado y logout
    # El panel completo está en el área principal (app.py)
    # ══════════════════════════════════════════════════════════════
    if is_admin:
        st.markdown("""
        <div style="
            background: rgba(34,197,94,0.1);
            border: 1px solid rgba(34,197,94,0.3);
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 12px;
        ">
            <div style="font-size:0.85rem; font-weight:700; color:#22c55e; margin-bottom:4px;">
                Administrador Activo
            </div>
            <div style="font-size:0.75rem; color:#94a3b8;">
                Panel completo en el área principal →
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Salir del modo Admin", key="logout_admin", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()

        # k_chunks por defecto para modo admin
        k_chunks = 5
        nivel = "Avanzado"
        lanzar_evaluacion = False
        return nivel, k_chunks, is_admin, lanzar_evaluacion, vs

    # ══════════════════════════════════════════════════════════════
    # MODO USUARIO NORMAL: perfil + evaluación + historial + login
    # ══════════════════════════════════════════════════════════════

    # ── Perfil de usuario ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Perfil de Usuario")

    # Sincronizar niveles desde Supabase; fallback a opciones hardcoded
    opciones_nivel = ["Principiante", "Avanzado", "General"]
    if _DB_AVAILABLE and obtener_niveles:
        try:
            niveles_db = obtener_niveles()
            if niveles_db:
                opciones_nivel = [n.strip().capitalize() for n in niveles_db if n.strip()]
        except Exception:
            pass

    nivel = st.radio(
        "Selecciona tu nivel de conocimiento:",
        options=opciones_nivel,
        index=0,
        disabled=disabled,
        help="Principiante: Explicaciones didácticas.\nAvanzado: Rigor clínico y anatómico.",
        key="nivel_radio"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    lanzar_evaluacion = st.button(
        "Realizar Autoevaluación",
        use_container_width=True,
        key="realizar_evaluacion_btn",
        disabled=disabled
    )

    # ── Historial reciente ─────────────────────────────────────────
    if st.session_state.historial:
        st.markdown("---")
        st.markdown("### Consultas Recientes")
        for h in reversed(st.session_state.historial[-5:]):
            st.markdown(
                f"<div style='font-size:0.82rem; padding:6px 10px; background:rgba(255,255,255,0.05); "
                f"border-radius:6px; margin-bottom:6px; white-space:nowrap; overflow:hidden; "
                f"text-overflow:ellipsis; border:1px solid rgba(255,255,255,0.05);' "
                f"title='{html_module.escape(h)}'>{html_module.escape(h)}</div>",
                unsafe_allow_html=True
            )

    # ── Login administrador ────────────────────────────────────────
    st.markdown("---")
    with st.expander("Acceso Administrador", expanded=False):
        if disabled:
            st.caption("Espera a que termine la consulta...")
        with st.form("admin_login_form", clear_on_submit=False):
            pin_input = st.text_input(
                "PIN de acceso:",
                type="password",
                max_chars=8,
                key="admin_pin_input",
                disabled=disabled,
            )
            submit_login = st.form_submit_button(
                "Ingresar como Admin",
                use_container_width=True,
                disabled=disabled
            )
            if submit_login:
                pin_valido = os.environ.get("ADMIN_PIN", ADMIN_PIN)
                if pin_input == pin_valido:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("PIN incorrecto")

    k_chunks = 5
    return nivel, k_chunks, is_admin, lanzar_evaluacion, vs
