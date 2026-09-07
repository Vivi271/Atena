import matplotlib.pyplot as plt
import numpy as np
import os

# Configuración de estilo visual profesional y tipografía limpia
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chart_assets")
os.makedirs(fig_dir, exist_ok=True)

# Paleta institucional de tres fases
COLOR_FASE1 = '#E53E3E' # Rojo Coral (Fase 1: Ollama Local)
COLOR_FASE2 = '#3182CE' # Azul Acero (Fase 2: Gemini Cloud Piloto)
COLOR_FASE3 = '#2F855A' # Verde Esmeralda (Fase 3: Groq LPU + ONNX Definitiva)

# ---------------------------------------------------------------------------
# 1. Gráfico de Latencia Total de Respuesta por Consulta (3 Fases)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=300)
categories = ['Pregunta Simple\n(Concepto)', 'Consulta RAG\n(Documento Mediano)', 'Consulta RAG Compleja\n(Múltiples Libros)']
ollama_total = [22.5, 38.0, 54.2]
gemini_total = [1.2, 2.1, 3.4]
groq_total = [0.6, 0.8, 0.9]

x = np.arange(len(categories))
width = 0.26

rects1 = ax.bar(x - width, ollama_total, width, label='Fase 1: Ollama (Llama 3.2 Local)', color=COLOR_FASE1, edgecolor='#9B2C2C', linewidth=1.1)
rects2 = ax.bar(x, gemini_total, width, label='Fase 2: Gemini API (Cloud Piloto)', color=COLOR_FASE2, edgecolor='#2B6CB0', linewidth=1.1)
rects3 = ax.bar(x + width, groq_total, width, label='Fase 3: Groq LPU + ONNX (Definitiva)', color=COLOR_FASE3, edgecolor='#22543D', linewidth=1.1)

ax.set_ylabel('Tiempo Total de Respuesta (Segundos)', fontsize=10.5, fontweight='bold', color='#1A202C')
ax.set_title('Figura 1. Comparativa de Latencia Total: Las Tres Generaciones (Menor es mejor)', fontsize=12, fontweight='bold', color='#1A365D', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=9.5, fontweight='bold')
ax.legend(frameon=True, facecolor='white', edgecolor='#CBD5E0', fontsize=9.5, loc='upper left')
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Anotaciones numéricas sobre cada barra
for rect in rects1:
    h = rect.get_height()
    ax.annotate(f'{h:.1f} s', xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontweight='bold', color='#9B2C2C', fontsize=8.5)
for rect in rects2:
    h = rect.get_height()
    ax.annotate(f'{h:.1f} s', xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontweight='bold', color='#2B6CB0', fontsize=8.5)
for rect in rects3:
    h = rect.get_height()
    ax.annotate(f'{h:.2f} s', xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontweight='bold', color='#22543D', fontsize=8.5)

ax.set_ylim(0, 62)
plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "grafico1_latencia.png"), dpi=300)
plt.close()

# ---------------------------------------------------------------------------
# 2. Gráfico de Consumo de RAM y Carga de Hardware (3 Fases)
# ---------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.8), dpi=300)

# Subplot 1: Huella de Memoria RAM en Servidor / Entorno de Ejecución (MB)
escenarios = ['Ollama Local\n(RAM Sistema)', 'Servidor Render\n(Gemini + PyTorch)', 'Servidor Render\n(Groq + ONNX Runtime)']
ram_usage_mb = [14800, 520, 138] # en MB
ram_colors = [COLOR_FASE1, '#DD6B20', COLOR_FASE3]

bars1 = ax1.bar(escenarios, [14.8, 0.52, 0.138], color=ram_colors, edgecolor='#4A5568', width=0.52)
ax1.set_ylabel('Memoria RAM Ocupada (Gigabytes)', fontsize=10, fontweight='bold')
ax1.set_title('Huella de Memoria RAM en Ejecución', fontsize=11, fontweight='bold', color='#1A365D')
ax1.axhline(y=0.512, color='#E53E3E', linestyle='--', linewidth=1.5, label='Límite Render Free (512 MB)')
ax1.set_ylim(0, 17)
ax1.grid(axis='y', linestyle='--', alpha=0.7)
ax1.legend(frameon=True, facecolor='white', fontsize=8.5, loc='upper right')

# Etiquetas sobre las barras
labels_ram = ['14.8 GB (Saturación)', '520 MB (Falla OOM)', '138 MB (Estable)']
for i, bar in enumerate(bars1):
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.4, labels_ram[i], ha='center', va='bottom', fontweight='bold', fontsize=8, color='#1A202C')

# Subplot 2: Sobrecarga en la Máquina de Desarrollo durante Inferencia
metrics = ['Uso CPU %', 'Carga GPU %', 'Temp CPU (°C)']
ollama_metrics = [88, 92, 86]
gemini_metrics = [18, 25, 52]
groq_metrics = [4, 0, 41]

x_m = np.arange(len(metrics))
width_m = 0.26

