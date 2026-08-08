import streamlit as st
import os
import html as html_module
from config import nombre_legible, NO_INFO_PHRASES, SALUDOS

def render_resultados(resultado, col1):
    """
    Renderiza la síntesis de respuesta, citas y el reporte descargable en la columna principal
    """
    preg_guard = st.session_state.get("_ultima_pregunta", "")
    es_respuesta_sin_info = any(p in resultado["respuesta"].lower() for p in NO_INFO_PHRASES)
    es_saludo = any(s in preg_guard.strip().lower() for s in SALUDOS)
    
    with col1:
        st.markdown("<div style='margin-top:24px; font-weight:600; font-size:1.15rem; color:#ffffff; font-family:\"Outfit\",sans-serif;'>Síntesis Científica</div>", unsafe_allow_html=True)

        # Renderizar en la tarjeta de respuesta personalizada
        st.markdown(
            f'<div class="response-card">{html_module.escape(resultado["respuesta"])}</div>', 
            unsafe_allow_html=True
        )

        # Si el sistema detectó que no hay info, mostramos un badge sutil de "Sin alucinación"
        if es_respuesta_sin_info:
            st.markdown(
                '<div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); '
                'color: #10b981; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; margin-top: 8px; '
                'display: inline-block; font-weight: 500;">'
                'Respuesta validada: El sistema reconoció el límite de su conocimiento'
                '</div>',
                unsafe_allow_html=True
            )

        # Mostrar evidencias si existen fragmentos y no es un saludo corto
        mostrar_evidencia = len(resultado.get("fragmentos", [])) > 0 and not es_saludo
        if mostrar_evidencia:
            with st.expander("Ver Evidencia Documental (Citas y Referencias)"):
                for i, doc in enumerate(resultado["fragmentos"], 1):
                    file_name = os.path.basename(doc.metadata.get("source", "desconocido"))
                    nombre_revista = nombre_legible(file_name)
                    pagina = doc.metadata.get("page", "?")
                    st.markdown(f"**Fragmento {i} — {nombre_revista} (Pág. {pagina})**")
                    st.markdown(
                        f'<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); '
                        f'padding: 12px; border-radius: 8px; font-size: 0.9rem; color: #cbd5e1; margin-bottom: 12px; '
                        f'line-height: 1.5; white-space: pre-wrap;">'
                        f'{html_module.escape(doc.page_content)}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # Generar archivo descargable
        fuentes_txt = "\n".join([
            f"  [{i+1}] {nombre_legible(os.path.basename(d.metadata.get('source','?')))} — Pág. {d.metadata.get('page','?')}"
            for i, d in enumerate(resultado["fragmentos"])
        ])
        
        reporte = f"""=========================================
CONSULTA NEUROANATÓMICA — REPORTE RAG
=========================================
FECHA: 2026

PREGUNTA:
{resultado["pregunta"]}

RESPUESTA:
{resultado["respuesta"]}

FUENTES RECUPERADAS:
{fuentes_txt}

=========================================
Generado por: Consultor IA en Neuroanatomía
Fundación Universitaria Konrad Lorenz
Programa de Psicología · Laboratorio de Neurociencias
=========================================
"""
        st.markdown("<br>", unsafe_allow_html=True)
        col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
        with col_dl2:
            st.download_button(
                label="📥 Exportar Reporte Académico (TXT)",
                data=reporte,
                file_name="reporte_neuroanatomia.txt",
                mime="text/plain",
                use_container_width=True
            )
