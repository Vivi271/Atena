"""
database.py — Gestión de base de datos local SQLite para registrar métricas e historial
del Consultor IA en Neuroanatomía (Universidad Konrad Lorenz)
"""

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chroma_neuro_db", "neuro_metrics.db")

def get_connection():
    """Retorna una conexión a la base de datos con soporte para tipos de datos estándar."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Crea las tablas necesarias si no existen."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla de Consultas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consultas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        pregunta TEXT NOT NULL,
        respuesta TEXT NOT NULL,
        nivel TEXT NOT NULL,
        latencia REAL
    )
    """)
    
    # Tabla de Evaluaciones (Quiz)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evaluaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        pregunta TEXT NOT NULL,
        respuesta_usuario TEXT NOT NULL,
        respuesta_correcta TEXT NOT NULL,
        es_correcta INTEGER NOT NULL, -- 0 o 1
        explicacion TEXT NOT NULL
    )
    """)

    # Tabla de Preguntas del Examen (CRUD dinámico por administrador)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS preguntas_examen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nivel TEXT NOT NULL, -- 'básico' o 'avanzado'
        pregunta TEXT NOT NULL,
        opcion_a TEXT NOT NULL,
        opcion_b TEXT NOT NULL,
        opcion_c TEXT NOT NULL,
        opcion_d TEXT NOT NULL,
        correcta TEXT NOT NULL, -- 'A', 'B', 'C' o 'D'
        explicacion TEXT NOT NULL
    )
    """)
    
    # Insertar preguntas por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM preguntas_examen")
    if cursor.fetchone()[0] == 0:
        default_questions = [
            (
                "básico",
                "¿Qué tracto de fibras conecta los dos hemisferios cerebrales permitiendo su comunicación?",
                "Fórnix",
                "Cuerpo Calloso",
                "Cápsula Interna",
                "Comisura Anterior",
                "B",
                "El cuerpo calloso es el tracto de fibras comisurales más grande del cerebro, sirviendo de puente para compartir información entre ambos hemisferios."
            ),
            (
                "básico",
                "¿Cuál de los siguientes lóbulos aloja la corteza visual primaria?",
                "Lóbulo Frontal",
                "Lóbulo Temporal",
                "Lóbulo Occipital",
                "Lóbulo Parietal",
                "C",
                "El lóbulo occipital se encarga principalmente de procesar e integrar la información visual."
            ),
            (
                "básico",
                "Las neuronas dopaminérgicas cuya pérdida produce la enfermedad de Parkinson se encuentran principalmente en:",
                "El Hipocampo",
                "La Amígdala",
                "La Sustancia Negra (pars compacta)",
                "El Tálamo",
                "C",
                "La degeneración de las neuronas dopaminérgicas en la sustancia negra pars compacta es el hallazgo patológico central en el Parkinson."
            ),
            (
                "básico",
                "¿Qué estructura profunda del lóbulo temporal medial es crítica para la consolidación de la memoria a largo plazo?",
                "La Amígdala",
                "El Hipocampo",
                "El Cuerpo Estriado",
                "El Cíngulo",
                "B",
                "El hipocampo es fundamental para la formación de nuevos recuerdos episódicos y de largo plazo."
            ),
            (
                "básico",
                "¿Qué parte del sistema nervioso central está principalmente involucrada en la regulación emocional y de respuesta al miedo?",
                "Cerebelo",
                "Amígdala",
                "Corteza Motora Primaria",
                "Médula Espinal",
                "B",
                "La amígdala desempeña un papel clave en el procesamiento de emociones como el miedo y el condicionamiento conductual."
            ),
            (
                "avanzado",
                "¿Cuál es el principal neurotransmisor excitatorio en el sistema nervioso central de los mamíferos?",
                "GABA",
                "Glutamato",
                "Glicina",
                "Dopamina",
                "B",
                "El glutamato es el neurotransmisor excitador más abundante y fundamental para la plasticidad sináptica en el cerebro."
            ),
            (
                "avanzado",
                "¿Qué estructura forma el piso del tercer ventrículo?",
                "Tálamo",
                "Hipotálamo",
                "Epitálamo",
                "Habénula",
                "B",
                "El hipotálamo se localiza debajo del tálamo y constituye el piso y las paredes laterales inferiores del tercer ventrículo."
            ),
            (
                "avanzado",
                "¿Cuál de los siguientes tractos es el principal responsable del control motor voluntario fino y fraccionado de las extremidades?",
                "Tracto vestibuloespinal lateral",
                "Tracto corticoespinal lateral",
                "Tracto rubroespinal",
                "Tracto reticuloespinal medial",
                "B",
                "El tracto corticoespinal lateral (piramidal) es el encargado de la motricidad voluntaria fina, especialmente distal."
            ),
            (
                "avanzado",
                "¿Cuál de las siguientes estructuras no forma parte del circuito de Papez original?",
                "Hipocampo",
                "Cuerpos mamilares",
                "Corteza del cíngulo",
                "Amígdala",
                "D",
                "El circuito de Papez original incluye el hipocampo, fórnix, cuerpos mamilares, tracto mamilotalámico, núcleo anterior del tálamo, cíngulo y corteza entorrinal. La amígdala se integró en concepciones posteriores del sistema límbico."
            ),
            (
                "avanzado",
                "¿Qué síndrome clínico se caracteriza por ceguera cortical donde el paciente niega su déficit visual e inventa confabulaciones?",
                "Síndrome de Balint",
                "Síndrome de Anton",
                "Síndrome de Gerstmann",
                "Síndrome de Kluver-Bucy",
                "B",
                "El síndrome de Anton es una forma de anosognosia donde el paciente con ceguera cortical cree y afirma que puede ver."
            )
        ]
        cursor.executemany(
            "INSERT INTO preguntas_examen (nivel, pregunta, opcion_a, opcion_b, opcion_c, opcion_d, correcta, explicacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            default_questions
        )
    
    conn.commit()
    conn.close()

