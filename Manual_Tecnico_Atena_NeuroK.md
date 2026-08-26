# 📋 Manual Técnico de Infraestructura en la Nube
## Proyecto Atena — NeuroK AR (Fundación Universitaria Konrad Lorenz)

---

> **Documento preparado para entrega institucional al Laboratorio de Neurociencias Aplicadas – NeuroK**  
> Fecha: Agosto 2026  
> Autora: Viviana Marcela García Valderrama  

---

## 🗂️ Tabla de Contenidos

1. [Resumen del Ecosistema](#1-resumen-del-ecosistema)
2. [Cuenta Institucional del Proyecto](#2-cuenta-institucional-del-proyecto)
3. [Repositorio de Código — GitHub](#3-repositorio-de-código--github)
4. [Backend en la Nube — Render.com](#4-backend-en-la-nube--rendercom)
5. [Base de Datos NoSQL — Firebase Firestore (Conexión y Flujo de Datos)](#5-base-de-datos-nosql--firebase-firestore-conexión-y-flujo-de-datos)
6. [Modelo de IA — Gemini API (Google AI Studio)](#6-modelo-de-ia--gemini-api-google-ai-studio)
7. [API REST — Endpoints y Funcionamiento](#7-api-rest--endpoints-y-funcionamiento)
8. [Script para Unity — AtenaClient.cs](#8-script-para-unity--atenaclientcs)
9. [Cómo Agregar y Vectorizar Nueva Literatura Científica](#9-cómo-agregar-y-vectorizar-nueva-literatura-científica)
10. [Cómo Administrar el Sistema](#10-cómo-administrar-el-sistema)
11. [Cómo Actualizar el Código y el Despliegue](#11-cómo-actualizar-el-código-y-el-despliegue)
12. [Ficha Técnica Final de Entrega](#12-ficha-técnica-final-de-entrega)

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

## 2. Cuenta Institucional del Proyecto

Para garantizar la **soberanía institucional** del proyecto (que la Fundación Universitaria Konrad Lorenz sea la propietaria real de todos los servicios en la nube), se creó una cuenta oficial centralizada:

| Campo | Valor |
|-------|-------|
| **Correo Institucional** | `atena.unikonrad@gmail.com` |
| **Contraseña** | *Se entregará de forma privada al administrador* |
| **Propósito** | Cuenta centralizada para administrar Render.com, Firebase Console y Google AI Studio |
| **Vinculada a** | Render.com, Firebase Console (Firestore), Google AI Studio (Gemini API) |

> ⚠️ **Seguridad:** Esta credencial es custodiada por el Laboratorio de Neurociencias Aplicadas – NeuroK como cuenta institucional oficial del sistema.

---

## 3. Repositorio de Código — GitHub

| Campo | Valor |
|-------|-------|
| **URL del Repositorio** | https://github.com/Vivi271/Atena |
| **Tipo de Repositorio** | Público (acceso abierto para compilación y auditoría) |
| **Rama principal** | `main` |

---

## 4. Backend en la Nube — Render.com

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

## 5. Base de Datos NoSQL — Firebase Firestore (Conexión y Flujo de Datos)

### ¿Qué es y por qué una base de datos NoSQL?
Cloud Firestore es una base de datos orientada a documentos (NoSQL) alojada en la infraestructura de Google Cloud. A diferencia de las bases de datos relacionales tradicionales (SQL), Firestore organiza la información en **Colecciones** y **Documentos JSON**, lo que permite:
1. **Escalabilidad automática:** Soporta múltiples usuarios simultáneos en el laboratorio sin saturar el servidor.
2. **Sincronización en tiempo real:** Los datos se transmiten de forma reactiva y bidireccional.
3. **Persistencia y Caché Offline:** Si el dispositivo móvil en el laboratorio pierde la conexión Wi-Fi temporalmente, los datos se guardan en el almacenamiento local del celular y se sincronizan automáticamente con la nube en cuanto se restablece la red.

---

### ¿Cómo se Conecta la Aplicación Móvil (Unity) con Firestore?

La comunicación entre el dispositivo del estudiante y la base de datos en la nube sigue este flujo:

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

### Estructura de Colecciones y Esquema de Documentos

#### 1. Colección `/evaluaciones` (Resultados de Quizzes)
Almacena cada intento de evaluación realizado en el módulo interactivo de selección múltiple:

```json
{
  "id_evaluacion": "eval_8f9a2b",
  "perfil_usuario": "estudiante",
  "nivel": "basico",
  "fecha_hora": "2026-08-25T14:30:00Z",
  "puntaje_total": 4,
  "total_preguntas": 5,
  "porcentaje_acierto": 80.0,
  "detalle_respuestas": [
    {
      "pregunta": "¿Qué estructura conecta los hemisferios cerebrales?",
      "respuesta_seleccionada": "Cuerpo calloso",
      "es_correcta": true
    },
    {
      "pregunta": "¿Dónde se localiza el lóbulo occipital?",
      "respuesta_seleccionada": "Región anterior",
      "es_correcta": false
    }
  ]
}
```

#### 2. Colección `/consultas` (Historial del Asistente IA)
Permite al cuerpo docente analizar cuáles son los temas o dudas más frecuentes de los estudiantes:

```json
{
  "id_consulta": "chat_4c7e1d",
  "perfil_usuario": "estudiante",
  "nivel": "avanzado",
  "pregunta": "¿Cuál es la función del núcleo caudado?",
  "respuesta_generada": "El núcleo caudado integra el cuerpo estriado y participa en el control motor...",
  "fuentes_consultadas": ["Neuroanatomia clinica - Lange.pdf (pág. 182)"],
  "fecha_hora": "2026-08-25T15:10:22Z"
}
```

#### 3. Colección `/metricas` (Telemetría de Uso del Laboratorio)
Registra la interacción con los modelos 3D y la alternancia de niveles de contenido:

```json
{
  "id_sesion": "ses_001928",
  "estructura_3d_explorada": "Cerebelo",
  "tiempo_interaccion_segundos": 145,
  "alternancias_nivel_realizadas": 3,
  "fecha": "2026-08-25"
}
```

---

### Código C# para Unity (`FirebaseManager.cs`)

Para guardar datos en Firestore desde Unity, se utiliza el siguiente script:

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;
using Firebase.Firestore;
using Firebase.Extensions;

public class FirebaseManager : MonoBehaviour
{
    private FirebaseFirestore db;

    void Start()
    {
        // Inicializa la instancia de Firestore conectada al proyecto atena-2d765
        db = FirebaseFirestore.DefaultInstance;
    }

    /// <summary>
    /// Guarda el resultado de un quiz completado en la nube.
    /// </summary>
    public void GuardarResultadoEvaluacion(string perfil, string nivel, int aciertos, int total)
    {
        DocumentReference docRef = db.Collection("evaluaciones").Document();
        
        Dictionary<string, object> evaluacion = new Dictionary<string, object>
        {
            { "perfil_usuario", perfil },
            { "nivel", nivel },
            { "fecha_hora", DateTime.UtcNow.ToString("o") },
            { "puntaje_total", aciertos },
            { "total_preguntas", total },
            { "porcentaje_acierto", (float)aciertos / total * 100f }
        };

        docRef.SetAsync(evaluacion).ContinueWithOnMainThread(task => {
            if (task.IsCompleted && !task.IsFaulted) {
                Debug.Log("[Firebase] Evaluación guardada exitosamente con ID: " + docRef.Id);
            } else {
                Debug.LogError("[Firebase] Error al guardar evaluación: " + task.Exception);
            }
        });
    }
}
```

---

## 6. Modelo de IA — Gemini API (Google AI Studio)

| Función | Modelo |
|---------|--------|
| **Generación de Respuestas RAG** | `gemini-2.5-flash` |
| **Vectorización Semántica** | `gemini-embedding-001` |

---

## 7. API REST — Endpoints y Funcionamiento

### URL Base de Producción
```
https://atena-vugz.onrender.com
```

- **`GET /docs`** — Documentación interactiva Swagger UI
- **`GET /salud`** — Health check de verificación
- **`GET /info`** — Metadatos y modelos
- **`POST /consultar`** — Inferencia RAG para Unity

---

## 8. Script para Unity — AtenaClient.cs

Script oficial en C# para la aplicación móvil NeuroK AR:
- **Archivo:** [`AtenaClient.cs`](AtenaClient.cs)
- **URL Base integrada:** `https://atena-vugz.onrender.com`

---

## 9. Cómo Agregar y Vectorizar Nueva Literatura Científica

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

## 10. Cómo Administrar el Sistema

| Plataforma | URL de Administración | Cuenta de Acceso |
|------------|-----------------------|------------------|
| **Render.com** (Servidor API) | [dashboard.render.com](https://dashboard.render.com) | `atena.unikonrad@gmail.com` |
| **Firebase Console** (Base de Datos) | [console.firebase.google.com](https://console.firebase.google.com) | `atena.unikonrad@gmail.com` |
| **Google AI Studio** (API Key Gemini) | [aistudio.google.com](https://aistudio.google.com) | `atena.unikonrad@gmail.com` |
| **GitHub** (Código Fuente) | [github.com/Vivi271/Atena](https://github.com/Vivi271/Atena) | Repositorio público |

---

## 11. Cómo Actualizar el Código y el Despliegue

La capa gratuita de Render entra en reposo tras 15 minutos de inactividad. Abrir `https://atena-vugz.onrender.com/salud` 1 minuto antes de una demostración para despertar el servicio de inmediato.

---

## 12. Ficha Técnica Final de Entrega

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
