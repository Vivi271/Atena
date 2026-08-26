# 📋 Manual Técnico de Infraestructura en la Nube
## Proyecto Atena — NeuroK AR (Fundación Universitaria Konrad Lorenz)

---

> **Documento preparado para entrega institucional al Laboratorio de Neurociencias Aplicadas – NeuroK**  
> Fecha: Agosto 2026  
> Autora: Viviana Marcela García Valderrama  

---

## 🗂️ Tabla de Contenidos

1. [Resumen del Ecosistema](#1-resumen-del-ecosistema)
2. [Justificación Arquitectónica: De Docker Local + Ollama a Cloud Native (Render + Gemini)](#2-justificación-arquitectónica-de-docker-local--ollama-a-cloud-native-render--gemini)
3. [Cuenta Institucional del Proyecto](#3-cuenta-institucional-del-proyecto)
4. [Repositorio de Código — GitHub](#4-repositorio-de-código--github)
5. [Backend en la Nube — Render.com](#5-backend-en-la-nube--rendercom)
6. [Base de Datos NoSQL — Firebase Firestore (Conexión y Flujo de Datos)](#6-base-de-datos-nosql--firebase-firestore-conexión-y-flujo-de-datos)
7. [Modelo de IA — Gemini API (Google AI Studio)](#7-modelo-de-ia--gemini-api-google-ai-studio)
8. [API REST — Endpoints y Funcionamiento](#8-api-rest--endpoints-y-funcionamiento)
9. [Script para Unity — AtenaClient.cs](#9-script-para-unity--atenaclientcs)
10. [Cómo Agregar y Vectorizar Nueva Literatura Científica](#10-cómo-agregar-y-vectorizar-nueva-literatura-científica)
11. [Cómo Administrar el Sistema](#11-cómo-administrar-el-sistema)
12. [Cómo Actualizar el Código y el Despliegue](#12-cómo-actualizar-el-código-y-el-despliegue)
13. [Ficha Técnica Final de Entrega](#13-ficha-técnica-final-de-entrega)

---

## 1. Resumen del Ecosistema

El proyecto está compuesto por **cuatro capas** que trabajan juntas de forma integrada:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         APLICACIÓN UNITY — NeuroK AR                        │
│                     (APK Android que usa el estudiante)                      │
└───────────────────────┬─────────────────────────┬────────────────────────────┘
                        │                         │
                        ▼                         ▼
         ┌──────────────────────┐     ┌────────────────────────────┐
         │  FIREBASE (Google)   │     │   RENDER.COM (API Atena)   │
         │  ─────────────────── │     │   ────────────────────────  │
         │  Base NoSQL en Nube: │     │  POST /consultar            │
         │  • Evaluaciones      │     │  → rag_pipeline.py          │
         │  • Puntajes          │     │  → ChromaDB (libros)        │
         │  • Historial chat    │     │  → Gemini API (IA)          │
         │  • Métricas de uso   │     │  ← Respuesta + Fuentes      │
         │  (SDK gRPC/HTTPS)    │     │   GET /salud, /info, /docs │
         └──────────────────────┘     └────────────────────────────┘
                        │                         │
                        └──────────┬──────────────┘
                                   ▼
                        ┌─────────────────────┐
                        │  GEMINI API (Google) │
                        │  Modelo de lenguaje  │
                        │  que genera las      │
                        │  respuestas de IA    │
                        └─────────────────────┘
```

---

## 2. Justificación Arquitectónica: De Docker Local + Ollama a Cloud Native (Render + Gemini)

Durante las etapas iniciales de prototipado, el sistema operaba bajo un esquema **100% local en una computadora portátil** utilizando Docker Desktop, Ollama (Llama 3.2 / Qwen 1.5B) y un túnel temporal de Cloudflare. Tras una rigurosa evaluación técnica y pruebas de rendimiento, se determinó la necesidad imperativa de migrar hacia una **arquitectura Cloud Native** (Render + Gemini API).

### Comparativa Técnica: Arquitectura Anterior vs. Arquitectura Actual

| Criterio | Arquitectura Anterior (Docker Local + Ollama) | Arquitectura Actual (Cloud Native en Render + Gemini) |
|---|---|---|
| **Disponibilidad** | **Crítica y Frágil:** Dependía de que la laptop estuviera encendida, con Docker Desktop abierto y conectada a internet residencial. | **Alta Disponibilidad 24/7:** Alojado en servidores profesionales de Render.com independientes del equipo de la desarrolladora. |
| **Tiempo de Respuesta (Latencia)** | **25 a 55 segundos por consulta** (saturaba la CPU/RAM del equipo en inferencia local). | **1.2 a 2.8 segundos por consulta** (Inferencia acelerada por TPU/GPU de Google). |
| **Integración con Unity Móvil** | Inestable; los túneles temporales de Cloudflare cambiaban de URL periódicamente, rompiendo la conexión con la app móvil. | **URL Fija y Permanente:** `https://atena-vugz.onrender.com` con certificado SSL/HTTPS institucional. |
| **Consumo de Recursos del Computador** | Alto consumo de memoria RAM (>8 GB), recalentamiento de CPU y degradación de batería. | **0% de consumo local:** El computador de desarrollo o del laboratorio no requiere ejecutar procesos pesados. |
| **Soberanía y Transferencia Institucional** | Difícil de transferir; requería instalar Docker, descargar modelos de 4 GB y configurar entornos en cada equipo. | **Transferencia en 1 Clic:** Todo el servicio está centralizado bajo la cuenta institucional `atena.unikonrad@gmail.com`. |

> **Conclusión de la Decisión:**  
> La migración de Docker Desktop local a Docker Cloud en Render permite que la aplicación de Realidad Aumentada (NeuroK AR) sea verdaderamente móvil, confiable y utilizable simultáneamente por múltiples estudiantes en el Laboratorio de Neurociencias de la Konrad Lorenz, eliminando puntos únicos de falla.

---

## 3. Cuenta Institucional del Proyecto

Para garantizar la **soberanía institucional** del proyecto, se creó una cuenta oficial centralizada:

| Campo | Valor |
|-------|-------|
| **Correo Institucional** | `atena.unikonrad@gmail.com` |
| **Contraseña** | *Se entregará de forma privada al administrador* |
| **Propósito** | Cuenta centralizada para administrar Render.com, Firebase Console y Google AI Studio |
| **Vinculada a** | Render.com, Firebase Console (Firestore), Google AI Studio (Gemini API) |

---

## 4. Repositorio de Código — GitHub

| Campo | Valor |
|-------|-------|
| **URL del Repositorio** | https://github.com/Vivi271/Atena |
| **Tipo de Repositorio** | Público (acceso abierto para compilación y auditoría) |
| **Rama principal** | `main` |

---

## 5. Backend en la Nube — Render.com

### Proceso de Despliegue Institucional

El despliegue se realizó directamente con la cuenta `atena.unikonrad@gmail.com`:

| Parámetro | Valor Configurado |
|-----------|-------------------|
| **Name** | `Atena` |
| **Region** | `Oregon (US West)` |
| **Runtime** | `Docker` |
| **Instance Type** | **`Free`** ($0 USD/mes permanente) |
| **Health Check Path** | `/salud` |
| **URL Oficial** | `https://atena-vugz.onrender.com` |

---

## 6. Base de Datos NoSQL — Firebase Firestore (Conexión y Flujo de Datos)

### ¿Qué es y por qué una base de datos NoSQL?
Cloud Firestore organiza la información en **Colecciones** y **Documentos JSON**, lo que permite escalabilidad automática, sincronización en tiempo real y persistencia offline si se pierde la conexión Wi-Fi en el laboratorio.

### Flujo de Datos entre Unity y Firestore

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DISPOSITIVO MÓVIL (ANDROID)                        │
│                                                                             │
│   1. Estudiante realiza una acción (termina Quiz o envía Consulta a IA)    │
│                                   │                                         │
│                                   ▼                                         │
│   2. Unity C# construye el objeto de datos (Score, Nivel, Fecha, Pregunta)  │
│                                   │                                         │
│                                   ▼                                         │
│   3. Firebase Unity SDK lee el archivo de configuración:                    │
│      Assets/google-services.json (contiene ProjectID: atena-2d765 y APIKey)│
│                                   │                                         │
│                                   ▼                                         │
│   4. Envío seguro vía canal encriptado (gRPC / HTTPS con TLS 1.3)           │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼ (Internet)
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NUBE DE GOOGLE (Cloud Firestore)                         │
│                                                                             │
│   5. Recepción en centro de datos nam5 (us-central)                         │
│   6. Validación de reglas de seguridad (Modo Test / Reglas Institucionales) │
│   7. Escritura atómica e indexación en la colección correspondiente         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Modelo de IA — Gemini API (Google AI Studio)

| Función | Modelo |
|---------|--------|
| **Generación de Respuestas RAG** | `gemini-2.5-flash` |
| **Vectorización Semántica** | `gemini-embedding-001` |

---

## 8. API REST — Endpoints y Funcionamiento

### URL Base de Producción
```
https://atena-vugz.onrender.com
```

- **`GET /docs`** — Documentación interactiva Swagger UI: https://atena-vugz.onrender.com/docs
- **`GET /salud`** — Health check de verificación: https://atena-vugz.onrender.com/salud
- **`GET /info`** — Metadatos y modelos: https://atena-vugz.onrender.com/info
- **`POST /consultar`** — Inferencia RAG para Unity

---

## 9. Script para Unity — AtenaClient.cs

Script oficial en C# para la aplicación móvil NeuroK AR:
- **Archivo:** [`AtenaClient.cs`](AtenaClient.cs)
- **URL Base integrada:** `https://atena-vugz.onrender.com`

---

## 10. Cómo Agregar y Vectorizar Nueva Literatura Científica

### ¿Cómo funciona el Pipeline de Vectorización?
```
┌─────────────────┐     ┌─────────────────────┐     ┌───────────────────────┐
│  Nuevo Archivo  │ ──► │  Limpieza & OCR     │ ──► │  Chunking Recursivo   │
│  (PDF o DOCX)   │     │  Normalización      │     │  (1000 caracteres     │
│                 │     │  de acentos         │     │   solape 200)         │
└─────────────────┘     └─────────────────────┘     └───────────┬───────────┘
                                                                │
                                                                ▼
┌─────────────────┐     ┌─────────────────────┐     ┌───────────────────────┐
│  ChromaDB       │ ◄── │  Vectorización      │ ◄── │  Generación de        │
│  (Vector Store  │     │  Almacén vectorial  │     │  Embeddings           │
│   persistente)  │     │  con Metadata       │     │  (gemini-embedding)   │
└─────────────────┘     └─────────────────────┘     └───────────────────────┘
```

1. **Vía GitHub (Automático):** Subir el PDF a `Docs/` y hacer commit. Render re-indexa el contenido en 2 minutos.
2. **Vía Streamlit UI (Local):** Abrir `streamlit run app.py`, ingresar al Panel Admin con PIN `1234` y usar el cargador de archivos.

---

## 11. Cómo Administrar el Sistema

| Plataforma | URL de Administración | Cuenta de Acceso |
|------------|-----------------------|------------------|
| **Render.com** (Servidor API) | [dashboard.render.com](https://dashboard.render.com) | `atena.unikonrad@gmail.com` |
| **Firebase Console** (Base de Datos) | [console.firebase.google.com](https://console.firebase.google.com) | `atena.unikonrad@gmail.com` |
| **Google AI Studio** (API Key Gemini) | [aistudio.google.com](https://aistudio.google.com) | `atena.unikonrad@gmail.com` |
| **GitHub** (Código Fuente) | [github.com/Vivi271/Atena](https://github.com/Vivi271/Atena) | Repositorio público |

---

## 12. Cómo Actualizar el Código y el Despliegue

La capa gratuita de Render entra en reposo tras 15 minutos de inactividad. Abrir `https://atena-vugz.onrender.com/salud` 1 minuto antes de una demostración para despertar el servicio de inmediato.

---

## 13. Ficha Técnica Final de Entrega

| Parámetro | Detalle Institucional |
|---|---|
| **Nombre del Proyecto** | Atena — Consultor RAG en Neuroanatomía |
| **Aplicación Móvil Cliente** | NeuroK AR (Unity / Android) |
| **Institución** | Fundación Universitaria Konrad Lorenz |
| **Laboratorio** | Neurociencias Aplicadas – NeuroK |
| **Autora** | Viviana Marcela García Valderrama |
| **Año** | 2026 |
| | |
| **URL Base de Producción** | `https://atena-vugz.onrender.com` |
| **Documentación Interactiva** | `https://atena-vugz.onrender.com/docs` |
| **Health Check** | `https://atena-vugz.onrender.com/salud` |
| **Repositorio Oficial** | `https://github.com/Vivi271/Atena` |
| | |
| **Cuenta Institucional Delegada** | `atena.unikonrad@gmail.com` |
| **Base de Datos NoSQL** | Firebase Cloud Firestore (`atena-2d765`) |
| **Motor de IA** | Google Gemini 2.5 Flash + Gemini Embedding 001 |
| **Infraestructura Cloud** | Render.com (Docker Container) |
| **Costo Operativo Mensual** | $0 USD |

---

*Documento técnico de entrega oficial — Proyecto de Grado — Facultad de Psicología — Fundación Universitaria Konrad Lorenz.*
