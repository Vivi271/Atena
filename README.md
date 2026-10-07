# Atena — Consultor RAG de Neuroanatomía

Sistema de Inteligencia Artificial que actúa como **consultor científico especializado en neuroanatomía**. Diseñado para responder consultas académicas y clínicas basándose **exclusivamente** en literatura científica indexada, implementando una arquitectura **RAG (Retrieval-Augmented Generation)** conectada con **Groq Cloud LPU** y expuesta mediante una **API REST en FastAPI**.

---

## Descripción General

**Atena** procesa textos académicos en neuroanatomía (PDF y DOCX), los fragmenta e indexa vectorialmente con **ChromaDB + ONNX Runtime** (`all-MiniLM-L6-v2`). Ante las consultas de estudiantes, aplica **Búsqueda Híbrida** y **Fuzzy Matching** para recuperar la evidencia más relevante, inyectándola como contexto a un modelo de lenguaje de última generación (**Groq LPU — `openai/gpt-oss-120b`**).

### Características Principales

- **Velocidad extrema:** Más de 350 tokens/segundo gracias al hardware LPU de Groq. Latencia < 0.9 s.
- **Cero alucinaciones:** Respuestas fundamentadas únicamente en el corpus indexado, con directiva de abstención si la información no existe en los textos.
- **Trazabilidad académica:** Cada afirmación se referencia con `[Fuente X, pág. Y]`.
- **Fuzzy Matching:** Corrección automática de términos mal escritos (`hipicampo`  `hipocampo`).
- **Bajo consumo de RAM:** ONNX Runtime < 140 MB (operación estable en Render plan gratuito de 512 MiB).
- **Doble nivel pedagógico:** Respuestas para nivel **Básico** (estudiantes iniciales) y **Avanzado** (psicología, medicina, investigadores).
- **API REST multiplataforma:** Endpoints para Unity (C#), móvil, web o herramientas analíticas.
- **Persistencia en la nube:** Supabase (PostgreSQL) para banco de preguntas, evaluaciones y métricas de uso.
- **Panel de Administración Web:** Gestión de documentos, banco de preguntas, estadísticas y cambio de PIN desde el navegador.

---

## Arquitectura del Sistema

```
Clientes
 Unity / NeuroK AR (C#)  
 Web — Chat + Panel Admin (frontend/web/static/)         POST /consultar
 Swagger UI (/docs)                                      GET  /api/*
                                                           
                              api.py  (FastAPI — Render.com Docker)
                                  
                    
                                                
           rag_pipeline.py               db_metrics.py / db_preguntas.py
       (Búsqueda híbrida + Fuzzy)       (Supabase PostgreSQL)
                    
       
                                
ChromaDB + ONNX               Groq Cloud LPU
(all-MiniLM-L6-v2)       (openai/gpt-oss-120b)
```

---

## Servicios en la Nube (Producción)

| Servicio | URL / Acceso |
|---|---|
| API REST | `https://atena-vugz.onrender.com` |
| Swagger (Documentación) | `https://atena-vugz.onrender.com/docs` |
| Health Check | `https://atena-vugz.onrender.com/salud` |
| Chat web | `https://atena-vugz.onrender.com` |
| Panel de administración | `https://atena-vugz.onrender.com/admin.html` |
| Base de datos | Supabase (PostgreSQL) |

---

## Endpoints de la API REST

### `POST /consultar`

Recibe una consulta de neuroanatomía y devuelve la respuesta del consultor con fuentes bibliográficas.

**Request:**
```json
{
  "pregunta": "Cuáles son las funciones del hipocampo?",
  "nivel": "avanzado",
  "k": 5
}
```

**Response:**
```json
{
  "respuesta": "El hipocampo es una estructura del sistema límbico... [Neuroanatomia clinica.pdf, pág. 214]",
  "fuentes": [
    {
      "fuente": "Neuroanatomia clinica 26va Edición - Lange.pdf",
      "pagina": 214,
      "fragmento": "El hipocampo forma parte del arquicórtex..."
    }
  ],
  "nivel": "avanzado"
}
```

### `GET /salud`

```json
{
  "estado": "activo",
  "servicio": "Atena API REST",
  "version": "3.0.0",
  "vector_store_listo": true,
  "documentos_indexados": 352
}
```

### `GET /info`

Retorna información técnica sobre los modelos activos y capacidades del pipeline.

### Endpoints de Admin (requieren header `X-Admin-Pin`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/admin/documents` | Lista documentos indexados |
| `POST` | `/api/admin/upload` | Sube y vectoriza un nuevo documento |
| `DELETE` | `/api/admin/documents/{nombre}` | Elimina un documento del índice |
| `GET` | `/api/admin/stats_sesion` | Estadísticas de uso (desde Supabase) |
| `POST` | `/api/admin/cambiar-pin` | Cambia el PIN de acceso al panel |
| `GET` | `/api/admin/preguntas` | Lista el banco de preguntas |
| `POST` | `/api/admin/preguntas` | Agrega una pregunta de evaluación |
| `PUT` | `/api/admin/preguntas/{id}` | Edita una pregunta |
| `DELETE` | `/api/admin/preguntas/{id}` | Elimina una pregunta |
| `GET` | `/diagnostico/db` | Verifica conectividad con Supabase |

---

## Tablas en Supabase

Ejecutar una sola vez en el SQL Editor de Supabase:

```sql
-- Consultas de usuarios al RAG
CREATE TABLE IF NOT EXISTS consultas (
    id BIGSERIAL PRIMARY KEY,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    nivel TEXT NOT NULL,
    latencia REAL
);

-- Respuestas de evaluaciones (quiz)
CREATE TABLE IF NOT EXISTS evaluaciones (
    id BIGSERIAL PRIMARY KEY,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    pregunta TEXT NOT NULL,
    respuesta_usuario TEXT NOT NULL,
    respuesta_correcta TEXT NOT NULL,
    es_correcta BOOLEAN NOT NULL,
    explicacion TEXT NOT NULL
);

-- PIN de administrador (cambiable desde el panel)
CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
INSERT INTO configuracion (clave, valor) VALUES ('admin_pin', '12345')
    ON CONFLICT (clave) DO NOTHING;
```

---

## Integración con Unity (C#)

```csharp
AtenaClient.Instance.ConsultarAsistente(
    "Qué es la sustancia negra?",
    "avanzado",
    (response) => {
        Debug.Log("Respuesta IA: " + response.respuesta);
    },
    (error) => {
        Debug.LogError("Error de red: " + error);
    }
);
```

Archivo: [`frontend/unity/AtenaClient.cs`](frontend/unity/AtenaClient.cs)

---

## Ejecución Local (Desarrollo)

### Requisitos

- Python 3.10 o 3.11
- Clave de API de Groq Cloud: [console.groq.com](https://console.groq.com)
- URL de conexión a Supabase (PostgreSQL)

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/Vivi271/Atena.git
cd Atena

# 2. Crear y activar entorno virtual
python3 -m venv env
source env/bin/activate       # Windows: env\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear archivo .env
GROQ_API_KEY=gsk_tu_clave_aqui
SUPABASE_DB_URL=postgresql://usuario:clave@host:5432/postgres
ADMIN_PIN=12345
```

### Iniciar servidor

```bash
PYTHONPATH=backend uvicorn backend.api:app --reload --port 8080
```

| URL | Descripción |
|---|---|
| `http://localhost:8080` | Chat web |
| `http://localhost:8080/admin.html` | Panel de administración |
| `http://localhost:8080/docs` | Swagger / Documentación interactiva |

---

## Interfaz Web

### Landing page (slider de diapositivas)

La landing page está diseñada como una presentación de pantalla completa con transiciones fluidas:

| Diapositiva | Contenido |
|---|---|
| 1 — Hero | Título, descripción, botones de acción, cerebro SVG animado, red neuronal en canvas |
| 2 — Características | 6 tarjetas de funcionalidades con iconos SVG |
| 3 — Cómo funciona | Flujo de 3 pasos + botones de acción + footer |

Navegación: flechas `` ``, puntos indicadores, teclas de flecha del teclado y swipe táctil.

### Autoevaluación

Quiz de neuroanatomía accesible desde el navbar o el hero. Flujo:

1. Selección de nivel: **Principiante / General / Avanzado / Todos los niveles**
2. 10 preguntas aleatorias del nivel elegido
3. Feedback inmediato por pregunta (colorea opción + mensaje "Correcto / Incorrecto — La respuesta correcta es: X")
4. Resultado final con nota sobre 5.0 y porcentaje de aciertos

### Responsividad

| Breakpoint | Comportamiento |
|---|---|
| `> 900px` | Layout completo con dos columnas, navegación horizontal |
| ` 900px` | Navbar colapsado (hamburguesa), hero en 1 columna, cerebro oculto |
| ` 600px` | Chat panel full-width, flechas del slider al pie, texto compacto |

---

## Panel de Administración

Accesible en `/admin.html`, protegido por PIN. Funcionalidades:

- **Documentos:** Ver, subir y eliminar documentos del índice vectorial en tiempo real.
- **Banco de preguntas:** Crear, editar y eliminar preguntas de evaluación por nivel.
- **Estadísticas:** Consultas históricas desde Supabase — total, latencia promedio, distribución por nivel, temas frecuentes y listado filtrable.
- **Sistema:** Estado de salud del servidor, banco de evaluaciones y cambio de PIN desde el navegador (sin necesidad de acceder a Render).

---

## Literatura Científica Indexada

1. **Neuroanatomía Clínica (26. Edición)** — Stephen G. Waxman (Lange / McGraw-Hill)
2. **El Cerebro y la Conducta: Neuroanatomía para Psicólogos** — Clark, Boutros, Mendez
3. **Manual de Modelo Neuroanatómico 3D** — Laboratorio de Neurociencias Aplicadas (NeuroK)

---

## Estructura del Repositorio

```
Atena/
 backend/
    api.py              # FastAPI — endpoints REST y panel admin
    rag_pipeline.py     # Motor RAG: carga, chunking, vectorización, búsqueda
    db_metrics.py       # Persistencia de métricas y PIN en Supabase
    db_preguntas.py     # Banco de preguntas (Supabase)
    config.py           # Variables de entorno y configuración
 frontend/
    web/
        static/
            index.html      # Chat web principal
            admin.html      # Panel de administración
            css/main.css    # Sistema de diseño (light/dark mode)
            js/
                app.js      # Lógica del chat
                admin.js    # Lógica del panel admin
 Docs/                   # Literatura científica indexada (PDF/DOCX)
 tesis/                  # Scripts auxiliares para el documento de grado
 Dockerfile              # Imagen Docker para Render
 render.yaml             # Configuración de despliegue en Render.com
 requirements.txt        # Dependencias Python
```

---

## Licencia y Créditos

Proyecto desarrollado en el marco del trabajo de grado de la **Fundación Universitaria Konrad Lorenz** para el **Laboratorio de Neurociencias Aplicadas — NeuroK**.

- **Autores:** Viviana Marcela García Valderrama — Braian Felipe Ramirez Ortiz
- **Institución:** Fundación Universitaria Konrad Lorenz (2026)