ax2.bar(x_m - width_m, ollama_metrics, width_m, label='Fase 1: Ollama Local', color=COLOR_FASE1, edgecolor='#9B2C2C')
ax2.bar(x_m, gemini_metrics, width_m, label='Fase 2: Gemini Cloud', color=COLOR_FASE2, edgecolor='#2B6CB0')
ax2.bar(x_m + width_m, groq_metrics, width_m, label='Fase 3: Groq + ONNX', color=COLOR_FASE3, edgecolor='#22543D')

ax2.set_ylabel('Porcentaje (%) / Temperatura (°C)', fontsize=10, fontweight='bold')
ax2.set_title('Impacto en Hardware durante Inferencia', fontsize=11, fontweight='bold', color='#1A365D')
ax2.set_xticks(x_m)
ax2.set_xticklabels(metrics, fontsize=9, fontweight='bold')
ax2.legend(frameon=True, facecolor='white', fontsize=8.5, loc='upper right')
ax2.grid(axis='y', linestyle='--', alpha=0.7)
ax2.set_ylim(0, 105)

for rect in ax2.patches:
    h = rect.get_height()
    if h > 0:
        ax2.annotate(f'{int(h)}', xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "grafico2_recursos_hardware.png"), dpi=300)
plt.close()

# ---------------------------------------------------------------------------
# 3. Gráfico de Velocidad de Inferencia (Throughput en Tokens/segundo)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=300)
modelos = [
    'Fase 1: Ollama Llama 3.2 8B\n(GPU AMD 5300M 4GB)',
    'Fase 1: Ollama Llama 3.2 3B\n(CPU Intel i7)',
    'Fase 2: Gemini 1.5 Pro\n(API Cloud)',
    'Fase 2: Gemini 1.5 Flash\n(API Cloud)',
    'Fase 3: Groq Cloud LPU\n(openai/gpt-oss-120b)'
]
tokens_sec = [4.1, 6.2, 62.0, 95.0, 385.0]
colores_t = [COLOR_FASE1, '#DD6B20', '#4299E1', COLOR_FASE2, COLOR_FASE3]

bars = ax.barh(modelos, tokens_sec, color=colores_t, edgecolor='#2D3748', height=0.56)
ax.set_xlabel('Velocidad de Generación (Tokens / Segundo)', fontsize=10.5, fontweight='bold', color='#1A202C')
ax.set_title('Figura 3. Rendimiento de Generación de Texto (Throughput)', fontsize=12, fontweight='bold', color='#1A365D', pad=15)
ax.grid(axis='x', linestyle='--', alpha=0.7)

for bar in bars:
    xval = bar.get_width()
    ax.text(xval + 5, bar.get_y() + bar.get_height()/2.0, f'{xval:.1f} tok/s', ha='left', va='center', fontweight='bold', fontsize=9, color='#1A202C')

ax.set_xlim(0, 440)
plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "grafico3_throughput.png"), dpi=300)
plt.close()

# ---------------------------------------------------------------------------
# 4. Gráfico Radar Multicriterio de las Tres Fases
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.2, 6.2), subplot_kw=dict(polar=True), dpi=300)

labels = np.array([
    'Velocidad de Respuesta\n(Latencia)',
    'Estabilidad de Cuotas\n(Concurrencia)',
    'Compatibilidad con\nUnity 3D',
    'Eficiencia de RAM\n(Servidor)',
    'Fidelidad RAG y\nCero Alucinación',
    'Viabilidad Cloud\n(Costo $0 USD)'
])
num_vars = len(labels)

angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]

ollama_scores = [2, 3, 3, 2, 6, 2]
ollama_scores += ollama_scores[:1]

gemini_scores = [8, 4, 8, 5, 8, 6]
gemini_scores += gemini_scores[:1]

groq_scores = [10, 10, 10, 10, 10, 10]
groq_scores += groq_scores[:1]

ax.plot(angles, ollama_scores, color=COLOR_FASE1, linewidth=2, linestyle='solid', label='Fase 1: Ollama Local')
ax.fill(angles, ollama_scores, color=COLOR_FASE1, alpha=0.18)

ax.plot(angles, gemini_scores, color=COLOR_FASE2, linewidth=2, linestyle='solid', label='Fase 2: Gemini Cloud Piloto')
ax.fill(angles, gemini_scores, color=COLOR_FASE2, alpha=0.18)

ax.plot(angles, groq_scores, color=COLOR_FASE3, linewidth=2.5, linestyle='solid', label='Fase 3: Groq LPU + ONNX Definitiva')
ax.fill(angles, groq_scores, color=COLOR_FASE3, alpha=0.22)

ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels, fontsize=8.5, fontweight='bold', color='#2D3748')
ax.set_rlabel_position(0)
plt.yticks([2, 4, 6, 8, 10], ["2", "4", "6", "8", "10"], color="#718096", size=8)
plt.ylim(0, 10)
plt.title('Figura 4. Evaluación Multicriterio Comparativa: Las Tres Generaciones (Escala 1 - 10)', size=11, color='#1A365D', weight='bold', y=1.09)
plt.legend(loc='upper right', bbox_to_anchor=(1.32, 1.12), frameon=True, facecolor='white', edgecolor='#CBD5E0', fontsize=8.5)

plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "grafico4_radar.png"), dpi=300)
plt.close()

print("All 3-way comparative charts generated successfully.")
