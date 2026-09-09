"""
db_metrics.py — Persistencia de métricas y registros de uso en Supabase (PostgreSQL).
Reemplaza database.py (SQLite) con almacenamiento persistente en la nube.

Tablas necesarias en Supabase (ejecutar en SQL Editor):
────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS consultas (
    id BIGSERIAL PRIMARY KEY,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    nivel TEXT NOT NULL,
    latencia REAL
);

CREATE TABLE IF NOT EXISTS evaluaciones (
    id BIGSERIAL PRIMARY KEY,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    pregunta TEXT NOT NULL,
    respuesta_usuario TEXT NOT NULL,
    respuesta_correcta TEXT NOT NULL,
    es_correcta BOOLEAN NOT NULL,
    explicacion TEXT NOT NULL
);
────────────────────────────────────────────────────────
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("SUPABASE_DB_URL")


def _clean_db_url(url: str) -> str:
    if not url:
        return ""
    return url.replace('["', '').replace('"]', '').replace('[', '').replace(']', '').strip()


def _get_conn():
    url = _clean_db_url(os.environ.get("SUPABASE_DB_URL") or DB_URL)
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL no está configurada en el .env. "
            "Cópiala desde Supabase → Settings → Database → URI."
        )
    return psycopg2.connect(url)


# ── Registro de consultas RAG ─────────────────────────────────────────────────

def registrar_consulta(pregunta: str, respuesta: str, nivel: str, latencia: float):
    """Registra una consulta del usuario al RAG en Supabase."""
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO consultas (pregunta, respuesta, nivel, latencia) VALUES (%s, %s, %s, %s)",
                    (pregunta, respuesta, nivel, latencia)
                )
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] No se pudo registrar la consulta: {e}")


# ── Registro de evaluaciones (quiz) ──────────────────────────────────────────

def registrar_evaluacion(
    pregunta: str,
    respuesta_usuario: str,
    respuesta_correcta: str,
    es_correcta: bool,
    explicacion: str,
):
    """Registra la respuesta de un usuario en un quiz de evaluación."""
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO evaluaciones
                       (pregunta, respuesta_usuario, respuesta_correcta, es_correcta, explicacion)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (pregunta, respuesta_usuario, respuesta_correcta, es_correcta, explicacion)
                )
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] No se pudo registrar la evaluación: {e}")


# ── Métricas para el panel de administración ─────────────────────────────────

def obtener_metricas() -> dict:
    """
    Retorna un diccionario con estadísticas consolidadas para el
    panel de administración de Streamlit.
    """
    stats = {
        "total_consultas": 0,
        "consultas_basico": 0,
        "consultas_avanzado": 0,
        "latencia_promedio": 0.0,
        "total_evaluaciones": 0,
        "evaluaciones_correctas": 0,
        "porcentaje_aciertos": 0.0,
    }
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            # Total y latencia promedio
            cur.execute("SELECT COUNT(*), AVG(latencia) FROM consultas")
            row = cur.fetchone()
            if row and row[0] > 0:
                stats["total_consultas"] = row[0]
                stats["latencia_promedio"] = round(row[1], 2) if row[1] else 0.0

            # Por nivel
            cur.execute("SELECT COUNT(*) FROM consultas WHERE nivel = 'básico'")
            stats["consultas_basico"] = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM consultas WHERE nivel = 'avanzado'")
            stats["consultas_avanzado"] = cur.fetchone()[0]

            # Evaluaciones
            cur.execute("SELECT COUNT(*), SUM(CASE WHEN es_correcta THEN 1 ELSE 0 END) FROM evaluaciones")
            row_eval = cur.fetchone()
            if row_eval and row_eval[0] > 0:
                stats["total_evaluaciones"] = row_eval[0]
                stats["evaluaciones_correctas"] = row_eval[1] or 0
                stats["porcentaje_aciertos"] = round(
                    (stats["evaluaciones_correctas"] / stats["total_evaluaciones"]) * 100, 1
                )
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] Error al obtener métricas: {e}")

    return stats
