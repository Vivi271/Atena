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
    # SECCIÓN 1: PANEL DE ADMINISTRACIÓN Y GESTIÓN DE LITERATURA
    # ═════════════════════════════════════════════════════════════════════
    if is_admin:
        st.markdown("<div style='background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.3); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; text-align: center;'><span style='color:#22c55e; font-weight:600; font-size:0.85rem;'>🔓 Modo Administrador Activo</span></div>", unsafe_allow_html=True)
        
        with st.expander(f"📚 Gestión de Literatura RAG ({len(pdfs_disponibles)} libros)", expanded=True):
            st.markdown("<div style='font-size:0.8rem; color:#94a3b8; margin-bottom:10px;'>Flujo ordenado para incorporar nuevo conocimiento al consultor y a Unity:</div>", unsafe_allow_html=True)
            
            # ── PASO 1: Subir archivos ──
            st.markdown("#### **Paso 1: Subir nuevo documento**")
            nuevos_archivos = st.file_uploader(
                "Arrastra aquí tus archivos (PDF / DOCX):",
                type=["pdf", "docx"],
                accept_multiple_files=True,
                disabled=disabled,
                help="Sube uno o varios archivos de neuroanatomía para la base de conocimientos."
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
                    st.success(f"✅ {len(nuevos)} archivo(s) guardado(s) en Docs/.")
                    time.sleep(1)
                    st.rerun()

            # Lista actual de documentos
            pdfs_actuales = sorted([f for f in os.listdir(docs_dir) if f.lower().endswith((".pdf", ".docx"))])
            if pdfs_actuales:
                st.markdown("<div style='font-size:0.75rem; color:#64748b; margin-top:6px;'>Archivos disponibles en Docs/:</div>", unsafe_allow_html=True)
                for pdf in pdfs_actuales:
                    nombre = nombre_legible(pdf)
                    col_n, col_d = st.columns([5, 1])
                    with col_n:
                        st.markdown(f"<div class='doc-item' title='{pdf}' style='font-size:0.78rem;'>{nombre}</div>", unsafe_allow_html=True)
                    with col_d:
                        if st.button("🗑️", key=f"del_{pdf}", help=f"Eliminar {pdf}", disabled=disabled):
                            st.session_state["_pending_delete"] = pdf

                # Confirmación de eliminación
                pending = st.session_state.get("_pending_delete", None)
                if pending and pending in pdfs_actuales:
                    nombre_pending = nombre_legible(pending)
                    st.warning(f"¿Eliminar **{nombre_pending}**?")
                    col_si, col_no = st.columns(2)
                    with col_si:
                        if st.button("Sí, eliminar", key="confirmar_delete", use_container_width=True, disabled=disabled):
                            os.remove(os.path.join(docs_dir, pending))
                            with st.spinner(f"Eliminando vectores..."):
                                try:
                                    vs, n_borrados = remove_documents_from_store(pending, vs_existente=vs)
                                    st.success(f"Eliminado — {n_borrados} vectores removidos.")
                                    time.sleep(1)
                                except Exception as e:
                                    st.error(f"Error al eliminar: {str(e)[:200]}")
                                    time.sleep(2)
                            st.session_state["_pending_delete"] = None
                            st.rerun()
                    with col_no:
                        if st.button("Cancelar", key="cancelar_delete", use_container_width=True, disabled=disabled):
                            st.session_state["_pending_delete"] = None
                            st.rerun()

            st.markdown("---")

            # ── PASO 2: Indexar / Reconstruir Vectores ──
            st.markdown("#### **Paso 2: Indexar y Vectorizar (Local ONNX)**")
            try:
                _sidebar_count = vs._collection.count() if vs is not None else 0
            except Exception:
                _sidebar_count = 0

            # Detectar si hay archivos sin indexar
            _docs_files = set(f for f in os.listdir(docs_dir) if f.lower().endswith(('.pdf', '.docx')))
            if vs is not None and _sidebar_count > 0:
                try:
                    _all_meta = vs._collection.get(include=["metadatas"])
                    _indexados = set(os.path.basename(m.get('source','')) for m in _all_meta["metadatas"])
                    _sin_indexar = _docs_files - _indexados
                except Exception:
                    _sin_indexar = set()
            else:
                _sin_indexar = _docs_files

            if _sin_indexar:
                st.warning(f"⚠️ Hay {len(_sin_indexar)} documento(s) nuevo(s) sin indexar.")
            else:
                st.info(f"📊 Base vectorial lista: {_sidebar_count} fragmentos indexados.")

            st.caption("Procesa los documentos en tu máquina usando ONNX Runtime ($0 costo, sin gasto de tokens).")
            if st.button("🔄 Reconstruir / Actualizar VectorDB", key="rebuild_db_btn", use_container_width=True, disabled=disabled):
                progress_bar = st.progress(0, text="⏳ Preparando vectorización...")
                try:
                    st.cache_resource.clear()
                    def _on_progress(pct: float, msg: str):
                        pct_int = max(1, min(99, int(pct * 100)))
                        progress_bar.progress(pct_int, text=f"{msg} ({pct_int}%)")

                    nuevo_vs = build_vector_store(force_rebuild=True, on_progress=_on_progress)
                    total_v = nuevo_vs._collection.count()
                    progress_bar.progress(100, text=f"¡Completado! {total_v} fragmentos vectorizados.")
                    st.success(f"✅ Base de datos actualizada con éxito ({total_v} fragmentos).")
                    time.sleep(1.5)
                    vs = nuevo_vs
                    st.rerun()
                except Exception as e:
                    progress_bar.empty()
                    st.error(f"Error durante la indexación: {e}")

            st.markdown("---")

            # ── PASO 3: Publicar a la Nube (Unity) ──
            st.markdown("#### **Paso 3: Publicar a la Nube (Unity)**")
            st.caption("Guarda los nuevos libros en GitHub y notifica a Render para actualizar la app móvil de los estudiantes.")
            if st.button("🚀 Publicar Cambios a la Nube", key="sync_cloud_btn", use_container_width=True, disabled=disabled):
                with st.spinner("Sincronizando con GitHub y Render..."):
                    try:
                        import subprocess
                        subprocess.run(["git", "add", "Docs/", "chroma_neuro_db/"], check=True)
                        res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                        if "Docs" in res.stdout or "chroma_neuro_db" in res.stdout:
                            subprocess.run(["git", "commit", "-m", "docs: actualizar literatura medica desde panel admin"], check=True)
                            push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=40)
                            if push_res.returncode == 0:
                                st.success("✅ ¡Publicación exitosa! En ~2 minutos Render actualizará la app de Unity.")
                            else:
                                st.warning(f"Guardado localmente. Detalle: {push_res.stderr[:200]}")
                        else:
                            st.info("ℹ️ Todo está al día. La nube ya tiene la versión más reciente.")
                    except Exception as err:
                        st.error(f"Error al sincronizar: {err}")

        # ── Parámetros del motor (solo admin) ──
        with st.expander("⚙️ Parámetros del Motor de IA", expanded=False):
            k_chunks = st.slider("Fragmentos a recuperar (k)", min_value=3, max_value=8, value=5, key="admin_slider_k", disabled=disabled)
            st.markdown(f"""
            <div style="background: rgba(0,0,0,0.25); padding: 10px; border-radius: 8px; font-size: 0.8rem; color: #94a3b8;">
                <b>LLM:</b> {GROQ_LLM_MODEL}<br>
                <b>Embeddings:</b> {EMBED_MODEL_NAME} (ONNX CPU)<br>
                <b>Temperatura:</b> 0.0 (Determinista)<br>
                <b>Chunk Size:</b> 1800 carácteres<br>
                <b>Plataforma:</b> Groq Cloud LPU
            </div>
            """, unsafe_allow_html=True)
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
    # ═════════════════════════════════════════════════════════════════════
    st.markdown("---")
    if is_admin:
        if st.button("🚪 Cerrar sesión admin", use_container_width=True, key="logout_admin", disabled=disabled):
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.expander("🔐 Acceso Administrador", expanded=False):
            if disabled:
                st.caption("⏳ Espera a que termine la consulta...")
            pin_input = st.text_input("PIN de acceso:", type="password", max_chars=4, key="admin_pin_input", disabled=disabled)
            if st.button("Ingresar como Admin", use_container_width=True, key="login_admin", disabled=disabled):
                if pin_input == ADMIN_PIN:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("PIN incorrecto")

    return nivel, k_chunks, is_admin, lanzar_evaluacion, vs
