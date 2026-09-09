import streamlit as st
from config import EJEMPLOS_CONSULTA

def render_consultor():
    """
    Renderiza el área del consultor RAG (caja de texto y preguntas de ejemplo).
    Retorna (pregunta, consultar_btn, col1) para poder meter los resultados dentro de la columna 1
    """
    col1, col2 = st.columns([2, 1], gap="large")

    with col2:
        st.markdown("### Ejemplos de consulta")
        st.caption("Haz clic en cualquier pregunta para cargarla directamente.")
        
        for i, (ej, tooltip) in enumerate(EJEMPLOS_CONSULTA):
            if st.button(f"{ej}", key=f"ej_{i}", use_container_width=True, help=tooltip):
                st.session_state["pregunta_ta"] = ej
                st.rerun()

    with col1:
        st.markdown("### Tu consulta científica")
        st.caption("Realiza preguntas específicas sobre neuroanatomía. El sistema responde exclusivamente con base en la literatura científica indexada y cita la fuente exacta.")
        pregunta = st.text_area(
            label="Consulta:",
            height=130,
            placeholder="Ej: ¿Cuáles son los núcleos del tronco del encéfalo descritos en el Lange y qué funciones cumplen?",
            key="pregunta_ta",
            label_visibility="collapsed",
        )
        consultar_btn = st.button("Analizar literatura científica", use_container_width=True)

    return pregunta, consultar_btn, col1
