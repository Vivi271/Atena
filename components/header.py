import streamlit as st

def render_header():
    st.markdown("""
    <div class="hero-header">
        <div class="logo-container" style="display:flex; align-items:center; justify-content:center; gap:16px; margin-bottom:12px;">
            <div style="font-size:1.2rem; font-weight:800; color:#5dade2; font-family:'Outfit',sans-serif; line-height:1.1; text-align:left;">
                <span style="color:#ffffff; white-space:nowrap;">KONRAD</span> <span style="color:#5dade2; white-space:nowrap;">LORENZ</span>
            </div>
            <div class="logo-divider" style="width:1px; height:26px; background:rgba(16, 185, 129, 0.3);"></div>
            <div class="logo-text-center" style="text-align:left; line-height:1.25;">
                <div style="font-size:0.68rem; color:#e2e8f0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Fundación Universitaria</div>
                <div style="font-size:0.65rem; color:#94a3b8; font-weight:500;">Acreditación Institucional de Alta Calidad</div>
            </div>
        </div>
        <h1>Consultor IA en Neuroanatomía</h1>
        <p>Asistente RAG fundamentado exclusivamente en literatura científica</p>
        <div class="kl-subtitle">Programa de Psicología · Laboratorio de Neurociencias</div>
    </div>
    """, unsafe_allow_html=True)
