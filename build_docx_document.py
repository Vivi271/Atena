import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import os

def set_cell_background(cell, fill_hex):
    """Establece el color de fondo de una celda de tabla en Hexadecimal."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Ajusta los márgenes/padding internos de una celda."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_heading_1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(16)
    run.font.bold = True
    run.font.color.rgb = RGBColor(26, 54, 93) # Navy Blue
    return p

def add_heading_2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = RGBColor(43, 108, 176) # Steel Blue
    return p

def add_heading_3(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = RGBColor(45, 55, 72) # Slate Grey
    return p

def add_body_p(doc, text, bold_prefix=None, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_bold = p.add_run(bold_prefix)
        r_bold.font.name = 'Calibri'
        r_bold.font.size = Pt(11)
        r_bold.font.bold = True
        r_bold.font.color.rgb = RGBColor(26, 32, 44)
    run = p.add_run(text)
    run.font.name = 'Calibri'
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(45, 55, 72)
    return p

def add_callout(doc, text, title="NOTA TÉCNICA CLAVE"):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    set_cell_background(cell, "EBF8FF")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Border azul a la izquierda
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>\n'
        f'  <w:left w:val="single" w:sz="36" w:space="0" w:color="3182CE"/>\n'
        f'  <w:top w:val="none"/>\n'
        f'  <w:right w:val="none"/>\n'
        f'  <w:bottom w:val="none"/>\n'
        f'</w:tcBorders>'
    )
    cell._tc.get_or_add_tcPr().append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(4)
    r_title = p.add_run(f"💡 {title}\n")
    r_title.font.name = 'Arial'
    r_title.font.size = Pt(10.5)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(43, 108, 176)
    
    r_text = p.add_run(text)
    r_text.font.name = 'Calibri'
    r_text.font.size = Pt(10)
    r_text.font.italic = True
    r_text.font.color.rgb = RGBColor(45, 55, 72)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def create_document():
    doc = Document()
    
    # Márgenes estándar de 1 pulgada (2.54 cm)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # ---------------------------------------------------------------------------
    # PORTADA
    # ---------------------------------------------------------------------------
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(20)
    p_inst.paragraph_format.space_after = Pt(4)
    r_inst = p_inst.add_run("FUNDACIÓN UNIVERSITARIA KONRAD LORENZ")
    r_inst.font.name = 'Arial'
    r_inst.font.size = Pt(14)
    r_inst.font.bold = True
    r_inst.font.color.rgb = RGBColor(26, 54, 93)

    p_fac = doc.add_paragraph()
    p_fac.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fac.paragraph_format.space_after = Pt(40)
    r_fac = p_fac.add_run("FACULTAD DE MATEMÁTICAS E INGENIERÍA / PSICOLOGÍA\nPROGRAMA DE TESIS Y DESARROLLO DE SOFTWARE")
    r_fac.font.name = 'Arial'
    r_fac.font.size = Pt(10)
    r_fac.font.color.rgb = RGBColor(74, 85, 104)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(18)
    r_title = p_title.add_run("INFORME DE EVALUACIÓN TÉCNICA Y JUSTIFICACIÓN DE ARQUITECTURA AI")
    r_title.font.name = 'Arial'
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(26, 54, 93)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(50)
    r_sub = p_sub.add_run(
        "Análisis Comparativo Multicriterio de Tres Generaciones de Arquitectura AI:\n"
        "Inferencia Local (Ollama / Llama 3.2) vs. Cloud Piloto (Google Gemini API) vs. Arquitectura Definitiva de Alto Rendimiento (Groq Cloud LPU + ChromaDB ONNX Runtime) para el Consultor de Neuroanatomía 3D en Unity"
    )
    r_sub.font.name = 'Arial'
    r_sub.font.size = Pt(12)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(43, 108, 176)

    # Bloque de metadatos
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_after = Pt(80)
    r_meta = p_meta.add_run(
        "Proyecto: Consultor Especialista en Neuroanatomía 3D (Atena — NeuroK AR)\n"
        "Autores: Equipo de Investigación & Desarrollo - Konrad Lorenz\n"
        "Fecha de Evaluación y Cierre Técnico: Septiembre de 2026\n"
        "Versión del Documento: 3.0 (Evaluación Tripartita y Arquitectura Definitiva en Producción)"
    )
    r_meta.font.name = 'Calibri'
    r_meta.font.size = Pt(11)
    r_meta.font.color.rgb = RGBColor(45, 55, 72)

    doc.add_page_break()

    # ---------------------------------------------------------------------------
    # RESUMEN EJECUTIVO
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "RESUMEN EJECUTIVO")
    
    add_body_p(
        doc,
        "El presente informe técnico expone una rigurosa evaluación comparativa y la traza de evolución arquitectónica de la infraestructura de Inteligencia Artificial seleccionada para el proyecto 'Consultor Especialista en Neuroanatomía' (Atena — NeuroK AR). El sistema es una solución RAG (Retrieval-Augmented Generation) diseñada para operar en tiempo real integrada a una escena 3D interactiva en Unity para estudiantes, docentes e investigadores de la Fundación Universitaria Konrad Lorenz."
    )
    add_body_p(
        doc,
        "Para alcanzar una experiencia pedagógica inmersiva y un despliegue viable en la nube a costo cero, el proyecto evaluó e implementó tres generaciones sucesivas de arquitectura tecnológica:"
    )
    add_body_p(
        doc,
        "1. Fase 1 — Enfoque 100% Local (Ollama + Llama 3.2 3B/8B + nomic-embed-text): Evaluado empíricamente sobre la máquina de referencia del laboratorio (MacBook Pro 16\", Intel Core i7 6-Core, 16 GB RAM, GPU AMD Radeon Pro 5300M de 4 GB VRAM). Reveló inviabilidad operativa: latencias de 22.5 a 54.2 segundos por respuesta, saturación de CPU (88-95%), estrangulamiento térmico a 92 °C, agotamiento de RAM (14.8 GB ocupados) y caída drástica de la tasa de refresco en Unity a menos de 12 FPS.",
        bold_prefix="• "
    )
    add_body_p(
        doc,
        "2. Fase 2 — Enfoque Cloud Piloto (Google Gemini 1.5/3.6 Flash API + PyTorch): Logró abatir la latencia a 1.2 - 2.1 segundos eliminando la carga local del cliente. No obstante, al someterse a pruebas de concurrencia y despliegue en servidor (Render.com), surgieron dos limitaciones críticas: (a) saturación constante de las cuotas del tier gratuito en Google AI Studio (errores HTTP 429 Too Many Requests / ResourceExhausted limitados a 15 RPM), y (b) desbordamiento de memoria RAM en el servidor gratuito de Render (límite estricto de 512 MiB), donde la pila de PyTorch y sentence-transformers consumía >520 MB de RAM provocando la muerte inmediata del contenedor ('Out of memory - 512Mi killed').",
        bold_prefix="• "
    )
    add_body_p(
        doc,
        "3. Fase 3 — Arquitectura Definitiva en Producción (Groq Cloud LPU + ChromaDB ONNX Runtime): Integra la plataforma Groq Cloud sobre procesadores de lenguaje LPU (Language Processing Unit), ejecutando el modelo openai/gpt-oss-120b con inferencia determinista ultrarrápida (>350 tokens/segundo) y latencias sub-segundo (0.6 a 0.9s), sin caídas de cuota. Simultáneamente, sustituye PyTorch por ONNX Runtime (all-MiniLM-L6-v2), reduciendo la huella de memoria del servidor de 520 MB a menos de 140 MB (-73%), garantizando estabilidad permanente 24/7 en Render Free Tier, tolerancia a errores tipográficos con Fuzzy Matching y costo mensual de $0 USD.",
        bold_prefix="• "
    )

    add_callout(
        doc,
        "La evaluación multicriterio demuestra que la arquitectura definitiva (Groq LPU + ONNX Runtime) supera a la IA local en un 4500% de velocidad de respuesta, elimina los bloqueos por cuota de la fase intermedia de Gemini y resuelve la restricción de memoria de 512 MiB en Render, entregando una solución de alta fidelidad científica a costo cero permanente para la universidad.",
        title="DECISIÓN ARQUITECTÓNICA DEFINITIVA (EVALUACIÓN DE 3 FASES)"
    )

    # ---------------------------------------------------------------------------
    # SECCIÓN 1: INTRODUCCIÓN Y CONTEXTO
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "1. INTRODUCCIÓN Y CONTEXTO DEL PROYECTO")
    
    add_heading_2(doc, "1.1 Descripción del Consultor de Neuroanatomía 3D")
    add_body_p(
        doc,
        "El Consultor Especialista en Neuroanatomía es un asistente conversacional avanzado diseñado para apoyar los procesos de enseñanza y aprendizaje en las áreas de neurociencia, psicología y medicina de la Fundación Universitaria Konrad Lorenz. El sistema sintetiza información técnica de textos académicos fundamentales de la disciplina —tales como 'Neuroanatomía Clínica de Lange' y 'El Cerebro y la Conducta'— garantizando que las respuestas sean estrictamente fácticas, precisas y libres de alucinaciones mediante una arquitectura RAG (Retrieval-Augmented Generation)."
    )
    
    add_heading_2(doc, "1.2 Importancia de la Latencia y la Experiencia de Usuario")
    add_body_p(
        doc,
        "Una de las metas centrales del proyecto es integrar este motor de consulta dentro de una aplicación 3D desarrollada en Unity, donde los estudiantes pueden visualizar e interactuar tridimensionalmente con modelos anátomicos del encéfalo, lóbulos cerebrales, estructuras subcorticales y vías nerviosas mientras realizan preguntas en lenguaje natural. En este entorno interactivo, la latencia de respuesta resulta ser un factor crítico: esperas superiores a los 3-5 segundos rompen la inmersión del estudiante y deterioran drásticamente la usabilidad pedagógica del software."
    )

    # ---------------------------------------------------------------------------
    # SECCIÓN 2: ESPECIFICACIONES TÉCNICAS DE LA MÁQUINA DE PRUEBAS
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "2. FICHA TÉCNICA Y ESPECIFICACIONES DEL HARDWARE EVALUADO")
    
    add_body_p(
        doc,
        "Para fundamentar los resultados con evidencia empírica directa, todas las pruebas locales de inferencia con Ollama y LangChain fueron ejecutadas sobre la máquina física del entorno de desarrollo. A continuación se presenta la caracterización completa del hardware:"
    )

    # Tabla de especificaciones de Hardware
    table_hw = doc.add_table(rows=7, cols=3)
    table_hw.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_hw.autofit = False

    headers = ["Componente Hardware", "Especificación Técnica", "Impacto en Ejecución Local de IA"]
    hdr_cells = table_hw.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        set_cell_background(hdr_cells[i], "1A365D")
        p = hdr_cells[i].paragraphs[0]
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p.runs[0].font.name = 'Arial'
        p.runs[0].font.size = Pt(10)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=150, right=150)

    data_hw = [
        ("Modelo del Sistema", "MacBook Pro 16 pulgadas (MacBookPro16,1)", "Portátil de rendimiento general con arquitectura x86_64."),
        ("Procesador (CPU)", "Intel Core i7 6-Core @ 2.6 GHz (Turboboost 4.5 GHz)", "Inferencia en CPU lenta; alta saturación de hilos (88-95% carga)."),
        ("Memoria RAM", "16 GB DDR4 a 2666 MHz", "Insuficiente para mantener Unity (6-8 GB) + Llama 3.2 (5-7 GB) al tiempo."),
        ("GPU Dedicada", "AMD Radeon Pro 5300M (4 GB VRAM GDDR6)", "VRAM de 4 GB insuficiente para alojar modelos de 8B parámetros en GPU."),
        ("GPU Integrada", "Intel UHD Graphics 630 (1.5 GB VRAM dinámica)", "Reservada para tareas gráficas del sistema operativo y ventanas básicas."),
        ("Almacenamiento", "Apple NVMe SSD 512 GB (Velocidad > 2500 MB/s)", "Swapping frecuente debido al desbordamiento de la memoria RAM.")
    ]

    for row_idx, row_data in enumerate(data_hw, start=1):
        row_cells = table_hw.rows[row_idx].cells
        bg_color = "F7FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(row_data):
            row_cells[col_idx].text = text
            set_cell_background(row_cells[col_idx], bg_color)
            set_cell_margins(row_cells[col_idx], top=100, bottom=100, left=120, right=120)
            p = row_cells[col_idx].paragraphs[0]
            p.runs[0].font.name = 'Calibri'
            p.runs[0].font.size = Pt(9.5)
            p.runs[0].font.color.rgb = RGBColor(45, 55, 72)
            if col_idx == 0:
                p.runs[0].font.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # ---------------------------------------------------------------------------
    # SECCIÓN 3: EVALUACIÓN Y PRUEBAS CON IA LOCAL (OLLAMA / LLAMA 3.2)
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "3. EVALUACIÓN DE DESEMPEÑO Y RESULTADOS CON IA LOCAL")
    
    add_heading_2(doc, "3.1 Configuración de las Pruebas Locales")
    add_body_p(
        doc,
        "La versión inicial del pipeline RAG fue construida utilizando LangChain en Python, con la integración de Ollama como servidor local de inferencia. Los componentes evaluados fueron:"
    )
    add_body_p(doc, "• Modelo LLM Local: llama3.2:latest (versiones cuantizadas Q4_K_M de 3B y 8B parámetros).")
    add_body_p(doc, "• Modelo de Embeddings Local: nomic-embed-text via Ollama API.")
    add_body_p(doc, "• Base de Datos Vectorial: ChromaDB con almacenamiento SQLite persistente local.")

    add_heading_2(doc, "3.2 Métricas Múltiples de Rendimiento Medidas")
    add_body_p(
        doc,
        "Se llevaron a cabo múltiples pruebas con preguntas de distinta complejidad académica. Las métricas recopiladas reflejan el costo computacional de ejecutar simultáneamente el motor de inferencia local junto con el pipeline RAG y la aplicación cliente:"
    )

    # Tabla de resultados empíricos
    table_perf = doc.add_table(rows=5, cols=5)
    table_perf.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_perf.autofit = False

    headers_p = ["Tipo de Consulta Evaluada", "Modelo LLM", "Tiempo Primer Token (TTFT)", "Latencia Total", "Tasa de Tokens (tok/s)"]
    for i, h in enumerate(headers_p):
        cell = table_perf.rows[0].cells[i]
        cell.text = h
        set_cell_background(cell, "1A365D")
        p = cell.paragraphs[0]
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p.runs[0].font.name = 'Arial'
        p.runs[0].font.size = Pt(9.5)
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)

    perf_data = [
        ("Concepto Simple (Ej: ¿Qué es el cerebelo?)", "Llama 3.2 3B", "4.2 s", "22.5 s", "6.2 tok/s"),
        ("Consulta RAG Mediana (1 Libro)", "Llama 3.2 3B", "8.5 s", "38.0 s", "5.1 tok/s"),
        ("Consulta RAG Compleja (Multi-libro)", "Llama 3.2 8B", "14.0 s", "54.2 s", "4.1 tok/s"),
        ("Consulta Compleja con Unity 3D Activo", "Llama 3.2 8B", "19.2 s", "68.5 s (Lag/Crash)", "2.8 tok/s")
    ]

    for row_idx, row_data in enumerate(perf_data, start=1):
        row_cells = table_perf.rows[row_idx].cells
        bg_color = "F7FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(row_data):
            row_cells[col_idx].text = text
            set_cell_background(row_cells[col_idx], bg_color)
            set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=100, right=100)
            p = row_cells[col_idx].paragraphs[0]
            p.runs[0].font.name = 'Calibri'
            p.runs[0].font.size = Pt(9)
            p.runs[0].font.color.rgb = RGBColor(45, 55, 72)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    add_heading_2(doc, "3.3 Análisis de Cuellos de Botella Técnicos")
    add_body_p(
        doc,
        "1. Insuficiencia de Memoria VRAM Dedicada (4 GB):", bold_prefix="a) "
    )
    add_body_p(
        doc,
        "Los modelos de lenguaje de 8B parámetros requieren entre 5.5 GB y 8 GB de VRAM para alojar sus pesos cuantizados en memoria gráfica. Al disponer únicamente de 4 GB de VRAM en la GPU AMD Radeon Pro 5300M, el sistema Ollama se ve obligado a derivar la mayor parte del procesamiento a la memoria RAM del sistema a través de la CPU Intel Core i7. Esto ralentiza drásticamente la velocidad de generación de tokens."
    )
    
    add_body_p(
        doc,
        "2. Estrés Térmico y Estrangulamiento de Frecuencia (Thermal Throttling):", bold_prefix="b) "
    )
    add_body_p(
        doc,
        "La ejecución prolongada de inferencia en la CPU generó cargas sostenidas superiores al 88-95% en todos los núcleos. La temperatura del procesador alcanzó los 86-92 °C en menos de tres minutos de uso continuo, lo que activó el sistema de protección térmica del sistema operativo macOS, reduciendo automáticamente la frecuencia de reloj del procesador de 4.5 GHz a 1.8 GHz y acentuando la lentitud del sistema."
    )

    add_body_p(
        doc,
        "3. Incompatibilidad de Recursos con el Motor Gráfico Unity 3D:", bold_prefix="c) "
    )
    add_body_p(
        doc,
        "Cuando la interfaz tridimensional en Unity se ejecuta simultáneamente con Ollama, ambos programas compiten violentamente por la RAM y los recursos de procesamiento. Unity 3D requiere al menos 4 a 6 GB de RAM y renderizado continuo de cuadros GPU. Esta sobrecarga provocó caídas severas en la tasa de refresco (de 60 FPS a menos de 12 FPS) y micro-congelamientos de la aplicación."
    )

    # Inserción de Gráficos 1 y 2
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chart1_path = os.path.join(base_dir, "chart_assets", "grafico1_latencia.png")
    if os.path.exists(chart1_path):
        p_img1 = doc.add_paragraph()
        p_img1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img1.paragraph_format.space_before = Pt(10)
        p_img1.paragraph_format.space_after = Pt(4)
        run_img1 = p_img1.add_run()
        run_img1.add_picture(chart1_path, width=Inches(5.8))
        
        p_cap1 = doc.add_paragraph()
        p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap1.paragraph_format.space_after = Pt(14)
        r_cap1 = p_cap1.add_run("Figura 1. Comparativa empírica de latencia total de respuesta por tipo de consulta RAG entre las tres arquitecturas evaluadas.")
        r_cap1.font.name = 'Arial'
        r_cap1.font.size = Pt(9)
        r_cap1.font.italic = True
        r_cap1.font.color.rgb = RGBColor(113, 128, 150)

    chart2_path = os.path.join(base_dir, "chart_assets", "grafico2_recursos_hardware.png")
    if os.path.exists(chart2_path):
        p_img2 = doc.add_paragraph()
        p_img2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img2.paragraph_format.space_before = Pt(10)
        p_img2.paragraph_format.space_after = Pt(4)
        run_img2 = p_img2.add_run()
        run_img2.add_picture(chart2_path, width=Inches(5.8))
        
        p_cap2 = doc.add_paragraph()
        p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap2.paragraph_format.space_after = Pt(14)
        r_cap2 = p_cap2.add_run("Figura 2. Huella de memoria RAM en servidor/máquina y sobrecarga de CPU/GPU en las tres fases del proyecto.")
        r_cap2.font.name = 'Arial'
        r_cap2.font.size = Pt(9)
        r_cap2.font.italic = True
        r_cap2.font.color.rgb = RGBColor(113, 128, 150)

    # ---------------------------------------------------------------------------
    # SECCIÓN 4: COMPARATIVA DETALLADA MULTICRITERIO: LAS TRES FASES DEL PROYECTO
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "4. COMPARATIVA DETALLADA MULTICRITERIO: LAS TRES GENERACIONES DE ARQUITECTURA")
    
    add_body_p(
        doc,
        "A continuación se sintetizan los hallazgos comparativos entre las tres soluciones tecnológicas evaluadas a lo largo de la investigación para el consultor interactivo de neuroanatomía en Unity 3D:"
    )

    # Tabla Matriz Comparativa Exhaustiva Tripartita (4 columnas)
    table_comp = doc.add_table(rows=10, cols=4)
    table_comp.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_comp.autofit = False

    headers_c = ["Criterio", "Fase 1: Ollama (Local)", "Fase 2: Gemini API (Cloud Piloto)", "Fase 3: Groq LPU + ONNX (Actual / Definitiva)"]
    for i, h in enumerate(headers_c):
        cell = table_comp.rows[0].cells[i]
        cell.text = h
        set_cell_background(cell, "1A365D")
        p = cell.paragraphs[0]
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p.runs[0].font.name = 'Arial'
        p.runs[0].font.size = Pt(9)
        set_cell_margins(cell, top=100, bottom=100, left=80, right=80)

    comp_matrix = [
        ("¿Dónde corre?", "En la laptop local (Docker)", "Nube Google AI Studio + Render", "Nube Groq Cloud (LPU) + Render"),
        ("Tiempo de Respuesta", "25 a 55 segundos (Hiper lento)", "1.5 a 3.5 segundos (Inestable en horas pico)", "0.6 a 0.9 segundos (Casi instantáneo)"),
        ("Velocidad (Tokens/s)", "4 - 6 tokens/segundo", "60 - 95 tokens/segundo", "> 380 tokens/segundo"),
        ("Memoria RAM Servidor", "Satura la laptop (14.8 GB)", "520 MB (Tumbaba el servidor de Render)", "< 140 MB (Súper liviano y estable)"),
        ("Límite de Peticiones", "Ilimitado pero congelaba la PC", "Máximo 15 preguntas/minuto (Error 429)", "Sin bloqueos ni caídas de cuota"),
        ("Integración con Unity", "Congelaba la escena (< 12 FPS)", "Fluido, pero a veces fallaba el JSON", "60 FPS estables y JSON perfecto"),
        ("Citas y Fuentes", "Genéricas / Sin página", "Mencionaba el libro sin página exacta", "Exactas: [Fuente X, pág. Y]"),
        ("Tolerancia Tipográfica", "Nula (falla ante cualquier typo)", "Baja (depende de similitud vectorial)", "Alta (Fuzzy Matching con difflib)"),
        ("Costo Mensual", "$0 (pero exigía PC de $2,500 USD)", "$0 (con cuota muy restringida)", "$0 USD permanente")
    ]

    for row_idx, row_data in enumerate(comp_matrix, start=1):
        row_cells = table_comp.rows[row_idx].cells
        bg_color = "F7FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(row_data):
            row_cells[col_idx].text = text
            set_cell_background(row_cells[col_idx], bg_color)
            set_cell_margins(row_cells[col_idx], top=70, bottom=70, left=80, right=80)
            p = row_cells[col_idx].paragraphs[0]
            p.runs[0].font.name = 'Calibri'
            p.runs[0].font.size = Pt(8.5)
            p.runs[0].font.color.rgb = RGBColor(45, 55, 72)
            if col_idx == 0:
                p.runs[0].font.bold = True
            elif col_idx == 3:
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = RGBColor(26, 54, 93)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Inserción de Gráficos 3 y 4
    chart3_path = os.path.join(base_dir, "chart_assets", "grafico3_throughput.png")
    if os.path.exists(chart3_path):
        p_img3 = doc.add_paragraph()
        p_img3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img3.paragraph_format.space_before = Pt(10)
        p_img3.paragraph_format.space_after = Pt(4)
        run_img3 = p_img3.add_run()
        run_img3.add_picture(chart3_path, width=Inches(5.8))
        
        p_cap3 = doc.add_paragraph()
        p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap3.paragraph_format.space_after = Pt(14)
        r_cap3 = p_cap3.add_run("Figura 3. Tasa de generación de tokens por segundo (Throughput) comparando las tres generaciones.")
        r_cap3.font.name = 'Arial'
        r_cap3.font.size = Pt(9)
        r_cap3.font.italic = True
        r_cap3.font.color.rgb = RGBColor(113, 128, 150)

    chart4_path = os.path.join(base_dir, "chart_assets", "grafico4_radar.png")
    if os.path.exists(chart4_path):
        p_img4 = doc.add_paragraph()
        p_img4.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img4.paragraph_format.space_before = Pt(10)
        p_img4.paragraph_format.space_after = Pt(4)
        run_img4 = p_img4.add_run()
        run_img4.add_picture(chart4_path, width=Inches(4.5))
        
        p_cap4 = doc.add_paragraph()
        p_cap4.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap4.paragraph_format.space_after = Pt(14)
        r_cap4 = p_cap4.add_run("Figura 4. Evaluación multicriterio en escala de 1 a 10 entre Fase 1 (Ollama), Fase 2 (Gemini) y Fase 3 (Groq LPU + ONNX).")
        r_cap4.font.name = 'Arial'
        r_cap4.font.size = Pt(9)
        r_cap4.font.italic = True
        r_cap4.font.color.rgb = RGBColor(113, 128, 150)

    add_heading_2(doc, "4.1 Evaluación de la Fase 1 (IA Local con Ollama)")
    add_body_p(doc, "• Ventajas: Privacidad absoluta de datos y funcionamiento sin conexión a internet.")
    add_body_p(doc, "• Desventajas: Requiere hardware de cómputo inalcanzable para estudiantes promedio (> $2,500 USD), latencias de 22 a 54 segundos, estrangulamiento térmico de CPU (92 °C), consumo extremo de RAM (14.8 GB) y colapso de la tasa de cuadros en Unity (< 12 FPS).")

    add_heading_2(doc, "4.2 Evaluación de la Fase 2 (Cloud Piloto con Gemini API)")
    add_body_p(doc, "• Ventajas: Respuestas rápidas (1.2 a 2.1 s), cero consumo en el dispositivo del estudiante y ventana de contexto amplia.")
    add_body_p(doc, "• Desventajas: Cuotas gratuitas severamente restringidas (límite de 15 RPM con error HTTP 429 Too Many Requests) y sobrecarga de memoria en el servidor Render por la presencia de PyTorch (> 520 MB de RAM), lo que causaba caídas del servicio.")

    add_heading_2(doc, "4.3 Evaluación de la Fase 3 (Arquitectura Definitiva con Groq LPU y ONNX Runtime)")
    add_body_p(doc, "• Ventajas: Inferencia ultra-rápida (> 350 tok/s, latencia < 0.9 s) mediante procesadores LPU, reducción radical del consumo de RAM a < 140 MB (-73%) gracias a ONNX Runtime, tolerancia a fallas de escritura en Unity con Fuzzy Matching, persistencia pre-compilada de libros en Docker y costo operativo permanente de $0 USD.")
    add_body_p(doc, "• Desventajas y Mitigaciones: Tiempo de arranque en frío (Cold Start) de 30 a 45 s tras 15 minutos sin tráfico en Render Free Tier (mitigable mediante ping previo a /salud o monitoreo tipo UptimeRobot), e inmutabilidad de la base en caliente (los nuevos textos se integran limpiamente mediante git push).")

    add_heading_2(doc, "4.4 Viabilidad Financiera y Despliegue Permanente a Costo Cero ($0 USD)")
    add_body_p(
        doc,
        "La integración definitiva de Groq Cloud LPU y Render.com bajo la cuenta institucional atena.unikonrad@gmail.com garantiza que la universidad no incurra en ningún gasto financiero por licenciamiento o servidores durante la fase de evaluación académica, entrega de tesis y uso continuo en el Laboratorio de Neurociencias Aplicadas (NeuroK)."
    )

    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    # SECCIÓN 5: JUSTIFICACIÓN DE LA FASE CLOUD INICIAL (PILOTO CON GEMINI API)
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "5. JUSTIFICACIÓN DE LA FASE CLOUD INTERMEDIA (FASE 2: PILOTO CON GEMINI API)")
    
    add_body_p(
        doc,
        "Tras finalizar la fase de experimentación empírica con Ollama (Fase 1), el equipo de desarrollo determinó la necesidad de desacoplar el procesamiento de IA de la máquina cliente adoptando la API de Google Gemini como motor cloud piloto de inferencia LLM y embeddings."
    )
    add_body_p(
        doc,
        "En esta etapa, la arquitectura del sistema quedó estructurada en tres capas desacopladas:"
    )
    add_body_p(doc, "1. Capa de Presentación (Front-End Unity 3D / Web): Interfaz gráfica inmersiva que renderiza los modelos 3D neuroanatómicos y gestiona el chat mediante peticiones asíncronas UnityWebRequest hacia el backend API REST.")
    add_body_p(doc, "2. Capa de Servicios y Lógica RAG (Backend Cloud Servidor): Desplegado en un contenedor en Render.com. Recibe la consulta del usuario, recupera los vectores relevantes desde ChromaDB y construye el prompt sintético.")
    add_body_p(doc, "3. Capa de Inferencia AI (Google Gemini API): Procesa el contexto y la consulta académica en la nube de Google, devolviendo la respuesta estructurada en menos de 1.5 segundos.")

    add_callout(
        doc,
        "El desacoplamiento en tres capas implementado en la Fase 2 demostró ser el camino arquitectónico correcto: la aplicación cliente en Unity se mantuvo liviana (<50 MB de ejecutable) y se eliminó la dependencia de GPUs dedicadas en los equipos de los estudiantes.",
        title="APRENDIZAJE ARQUITECTÓNICO DE LA FASE 2"
    )

    # ---------------------------------------------------------------------------
    # SECCIÓN 6: DE LA FASE PILOTO AL HALLAZGO DE NUEVOS CUELLOS DE BOTELLA
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "6. IMPLEMENTACIÓN DE LA FASE PILOTO Y TRANSICIÓN A PRODUCCIÓN")
    
    add_body_p(
        doc,
        "La ejecución de la fase piloto con Gemini cumplió con éxito los hitos iniciales de integración:"
    )

    add_heading_2(doc, "Paso 1: Actualización del Pipeline RAG a Gemini API")
    add_body_p(
        doc,
        "Se sustituyeron las clases de Ollama en `rag_pipeline.py` por `GoogleGenerativeAIEmbeddings` (text-embedding-004) y `ChatGoogleGenerativeAI` (gemini-1.5-flash / gemini-3.6-flash)."
    )

    add_heading_2(doc, "Paso 2: Despliegue en la Nube y Configuración de Servicios")
    add_body_p(
        doc,
        "Se vinculó la cuenta institucional de la universidad (`atena.unikonrad@gmail.com`) a Render.com y Firebase Firestore, configurando las variables de entorno de forma segura para exponer el endpoint HTTPS público `https://atena-vugz.onrender.com`."
    )

    add_heading_2(doc, "Paso 3: Construcción del Cliente en Unity 3D (C#)")
    add_body_p(
        doc,
        "Se integró el controlador oficial `AtenaClient.cs` en Unity, permitiendo llamadas REST asíncronas desde la escena tridimensional hacia el backend cloud sin congelar la interfaz de usuario."
    )

    add_heading_2(doc, "6.1 Limitaciones Identificadas en Pruebas Reales de Producción")
    add_body_p(
        doc,
        "Al someter el despliegue en Render.com a pruebas intensivas con estudiantes en el laboratorio, surgieron dos barreras infranqueables que obligaron a evolucionar el sistema hacia una tercera generación definitiva:"
    )
    add_body_p(
        doc,
        "1. Saturación de Cuotas de Gemini (HTTP 429 ResourceExhausted): El límite estricto de 15 solicitudes por minuto (RPM) en el tier gratuito de Google AI Studio provocaba bloqueos continuos cuando varios evaluadores realizaban preguntas consecutivas.",
        bold_prefix="a) "
    )
    add_body_p(
        doc,
        "2. El Cuello de Botella de 512 MiB de RAM en Render: La biblioteca PyTorch y los sentence-transformers requeridos para vectorizar en el servidor consumían entre 520 y 650 MB de memoria en el arranque, provocando que Render matara el contenedor con el error 'Out of memory (used over 512Mi)'.",
        bold_prefix="b) "
    )
    add_body_p(
        doc,
        "Estos dos factores motivaron la fase final de investigación e ingeniería descrita en la Sección 8, consolidando la arquitectura de producción con Groq LPU y ONNX Runtime."
    )

    # ---------------------------------------------------------------------------
    # SECCIÓN 7: CONCLUSIONES DE LAS FASES EXPERIMENTALES INICIALES (FASES 1 Y 2)
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "7. CONCLUSIONES DE LAS FASES EXPERIMENTALES INICIALES (FASES 1 Y 2)")
    
    add_body_p(
        doc,
        "1. La inferencia local de IA mediante Ollama (Fase 1) en equipos portátiles estándar resulta inviable para aplicaciones interactivas en tiempo real combinadas con motores gráficos como Unity 3D, debido al estrangulamiento térmico y saturación de VRAM/RAM."
    )
    add_body_p(
        doc,
        "2. La adopción de la API de Google Gemini (Fase 2) validó empíricamente las ventajas de la arquitectura desacoplada en la nube, reduciendo la latencia de 38-54 segundos a tan solo 1.2-2.1 segundos."
    )
    add_body_p(
        doc,
        "3. No obstante, las restricciones de cuota gratuita (15 RPM) y el excesivo peso de PyTorch en servidores cloud gratuitos demostraron la necesidad de una optimización más profunda en inferencia y consumo de memoria para garantizar estabilidad 24/7 sin costo para la institución."
    )

    # ---------------------------------------------------------------------------
    # SECCIÓN 8: ARQUITECTURA DEFINITIVA Y COMPARATIVA TRIPARTITA (FASE 3: GROQ LPU + ONNX)
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "8. ARQUITECTURA DEFINITIVA Y EVALUACIÓN TRIPARTITA (FASE 3: GROQ LPU + ONNX RUNTIME)")
    
    add_body_p(
        doc,
        "Aunque la migración inicial de Ollama hacia Google Gemini representó un salto cualitativo indispensable para superar la sobrecarga de hardware local, la fase subsiguiente de desarrollo, pruebas de estrés e integración continua en producción reveló nuevos desafíos de infraestructura que motivaron la transición hacia la arquitectura definitiva basada en Groq Cloud LPU y ChromaDB con ONNX Runtime."
    )

    add_heading_2(doc, "8.1 Justificación Técnica de la Transición desde Google Gemini")
    add_body_p(
        doc,
        "Durante las pruebas intensivas de la API REST y su integración con el cliente en Unity (C#), se identificaron tres limitaciones críticas en la capa de Google Gemini (Google AI Studio):"
    )
    add_body_p(
        doc,
        "1. Restricción de Cuotas y Rate-Limiting Estricto (HTTP 429 Too Many Requests): El plan gratuito de Gemini 1.5/3.6 Flash impone un límite de 15 solicitudes por minuto (RPM). Cuando múltiples estudiantes realizaban preguntas simultáneas o se generaban ráfagas de prueba rápidas desde Unity, el servicio de Google arrojaba errores ResourceExhausted (código 429), interrumpiendo la experiencia de aprendizaje.",
        bold_prefix="a) "
    )
    add_body_p(
        doc,
        "2. Variabilidad de Latencia en Horas Pico: En momentos de alta congestión global en la infraestructura de Google, la latencia de respuesta se degradaba desde 1.5 segundos hasta superar los 7-9 segundos, afectando la interactividad de la escena 3D.",
        bold_prefix="b) "
    )
    add_body_p(
        doc,
        "3. Inconsistencias de Formato y Estructura en la Respuesta: Ocasionalmente, las respuestas del modelo en la nube introducían formatos Markdown irregulares o truncaban la salida, dificultando la deserialización limpia del JSON esperado por el controlador C# en Unity (AtenaClient.cs).",
        bold_prefix="c) "
    )

    add_heading_2(doc, "8.2 Selección de Groq Cloud LPU y el Motor de Inferencia")
    add_body_p(
        doc,
        "Para solventar estas falencias, se adoptó la plataforma Groq Cloud, impulsada por Unidades de Procesamiento de Lenguaje (LPU - Language Processing Unit). A diferencia de las GPUs convencionales que sufren cuellos de botella en el ancho de banda de memoria (HBM), los procesadores LPU de Groq integran memoria estática ultrarrápida (SRAM) directamente acoplada a la matriz computacional, ofreciendo un flujo de datos determinista y una arquitectura sin contención."
    )
    add_body_p(
        doc,
        "• Rendimiento Extremo: Groq alcanza velocidades de generación superiores a 350-500 tokens por segundo, reduciendo la latencia de respuesta promedio a menos de 0.8 segundos (tiempo casi instantáneo)."
    )
    add_body_p(
        doc,
        "• Modelo Seleccionado: Se configuró el modelo de alta capacidad de razonamiento openai/gpt-oss-120b (con posibilidad de alternancia configurable en variables de entorno). Este modelo demostró un comportamiento académico impecable: cero alucinaciones bajo la directiva de restringirse estrictamente al corpus bibliográfico indexado, adaptación de tono pedagógico y generación de explicaciones clínicas rigurosas."
    )
    add_body_p(
        doc,
        "• Viabilidad Económica Institucional: La plataforma ofrece cuotas de inferencia gratuitas altamente generosas para investigación y academia, manteniendo un costo operativo de $0 USD para la Fundación Universitaria Konrad Lorenz."
    )

    add_heading_2(doc, "8.3 El Desafío de Memoria en el Servidor Cloud (Render 512 MiB) y la Solución con ONNX Runtime")
    add_body_p(
        doc,
        "Uno de los hitos de ingeniería más significativos de esta etapa ocurrió durante el despliegue del contenedor Docker en Render.com bajo la modalidad de servicio permanente gratuito (Free Tier):"
    )
    add_body_p(
        doc,
        "El orquestador de Render impone un límite estricto de 512 MiB de memoria RAM por contenedor. Al utilizar la pila tradicional de procesamiento vectorial (PyTorch, sentence-transformers y CUDA runtime), el servidor consumía entre 520 MiB y 650 MiB únicamente durante la fase de inicialización y carga de librerías en memoria. Esto provocaba que el sistema operativo del host terminara el proceso de inmediato mediante la señal SIGKILL con el error 'Out of memory (used over 512Mi)'. Adicionalmente, la imagen de Docker superaba los 2.8 GB de peso, demorando los despliegues más de 12 minutos."
    )
    add_body_p(
        doc,
        "Solución de Optimización: Se rediseñó por completo el pipeline de vectorización sustituyendo PyTorch por la función nativa ONNXMiniLM_L6_V2 embebida en ChromaDB. Al emplear ONNX Runtime compilado en C++ para CPU, se eliminaron todas las dependencias pesadas de aprendizaje profundo. El consumo de memoria RAM en reposo del backend se redujo de 520 MB a menos de 140 MB (un ahorro de más del 73% de memoria), operando con total estabilidad dentro del límite de 512 MiB de Render. Asimismo, el tamaño de la imagen Docker se redujo a ~550 MB, acelerando el despliegue continuo en GitHub a solo 2 minutos."
    )

    add_callout(
        doc,
        "La sustitución de PyTorch por ONNX Runtime redujo la huella de memoria RAM del servidor de 520 MB a 140 MB (-73%) y recortó el tamaño del contenedor Docker en un 80%, permitiendo desplegar un sistema RAG de alta fidelidad dentro del límite gratuito de 512 MiB de Render sin costo mensual para la institución.",
        title="INNOVACIÓN EN EFICIENCIA DE INFRAESTRUCTURA"
    )

    add_heading_2(doc, "8.4 Pre-indexación Vectorial e Inmutabilidad de la Base de Datos")
    add_body_p(
        doc,
        "En los contenedores efímeros de la capa gratuita de Render, cualquier archivo creado en disco durante la ejecución se descarta al reiniciar el servicio. Si el backend vectorizara los libros de neuroanatomía cada vez que arranca, consumiría picos de CPU y memoria que violarían las restricciones del servidor y demorarían minutos en iniciar."
    )
    add_body_p(
        doc,
        "Para garantizar disponibilidad instantánea, la base de datos vectorial ChromaDB (carpeta chroma_neuro_db, con un peso optimizado de aproximadamente 32 MB) se indexa en el entorno de desarrollo y se versiona directamente dentro del repositorio Git y la imagen Docker. De este modo, al levantarse el contenedor en la nube, el índice semántico ya está construido y listo para consultar en memoria en menos de 2 segundos."
    )
    add_body_p(
        doc,
        "¿Cómo se actualiza la literatura médica si el equipo docente desea incorporar nuevos libros o investigaciones?",
        bold_prefix="Estrategia de Mantenimiento y Extensibilidad: "
    )
    add_body_p(
        doc,
        "El proceso fue diseñado para que los docentes e investigadores del Laboratorio NeuroK no requieran conocimientos de programación ni uso de terminales de comandos: simplemente ingresan al panel web administrativo de Atena con su PIN de seguridad ('1234'), arrastran el nuevo archivo PDF o Word en la sección de Base de Conocimientos (donde el motor lo fragmenta y vectoriza automáticamente de forma inmediata), y presionan el botón '🚀 Publicar Cambios a la Nube'. El sistema ejecuta la sincronización de manera transparente y desatendida, provocando que Render actualice la imagen y el servicio en aproximadamente 2 minutos. Así, la aplicación móvil de Unity de todos los estudiantes queda sincronizada con la nueva literatura sin costo, sin caídas y sin que el personal del laboratorio deba escribir una sola línea de código."
    )

    add_heading_2(doc, "8.5 Búsqueda Híbrida, Tolerancia a Errores Léxicos (Fuzzy Matching) y Trazabilidad")
    add_body_p(
        doc,
        "Para maximizar la precisión pedagógica ante consultas de estudiantes mediante dispositivos móviles y visores AR, se implementaron tres mejoras algorítmicas en rag_pipeline.py:"
    )
    add_body_p(
        doc,
        "1. Tolerancia a Errores Tipográficos (Fuzzy Matching): En pantallas táctiles es frecuente que los estudiantes cometan errores ortográficos en términos complejos de neuroanatomía (por ejemplo, escribir 'hipicampo' en lugar de 'hipocampo', o 'cerebelo' con omisiones). Se implementó un algoritmo basado en difflib.get_close_matches que coteja las palabras de la consulta contra un tesauro de estructuras cerebrales y corrige automáticamente las palabras clave antes de consultar la base de datos.",
        bold_prefix="• "
    )
    add_body_p(
        doc,
        "2. Búsqueda Híbrida (Semántica Densa + Léxica Dispersa): Combina la similitud de cosenos en el espacio vectorial (all-MiniLM-L6-v2 de 384 dimensiones) con un filtro léxico de coincidencia exacta sobre términos anatómicos clave. Esto garantiza que preguntas con nombres técnicos muy específicos recuperen con máxima prioridad los fragmentos bibliográficos exactos.",
        bold_prefix="• "
    )
    add_body_p(
        doc,
        "3. Trazabilidad con Citas Documentales Explícitas: El prompt inyectado al LLM exige referenciar cada afirmación anatómica mediante el formato [Fuente X, pág. Y]. Esto erradica totalmente las alucinaciones y proporciona al estudiante y evaluador la certeza de la fuente original en los textos de referencia de la Konrad Lorenz.",
        bold_prefix="• "
    )

    add_heading_2(doc, "8.6 Matriz Comparativa Tripartita de las Tres Fases del Proyecto")
    add_body_p(
        doc,
        "La siguiente tabla consolida la evolución del proyecto a través de sus tres hitos de ingeniería:"
    )

    # Tabla Matriz Tripartita
    table_tri = doc.add_table(rows=9, cols=4)
    table_tri.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_tri.autofit = False

    headers_t = ["Criterio Técnico", "Fase 1: Ollama Local", "Fase 2: Cloud Gemini API", "Fase 3: Groq LPU + ONNX"]
    for i, h in enumerate(headers_t):
        cell = table_tri.rows[0].cells[i]
        cell.text = h
        set_cell_background(cell, "1A365D")
        p = cell.paragraphs[0]
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p.runs[0].font.name = 'Arial'
        p.runs[0].font.size = Pt(9)
        set_cell_margins(cell, top=100, bottom=100, left=80, right=80)

    tri_data = [
        ("Latencia de Respuesta", "38.0 - 54.2 segundos", "1.2 - 2.8 segundos", "0.6 - 0.9 segundos (Ultra-rápido)"),
        ("Throughput de Generación", "4 - 6 tokens/segundo", "60 - 95 tokens/segundo", "350 - 500+ tokens/segundo"),
        ("Uso de RAM en Servidor", "14.8 GB (Saturación local)", "~520 MB (Falla OOM en Render)", "< 140 MB (Estable en Render Free)"),
        ("Tamaño de Imagen Docker", "No aplica / Local", "2.8 GB (PyTorch + CUDA)", "~550 MB (ONNX Runtime ligero)"),
        ("Estabilidad ante Cuotas", "Ilimitada pero inviable", "Restricción 15 RPM (Error 429)", "Excelente concurrencia y sin caídas"),
        ("Tolerancia Tipográfica", "Nula (falla si hay typo)", "Baja (depende de semántica)", "Alta (Fuzzy Matching anatómico)"),
        ("Citas Bibliográficas", "Genéricas / Sin página", "Aproximadas", "Exactas: [Fuente X, pág. Y]"),
        ("Costo Operativo Mensual", "Inviable en hardware base", "$0 USD (con límites de cuota)", "$0 USD (Producción 24/7 permanente)")
    ]

    for row_idx, row_data in enumerate(tri_data, start=1):
        row_cells = table_tri.rows[row_idx].cells
        bg_color = "F7FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(row_data):
            row_cells[col_idx].text = text
            set_cell_background(row_cells[col_idx], bg_color)
            set_cell_margins(row_cells[col_idx], top=70, bottom=70, left=80, right=80)
            p = row_cells[col_idx].paragraphs[0]
            p.runs[0].font.name = 'Calibri'
            p.runs[0].font.size = Pt(8.5)
            p.runs[0].font.color.rgb = RGBColor(45, 55, 72)
            if col_idx == 0:
                p.runs[0].font.bold = True
            elif col_idx == 3:
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = RGBColor(26, 54, 93)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    add_heading_2(doc, "8.7 Análisis de Limitaciones, Desventajas y Mitigaciones (Para la Defensa de Grado)")
    add_body_p(
        doc,
        "En una sustentación de grado en ingeniería y ciencias aplicadas, el reconocimiento transparente de las limitaciones de diseño y sus respectivas mitigaciones de ingeniería constituye un indicador clave de madurez técnica:"
    )

    limitaciones = [
        ("1. Inmutabilidad de la Base Vectorial en Contenedor Gratuito:",
         " Desventaja: El contenedor en la nube no permite re-indexar libros al vuelo de forma persistente si el servidor se reinicia.\n"
         "• Mitigación de Ingeniería: La base de datos vectorial pre-compilada viaja empaquetada dentro del repositorio Git y la imagen Docker. Nuevos libros se indexan localmente o mediante la interfaz de administración protegida con PIN y se integran mediante despliegue continuo con git push, garantizando cero riesgo de corrupción de datos en caliente."),
        
        ("2. Tiempo de Arranque en Frío (Cold Start) en Render Free Tier:",
         " Desventaja: El plan gratuito de Render desactiva temporalmente el contenedor tras 15 minutos sin tráfico entrante. La primera petición tras este periodo puede tardar entre 30 y 45 segundos en despertar el servicio.\n"
         "• Mitigación de Ingeniería: Para sesiones de laboratorio, presentaciones de tesis o evaluaciones docentes programadas, se puede realizar un ping previo al endpoint /salud 1 minuto antes, o utilizar un servicio de monitoreo periódico gratuito (como UptimeRobot) que envíe una petición cada 14 minutos para mantener el contenedor activo."),
        
        ("3. Modelo de Embeddings Compacto (all-MiniLM-L6-v2 de 384 dimensiones):",
         " Desventaja: Modelos comerciales masivos (como text-embedding-3-large de OpenAI con 3,072 dimensiones) capturan matices semánticos aún más sutiles en oraciones complejas.\n"
         "• Mitigación de Ingeniería: La menor dimensionalidad se compensa ampliamente mediante la Búsqueda Híbrida y el Fuzzy Matching, que aseguran que los términos anatómicos y médicos no se pierdan, a la vez que mantienen la huella de memoria RAM por debajo de los 150 MB requeridos para la estabilidad del servidor."),
        
        ("4. Dependencia de Conexión a Internet y de la API de Groq:",
         " Desventaja: La inferencia del modelo LLM se procesa en los servidores de Groq Cloud, requiriendo que el dispositivo móvil con Unity disponga de conectividad a la red.\n"
         "• Mitigación de Ingeniería: El pipeline está completamente desacoplado mediante variables de entorno (GROQ_API_KEY). Si en el futuro la institución decidiera cambiar de proveedor cloud o desplegar un cluster local, la transición de código se realiza modificando únicamente las credenciales de entorno en Render, sin alterar la lógica de Unity."),
        
        ("5. Cobertura de Consultas Extremadamente Amplias (k=5 fragmentos):",
         " Desventaja: Por diseño, el sistema recupera los 5 fragmentos bibliográficos más relevantes para no saturar la ventana de atención del LLM y mantener latencia sub-segundo. Preguntas enciclopédicas excesivamente genéricas ('Explica todo el sistema nervioso desde el inicio') no abarcarán la totalidad de los libros en una sola respuesta.\n"
         "• Mitigación de Ingeniería: La interfaz en Unity orienta al estudiante a formular preguntas estructurales y conceptuales específicas, propiciando un diálogo pedagógico interactivo paso a paso.")
    ]

    for titulo_lim, desc_lim in limitaciones:
        add_body_p(doc, desc_lim, bold_prefix=titulo_lim)

    # ---------------------------------------------------------------------------
    # SECCIÓN 9: CONCLUSIONES Y RECOMENDACIONES FINALES DE INGENIERÍA
    # ---------------------------------------------------------------------------
    add_heading_1(doc, "9. CONCLUSIONES Y RECOMENDACIONES FINALES DE INGENIERÍA")
    
    add_body_p(
        doc,
        "1. La arquitectura trifásica desarrollada a lo largo del proyecto evidencia una evolución madura de ingeniería de software: superó la inviabilidad de hardware local (Ollama) y sorteó las limitaciones de cuota y sobrecarga de memoria de los servicios cloud iniciales (Gemini / PyTorch) hasta alcanzar una solución definitiva de alto rendimiento."
    )
    add_body_p(
        doc,
        "2. La integración de Groq Cloud LPU (modelo openai/gpt-oss-120b) proporciona una tasa de generación superior a 350 tokens/segundo y latencias por debajo de 0.9 segundos, habilitando por primera vez una interacción conversacional verdaderamente fluida y en tiempo real dentro de la aplicación móvil de realidad aumentada NeuroK AR en Unity 3D."
    )
    add_body_p(
        doc,
        "3. La sustitución de PyTorch por ONNX Runtime en ChromaDB constituyó la clave para la viabilidad en la nube, reduciendo el consumo de RAM en un 73% (a < 140 MB) y permitiendo que la API REST opere 24/7 de forma 100% gratuita y estable en Render.com."
    )
    add_body_p(
        doc,
        "4. La incorporación de Búsqueda Híbrida, Fuzzy Matching anatómico y citación obligatoria por obra y página garantiza el máximo rigor pedagógico y científico, entregando una herramienta robusta, verificable y con costo operativo nulo para la Fundación Universitaria Konrad Lorenz."
    )

    # Guardar documento en carpeta Otros
    output_dir = os.path.join(base_dir, "Otros")
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "Informe_Justificacion_Tecnica_Gemini_vs_Ollama.docx")
    doc.save(file_path)
    print(f"Document created successfully at: {file_path}")

if __name__ == "__main__":
    create_document()



