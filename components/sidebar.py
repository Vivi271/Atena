import streamlit as st
import os
import time
import html as html_module
from config import ADMIN_PIN, nombre_legible

def render_sidebar(vs, disabled=False):
    """
    Renderiza la barra lateral (logo, base de conocimiento, nivel de usuario,
    parámetros del motor, y acceso de administrador).
    Retorna (nivel, k_chunks, is_admin, vs_actualizado)
    """
    from rag_pipeline import (
        add_documents_incremental,
        remove_documents_from_store,
        DOCS_DIR
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

    # ── Solo admin puede gestionar documentos ──
    if is_admin:
        with st.expander(f"📂 Base de Conocimientos ({len(pdfs_disponibles)} docs)", expanded=False):
            # Subir nuevos archivos
            nuevos_archivos = st.file_uploader(
                "📤 Agregar documentos (PDF / DOCX)",
                type=["pdf", "docx"],
                accept_multiple_files=True,
                disabled=disabled,
                help="Sube uno o más PDFs o archivos Word. Luego se indexarán automáticamente."
            )
            if nuevos_archivos:
                ya_guardados = st.session_state.get("_uploads_guardados", set())
                nuevos = [uf for uf in nuevos_archivos if uf.name not in ya_guardados]
                if nuevos:
                    rutas_nuevas = []
                    for uf in nuevos:
                        destino = os.path.join(docs_dir, uf.name)
                        with open(destino, "wb") as f:
                            f.write(uf.getbuffer())
                        ya_guardados.add(uf.name)
                        rutas_nuevas.append(destino)
                    st.session_state["_uploads_guardados"] = ya_guardados
                    
                    # Ejecutar indexación incremental inmediata
                    with st.spinner(f"Indexando {len(rutas_nuevas)} archivo(s) nuevos..."):
                        try:
                            vs = add_documents_incremental(rutas_nuevas, vs_existente=vs)
                            n = vs._collection.count()
                            st.success(f"¡Indexación completa! Base tiene {n} vectores.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error indexando: {str(e)[:300]}")
            else:
                st.session_state["_uploads_guardados"] = set()

            # Lista de archivos con opción de eliminar
            pdfs_actuales = sorted([f for f in os.listdir(docs_dir) if f.lower().endswith((".pdf", ".docx"))])
            if pdfs_actuales:
                st.markdown("<div style='margin-top:8px; font-size:0.8rem; color:#64748b;'>Archivos subidos:</div>", unsafe_allow_html=True)
                for pdf in pdfs_actuales:
                    nombre = nombre_legible(pdf)
                    col_n, col_d = st.columns([5, 1])
                    with col_n:
                        st.markdown(
                            f"<div class='doc-item' title='{pdf}'>{nombre}</div>",
                            unsafe_allow_html=True
                        )
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
            else:
                st.info("No hay documentos subidos.")

    st.markdown("---")
    st.markdown("### Perfil de Usuario (Nivel)")
    nivel = st.radio(
         "Selecciona tu nivel de conocimiento:",
         options=["Básico", "Avanzado"],
         index=1,
         disabled=disabled,
         help="Básico: Explicaciones sencillas.\nAvanzado: Rigor académico."
     )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón de autoevaluación (el modal se llamará en app.py si se pulsa)
    lanzar_evaluacion = st.button("Realizar Autoevaluación", use_container_width=True, key="realizar_evaluacion_btn", disabled=disabled)

    # ── Parámetros del motor (solo para admin) ──
    if is_admin:
        from rag_pipeline import GEMINI_LLM_MODEL, GEMINI_EMBED_MODEL
        with st.container():
            st.markdown("### Parámetros del Motor")
            k_chunks = st.slider("Fragmentos a recuperar (k)", min_value=3, max_value=8, value=5, key="admin_slider_k", disabled=disabled)
            
            st.markdown(f"""
            <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; font-size: 0.82rem; color: #94a3b8; margin-top: 10px;">
                <b>LLM:</b> {GEMINI_LLM_MODEL} (Gemini API)
                <span title="Modelo de lenguaje en la nube de Google. Rápido y sin carga local." style="cursor:help; color:#5dade2;"> ℹ️</span><br>
                <b>Embeddings:</b> {GEMINI_EMBED_MODEL} (Google)
                <span title="Modelo de vectorización de Google." style="cursor:help; color:#5dade2;"> ℹ️</span><br>
                <b>Temp:</b> 0.0
                <span title="Respuestas académicas deterministas." style="cursor:help; color:#5dade2;"> ℹ️</span>
                | <b>Chunk:</b> 1800
                | <b>🌐 Gemini Cloud</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        k_chunks = 6
        
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Estado de la base de datos (solo para admin) ──
    if is_admin:
        with st.container():
            st.markdown("<br>", unsafe_allow_html=True)
            try:
                _sidebar_count = vs._collection.count() if vs is not None else 0
            except Exception:
                _sidebar_count = 0
                
            # Detectar archivos sin indexar
            _docs_files = set(f for f in os.listdir(docs_dir) if f.lower().endswith(('.pdf', '.docx')))
            if vs is not None and _sidebar_count > 0:
                try:
                    _all_meta = vs._collection.get(include=["metadatas"])
                    _indexados = set(os.path.basename(m.get('source','')) for m in _all_meta["metadatas"])
                    _sin_indexar = _docs_files - _indexados
                    _vectores_huerfanos = _indexados - _docs_files
                except Exception:
                    _sin_indexar = set()
                    _vectores_huerfanos = set()
            else:
                _sin_indexar = _docs_files
                _vectores_huerfanos = set()

            if not _sin_indexar and _sidebar_count > 0:
                st.success(f"Base de conocimiento lista — {_sidebar_count} fragmentos indexados")
            elif _sin_indexar:
                if st.session_state.get("_iniciar_indexado"):
                    st.info("Indexando documentos nuevos, por favor espera...")
                else:
                    n_p = len(_sin_indexar)
                    st.warning(f"{n_p} documento{'s' if n_p > 1 else ''} sin indexar ({_sidebar_count} fragmentos ya listos)")
                    if st.button(f"Indexar {n_p} documento{'s' if n_p > 1 else ''} nuevo{'s' if n_p > 1 else ''}", use_container_width=True, key="btn_sync", disabled=disabled):
                        st.session_state["_iniciar_indexado"] = sorted(list(_sin_indexar))
                        st.rerun()

            # Procesar cola de indexación pendiente
            if st.session_state.get("_iniciar_indexado"):
                pendientes = st.session_state.pop("_iniciar_indexado")
                total = len(pendientes)
                progreso = st.progress(0, text="Iniciando indexación...")
                try:
                    for i, archivo in enumerate(pendientes):
                        pct = int((i / total) * 100)
                        progreso.progress(i / total, text=f"Procesando '{archivo}'... ({pct}%)")
                        ruta = os.path.join(docs_dir, archivo)
                        vs = add_documents_incremental([ruta], vs_existente=vs)
                    progreso.progress(1.0, text=f"Indexación completada — {total} documento{'s' if total > 1 else ''} agregado{'s' if total > 1 else ''}.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al indexar: {e}")

            if _vectores_huerfanos:
                st.caption(f"{len(_vectores_huerfanos)} documento(s) eliminado(s) — usa 'Reparar DB' para limpiar")

            # Botón de rebuild completo
            with st.expander("🛠️ Reparar / Reconstruir DB completa", expanded=False):
                if st.button("Reconstruir VectorDB", use_container_width=True, key="rebuild_db_btn", disabled=disabled):
                    progress_bar = st.progress(0, text="⏳ Preparando reconstrucción...")
                    status_txt = st.empty()
                    try:
                        # PASO 1: Limpiar caché de Streamlit
                        progress_bar.progress(1, text="🧹 Limpiando caché de Streamlit...")
                        st.cache_resource.clear()

                        # Callback de progreso: actualiza la barra en tiempo real
                        def _on_progress(pct: float, msg: str):
                            pct_int = max(1, min(99, int(pct * 100)))
                            progress_bar.progress(pct_int, text=f"{msg}  ({pct_int}%)")

                        # PASO 2: Reconstruir con Gemini embeddings (progreso real lote a lote)
                        from rag_pipeline import build_vector_store
                        nuevo_vs = build_vector_store(force_rebuild=True, on_progress=_on_progress)

                        total_v = nuevo_vs._collection.count()
                        progress_bar.progress(100, text=f"Reconstrucción completada — {total_v} fragmentos indexados.")
                        st.success(f"Reconstrucción terminada. La base de conocimiento tiene {total_v} fragmentos listos para consultar.")
                        time.sleep(2)
                        vs = nuevo_vs
                        st.rerun()
                    except Exception as e:
                        progress_bar.empty()
                        st.error(f"Ocurrió un error durante la reconstrucción. Intenta de nuevo o revisa el detalle abajo.")
                        st.caption(str(e))
                        import traceback
                        with st.expander("Ver detalle del error"):
                            st.code(traceback.format_exc(), language="python")

    # Historial reciente
    if st.session_state.historial:
        with st.container():
            st.markdown("### Consultas Recientes")
            historial_html = ""
            for i, h in enumerate(reversed(st.session_state.historial[-5:])):
                historial_html += (
                    f"<div style='font-size: 0.85rem; padding: 6px 10px; background: rgba(255,255,255,0.05); "
                    f"border-radius: 6px; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; "
                    f"border: 1px solid rgba(255,255,255,0.05);' title='{html_module.escape(h)}'>"
                    f"{html_module.escape(h)}</div>"
                )
            st.markdown(historial_html, unsafe_allow_html=True)

    # ── Acceso administrador (login / logout) ──
    st.markdown("---")
    if is_admin:
        with st.container():
            st.markdown("<div style='text-align:center; font-size:0.8rem; color:#22c55e; padding:4px 0;'>🔓 Modo Administrador activo</div>", unsafe_allow_html=True)
            if st.button("Cerrar sesión admin", use_container_width=True, key="logout_admin", disabled=disabled):
                st.session_state.is_admin = False
                st.rerun()
    else:
        with st.expander("Acceso administrador", expanded=False):
            if disabled:
                st.caption("⏳ Espera a que termine la consulta para ingresar...")
            pin_input = st.text_input("PIN de acceso:", type="password", max_chars=4, key="admin_pin_input", disabled=disabled)
            if st.button("Ingresar", use_container_width=True, key="login_admin", disabled=disabled):
                if pin_input == ADMIN_PIN:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("PIN incorrecto")

    return nivel, k_chunks, is_admin, lanzar_evaluacion, vs
