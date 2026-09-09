"""
config.py — Constantes y configuración del Consultor de Neuroanatomía
"""
import os
import re
from dotenv import load_dotenv
load_dotenv()

# PIN de acceso administrador (se puede cambiar aquí o en el archivo .env)
ADMIN_PIN = os.getenv("ADMIN_PIN", "1234")

# Mapeo MANUAL de nombres conocidos → títulos legibles
# Si un archivo NO está aquí, el sistema genera un nombre bonito automáticamente
_MAPEO_MANUAL = {
    "El cerebro y la conducta Neuroanatomía para psicólogos.pdf": "El Cerebro y la Conducta — Neuroanatomía para Psicólogos",
    "MODELO NEUROANATÓMICO 3D.docx": "Manual de Modelo Neuroanatómico 3D",
    "Neuroanatomia clinica  26va Edición - Lange.pdf": "Neuroanatomía Clínica (26ª Ed.) — Lange",
    "0717-9502-ijmorphol-41-04-996.pdf": "Regla Simple para el Aprendizaje de la Neuroanatomía",
    "circir_25_93_2_197-201.pdf": "Modelos 3D y Realidad Aumentada en Neuroanatomía",
    "SCT_2025_1250.pdf": "Tecnologías Inmersivas vs. Convencionales en la Enseñanza",
}


def nombre_legible(filename: str) -> str:
    """
    Dado un nombre de archivo (ej: 'mi_articulo_2025.pdf'), devuelve un
    título legible. Primero busca en el mapeo manual; si no lo encuentra,
    genera uno limpio automáticamente quitando extensiones, guiones bajos, etc.
    """
    # 1. Buscar en el mapeo manual
    if filename in _MAPEO_MANUAL:
        return _MAPEO_MANUAL[filename]

    # 2. Generar nombre bonito automáticamente
    nombre = filename
    # Quitar extensión
    nombre = re.sub(r'\.(pdf|docx|doc)$', '', nombre, flags=re.IGNORECASE)
    # Reemplazar guiones bajos y guiones por espacios
    nombre = nombre.replace("_", " ").replace("-", " ")
    # Limpiar espacios múltiples
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    # Capitalizar cada palabra
    nombre = nombre.title()
    return nombre


# Para compatibilidad con el código existente que usa MAPEO_NOMBRES.get(archivo, fallback)
# ahora es un diccionario que se actualiza dinámicamente
MAPEO_NOMBRES = _MAPEO_MANUAL.copy()


# Frases que indican que el sistema no encontró información
NO_INFO_PHRASES = [
    "no se encuentra en los documentos", "no está en los documentos",
    "no hay información", "no tengo información",
    "plantee su consulta", "formula una pregunta",
    "pregunta específica", "no encontr",
]

# Mensajes de cortesía predefinidos (respuestas instantáneas)
MENSAJE_BIENVENIDA = (
    "¡Hola! Soy **Atena**, tu asistente de neuroanatomía en la Konrad Lorenz.\n\n"
    "Puedo resolver tus dudas sobre anatomía del sistema nervioso, circuitos neuronales "
    "y funciones cerebrales. ¿En qué tema profundizamos hoy?"
)

MENSAJE_DESPEDIDA = (
    "¡Con gusto! Aquí estaré cuando necesites repasar o consultar cualquier tema de neuroanatomía. "
    "¡Muchos éxitos en tu estudio!"
)

# Saludos y mensajes de cortesía estrictos (no requieren búsqueda vectorial)
SALUDOS = {
    "hola", "hello", "hi", "hey", "buenas", "buenos", "dias", "días", "tardes",
    "noches", "gracias", "muchas", "de", "nada", "ok", "okay", "si", "sí", "no",
    "perfecto", "genial", "bien", "mal", "como", "cómo", "estas", "estás", "esta", "está",
    "va", "tal", "que", "qué", "atena", "athena", "bot", "asistente",
    "adios", "adiós", "bye", "chao", "hasta", "luego", "saludos",
}

def es_consulta_saludo(texto: str) -> bool:
    """Detecta si la consulta del usuario es estrictamente un saludo o cortesía corta."""
    if not texto:
        return False
    limpio = re.sub(r"[^\w\s]", "", texto.strip().lower())
    palabras = limpio.split()
    if not palabras:
        return False
    return len(palabras) <= 5 and all(p in SALUDOS for p in palabras)

def obtener_respuesta_cortesia(texto: str):
    """Retorna el mensaje de bienvenida o despedida si la entrada es un saludo/cortesía."""
    if not es_consulta_saludo(texto):
        return None
    t_lower = texto.lower()
    if any(w in t_lower for w in ["gracias", "adios", "adiós", "chao", "bye", "hasta luego"]):
        return MENSAJE_DESPEDIDA
    return MENSAJE_BIENVENIDA

# Ejemplos de consulta para la interfaz
EJEMPLOS_CONSULTA = [
    ("¿Cuáles son los lóbulos cerebrales y sus funciones principales?",
     "El Lange y El cerebro y la conducta describen los lóbulos frontales, parietales, temporales y occipitales con sus roles funcionales."),
    ("¿Qué es la sustancia negra y qué rol cumple en el sistema nervioso?",
     "Consulta la descripción del complejo nigral: neuronas dopaminérgicas, vías nigroestriatales y relación con el Parkinson."),
    ("¿Cómo se clasifican las neuronas según su función y morfología?",
     "Los libros describen neuronas aferentes, eferentes, interneuronas, unipolares, bipolares y multipolares."),
    ("¿Qué es el sistema límbico y cómo influye en la conducta?",
     "Consulta cómo el hipocampo, amígdala e hipotálamo integran emociones, memoria y motivación."),
    ("¿Cuál es la diferencia entre materia gris y materia blanca?",
     "Busca la descripción histológica y funcional de ambos tipos de tejido nervioso según el Lange."),
    ("¿Qué es el reflejo miotático y cómo se produce?",
     "El Lange describe el arco reflejo, los husos neuromusculares y los reflejos tendinosos profundos."),
]


# ── Directrices de Estructura de Respuesta del Agente ────────────────────────
# Estas constantes definen el COMPORTAMIENTO de presentación del agente Atena.
# Se mantienen separadas del dominio académico-científico (rag_pipeline.py)
# para respetar el principio de separación de responsabilidades (SRP).
RESPONSE_STRUCTURE_BASICO = (
    "Organiza la respuesta con fluidez y claridad pedagógica: "
    "inicia con una breve introducción que sitúe el concepto consultado, "
    "desarrolla los componentes principales en apartados claramente delimitados, "
    "y concluye con una síntesis sobre su relevancia funcional."
)

RESPONSE_STRUCTURE_AVANZADO = (
    "Estructura la respuesta con cohesión expositiva de alto nivel: "
    "inicia con una contextualización neuroanatómica formal del sistema o región, "
    "desarrolla cada subdivisión, circuito o componente en bloques temáticos bien separados, "
    "y finaliza con una síntesis integradora sobre el correlato funcional o clínico."
)


def obtener_enlace_cloudflare() -> str:
    """
    Lee el archivo de logs del túnel Cloudflare y extrae la URL generada.
    """
    import os
    log_path = "/app/shared_logs/tunnel.log"
    if not os.path.exists(log_path):
        # Fallback local fuera del contenedor
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shared_logs", "tunnel.log")
        if not os.path.exists(log_path):
            return None
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
        urls = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
        if urls:
            return urls[-1]
    except Exception:
        pass
    return None

