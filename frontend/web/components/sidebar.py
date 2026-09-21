"""
sidebar.py — Panel lateral de Atena RAG
Modo nube: admin con CRUD completo via API + Supabase
"""
import streamlit as st
import os
import time
import html as html_module
import httpx

def render_sidebar(vs, disabled=False):
    """
    Renderiza la barra lateral.
    En modo nube (_RAG_AVAILABLE=False), el admin gestiona documentos via API
    y preguntas directamente via Supabase.
    """
    # ── Intentar importar módulos locales (solo disponibles en modo completo)
    try:
        from rag_pipeline import (
            add_documents_incremental,
            remove_documents_from_store,
            build_vector_store,
            DOCS_DIR,
            GROQ_LLM_MODEL,
            EMBED_MODEL_NAME
        )
        _RAG_AVAILABLE = True
    except ImportError:
        _RAG_AVAILABLE = False
        DOCS_DIR = None
        GROQ_LLM_MODEL = os.environ.get("GROQ_LLM_MODEL", "N/A")
        EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL", "N/A")

    try:
        from config import ADMIN_PIN, nombre_legible
    except ImportError:
        ADMIN_PIN = os.environ.get("ADMIN_PIN", "12345")
        def nombre_legible(nombre):
            return os.path.splitext(nombre)[0].replace("_", " ").replace("-", " ").title()

    try:
        from db_preguntas import (
            obtener_preguntas_por_nivel,
            agregar_pregunta,
            actualizar_pregunta,
            eliminar_pregunta,
            obtener_niveles,
            obtener_temas,
        )
        _DB_AVAILABLE = True
    except ImportError:
        _DB_AVAILABLE = False

    ATENA_API_URL = os.environ.get("ATENA_API_URL", "https://atena-vugz.onrender.com").rstrip("/")
    ADMIN_PIN_ENV = os.environ.get("ADMIN_PIN", ADMIN_PIN)

    is_admin = st.session_state.is_admin

    # ── Logo Konrad Lorenz ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="kl-badge">
        <img src="https://colombiaestudia.com/wp-content/uploads/2021/06/logo_Konrad.png"
             alt="Konrad Lorenz Fundación Universitaria"
             style="max-width: 180px; width: 100%; margin: 0 auto; display: block;">
    </div>
    """, unsafe_allow_html=True)

    if disabled:
        st.info("⏳ Consulta en progreso. Por favor, espera a que termine para usar estos controles.")

    # ═══════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: PANEL DE ADMINISTRACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    if is_admin:
        col_adm1, col_adm2 = st.columns([3, 2])
        with col_adm1:
            st.markdown("<div style='font-size:0.82rem; font-weight:600; color:#22c55e; padding:6px 0;'>🔓 Admin Activo</div>", unsafe_allow_html=True)
        with col_adm2:
            if st.button("Salir", key="logout_admin", disabled=disabled, use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()

        with st.expander("🛠️ Herramientas Admin", expanded=False):
            tab_libros, tab_preguntas, tab_motor, tab_pin = st.tabs(["📚 Libros", "📋 Preguntas", "⚙️ Motor", "🔑 PIN"])

            # ── TAB 1: GESTIÓN DE DOCUMENTOS ───────────────────────────────
            with tab_libros:
                if _RAG_AVAILABLE and DOCS_DIR:
                    # Modo local: gestión directa de archivos
                    _render_libros_local(DOCS_DIR, vs, disabled, nombre_legible,
                                         add_documents_incremental, remove_documents_from_store,
                                         build_vector_store)
                else:
                    # Modo nube: gestión via API
                    _render_libros_nube(ATENA_API_URL, ADMIN_PIN_ENV, disabled, nombre_legible)

            # ── TAB 2: CRUD PREGUNTAS ───────────────────────────────────────
            with tab_preguntas:
                if _DB_AVAILABLE:
                    _render_crud_preguntas(
                        disabled, obtener_preguntas_por_nivel,
                        agregar_pregunta, actualizar_pregunta, eliminar_pregunta,
                        obtener_niveles, obtener_temas, nombre_legible
                    )
                else:
                    st.warning("❌ No se pudo conectar a la base de datos de preguntas.")

            # ── TAB 3: MOTOR ───────────────────────────────────────────────
            with tab_motor:
                k_chunks_motor = st.slider("Fragmentos a recuperar (k)", min_value=3, max_value=8,
                                            value=st.session_state.get("k_chunks_val", 5),
                                            key="admin_slider_k", disabled=disabled)
                st.session_state["k_chunks_val"] = k_chunks_motor
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px; font-size: 0.75rem; color: #94a3b8;">
                    <b>LLM:</b> {GROQ_LLM_MODEL}<br>
                    <b>Embeddings:</b> {EMBED_MODEL_NAME}<br>
                    <b>API:</b> {ATENA_API_URL}
                </div>
                """, unsafe_allow_html=True)

                st.markdown("---")
                if st.button("🔄 Reindexar Vectores", key="rebuild_nube_btn",
                              use_container_width=True, disabled=disabled):
                    with st.spinner("Reconstruyendo vectores en el servidor..."):
                        try:
                            resp = httpx.post(
                                f"{ATENA_API_URL}/api/admin/rebuild",
                                headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                                timeout=120.0,
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                st.success(f"✅ {data.get('mensaje', 'Reconstruido')} — {data.get('total_vectores', '?')} vectores")
                            else:
                                st.error(f"Error {resp.status_code}: {resp.text[:200]}")
                        except Exception as e:
                            st.error(f"Error de conexión: {e}")

            # ── TAB 4: PIN ─────────────────────────────────────────────────
            with tab_pin:
                with st.form("change_pin_form", clear_on_submit=True):
                    nuevo_pin = st.text_input("Nuevo PIN:", type="password", max_chars=8)
                    confirmar_pin = st.text_input("Confirmar PIN:", type="password", max_chars=8)
                    if st.form_submit_button("Guardar PIN", use_container_width=True):
                        if len(nuevo_pin) < 4:
                            st.warning("Mínimo 4 caracteres.")
                        elif nuevo_pin != confirmar_pin:
                            st.error("No coinciden.")
                        else:
                            os.environ["ADMIN_PIN"] = nuevo_pin
                            st.success("✅ PIN cambiado para esta sesión. Recuerda actualizarlo en Render > Environment.")

        k_chunks = st.session_state.get("k_chunks_val", 5)

    else:
        k_chunks = 5

    # ═══════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: PERFIL DE USUARIO Y EVALUACIÓN
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### Perfil de Usuario (Nivel)")

    # Intentar obtener niveles desde Supabase; fallback a opciones hardcoded
    opciones_nivel = ["Principiante", "Avanzado"]
    if _DB_AVAILABLE:
        try:
            niveles_db = obtener_niveles()
            if niveles_db:
                # Capitalizar y filtrar vacíos
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

    # Historial reciente
    if st.session_state.historial:
        st.markdown("---")
        st.markdown("### Consultas Recientes")
        historial_html = ""
        for h in reversed(st.session_state.historial[-5:]):
            historial_html += (
                f"<div style='font-size: 0.82rem; padding: 6px 10px; background: rgba(255,255,255,0.05); "
                f"border-radius: 6px; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; "
                f"border: 1px solid rgba(255,255,255,0.05);' title='{html_module.escape(h)}'>"
                f"{html_module.escape(h)}</div>"
            )
        st.markdown(historial_html, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: LOGIN ADMINISTRADOR
    # ═══════════════════════════════════════════════════════════════════════
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
                    help="Ingresa el PIN de administrador"
                )
                submit_login = st.form_submit_button("Ingresar como Admin", use_container_width=True, disabled=disabled)
                if submit_login:
                    pin_valido = os.environ.get("ADMIN_PIN", ADMIN_PIN)
                    if pin_input == pin_valido:
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("PIN incorrecto")

    return nivel, k_chunks, is_admin, lanzar_evaluacion, vs


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers del panel admin
# ═══════════════════════════════════════════════════════════════════════════════

def _render_libros_local(DOCS_DIR, vs, disabled, nombre_legible,
                          add_documents_incremental, remove_documents_from_store,
                          build_vector_store):
    """Panel de libros en modo local (con acceso directo al filesystem)."""
    import time
    pdfs_actuales = sorted([f for f in os.listdir(DOCS_DIR) if f.lower().endswith((".pdf", ".docx"))])

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
                destino = os.path.join(DOCS_DIR, uf.name)
                with open(destino, "wb") as f:
                    f.write(uf.getbuffer())
                ya_guardados.add(uf.name)
            st.session_state["_uploads_guardados"] = ya_guardados
            st.success(f"Guardado ({len(nuevos)}).")
            time.sleep(1)
            st.rerun()

    if pdfs_actuales:
        st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#cbd5e1; margin-top:8px;'>Documentos activos:</div>", unsafe_allow_html=True)
        for pdf in pdfs_actuales:
            col_n, col_d = st.columns([5, 1])
            with col_n:
                st.markdown(f"<div style='font-size:0.75rem; padding:4px 6px;'>{nombre_legible(pdf)}</div>", unsafe_allow_html=True)
            with col_d:
                if st.button("🗑️", key=f"del_{pdf}", disabled=disabled):
                    st.session_state["_pending_delete"] = pdf

        pending = st.session_state.get("_pending_delete", None)
        if pending and pending in pdfs_actuales:
            st.warning(f"¿Eliminar {nombre_legible(pending)}?")
            c_si, c_no = st.columns(2)
            with c_si:
                if st.button("Sí", key="c_del", use_container_width=True):
                    os.remove(os.path.join(DOCS_DIR, pending))
                    remove_documents_from_store(pending, vs_existente=vs)
                    st.session_state["_pending_delete"] = None
                    st.rerun()
            with c_no:
                if st.button("No", key="c_can", use_container_width=True):
                    st.session_state["_pending_delete"] = None
                    st.rerun()


def _render_libros_nube(ATENA_API_URL, ADMIN_PIN_ENV, disabled, nombre_legible):
    """Panel de libros en modo nube (via API REST)."""
    st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#cbd5e1; margin-bottom:4px;'>1. Subir documento al servidor:</div>", unsafe_allow_html=True)

    nuevos_archivos = st.file_uploader(
        "Subir PDF/DOCX:",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        disabled=disabled,
        label_visibility="collapsed",
        key="nube_uploader"
    )
    if nuevos_archivos:
        ya_subidos = st.session_state.get("_uploads_nube", set())
        nuevos = [uf for uf in nuevos_archivos if uf.name not in ya_subidos]
        if nuevos:
            for uf in nuevos:
                with st.spinner(f"Subiendo e indexando '{uf.name}'..."):
                    try:
                        resp = httpx.post(
                            f"{ATENA_API_URL}/api/admin/upload",
                            headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                            files={"file": (uf.name, uf.getvalue(), "application/octet-stream")},
                            timeout=180.0,  # Indexar puede tardar
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.success(f"✅ {data.get('mensaje', 'Subido')} — {data.get('fragmentos_indexados', '?')} fragmentos")
                            ya_subidos.add(uf.name)
                        else:
                            st.error(f"Error al subir '{uf.name}': {resp.text[:200]}")
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")
            st.session_state["_uploads_nube"] = ya_subidos

    # Listar documentos disponibles en el servidor
    st.markdown("---")
    st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#cbd5e1;'>2. Documentos en el servidor:</div>", unsafe_allow_html=True)

    if st.button("🔄 Actualizar lista", key="refresh_docs_btn", disabled=disabled):
        st.session_state.pop("_docs_nube_cache", None)

    if "_docs_nube_cache" not in st.session_state:
        try:
            resp = httpx.get(
                f"{ATENA_API_URL}/api/admin/documents",
                headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                timeout=15.0,
            )
            if resp.status_code == 200:
                st.session_state["_docs_nube_cache"] = resp.json().get("documentos", [])
            else:
                st.session_state["_docs_nube_cache"] = []
                st.warning(f"No se pudo obtener la lista: {resp.status_code}")
        except Exception as e:
            st.session_state["_docs_nube_cache"] = []
            st.warning(f"Error al conectar con el API: {e}")

    docs = st.session_state.get("_docs_nube_cache", [])
    if docs:
        for doc in docs:
            nombre = doc["nombre"]
            col_n, col_d = st.columns([5, 1])
            with col_n:
                st.markdown(f"<div style='font-size:0.75rem; padding:4px 6px;'>{nombre_legible(nombre)}</div>", unsafe_allow_html=True)
            with col_d:
                if st.button("🗑️", key=f"del_nube_{nombre}", disabled=disabled):
                    st.session_state["_pending_delete_nube"] = nombre

        pending = st.session_state.get("_pending_delete_nube", None)
        if pending:
            st.warning(f"¿Eliminar '{nombre_legible(pending)}' del servidor?")
            c_si, c_no = st.columns(2)
            with c_si:
                if st.button("Sí, eliminar", key="c_del_nube", use_container_width=True):
                    with st.spinner("Eliminando..."):
                        try:
                            resp = httpx.delete(
                                f"{ATENA_API_URL}/api/admin/delete/{pending}",
                                headers={"X-Admin-Pin": ADMIN_PIN_ENV},
                                timeout=30.0,
                            )
                            if resp.status_code == 200:
                                st.success(f"✅ '{pending}' eliminado.")
                                st.session_state.pop("_docs_nube_cache", None)
                            else:
                                st.error(f"Error: {resp.text[:200]}")
                        except Exception as e:
                            st.error(f"Error de conexión: {e}")
                    st.session_state["_pending_delete_nube"] = None
                    st.rerun()
            with c_no:
                if st.button("Cancelar", key="c_can_nube", use_container_width=True):
                    st.session_state["_pending_delete_nube"] = None
                    st.rerun()
    else:
        st.caption("No hay documentos en el servidor o no se pudo obtener la lista.")


def _render_crud_preguntas(disabled, obtener_preguntas_por_nivel, agregar_pregunta,
                            actualizar_pregunta, eliminar_pregunta,
                            obtener_niveles, obtener_temas, nombre_legible):
    """Panel CRUD de preguntas de evaluación."""

    # Obtener niveles y temas de Supabase
    try:
        niveles_db = obtener_niveles()
        temas_db = obtener_temas()
    except Exception as e:
        st.error(f"Error al conectar con la BD: {e}")
        return

    if not niveles_db:
        st.warning("No hay niveles disponibles en la base de datos.")
        return

    # Sub-tabs: ver/editar | agregar nueva
    sub_ver, sub_nueva = st.tabs(["📖 Ver / Editar", "➕ Nueva Pregunta"])

    # ── Sub-tab: VER / EDITAR ──────────────────────────────────────────────
    with sub_ver:
        nivel_filtro = st.selectbox(
            "Filtrar por nivel:",
            options=["todos"] + niveles_db,
            key="crud_nivel_filtro"
        )
        try:
            preguntas = obtener_preguntas_por_nivel(
                nivel=None if nivel_filtro == "todos" else nivel_filtro,
                cantidad=50
            )
        except Exception as e:
            st.error(f"Error al cargar preguntas: {e}")
            preguntas = []

        if not preguntas:
            st.info("No hay preguntas para este nivel.")
        else:
            st.caption(f"{len(preguntas)} pregunta(s) encontrada(s)")
            for p in preguntas:
                pid = p["id"]
                enunciado_corto = p["enunciado"][:60] + "..." if len(p["enunciado"]) > 60 else p["enunciado"]
                with st.expander(f"#{pid} — {enunciado_corto}", expanded=False):
                    # Determinar respuestas
                    respuestas = p.get("respuestas", [])
                    textos = [r["texto"] for r in respuestas]
                    while len(textos) < 4:
                        textos.append("")
                    idx_correcta = next((i for i, r in enumerate(respuestas) if r.get("es_correcta")), 0)
                    letras = ["A", "B", "C", "D"]

                    with st.form(f"edit_form_{pid}"):
                        nuevo_enunciado = st.text_area("Enunciado:", value=p["enunciado"], key=f"enun_{pid}")
                        nuevo_nivel = st.selectbox("Nivel:", options=niveles_db,
                                                    index=niveles_db.index(p["nivel"]) if p["nivel"] in niveles_db else 0,
                                                    key=f"niv_{pid}")
                        nuevo_tema = st.selectbox("Tema:", options=temas_db,
                                                   index=temas_db.index(p["tema"]) if p["tema"] in temas_db else 0,
                                                   key=f"tem_{pid}")
                        cols = st.columns(2)
                        nuevas_opciones = []
                        for i, letra in enumerate(letras):
                            with cols[i % 2]:
                                nuevas_opciones.append(
                                    st.text_input(f"Opción {letra}:", value=textos[i] if i < len(textos) else "", key=f"op{letra}_{pid}")
                                )
                        nueva_correcta = st.radio("Respuesta correcta:", options=letras,
                                                   index=idx_correcta, horizontal=True, key=f"cor_{pid}")

                        col_g, col_e = st.columns(2)
                        with col_g:
                            if st.form_submit_button("💾 Guardar", use_container_width=True):
                                ok = actualizar_pregunta(
                                    pid, nuevo_nivel, nuevo_tema, nuevo_enunciado,
                                    nuevas_opciones[0], nuevas_opciones[1],
                                    nuevas_opciones[2], nuevas_opciones[3], nueva_correcta
                                )
                                if ok:
                                    st.success("✅ Pregunta actualizada.")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Error al guardar.")
                        with col_e:
                            if st.form_submit_button("🗑️ Eliminar", use_container_width=True):
                                st.session_state[f"_confirm_del_{pid}"] = True

                    # Confirmación de eliminación fuera del form
                    if st.session_state.get(f"_confirm_del_{pid}"):
                        st.warning("¿Seguro que quieres eliminar esta pregunta?")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("Sí, eliminar", key=f"yes_del_{pid}", use_container_width=True):
                                eliminar_pregunta(pid)
                                st.session_state.pop(f"_confirm_del_{pid}", None)
                                st.success("🗑️ Eliminada.")
                                time.sleep(0.5)
                                st.rerun()
                        with cc2:
                            if st.button("Cancelar", key=f"no_del_{pid}", use_container_width=True):
                                st.session_state.pop(f"_confirm_del_{pid}", None)
                                st.rerun()

    # ── Sub-tab: NUEVA PREGUNTA ───────────────────────────────────────────
    with sub_nueva:
        with st.form("nueva_pregunta_form", clear_on_submit=True):
            nuevo_enunciado = st.text_area("Enunciado de la pregunta:")
            nuevo_nivel = st.selectbox("Nivel:", options=niveles_db, key="nueva_niv")
            nuevo_tema = st.selectbox("Tema:", options=temas_db, key="nueva_tem")
            st.markdown("**Opciones de respuesta:**")
            cols = st.columns(2)
            with cols[0]:
                op_a = st.text_input("Opción A:")
                op_c = st.text_input("Opción C:")
            with cols[1]:
                op_b = st.text_input("Opción B:")
                op_d = st.text_input("Opción D:")
            correcta = st.radio("Respuesta correcta:", options=["A", "B", "C", "D"], horizontal=True, key="nueva_cor")

            if st.form_submit_button("✅ Crear Pregunta", use_container_width=True):
                if not nuevo_enunciado.strip():
                    st.error("El enunciado no puede estar vacío.")
                elif not all([op_a, op_b, op_c, op_d]):
                    st.error("Debes llenar las 4 opciones.")
                else:
                    ok = agregar_pregunta(nuevo_nivel, nuevo_tema, nuevo_enunciado,
                                          op_a, op_b, op_c, op_d, correcta)
                    if ok:
                        st.success("✅ Pregunta creada exitosamente.")
                    else:
                        st.error("Error al crear la pregunta. Verifica que el nivel y tema existan en la BD.")
