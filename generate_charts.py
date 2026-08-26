import matplotlib.pyplot as plt
import numpy as np
import os

# Configuración de estilo estético profesional
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig_dir = "/Users/vivianagarcia/Desktop/Konrad lorenz/9 SEMESTRE/TESIS/ConsultorNeuroanatomia/chart_assets"
os.makedirs(fig_dir, exist_ok=True)

colors_blue = ['#1A365D', '#2B6CB0', '#4299E1', '#63B3ED']
colors_accent = ['#C53030', '#DD6B20', '#319795', '#3182CE']

# -------------------------------------------------------------
# 1. Gráfico de Latencia Total y Time to First Token (TTFT)
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
categories = ['Pregunta Simple\n(Concepto)', 'Consulta RAG\n(Documento Mediano)', 'Consulta RAG Compleja\n(Múltiples Libros)']
ollama_ttft = [4.2, 8.5, 14.0]
ollama_total = [22.5, 38.0, 54.2]
gemini_ttft = [0.4, 0.6, 0.8]
gemini_total = [1.2, 2.1, 3.4]

x = np.arange(len(categories))
width = 0.35

rects1 = ax.bar(x - width/2, ollama_total, width, label='Ollama (Llama 3.2 Local)', color='#E53E3E', edgecolor='#9B2C2C', linewidth=1.2)
rects2 = ax.bar(x + width/2, gemini_total, width, label='Gemini API (Cloud)', color='#3182CE', edgecolor='#2B6CB0', linewidth=1.2)

ax.set_ylabel('Tiempo de Respuesta (Segundos)', fontsize=11, fontweight='bold', color='#1A202C')
ax.set_title('Comparativa de Latencia Total de Respuesta por Consulta (Menor es mejor)', fontsize=12, fontweight='bold', color='#1A365D', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=10, fontweight='bold')
ax.legend(frameon=True, facecolor='white', edgecolor='#CBD5E0', fontsize=10)
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Etiquetas de valores
for rect in rects1:
    height = rect.get_height()
    ax.annotate(f'{height:.1f} s', xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontweight='bold', color='#9B2C2C', fontsize=9)
for rect in rects2:
    height = rect.get_height()
    ax.annotate(f'{height:.1f} s', xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontweight='bold', color='#2B6CB0', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "grafico1_latencia.png"), dpi=300)
plt.close()

# -------------------------------------------------------------
# 2. Gráfico de Consumo de RAM y Carga de CPU/GPU Local
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), dpi=300)

# Uso de Memoria RAM (GB)
escenarios = ['Sistema + Unity', 'Unity + Ollama', 'Unity + Gemini API']
ram_usage = [6.5, 14.8, 7.2] # GB de 16GB disponibles
ram_colors = ['#A0AEC0', '#E53E3E', '#319795']

bars1 = ax1.bar(escenarios, ram_usage, color=ram_colors, edgecolor='#4A5568', width=0.55)
ax1.set_ylabel('Uso de Memoria RAM (GB) [Máx: 16 GB]', fontsize=10, fontweight='bold')
ax1.set_title('Consumo de RAM en Máquina de Pruebas', fontsize=11, fontweight='bold', color='#1A365D')
ax1.axhline(y=16, color='#E53E3E', linestyle='--', label='Límite RAM (16 GB)')
ax1.set_ylim(0, 18)
ax1.grid(axis='y', linestyle='--', alpha=0.7)

for bar in bars1:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.4, f'{yval:.1f} GB', ha='center', va='bottom', fontweight='bold', fontsize=9)

# Uso de CPU (%) y temperatura estimada (°C)
metrics = ['Uso CPU %', 'Carga GPU %', 'Temp CPU (°C)']
ollama_metrics = [88, 92, 86]
gemini_metrics = [18, 25, 52]

x_m = np.arange(len(metrics))
width_m = 0.35

