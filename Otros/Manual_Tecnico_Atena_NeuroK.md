# 📋 Manual Técnico de Infraestructura en la Nube
## Proyecto Atena — NeuroK AR (Fundación Universitaria Konrad Lorenz)

---

> **Documento preparado para entrega institucional al Laboratorio de Neurociencias Aplicadas – NeuroK**  
> Fecha: Septiembre 2026 (Versión 3.0 — Consolidación Cloud Native Groq LPU + ONNX Runtime)  
> **Autores:** Viviana Marcela García Valderrama — Braian Felipe Ramirez Ortiz  

---

## 🗂️ Tabla de Contenidos

1. [Resumen del Ecosistema](#1-resumen-del-ecosistema)
2. [Evolución Arquitectónica: De Docker Local (Ollama) a Cloud Gemini y la Arquitectura Definitiva (Groq LPU + ONNX)](#2-evolución-arquitectónica-de-docker-local-ollama-a-cloud-gemini-y-la-arquitectura-definitiva-groq-lpu--onnx)
3. [Cuenta Institucional del Proyecto](#3-cuenta-institucional-del-proyecto)
4. [Repositorio de Código — GitHub](#4-repositorio-de-código--github)
5. [Backend en la Nube — Render.com](#5-backend-en-la-nube--rendercom)
6. [Base de Datos NoSQL — Firebase Firestore (Conexión y Flujo de Datos)](#6-base-de-datos-nosql--firebase-firestore-conexión-y-flujo-de-datos)
7. [Modelos de IA — Inferencia Groq LPU y Embeddings ONNX Runtime](#7-modelos-de-ia--inferencia-groq-lpu-y-embeddings-onnx-runtime)
8. [API REST — Endpoints y Funcionamiento](#8-api-rest--endpoints-y-funcionamiento)
9. [Script para Unity — AtenaClient.cs](#9-script-para-unity--atenaclientcs)
10. [Cómo Agregar y Vectorizar Nueva Literatura Científica](#10-cómo-agregar-y-vectorizar-nueva-literatura-científica)
11. [Cómo Administrar el Sistema](#11-cómo-administrar-el-sistema)
12. [Monitoreo, Tiempos de Respuesta y Manejo del Cold Start](#12-monitoreo-tiempos-de-respuesta-y-manejo-del-cold-start)
13. [Ficha Técnica Final de Entrega](#13-ficha-técnica-final-de-entrega)

---

## 1. Resumen del Ecosistema

El proyecto está compuesto por **cuatro capas desacopladas** que trabajan juntas de forma integrada y en tiempo real:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         APLICACIÓN UNITY — NeuroK AR                        │
│                     (APK Android que usa el estudiante)                      │
└───────────────────────┬─────────────────────────┬────────────────────────────┘
                        │                         │
                        ▼                         ▼
         ┌──────────────────────┐     ┌────────────────────────────────────────┐
         │  FIREBASE (Google)   │     │        RENDER.COM (API Atena)          │
         │  ─────────────────── │     │   ──────────────────────────────────   │
         │  Base NoSQL en Nube: │     │  POST /consultar                       │
         │  • Evaluaciones      │     │  → rag_pipeline.py (Búsqueda Híbrida)  │
         │  • Puntajes Quizzes  │     │  → ChromaDB Nativo (ONNX all-MiniLM)   │
         │  • Historial chat    │     │  → Tolerancia Léxica (Fuzzy Matching)  │
         │  • Métricas de uso   │     │  → Groq LPU API (openai/gpt-oss-120b)  │
         │  (SDK gRPC/HTTPS)    │     │  ← Respuesta Estructurada + Fuentes    │
         │                      │     │   GET /salud, /info, /docs             │
         └──────────────────────┘     └────────────────────────────────────────┘
                        │                         │
                        └──────────┬──────────────┘
                                   ▼
                        ┌────────────────────────────────────────┐
                        │            GROQ CLOUD LPU              │
                        │  Unidad de Procesamiento de Lenguaje   │
                        │  Inferencia de alta fidelidad:         │
                        │  >350 tokens/s | Latencia < 0.9s       │
                        └────────────────────────────────────────┘
```

---

## 2. Evolución Arquitectónica: De Docker Local (Ollama) a Cloud Gemini y la Arquitectura Definitiva (Groq LPU + ONNX)

El sistema atravesó un riguroso proceso de maduración de ingeniería en tres etapas sucesivas:

1. **Fase 1 (Prototipo Local con Ollama y Docker):**  
   Ejecutaba modelos locales (Llama 3.2 3B/8B) en una laptop de desarrollo. Presentó cuellos de botella severos: latencias de 25 a 55 segundos, sobrecarga térmica de CPU (88-95% sostenido a 92°C), saturación de memoria RAM (14.8 GB sobre 16 GB) y caídas de cuadros en Unity 3D a menos de 12 FPS.

2. **Fase 2 (Prueba Piloto Cloud con Google Gemini API):**  
   Descargó el procesamiento local hacia la nube de Google AI Studio, reduciendo el tiempo de respuesta a 1.8 segundos. No obstante, al someter el sistema a pruebas de concurrencia e integración con Unity, surgieron bloqueos por límites de cuota gratuita (**HTTP 429 Too Many Requests / ResourceExhausted** limitado a 15 peticiones por minuto) y fluctuaciones de latencia en horas pico.

3. **Fase 3 (Arquitectura Definitiva: Groq LPU + ChromaDB ONNX Runtime en Render):**  
   - **Inferencia LLM:** Migración a Groq Cloud con tecnología LPU (*Language Processing Unit*). Generación ultra-veloz (>350 tokens/segundo) y latencia sub-segundo (< 0.9s).
   - **Embeddings y Memoria del Servidor:** Reemplazo de PyTorch por ONNX Runtime (`ONNXMiniLM_L6_V2`). El consumo de RAM en reposo del servidor cayó de 520 MB a menos de 140 MB (-73%), resolviendo de manera definitiva las caídas por falta de memoria (**Out Of Memory - 512Mi limit**) en el plan gratuito de Render.
   - **Robustez RAG:** Búsqueda híbrida y *Fuzzy Matching* que corrige automáticamente errores ortográficos comunes en neuroanatomía (`hipicampo` $\rightarrow$ `hipocampo`) y genera citas bibliográficas exactas (`[Fuente X, pág. Y]`).

### Comparativa Técnica Integral de las Tres Fases

| Criterio | Fase 1: Ollama (Local) | Fase 2: Gemini API (Cloud Piloto) | Fase 3: Groq LPU + ONNX (Actual / Definitiva) |
|---|---|---|---|
| **¿Dónde corre?** | En la laptop local (Docker) | Nube Google AI Studio + Render | **Nube Groq Cloud (LPU) + Render** |
| **Tiempo de Respuesta** | 25 a 55 segundos (Hiper lento) | 1.5 a 3.5 segundos (Inestable en horas pico) | **0.6 a 0.9 segundos (Casi instantáneo)** |
| **Velocidad (Tokens/s)** | 4 - 6 tokens/segundo | 60 - 95 tokens/segundo | **> 380 tokens/segundo** |
| **Memoria RAM Servidor** | Satura la laptop (14.8 GB) | 520 MB (Tumbaba el servidor de Render) | **< 140 MB (Súper liviano y estable)** |
| **Límite de Peticiones** | Ilimitado pero congelaba la PC | Máximo 15 preguntas/minuto (Error 429) | **Sin bloqueos ni caídas de cuota** |
| **Integración con Unity** | Congelaba la escena (< 12 FPS) | Fluido, pero a veces fallaba el JSON | **60 FPS estables y JSON perfecto** |
| **Citas y Fuentes** | Genéricas / Sin página | Mencionaba el libro sin página exacta | **Exactas: `[Fuente X, pág. Y]`** |
| **Tolerancia Tipográfica** | Nula (falla si hay errores tipográficos) | Baja (dependencia exclusiva de similitud vectorial) | **Alta (Fuzzy Matching automático con `difflib`)** |
| **Costo Mensual** | $0 (pero exigía PC de $2,500 USD) | $0 (con cuota muy restringida) | **$0 USD permanente** |

---

## 3. Cuenta Institucional del Proyecto

Para asegurar la **soberanía tecnológica** y la transferencia ordenada al Laboratorio NeuroK, todos los servicios están centralizados bajo la cuenta oficial:

| Campo | Valor |
|-------|-------|
| **Correo Institucional** | `atena.unikonrad@gmail.com` |
| **Contraseña** | *Se entrega en el acta privada de recepción técnica* |
| **Plataformas Vinculadas** | Render.com (Servidor API), Groq Cloud Console (Motor LLM), Firebase Console (Firestore NoSQL), GitHub (Código Fuente) |

---

## 4. Repositorio de Código — GitHub

| Campo | Valor |
|-------|-------|
| **URL del Repositorio** | [https://github.com/Vivi271/Atena](https://github.com/Vivi271/Atena) |
| **Tipo de Repositorio** | Público (Acceso abierto para auditoría y compilación) |
| **Rama principal** | `main` |
| **Despliegue Continuo (CI/CD)** | Vinculado automáticamente con Render via GitHub Webhook |

---

## 5. Backend en la Nube — Render.com

### Configuración del Servicio en Producción

El servicio web está configurado como contenedor Docker en Render:

| Parámetro | Valor Configurado |
|-----------|-------------------|
| **Service Name** | `Atena` |
| **Region** | `Oregon (US West)` |
| **Runtime** | `Docker` |
| **Instance Type** | **`Free`** (512 MiB RAM / 0.1 CPU compartida — $0 USD/mes) |
| **Health Check Path** | `/salud` |
| **URL Oficial de Producción** | `https://atena-vugz.onrender.com` |

### Variables de Entorno en Render

Configuradas de forma segura en el panel de Render (*Environment Variables*):

- `GROQ_API_KEY`: Clave secreta para la inferencia de lenguaje en Groq Cloud.
- `CHROMA_DB_DIR`: Ruta relativa al almacén vectorial (`chroma_neuro_db`).
- `SECRET_PIN`: Clave de seguridad (`1234`) para acceder al panel de administración.
- `PORT`: `8000` (puerto estándar expuesto por el contenedor Docker).

---

## 6. Base de Datos NoSQL — Firebase Firestore (Conexión y Flujo de Datos)

### ¿Qué almacena Firestore en el Proyecto?
Cloud Firestore almacena de forma independiente los datos transaccionales de los estudiantes:
- **Colección `evaluaciones`:** Puntajes de quizzes y progreso pedagógico en AR.
- **Colección `sesiones_chat`:** Historial de interacción para analítica académica del laboratorio.
- **Colección `metricas_sistema`:** Tiempos de respuesta y estructuras cerebrales más consultadas.

### Flujo de Comunicación
```
Unity (NeuroK AR Móvil)
  ├──► Firebase Firestore (gRPC seguro / TLS 1.3) → Guarda métricas y quizzes
  └──► Render.com (HTTPS REST /consultar)        → Inferencia y consulta RAG
```

---

## 7. Modelos de IA — Inferencia Groq LPU y Embeddings ONNX Runtime

### Componentes de Inteligencia Artificial

| Función | Tecnología / Modelo | Justificación Técnica |
|---|---|---|
| **Generación de Respuestas RAG** | **Groq Cloud LPU — `openai/gpt-oss-120b`** | Inferencia ultra-rápida (>350 tok/s), seguimiento riguroso de contexto científico, cero alucinaciones y adaptación a niveles básico/avanzado. |
| **Vectorización Semántica** | **ChromaDB Nativo — `all-MiniLM-L6-v2` (ONNX)** | Generación de embeddings de 384 dimensiones sin requerir PyTorch ni CUDA. Reduce el consumo de RAM a <140 MB, garantizando estabilidad en contenedores de 512 MiB. |
| **Corrección Fonética / Léxica** | **Fuzzy Matching (`difflib`)** | Intercepta términos anatómicos mal digitados en la pantalla táctil móvil antes de consultar la base de datos. |
| **Estrategia de Cita** | **Citas Documentales Forzadas** | Inyecta metadatos obligatorios en el prompt del sistema: `[Fuente X, pág. Y]`. |

---

## 8. API REST — Endpoints y Funcionamiento

### URL Base de Producción
```
https://atena-vugz.onrender.com
```

### Endpoints Disponibles

#### 1. `POST /consultar` (Principal para Unity 3D)
Recibe la consulta del estudiante y devuelve la síntesis RAG con fuentes y páginas verificadas.

- **Request Payload:**
```json
{
  "pregunta": "¿Qué función cumple el hipocampo?",
  "nivel": "avanzado",
  "k": 5
}
```

- **Response Payload:**
```json
{
  "respuesta": "El hipocampo es una estructura crítica del sistema límbico vinculada a la consolidación de la memoria a largo plazo y la navegación espacial [Neuroanatomia clinica 26va Edición - Lange.pdf, pág. 214]. Recibe aferencias de la corteza entorrinal a través de la vía perforante...",
  "fuentes": [
    {
      "fuente": "Neuroanatomia clinica  26va Edición - Lange.pdf",
      "pagina": 214,
      "fragmento": "El hipocampo forma parte del arquicórtex y desempeña un papel central en la consolidación..."
    }
  ],
  "nivel": "avanzado"
}
```

#### 2. `GET /salud`
Endpoint de comprobación de salud (*health-check*). Devuelve el estado del servidor, conectividad de ChromaDB y hora del sistema:
```json
{
  "estado": "activo",
  "servicio": "Atena API REST",
  "version": "3.0.0",
  "documentos_indexados": 352
}
```

#### 3. `GET /info`
Retorna metadatos técnicos, modelos activos y estado de configuración.

#### 4. `GET /docs`
Interfaz Swagger UI interactiva para pruebas en navegador: [https://atena-vugz.onrender.com/docs](https://atena-vugz.onrender.com/docs).

---

## 9. Script para Unity — AtenaClient.cs

El script oficial en C# gestiona las peticiones asíncronas desde la aplicación móvil:
- **Ubicación en el repositorio:** [`AtenaClient.cs`](../AtenaClient.cs)
- **URL Base:** `https://atena-vugz.onrender.com`
- **Manejo de Red:** Utiliza `UnityWebRequest` con serialización JSON nativa (`JsonUtility`).
- **Callback Desacoplado:** Envía la respuesta formateada a la UI del Canvas sin bloquear el hilo principal de renderizado de Unity (60 FPS sostenidos).

---

## 10. Cómo Agregar y Vectorizar Nueva Literatura Científica

### Flujo de Persistencia Eficiente (Inmutabilidad en Servidor Gratuito)
Los contenedores gratuitos de Render tienen un sistema de archivos efímero: no deben realizar tareas pesadas de vectorización en caliente para evitar caídas por límite de RAM (512 MiB). 

Por tal motivo, la base vectorial `chroma_neuro_db` (~32 MB) está pre-indexada y empaquetada dentro del repositorio.

```
┌─────────────────┐     ┌─────────────────────┐     ┌───────────────────────┐
│  Nuevo Libro    │ ──► │  Entorno Local o    │ ──► │  ChromaDB ONNX        │
│  (PDF en Docs/) │     │  Panel Admin Web    │     │  Vectorización ligera │
│                 │     │  (PIN: 1234)        │     │  (all-MiniLM-L6-v2)   │
└─────────────────┘     └─────────────────────┘     └───────────┬───────────┘
                                                                │
                                                                ▼
┌─────────────────┐     ┌─────────────────────┐     ┌───────────────────────┐
│  Render Cloud   │ ◄── │  Despliegue         │ ◄── │  Git Commit & Push    │
│  Servicio listo │     │  Automático (2 min) │     │  Actualiza            │
│  en producción  │     │  Cero tiempo caído  │     │  chroma_neuro_db/     │
└─────────────────┘     └─────────────────────┘     └───────────────────────┘
```

### Paso a Paso para Incorporar Nuevos Textos:
1. Copiar el nuevo archivo PDF o DOCX en la carpeta `Docs/`.
2. Ejecutar la indexación localmente:
   ```bash
   python indexar_documentos.py
   ```
   *(O bien, abrir `streamlit run app.py`, ingresar al Panel Admin con PIN `1234` y usar el cargador web).*
3. Confirmar que la carpeta `chroma_neuro_db/` se haya actualizado.
4. Enviar los cambios al repositorio institucional:
   ```bash
   git add Docs/ chroma_neuro_db/
   git commit -m "docs: indexar nuevo texto académico de neuroanatomía"
   git push origin main
   ```
5. Render detectará el push y reconstruirá el servicio en aproximadamente 2 minutos, poniendo a disposición el nuevo conocimiento sin costo adicional.

---

## 11. Cómo Administrar el Sistema

| Plataforma | Propósito | URL de Acceso | Credenciales |
|---|---|---|---|
| **Render.com** | Servidor Backend Docker | [dashboard.render.com](https://dashboard.render.com) | `atena.unikonrad@gmail.com` |
| **Groq Console** | Monitoreo y API Keys LLM | [console.groq.com](https://console.groq.com) | `atena.unikonrad@gmail.com` |
| **Firebase Console** | Base de Datos NoSQL Firestore | [console.firebase.google.com](https://console.firebase.google.com) | `atena.unikonrad@gmail.com` |
| **GitHub** | Código Fuente y Control de Versiones | [github.com/Vivi271/Atena](https://github.com/Vivi271/Atena) | Repositorio Oficial |

---

## 12. Monitoreo, Tiempos de Respuesta y Manejo del Cold Start

### Comportamiento del Servidor Gratuito (Cold Start)
En la capa gratuita de Render, la instancia entra en estado de suspensión (*sleep*) tras **15 minutos sin tráfico entrante**.
- **Impacto:** La primera consulta recibida después de un periodo de inactividad puede tardar **entre 30 y 45 segundos** mientras Render despierta el contenedor Docker.
- **A partir de la segunda consulta:** El servidor responde a velocidad plena en **0.6 a 0.9 segundos**.

### Estrategia de Mitigación para Prácticas y Sustentaciones
1. **Despertar Previo:** Abrir la URL `https://atena-vugz.onrender.com/salud` en cualquier navegador 1 minuto antes de iniciar una clase, práctica de laboratorio o sustentación de tesis.
2. **Monitoreo Automático Gratuito (Opcional):** Configurar un servicio gratuito de monitoreo tipo *UptimeRobot* (https://uptimerobot.com) que envíe una petición `GET /salud` cada 14 minutos, impidiendo que el servidor entre en reposo durante las jornadas académicas.

---

## 13. Ficha Técnica Final de Entrega

| Parámetro | Detalle Institucional |
|---|---|
| **Nombre del Proyecto** | Atena — Consultor RAG en Neuroanatomía 3D |
| **Aplicación Móvil Cliente** | NeuroK AR (Unity 3D / C# / Android) |
| **Institución Académica** | Fundación Universitaria Konrad Lorenz |
| **Laboratorio Destino** | Laboratorio de Neurociencias Aplicadas – NeuroK |
| **Autores** | Viviana Marcela García Valderrama — Braian Felipe Ramirez Ortiz |
| **Año y Versión** | 2026 — Versión 3.0 (Cloud Native Consolidada) |
| | |
| **URL Base de Producción** | `https://atena-vugz.onrender.com` |
| **Health Check** | `https://atena-vugz.onrender.com/salud` |
| **Documentación Swagger** | `https://atena-vugz.onrender.com/docs` |
| **Repositorio GitHub** | `https://github.com/Vivi271/Atena` |
| | |
| **Motor de Inferencia LLM** | Groq Cloud LPU — `openai/gpt-oss-120b` |
| **Velocidad de Inferencia** | >350 tokens/segundo (Latencia promedio: 0.8s) |
| **Modelo de Embeddings** | ChromaDB Nativo — `all-MiniLM-L6-v2` (ONNX Runtime, 384 dim) |
| **Almacenamiento Vectorial** | ChromaDB Persistent Store (`chroma_neuro_db`, ~32 MB) |
| **Consumo de RAM en Servidor** | < 140 MB (Operación holgada dentro de los 512 MiB de Render) |
| **Tolerancia a Fallos de Usuario**| *Fuzzy Matching* léxico y Búsqueda Híbrida |
| **Citas Documentales** | Trazabilidad exacta por texto y página: `[Fuente X, pág. Y]` |
| **Costo Operativo Mensual** | **$0 USD (100% Permanente)** |

---

*Manual Técnico de Infraestructura — Documento Oficial de Entrega — Facultad de Psicología / Ingeniería de Sistemas — Fundación Universitaria Konrad Lorenz.*
