import streamlit as st
import os
import time
import html as html_module
from config import ADMIN_PIN, nombre_legible

def render_sidebar(vs, disabled=False):
    """
    Renderiza la barra lateral organizada con flujo paso a paso:
    Paso 1: Subir documentos
    Paso 2: Indexar / Reconstruir VectorDB (ONNX local)
    Paso 3: Publicar cambios a la Nube / Unity (GitHub + Render)
    """
    from rag_pipeline import (
        add_documents_incremental,
        remove_documents_from_store,
        build_vector_store,
        DOCS_DIR,
        GROQ_LLM_MODEL,
        EMBED_MODEL_NAME
    )
    
    is_admin = st.session_state.is_admin

    # --- LOGO KONRAD LORENZ ---
    st.markdown("""
    <div class="kl-badge">
        <img src="https://colombiaestudia.com/wp-content/uploads/2021/06/logo_Konrad.png" 
             alt="Konrad Lorenz Fundación Universitaria" 
             style="max-width: 180px; width: 100%; margin: 0 auto; display: block;">
    </div>
    """, unsafe_allow_html=True)

    if disabled:
        st.info("⏳ Consulta en progreso. Por favor, espera a que termine para usar estos controles.")

    # Directorio de documentos
    docs_dir = DOCS_DIR
    os.makedirs(docs_dir, exist_ok=True)
    pdfs_disponibles = sorted([f for f in os.listdir(docs_dir) if f.lower().endswith((".pdf", ".docx"))])

    # ═════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: PANEL DE ADMINISTRACIÓN COMPACTO (PESTAÑAS)
    # ═════════════════════════════════════════════════════════════════════
    if is_admin:
        col_adm1, col_adm2 = st.columns([3, 2])
        with col_adm1:
            st.markdown("<div style='font-size:0.82rem; font-weight:600; color:#22c55e; padding:6px 0;'>🔓 Admin Activo</div>", unsafe_allow_html=True)
        with col_adm2:
            if st.button("Salir", key="logout_admin", disabled=disabled, use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()

        with st.expander(f"🛠️ Herramientas Admin ({len(pdfs_disponibles)} docs)", expanded=False):
            tab_libros, tab_motor, tab_seguridad = st.tabs(["📚 Libros", "⚙️ Motor", "🔑 PIN"])

            # ── TAB 1: GESTIÓN DE LITERATURA ──
            with tab_libros:
                st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#cbd5e1; margin-bottom:2px;'>1. Subir documento:</div>", unsafe_allow_html=True)
                nuevos_archivos = st.file_uploader(
                    "Subir PDF/DOCX:",
                    type=["pdf", "docx"],
                    accept_multiple_files=True,
                    disabled=disabled,
                    label_visibility="collapsed"
                )
                if nuevos_archivos:
                    ya_guardados = st.session_state.get("_uploads_guardados", set())
                    nuevos = [uf for uf in nuevos_archivos if uf.name not in ya_guardados]
                    if nuevos:
                        for uf in nuevos:
                            destino = os.path.join(docs_dir, uf.name)
                            with open(destino, "wb") as f:
                                f.write(uf.getbuffer())
                            ya_guardados.add(uf.name)
                        st.session_state["_uploads_guardados"] = ya_guardados
                        st.success(f"Guardado ({len(nuevos)}).")
                        time.sleep(1)
                        st.rerun()

                # Lista resumida de documentos
                pdfs_actuales = sorted([f for f in os.listdir(docs_dir) if f.lower().endswith((".pdf", ".docx"))])
                if pdfs_actuales:
                    st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#cbd5e1; margin-top:8px;'>Documentos activos:</div>", unsafe_allow_html=True)
                    for pdf in pdfs_actuales:
                        col_n, col_d = st.columns([5, 1])
                        with col_n:
                            st.markdown(f"<div class='doc-item' title='{pdf}' style='font-size:0.75rem; padding:4px 6px;'>{nombre_legible(pdf)}</div>", unsafe_allow_html=True)
                        with col_d:
                            if st.button("🗑️", key=f"del_{pdf}", help=f"Eliminar {pdf}", disabled=disabled):
                                st.session_state["_pending_delete"] = pdf

                    pending = st.session_state.get("_pending_delete", None)
                    if pending and pending in pdfs_actuales:
                        st.warning(f"¿Eliminar {nombre_legible(pending)}?")
                        c_si, c_no = st.columns(2)
                        with c_si:
                            if st.button("Sí", key="c_del", use_container_width=True):
                                os.remove(os.path.join(docs_dir, pending))
                                vs, _ = remove_documents_from_store(pending, vs_existente=vs)
                                st.session_state["_pending_delete"] = None
                                st.rerun()
                        with c_no:
                            if st.button("No", key="c_can", use_container_width=True):
                                st.session_state["_pending_delete"] = None
                                st.rerun()

                st.markdown("---")
                # Paso 2: Reconstruir VectorDB
                try:
                    _sidebar_count = vs._collection.count() if vs is not None else 0
                except Exception:
                    _sidebar_count = 0

                st.markdown(f"<div style='font-size:0.75rem; color:#94a3b8;'>2. Base de datos: <b>{_sidebar_count} vectores</b></div>", unsafe_allow_html=True)
                if st.button("🔄 Reindexar Vectores", key="rebuild_db_btn", use_container_width=True, disabled=disabled):
                    p_bar = st.progress(0, text="Indexando...")
                    try:
                        st.cache_resource.clear()
                        def _p(pct: float, msg: str):
                            p_bar.progress(max(1, min(99, int(pct * 100))), text=f"{msg}")
                        nuevo_vs = build_vector_store(force_rebuild=True, on_progress=_p)
                        p_bar.progress(100, text="Completado.")
                        st.success("✅ Base vectorial actualizada.")
                        time.sleep(1)
                        vs = nuevo_vs
                        st.rerun()
                    except Exception as e:
                        p_bar.empty()
                        st.error(f"Error: {e}")

                st.markdown("---")
                # Paso 3: Publicar a la Nube
                st.markdown("<div style='font-size:0.75rem; color:#94a3b8;'>3. Publicar a la App Móvil:</div>", unsafe_allow_html=True)
                if st.button("🚀 Publicar a Unity (Nube)", key="sync_cloud_btn", use_container_width=True, disabled=disabled):
                    with st.spinner("Sincronizando..."):
                        try:
                            import subprocess
                            subprocess.run(["git", "add", "Docs/", "chroma_neuro_db/"], check=True)
                            res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                            if "Docs" in res.stdout or "chroma_neuro_db" in res.stdout:
                                subprocess.run(["git", "commit", "-m", "docs: actualizar literatura medica"], check=True)
                                push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=40)
                                if push_res.returncode == 0:
                                    st.success("✅ ¡Publicado a Unity! Render actualiza en ~2 min.")
                                else:
                                    st.warning(f"Guardado local. Detalle: {push_res.stderr[:100]}")
                            else:
                                st.info("Todo está sincronizado.")
                        except Exception as err:
                            st.error(f"Error: {err}")

            # ── TAB 2: PARÁMETROS DEL MOTOR ──
            with tab_motor:
                k_chunks = st.slider("Fragmentos a recuperar (k)", min_value=3, max_value=8, value=5, key="admin_slider_k", disabled=disabled)
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px; font-size: 0.75rem; color: #94a3b8;">
                    <b>LLM:</b> {GROQ_LLM_MODEL}<br>
                    <b>Embeddings:</b> {EMBED_MODEL_NAME} (ONNX)<br>
                    <b>Temp:</b> 0.0 | <b>Chunk:</b> 1800
                </div>
                """, unsafe_allow_html=True)

            # ── TAB 3: CAMBIAR PIN ──
            with tab_seguridad:
                with st.form("change_pin_form", clear_on_submit=True):
                    nuevo_pin = st.text_input("Nuevo PIN:", type="password", max_chars=8)
                    confirmar_pin = st.text_input("Confirmar PIN:", type="password", max_chars=8)
                    if st.form_submit_button("Guardar PIN", use_container_width=True):
                        if len(nuevo_pin) < 4:
                            st.warning("Mínimo 4 caracteres.")
                        elif nuevo_pin != confirmar_pin:
                            st.error("No coinciden.")
                        else:
                            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
                            lines = []
                            if os.path.exists(env_path):
                                with open(env_path, "r", encoding="utf-8") as f:
                                    lines = f.readlines()
                            updated = False
                            new_lines = []
                            for l in lines:
                                if l.strip().startswith("ADMIN_PIN="):
                                    new_lines.append(f"ADMIN_PIN={nuevo_pin}\n")
                                    updated = True
                                else:
                                    new_lines.append(l)
                            if not updated:
                                new_lines.append(f"ADMIN_PIN={nuevo_pin}\n")
                            with open(env_path, "w", encoding="utf-8") as f:
                                f.writelines(new_lines)
                            os.environ["ADMIN_PIN"] = nuevo_pin
                            st.success(f"✅ PIN cambiado.")
                            time.sleep(1)
                            st.rerun()
    else:
        k_chunks = 5

    # ═════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: PERFIL DE USUARIO Y EVALUACIÓN (ESTUDIANTES Y DOCENTES)
    # ═════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### Perfil de Usuario (Nivel)")
    nivel = st.radio(
        "Selecciona tu nivel de conocimiento:",
        options=["Básico", "Avanzado"],
        index=1,
        disabled=disabled,
        help="Básico: Explicaciones didácticas.\nAvanzado: Rigor clínico y anatómico."
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    lanzar_evaluacion = st.button("Realizar Autoevaluación", use_container_width=True, key="realizar_evaluacion_btn", disabled=disabled)

    # Historial reciente
    if st.session_state.historial:
        st.markdown("---")
        st.markdown("### Consultas Recientes")
        historial_html = ""
        for i, h in enumerate(reversed(st.session_state.historial[-5:])):
            historial_html += (
                f"<div style='font-size: 0.82rem; padding: 6px 10px; background: rgba(255,255,255,0.05); "
                f"border-radius: 6px; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; "
                f"border: 1px solid rgba(255,255,255,0.05);' title='{html_module.escape(h)}'>"
                f"{html_module.escape(h)}</div>"
            )
        st.markdown(historial_html, unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: ACCESO ADMINISTRADOR (LOGIN / LOGOUT)
    if not is_admin:
        st.markdown("---")
        with st.expander("🔐 Acceso Administrador", expanded=False):
            if disabled:
                st.caption("⏳ Espera a que termine la consulta...")
            with st.form("admin_login_form", clear_on_submit=False):
                pin_input = st.text_input(
                    "PIN de acceso:", 
                    type="password", 
                    max_chars=8, 
                    key="admin_pin_input", 
                    disabled=disabled,
                    help="Ingresa el PIN (por defecto: 1234)"
                )
                submit_login = st.form_submit_button("Ingresar como Admin", use_container_width=True, disabled=disabled)
                if submit_login:
                    from config import ADMIN_PIN as CURRENT_PIN
                    pin_valido = os.getenv("ADMIN_PIN", CURRENT_PIN)
                    if pin_input == pin_valido:
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("PIN incorrecto")

    return nivel, k_chunks, is_admin, lanzar_evaluacion, vs
