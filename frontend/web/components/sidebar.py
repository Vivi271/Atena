"""
sidebar.py — Panel lateral de Atena RAG
"""
import streamlit as st
import os
import html as html_module

def render_sidebar(vs, disabled=False):
    """
    Renderiza la barra lateral para Administrador o Usuario normal.
    Incluye el toggle de modo claro/oscuro en la parte inferior del panel.
    """
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

    is_admin = st.session_state.get("is_admin", False)

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
    # MODO ADMIN: estado + cerrar sesión + modo oscuro al final
    # ══════════════════════════════════════════════════════════════
    if is_admin:
        st.markdown("""
        <div style="
            background: rgba(140,198,63,0.12);
            border: 1px solid rgba(140,198,63,0.3);
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 14px;
        ">
            <div style="font-size:0.85rem; font-weight:700; color:#8CC63F; margin-bottom:4px;">
                Administrador Activo
            </div>
            <div style="font-size:0.75rem; color:#94a3b8;">
                Gestión de documentos, preguntas y estadísticas.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Cerrar sesión de Admin", key="logout_admin_sidebar", use_container_width=True):
            st.session_state.is_admin = False
            st.session_state.adm_pin_activo = False
            try:
                st.query_params.pop("adm_ok", None)
            except Exception:
                pass
            st.rerun()

        # Separador y controles inferiores
        st.markdown("---")
        modo_txt = "Modo claro" if st.session_state.get("dark_mode", False) else "Modo oscuro"
        if st.button(modo_txt, key="sidebar_dark_toggle_admin", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.get("dark_mode", False)
            st.rerun()

        k_chunks = 5
        nivel = "Avanzado"
        lanzar_evaluacion = False
        return nivel, k_chunks, is_admin, lanzar_evaluacion, vs

    # ══════════════════════════════════════════════════════════════
    # MODO USUARIO NORMAL: perfil + evaluación + historial + login + modo oscuro
    # ══════════════════════════════════════════════════════════════

    # ── Perfil de usuario ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Perfil de Usuario")

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
    if st.session_state.get("historial"):
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
                    st.session_state.adm_pin_activo = True
                    try:
                        st.query_params["adm_ok"] = "1"
                    except Exception:
                        pass
                    st.rerun()
                else:
                    st.error("PIN incorrecto")

    # ── Toggle de modo oscuro en la parte inferior del panel ──
    st.markdown("---")
    modo_txt = "Modo claro" if st.session_state.get("dark_mode", False) else "Modo oscuro"
    if st.button(modo_txt, key="sidebar_dark_toggle_user", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.get("dark_mode", False)
        st.rerun()

    k_chunks = 5
    return nivel, k_chunks, is_admin, lanzar_evaluacion, vs
