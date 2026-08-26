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
5. [Base de Datos NoSQL — Firebase Firestore](#5-base-de-datos-nosql--firebase-firestore)
6. [Modelo de IA — Gemini API (Google AI Studio)](#6-modelo-de-ia--gemini-api-google-ai-studio)
7. [API REST — Endpoints y Funcionamiento](#7-api-rest--endpoints-y-funcionamiento)
8. [Script para Unity — AtenaClient.cs](#8-script-para-unity--atenaclientcs)
9. [Cómo Ser Administrador del Sistema](#9-cómo-ser-administrador-del-sistema)
10. [Cómo Actualizar el Sistema en el Futuro](#10-cómo-actualizar-el-sistema-en-el-futuro)
11. [Ficha Técnica Final de Entrega](#11-ficha-técnica-final-de-entrega)

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
         │  Auth: Perfil de     │     │  POST /consultar            │
         │  usuario (nivel      │     │  → rag_pipeline.py          │
         │  básico/avanzado)    │     │  → ChromaDB (libros)        │
         │                      │     │  → Gemini API (IA)          │
         │  Firestore: Guarda   │     │  ← Respuesta + Fuentes      │
         │  • Evaluaciones      │     │                             │
         │  • Puntajes          │     │   GET /salud                │
         │  • Historial chat    │     │   GET /info                 │
         │  • Métricas de uso   │     │   GET /docs                 │
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

Para garantizar la **soberanía institucional** del proyecto (que la Konrad Lorenz sea la propietaria real de todos los servicios), se creó una cuenta de Gmail exclusiva del proyecto:

| Campo                 | Valor                                                                                         |
| --------------------- | --------------------------------------------------------------------------------------------- |
| **Correo**      | `atena.unikonrad@gmail.com`                                                                 |
| **Contraseña** | Se le entregará al administrador                                                            |
| **Propósito**  | Cuenta centralizada para administrar Firebase, Google AI Studio y como identidad del proyecto |
| **Vinculada a** | Firebase Console, Google AI Studio (Gemini API)                                               |

> ⚠️ **Importante:** Esta contraseña debe ser custodiada por el Laboratorio de Neurociencias Aplicadas – NeuroK como credencial institucional oficial del sistema. No compartir públicamente.

---

## 3. Repositorio de Código — GitHub

### ¿Qué es GitHub?

GitHub es la plataforma donde vive el **código fuente completo del sistema**. Es el punto de verdad (Single Source of Truth) de la arquitectura. Cualquier actualización que se haga al código se sube aquí primero, y automáticamente se propaga a Render.

### Datos del Repositorio

| Campo                         | Valor                                      |
| ----------------------------- | ------------------------------------------ |
| **URL del Repositorio** | https://github.com/Vivi271/Atena           |
| **Repositorio**         | Público (cualquiera puede leerlo)         |
| **Rama principal**      | `main`                                   |
| **Cuenta propietaria**  | `Vivi271` (cuenta personal de la autora) |

### Estructura del Repositorio

```
Atena/
├── api.py                  ← Servidor FastAPI (endpoints REST)
├── rag_pipeline.py         ← Lógica del RAG (búsqueda + IA)
├── config.py               ← Configuración del sistema
├── database.py             ← Gestión de métricas locales
├── app.py                  ← Interfaz Streamlit (local)
├── AtenaClient.cs          ← Script de C# para Unity
├── Dockerfile              ← Receta de construcción del servidor
├── requirements_docker.txt ← Librerías Python necesarias
├── .gitignore              ← Archivos ignorados por Git
├── components/             ← Componentes de la UI Streamlit
│   ├── sidebar.py
│   └── ...
└── Docs/                   ← Literatura científica indexada
    ├── El cerebro y la conducta...pdf
    ├── Neuroanatomia clinica 26va...pdf
    └── MODELO NEUROANATÓMICO 3D.docx
```

### ¿Qué es el Dockerfile?

El `Dockerfile` es simplemente un **archivo de texto plano** (como una receta) que le dice a Render:

1. Usar Python 3.11
2. Instalar las librerías necesarias
3. Copiar el código y los documentos
4. Iniciar el servidor FastAPI en el puerto 8080

**No tiene contraseñas ni datos personales.** Es público y puede ser leído por cualquier persona o plataforma de hosting para replicar el sistema.

### Cómo Agregar Colaboradores al Código (Sin dar contraseñas)

Si el Laboratorio desea tener acceso de escritura al código en GitHub:

1. Ingresar a: https://github.com/Vivi271/Atena/settings/access
2. Hacer clic en **"Add people"**
3. Buscar el usuario de GitHub del docente o investigador
4. Seleccionar el rol: **"Write"** (escritura) o **"Admin"** (administrador total)
5. El invitado recibirá un correo de confirmación

> ✅ El repositorio es **público**, lo que significa que cualquier persona puede ver el código y la documentación **sin necesidad de tener cuenta de GitHub**.

---

## 4. Backend en la Nube — Render.com

### ¿Qué es Render?

Render es la plataforma gratuita donde está desplegado el servidor que procesa las preguntas de los estudiantes y devuelve las respuestas de IA. Funciona como un servidor en la nube disponible 24/7.

### ¿Cómo se desplegó?

**Paso 1 — Crear cuenta:**

- Se ingresó a [dashboard.render.com/register](https://dashboard.render.com/register)
- Se seleccionó **"Continue with GitHub"** con la cuenta `Vivi271`

**Paso 2 — Crear el Web Service:**

- Se hizo clic en **"New +"** → **"Web Service"**
- Se seleccionó la pestaña **"Git Provider"** y se eligió el repositorio `Vivi271/Atena`

**Paso 3 — Configuración del servicio:**

| Campo             | Valor configurado                                            |
| ----------------- | ------------------------------------------------------------ |
| Name              | `Atena`                                                    |
| Region            | Oregon (US West)                                             |
| Runtime           | `Docker` (Render detectó el Dockerfile automáticamente)  |
| Instance Type     | **`Free`** ($0/mes)                                  |
| Auto-Deploy       | **Activado** (cada push al repo actualiza el servidor) |
| Health Check Path | `/salud`                                                   |

**Paso 4 — Variable de entorno:**

| Nombre             | Valor                                    |
| ------------------ | ---------------------------------------- |
| `GEMINI_API_KEY` | *(Clave secreta de Google Gemini API)* |

**Paso 5 — Despliegue:**

- Se hizo clic en **"Deploy Web Service"**
- Render leyó el `Dockerfile`, instaló Python, las librerías y el corpus de neuroanatomía
- En ~3 minutos el servicio quedó en estado: **✅ Live (Deployed)**

### ¿Cómo administrar Render?

1. Ingresar a [dashboard.render.com](https://dashboard.render.com)
2. Iniciar sesión con la cuenta `Vivi271` de GitHub *(o crear un nuevo despliegue con la cuenta `atena.unikonrad@gmail.com` usando Public Git Repository → `https://github.com/Vivi271/Atena`)*
3. En la lista de servicios, hacer clic en **"Atena"**
4. Desde el menú lateral, acceder a:
   - **Events** → Ver el historial de despliegues
   - **Logs** → Ver los logs en tiempo real
   - **Environment** → Cambiar variables de entorno (ej: actualizar la API Key)
   - **Settings** → Configuración general del servicio

### URL del Servicio (Producción)

```
https://atena-ic4u.onrender.com
```

---

## 5. Base de Datos NoSQL — Firebase Firestore

### ¿Qué es Firebase?

Firebase es la plataforma de Google para almacenamiento de datos en la nube en tiempo real. Es la capa del sistema donde se guardan los datos de uso y evaluaciones de los estudiantes.

### ¿Cómo se configuró?

**Paso 1 — Ingresar a Firebase:**

- Se ingresó a [console.firebase.google.com](https://console.firebase.google.com)
- Se inició sesión con la cuenta institucional: **`atena.unikonrad@gmail.com`**

**Paso 2 — Crear el Proyecto:**

- Se hizo clic en **"Para comenzar, configura un proyecto de Firebase"**
- **Nombre del proyecto:** `Atena`
- **ID automático del proyecto:** `atena-2d765`
- Se aceptaron los términos y condiciones de Firebase y Google Analytics
- Se hizo clic en **"Crear proyecto"**

**Paso 3 — Crear la base de datos Firestore:**

- En el menú lateral: **Bases de datos y almacenamiento** → **Cloud Firestore**
- Se hizo clic en **"Crear base de datos"**
- **Edición:** Standard (gratuita)
- **Ubicación de servidores:** `nam5 (United States)` *(mayor disponibilidad y velocidad para la región)*
- **Reglas de seguridad:** Modo de prueba *(permite lectura/escritura libre durante 30 días, suficiente para las pruebas del proyecto)*
- Se hizo clic en **"Crear"**

### ¿Qué queda guardado en Firestore?

Según el anteproyecto aprobado, Firestore almacena:

| Colección       | ¿Qué guarda?                                                                                                     |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| `evaluaciones` | Resultados de los quizzes de selección múltiple (pregunta, respuesta seleccionada, correcta/incorrecta, puntaje) |
| `consultas`    | Historial de preguntas realizadas al asistente de IA                                                               |
| `metricas`     | Tiempo de uso, estructuras visitadas, nivel seleccionado (básico/avanzado)                                        |
| `sesiones`     | Fecha, hora y perfil del usuario en cada sesión de uso                                                            |

### Cómo Acceder a la Consola de Firebase

1. Ingresar a [console.firebase.google.com](https://console.firebase.google.com)
2. Iniciar sesión con **`atena.unikonrad@gmail.com`** / `Se entregará de forma privada al administrador`
3. Seleccionar el proyecto **"Atena"** (ID: `atena-2d765`)
4. En el menú lateral, hacer clic en **Firestore Database** para ver los datos en tiempo real

---

## 6. Modelo de IA — Gemini API (Google AI Studio)

### ¿Qué es la Gemini API?

Es el modelo de inteligencia artificial (LLM) de Google que procesa las preguntas de los estudiantes y genera las respuestas especializadas en neuroanatomía. El sistema usa dos modelos:

| Uso                         | Modelo                   |
| --------------------------- | ------------------------ |
| Generar respuestas de texto | `gemini-2.5-flash`     |
| Crear vectores de búsqueda | `gemini-embedding-001` |

### API Key

La clave de acceso (API Key) es lo que autoriza al servidor en Render a usar la inteligencia de Gemini. Está configurada como variable de entorno privada en Render bajo el nombre `GEMINI_API_KEY`.

### Cómo Administrar la API Key Institucional

1. Ingresar a [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Iniciar sesión con **`atena.unikonrad@gmail.com`**
3. Desde ahí se puede ver la clave activa, crear nuevas claves o revocar el acceso si es necesario

---

## 7. API REST — Endpoints y Funcionamiento

### ¿Qué es una API REST?

Es la "ventanilla" de comunicación entre Unity (o cualquier cliente) y el servidor de Atena. Unity envía preguntas a la ventanilla y el servidor devuelve respuestas.

### URL Base

```
https://atena-ic4u.onrender.com
```

### Endpoints Disponibles

#### `GET /salud` — Health Check

Verifica que el servidor esté activo y que la base de conocimientos esté cargada.

**Respuesta de ejemplo:**

```json
{
  "estado": "ok",
  "servicio": "Atena API",
  "version": "1.0.0",
  "vector_store_listo": true
}
```

**Uso:** Verificar disponibilidad antes de la sustentación o demo.

---

#### `GET /info` — Información del Servicio

Muestra los detalles técnicos del sistema (modelos usados, descripción, endpoints).

**Respuesta de ejemplo:**

```json
{
  "nombre": "Atena — Consultor RAG de Neuroanatomía",
  "modelo_llm": "gemini-2.5-flash",
  "modelo_embeddings": "gemini-embedding-001",
  "endpoints": {
    "POST /consultar": "Enviar pregunta y recibir respuesta con fuentes",
    "GET /salud": "Health check",
    "GET /info": "Información del servicio"
  }
}
```

---

#### `POST /consultar` — Consulta al Asistente IA (Endpoint Principal)

Recibe una pregunta y devuelve la respuesta generada por IA con fuentes bibliográficas.

**JSON de entrada (Request Body):**

```json
{
  "pregunta": "¿Cuáles son las funciones del lóbulo frontal?",
  "nivel": "basico",
  "k": 6
}
```

| Campo        | Tipo    | Descripción                                                    |
| ------------ | ------- | --------------------------------------------------------------- |
| `pregunta` | String  | Texto de la pregunta del estudiante (obligatorio)               |
| `nivel`    | String  | `"basico"` o `"avanzado"` (por defecto `"avanzado"`)      |
| `k`        | Integer | Número de fragmentos del corpus a recuperar (por defecto`6`) |

**JSON de salida (Response):**

```json
{
  "respuesta": "El lóbulo frontal es responsable de las funciones ejecutivas...",
  "fuentes": [
    {
      "fuente": "Neuroanatomia clinica 26va Edición - Lange.pdf",
      "pagina": 214,
      "fragmento": "El lóbulo frontal ocupa la parte anterior del cerebro..."
    }
  ],
  "nivel": "basico"
}
```

---

#### `GET /docs` — Documentación Interactiva (Swagger UI)

Interfaz visual donde se pueden probar los endpoints directamente desde el navegador sin necesidad de escribir código.

**URL:** https://atena-ic4u.onrender.com/docs

---

### Cómo Funciona Internamente (Pipeline RAG)

Cuando Unity envía la pregunta `"¿Qué es el hipocampo?"`, el sistema:

```
1. Recibe la pregunta vía HTTP POST

2. Expande la pregunta con sinónimos y variaciones
   ("hipocampo" → "hippocampus", "formación hipocampal", etc.)

3. Búsqueda Híbrida en ChromaDB
   ├── Búsqueda vectorial (semántica): encuentra fragmentos por similitud de significado
   └── Búsqueda por palabras clave: encuentra coincidencias exactas de términos

4. Re-ranking: filtra y ordena los 6 mejores fragmentos por relevancia

5. Construcción del Prompt: combina la pregunta + los 6 fragmentos + instrucciones de nivel

6. Envío a Gemini API: el modelo genera la respuesta final en lenguaje apropiado al nivel

7. Retorna JSON con respuesta + fuentes bibliográficas a Unity
```

---

## 8. Script para Unity — AtenaClient.cs

### ¿Qué es?

Un script en C# que se agrega al proyecto de Unity para que la aplicación móvil pueda comunicarse con la API de Atena.

### Ubicación en el Repositorio

```
https://github.com/Vivi271/Atena/blob/main/AtenaClient.cs
```

### Cómo Instalarlo en Unity

1. Descargar el archivo `AtenaClient.cs` desde el repositorio de GitHub
2. Copiar el archivo dentro de la carpeta `Assets/Scripts/` del proyecto de Unity
3. En la escena principal, crear un `GameObject` vacío y nombrarlo `[NetworkManager]`
4. Arrastrar el script `AtenaClient.cs` al `GameObject`
5. En el Inspector de Unity, verificar que el campo **Base Url** diga: `https://atena-ic4u.onrender.com`

### Cómo Usarlo desde el Script del Chat

```csharp
// Cuando el usuario presiona "Enviar" en la interfaz del chat:
AtenaClient.Instance.ConsultarAsistente(
    inputField.text,           // Pregunta del estudiante
    "basico",                  // Nivel: "basico" o "avanzado"
    (respuesta) => {
        // Mostrar la respuesta de la IA en la interfaz
        panelChatTexto.text = respuesta.respuesta;
        // Las fuentes bibliográficas también están disponibles
        // foreach (var fuente in respuesta.fuentes) { ... }
    },
    (error) => {
        // Mostrar mensaje de error si no hay conexión
        panelChatTexto.text = "⚠️ Sin conexión. Verifica tu internet.";
        Debug.LogError("[Atena] Error: " + error);
    }
);
```

---

## 9. Cómo Ser Administrador del Sistema

### Acceso a cada plataforma

| Plataforma                           | URL                                                               | Credenciales                                                                            |
| ------------------------------------ | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **Render** (servidor API)      | [dashboard.render.com](https://dashboard.render.com)               | Iniciar sesión con GitHub`Vivi271` o crear nuevo despliegue con repositorio público |
| **Firebase** (base de datos)   | [console.firebase.google.com](https://console.firebase.google.com) | `atena.unikonrad@gmail.com` / `Se entregará de forma privada al administrador`                                       |
| **Google AI Studio** (API Key) | [aistudio.google.com](https://aistudio.google.com)                 | `atena.unikonrad@gmail.com` / `Se entregará de forma privada al administrador`                                       |
| **GitHub** (código fuente)    | [github.com/Vivi271/Atena](https://github.com/Vivi271/Atena)       | Repositorio público (solo lectura sin cuenta)                                          |

### ¿Qué puede hacer un administrador?

#### En Render:

- 🔁 Reiniciar el servidor manualmente
- 📋 Ver los logs en tiempo real (para detectar errores)
- 🔑 Cambiar la API Key de Gemini en las variables de entorno
- 📊 Ver métricas de uso del servidor (peticiones, tiempo de respuesta)
- 🆕 Re-desplegar una nueva versión al hacer push al repositorio

#### En Firebase:

- 👁️ Ver todos los datos de evaluaciones y métricas en tiempo real
- 🗑️ Eliminar datos si es necesario
- 📤 Exportar datos para análisis estadístico
- 🔐 Cambiar las reglas de seguridad de la base de datos

#### En Google AI Studio:

- 🔑 Crear nuevas API Keys o revocar accesos
- 📊 Ver el consumo del modelo de IA (cuántas peticiones se han hecho)
- 🚀 Habilitar acceso a nuevos modelos de Gemini cuando estén disponibles

---

## 10. Cómo Actualizar el Sistema en el Futuro

### Actualizar el Corpus Científico (Agregar nuevos libros)

Si el laboratorio desea agregar nuevos PDFs o documentos al sistema de conocimiento:

1. Agregar el nuevo PDF a la carpeta `Docs/` en el repositorio local o en GitHub
2. Hacer commit y push al repositorio: el servidor en Render se actualiza automáticamente
3. La próxima vez que un estudiante haga una consulta, el sistema indexará y considerará el nuevo documento

### Actualizar el Código (Mejoras o correcciones)

El sistema usa **Auto-Deploy** en Render: cualquier cambio que se suba al repositorio de GitHub (`git push`) automáticamente se refleja en el servidor en producción en ~2 minutos.

### Si el Servidor de Render se Duerme (Instancia Gratuita)

La instancia gratuita de Render "duerme" después de 15 minutos de inactividad. Cuando llega una nueva petición, tarda ~50 segundos en "despertar" (cold start). Para evitar esto en el día de la sustentación:

1. Abrir el navegador y acceder a: `https://atena-ic4u.onrender.com/salud` unos minutos antes de la demo
2. Esto "despierta" el servidor y queda listo para responder de inmediato

### Desplegar una Copia del Sistema (Para la Universidad)

Si la universidad desea tener su propio servidor independiente:

1. Ingresar a [render.com](https://render.com) con la cuenta `atena.unikonrad@gmail.com`
2. Hacer clic en **"New +"** → **"Web Service"**
3. Seleccionar la pestaña **"Public Git Repository"**
4. Pegar la URL: `https://github.com/Vivi271/Atena`
5. Configurar **Instance Type:** `Free` e ingresar la variable `GEMINI_API_KEY`
6. Hacer clic en **"Deploy Web Service"**

El sistema estará en vivo en ~3 minutos bajo una nueva URL propia de la universidad, sin depender de la cuenta personal de la autora.

---

## 11. Ficha Técnica Final de Entrega

| Elemento                              | Detalle                                   |
| ------------------------------------- | ----------------------------------------- |
| **Nombre del Sistema**          | Atena — Consultor RAG de Neuroanatomía  |
| **Componente Móvil**           | NeuroK AR (Unity + Vuforia, Android)      |
| **Institución**                | Fundación Universitaria Konrad Lorenz    |
| **Laboratorio**                 | Neurociencias Aplicadas – NeuroK         |
| **Autora**                      | Viviana Marcela García Valderrama        |
| **Año**                        | 2026                                      |
|                                       |                                           |
| **URL de la API (Producción)** | `https://atena-ic4u.onrender.com`       |
| **Documentación Interactiva**  | `https://atena-ic4u.onrender.com/docs`  |
| **Health Check**                | `https://atena-ic4u.onrender.com/salud` |
| **Repositorio de Código**      | `https://github.com/Vivi271/Atena`      |
|                                       |                                           |
| **Cuenta Institucional**        | `atena.unikonrad@gmail.com`             |
| **Contraseña Institucional**   | `Se entregará de forma privada al administrador`                         |
| **Servicios bajo esta cuenta**  | Firebase Console, Google AI Studio        |
|                                       |                                           |
| **Motor de IA**                 | Google Gemini 2.5 Flash                   |
| **Embeddings**                  | Gemini Embedding 001                      |
| **Base Vectorial**              | ChromaDB (corpus neuroanatómico)         |
| **Base de Datos en la Nube**    | Firebase Cloud Firestore                  |
| **ID Proyecto Firebase**        | `atena-2d765`                           |
| **Hosting Backend**             | Render.com (Plan Gratuito)                |
| **Costo mensual total**         | $0 USD                                    |

---

*Documento generado para la entrega formal del Proyecto de Grado — Programa de Psicología — Fundación Universitaria Konrad Lorenz — 2026.*