ax2.bar(x_m - width_m/2, ollama_metrics, width_m, label='Ollama (Local)', color='#DD6B20', edgecolor='#C05621')
ax2.bar(x_m + width_m/2, gemini_metrics, width_m, label='Gemini API (Cloud)', color='#3182CE', edgecolor='#2B6CB0')

ax2.set_ylabel('Porcentaje / Temperatura (°C)', fontsize=10, fontweight='bold')
ax2.set_title('Impacto en Hardware durante Inferencia', fontsize=11, fontweight='bold', color='#1A365D')
ax2.set_xticks(x_m)
ax2.set_xticklabels(metrics, fontsize=9, fontweight='bold')
ax2.legend(frameon=True, facecolor='white', fontsize=9)
ax2.grid(axis='y', linestyle='--', alpha=0.7)

for rect in ax2.patches:
    h = rect.get_height()
    if h > 0:
        ax2.annotate(f'{int(h)}', xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "grafico2_recursos_hardware.png"), dpi=300)
plt.close()

# -------------------------------------------------------------
# 3. Gráfico de Velocidad de Inferencia (Tokens/segundo)
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=300)
modelos = ['Ollama Llama 3.2 3B\n(CPU Intel i7)', 'Ollama Llama 3.2 8B\n(AMD 5300M 4GB)', 'Gemini 1.5 Flash\n(API Cloud)', 'Gemini 1.5 Pro\n(API Cloud)']
tokens_sec = [6.2, 4.1, 95.0, 62.0]
colores_t = ['#E53E3E', '#DD6B20', '#38A169', '#3182CE']

bars = ax.barh(modelos, tokens_sec, color=colores_t, edgecolor='#2D3748', height=0.55)
ax.set_xlabel('Velocidad de Generación (Tokens / Segundo)', fontsize=11, fontweight='bold', color='#1A202C')
ax.set_title('Rendimiento de Generación de Texto (Throughput)', fontsize=12, fontweight='bold', color='#1A365D', pad=15)
ax.grid(axis='x', linestyle='--', alpha=0.7)

for bar in bars:
    xval = bar.get_width()
    ax.text(xval + 2, bar.get_y() + bar.get_height()/2.0, f'{xval:.1f} tok/s', ha='left', va='center', fontweight='bold', fontsize=9, color='#1A202C')

ax.set_xlim(0, 115)
plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "grafico3_throughput.png"), dpi=300)
plt.close()

# -------------------------------------------------------------
# 4. Gráfico Radar / Multi-criterio
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 6), subplot_kw=dict(polar=True), dpi=300)

labels = np.array(['Velocidad / Latencia', 'Escalabilidad', 'Compatibilidad Unity', 'Uso Eficiente Hardware', 'Calidad RAG / Contexto', 'Facilidad Despliegue'])
num_vars = len(labels)

angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]

ollama_scores = [2, 3, 4, 2, 6, 4]
ollama_scores += ollama_scores[:1]

gemini_scores = [10, 10, 10, 10, 9, 9]
gemini_scores += gemini_scores[:1]

ax.plot(angles, ollama_scores, color='#E53E3E', linewidth=2, linestyle='solid', label='Ollama (Local)')
ax.fill(angles, ollama_scores, color='#E53E3E', alpha=0.25)

ax.plot(angles, gemini_scores, color='#3182CE', linewidth=2, linestyle='solid', label='Gemini API (Cloud)')
ax.fill(angles, gemini_scores, color='#3182CE', alpha=0.25)

ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels, fontsize=9, fontweight='bold')
ax.set_rlabel_position(0)
plt.yticks([2, 4, 6, 8, 10], ["2", "4", "6", "8", "10"], color="#718096", size=8)
plt.ylim(0, 10)
plt.title('Evaluación Multicriterio (Escala 1 - 10)', size=12, color='#1A365D', weight='bold', y=1.08)
plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), frameon=True, facecolor='white', fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "grafico4_radar.png"), dpi=300)
plt.close()

print("Charts created successfully.")
