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


def obtener_consultas_recientes(limite: int = 20) -> list:
    """Retorna las N consultas más recientes."""
    rows = []
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT fecha, pregunta, nivel, latencia FROM consultas ORDER BY fecha DESC LIMIT %s",
                (limite,)
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return rows


def obtener_preguntas_frecuentes(limite: int = 10) -> list:
    """Retorna las preguntas más repetidas por los usuarios."""
    rows = []
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT pregunta, COUNT(*) AS veces, AVG(latencia) AS latencia_avg
                   FROM consultas GROUP BY pregunta ORDER BY veces DESC LIMIT %s""",
                (limite,)
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return rows


def obtener_volumen_diario(dias: int = 30) -> list:
    """Retorna el número de consultas por día para los últimos N días."""
    rows = []
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT DATE(fecha) AS dia, COUNT(*) AS total, AVG(latencia) AS latencia_avg
                   FROM consultas
                   WHERE fecha >= NOW() - INTERVAL '%s days'
                   GROUP BY dia ORDER BY dia""",
                (dias,)
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return rows


def obtener_distribucion_niveles() -> dict:
    """Retorna conteo de consultas por nivel."""
    dist = {}
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT nivel, COUNT(*) AS total FROM consultas GROUP BY nivel ORDER BY total DESC")
            for row in cur.fetchall():
                dist[row["nivel"]] = row["total"]
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return dist


def obtener_precision_evaluaciones() -> list:
    """Retorna precisión por pregunta de evaluación (% aciertos)."""
    rows = []
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT pregunta,
                          COUNT(*) AS intentos,
                          SUM(CASE WHEN es_correcta THEN 1 ELSE 0 END) AS aciertos,
                          ROUND(100.0 * SUM(CASE WHEN es_correcta THEN 1 ELSE 0 END) / COUNT(*), 1) AS porcentaje
                   FROM evaluaciones GROUP BY pregunta ORDER BY porcentaje ASC LIMIT 15"""
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return rows


def obtener_tendencia_aciertos_diaria(dias: int = 30) -> list:
    """Retorna el porcentaje de aciertos en evaluaciones por día."""
    rows = []
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT DATE(fecha) AS dia,
                          COUNT(*) AS intentos,
                          ROUND(100.0 * SUM(CASE WHEN es_correcta THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_aciertos
                   FROM evaluaciones
                   WHERE fecha >= NOW() - INTERVAL '%s days'
                   GROUP BY dia ORDER BY dia""",
                (dias,)
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return rows