def registrar_consulta(pregunta: str, respuesta: str, nivel: str, latencia: float):
    """Registra una consulta realizada por el usuario en el RAG."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO consultas (pregunta, respuesta, nivel, latencia) VALUES (?, ?, ?, ?)",
            (pregunta, respuesta, nivel, latencia)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] No se pudo registrar la consulta: {e}")

def registrar_evaluacion(pregunta: str, respuesta_usuario: str, respuesta_correcta: str, es_correcta: bool, explicacion: str):
    """Registra la respuesta de un usuario en un Quiz de evaluación."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO evaluaciones (pregunta, respuesta_usuario, respuesta_correcta, es_correcta, explicacion) VALUES (?, ?, ?, ?, ?)",
            (pregunta, respuesta_usuario, respuesta_correcta, 1 if es_correcta else 0, explicacion)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] No se pudo registrar la evaluación: {e}")

def obtener_preguntas_por_nivel(nivel: str):
    """Retorna una lista de preguntas asociadas a un nivel específico ('básico' o 'avanzado')."""
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nivel, pregunta, opcion_a, opcion_b, opcion_c, opcion_d, correcta, explicacion FROM preguntas_examen WHERE nivel = ? ORDER BY id ASC",
            (nivel.lower(),)
        )
        rows = cursor.fetchall()
        preguntas = [dict(row) for row in rows]
        conn.close()
        return preguntas
    except Exception as e:
        print(f"[DB ERROR] Error al obtener preguntas por nivel: {e}")
        return []

def agregar_pregunta(nivel: str, pregunta: str, opcion_a: str, opcion_b: str, opcion_c: str, opcion_d: str, correcta: str, explicacion: str):
    """Agrega una nueva pregunta al banco de preguntas del examen."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO preguntas_examen (nivel, pregunta, opcion_a, opcion_b, opcion_c, opcion_d, correcta, explicacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nivel.lower(), pregunta, opcion_a, opcion_b, opcion_c, opcion_d, correcta.upper(), explicacion)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB ERROR] Error al agregar pregunta: {e}")
        return False

def actualizar_pregunta(id_pregunta: int, nivel: str, pregunta: str, opcion_a: str, opcion_b: str, opcion_c: str, opcion_d: str, correcta: str, explicacion: str):
    """Actualiza una pregunta existente por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE preguntas_examen
            SET nivel = ?, pregunta = ?, opcion_a = ?, opcion_b = ?, opcion_c = ?, opcion_d = ?, correcta = ?, explicacion = ?
            WHERE id = ?
            """,
            (nivel.lower(), pregunta, opcion_a, opcion_b, opcion_c, opcion_d, correcta.upper(), explicacion, id_pregunta)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB ERROR] Error al actualizar pregunta: {e}")
        return False

def eliminar_pregunta(id_pregunta: int):
    """Elimina una pregunta por su ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM preguntas_examen WHERE id = ?", (id_pregunta,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB ERROR] Error al eliminar pregunta: {e}")
        return False

def obtener_metricas():
    """
    Retorna un diccionario con estadísticas consolidadas para el
    Panel de Evaluación en Streamlit.
    """
    stats = {
        "total_consultas": 0,
        "consultas_basico": 0,
        "consultas_avanzado": 0,
        "latencia_promedio": 0.0,
        "total_evaluaciones": 0,
        "evaluaciones_correctas": 0,
        "porcentaje_aciertos": 0.0
    }
    
    if not os.path.exists(DB_PATH):
        return stats
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Métricas de Consultas
        cursor.execute("SELECT COUNT(*), AVG(latencia) FROM consultas")
        row = cursor.fetchone()
        if row and row[0] > 0:
            stats["total_consultas"] = row[0]
            stats["latencia_promedio"] = round(row[1], 2) if row[1] is not None else 0.0
            
        cursor.execute("SELECT COUNT(*) FROM consultas WHERE nivel = 'básico'")
        stats["consultas_basico"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM consultas WHERE nivel = 'avanzado'")
        stats["consultas_avanzado"] = cursor.fetchone()[0]
        
        # Métricas de Evaluaciones
        cursor.execute("SELECT COUNT(*), SUM(es_correcta) FROM evaluaciones")
        row_eval = cursor.fetchone()
        if row_eval and row_eval[0] > 0:
            stats["total_evaluaciones"] = row_eval[0]
            stats["evaluaciones_correctas"] = row_eval[1] or 0
            stats["porcentaje_aciertos"] = round((stats["evaluaciones_correctas"] / stats["total_evaluaciones"]) * 100, 1)
            
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] Error al obtener métricas: {e}")
        
    return stats

# Inicializar base de datos al importar el módulo
init_db()
