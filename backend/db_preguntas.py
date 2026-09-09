"""
db_preguntas.py — Persistencia del banco de preguntas de evaluación
usando PostgreSQL (Supabase), con esquema normalizado:
niveles -> preguntas -> respuestas, temas -> preguntas.
"""

import os
import psycopg2
import psycopg2.extras
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("SUPABASE_DB_URL")


def _clean_db_url(url: str) -> str:
    if not url:
        return ""
    return url.replace('["', '').replace('"]', '').replace('[', '').replace(']', '').strip()


def get_connection():
    url = _clean_db_url(os.environ.get("SUPABASE_DB_URL") or DB_URL)
    if not url:
        raise RuntimeError("La variable de entorno SUPABASE_DB_URL no está configurada.")
    return psycopg2.connect(url)


def _normalizar_filtro_nivel(nivel: str) -> list:
    """Mapea sinónimos y alias al nombre registrado en Supabase."""
    n = (nivel or "").strip().lower()
    if n in ("basico", "básico", "principiante", "basic"):
        return ["principiante", "básico", "basico"]
    elif n in ("avanzado", "advanced"):
        return ["avanzado"]
    elif n in ("general",):
        return ["general"]
    return [n] if n else ["principiante", "avanzado", "general"]


def obtener_preguntas_por_nivel(nivel: str, cantidad: int = None, aleatorio: bool = False):
    """
    Retorna preguntas de un nivel dado, cada una con su lista de respuestas
    (texto + es_correcta), agrupadas desde el resultado plano del JOIN.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Normalizar alias de nivel para soportar basico, principiante, avanzado, etc.
        filtros_nivel = _normalizar_filtro_nivel(nivel)

        # Primero seleccionamos los IDs de preguntas del nivel (aleatorios o no, limitados)
        query_ids = """
            SELECT p.id
            FROM preguntas p
            JOIN niveles n ON p.nivel_id = n.id
            WHERE LOWER(n.nombre) = ANY(%s)
        """
        params = [filtros_nivel]

        if aleatorio:
            query_ids += " ORDER BY RANDOM()"
        else:
            query_ids += " ORDER BY p.id ASC"

        if cantidad:
            query_ids += " LIMIT %s"
            params.append(cantidad)

        cursor.execute(query_ids, tuple(params))
        ids_preguntas = [row["id"] for row in cursor.fetchall()]

        if not ids_preguntas:
            cursor.close()
            conn.close()
            return []

        # Traemos preguntas + respuestas + tema en un solo JOIN, filtrando por esos IDs
        cursor.execute(
            """
            SELECT
                p.id AS pregunta_id,
                p.enunciado,
                t.nombre AS tema,
                n.nombre AS nivel,
                r.id AS respuesta_id,
                r.texto AS respuesta_texto,
                r.es_correcta
            FROM preguntas p
            JOIN temas t ON p.tema_id = t.id
            JOIN niveles n ON p.nivel_id = n.id
            JOIN respuestas r ON r.pregunta_id = p.id
            WHERE p.id = ANY(%s)
            """,
            (ids_preguntas,)
        )
        filas = cursor.fetchall()
        cursor.close()
        conn.close()

        # Agrupamos las filas planas en preguntas con su lista de respuestas
        preguntas_dict = {}
        for fila in filas:
            pid = fila["pregunta_id"]
            if pid not in preguntas_dict:
                preguntas_dict[pid] = {
                    "id": pid,
                    "enunciado": fila["enunciado"],
                    "tema": fila["tema"],
                    "nivel": fila["nivel"],
                    "respuestas": []
                }
            preguntas_dict[pid]["respuestas"].append({
                "id": fila["respuesta_id"],
                "texto": fila["respuesta_texto"],
                "es_correcta": fila["es_correcta"]
            })

        # Mantenemos el orden aleatorio/original que definimos en ids_preguntas
        preguntas_ordenadas = [preguntas_dict[pid] for pid in ids_preguntas if pid in preguntas_dict]
        return preguntas_ordenadas

    except Exception as e:
        print(f"[DB_PREGUNTAS ERROR] Error al obtener preguntas: {e}")
        return []


def agregar_pregunta(nivel: str, tema: str, enunciado: str,
                      opcion_a: str, opcion_b: str, opcion_c: str, opcion_d: str, correcta: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM niveles WHERE LOWER(nombre) = LOWER(%s)", (nivel,))
        row_nivel = cursor.fetchone()
        cursor.execute("SELECT id FROM temas WHERE LOWER(nombre) = LOWER(%s)", (tema,))
        row_tema = cursor.fetchone()

        if not row_nivel or not row_tema:
            print(f"[DB_PREGUNTAS ERROR] Nivel o tema no encontrado: {nivel} / {tema}")
            cursor.close()
            conn.close()
            return False

        nivel_id, tema_id = row_nivel[0], row_tema[0]

        cursor.execute(
            "INSERT INTO preguntas (nivel_id, tema_id, enunciado) VALUES (%s, %s, %s) RETURNING id",
            (nivel_id, tema_id, enunciado)
        )
        pregunta_id = cursor.fetchone()[0]

        opciones = [opcion_a, opcion_b, opcion_c, opcion_d]
        letras = ["A", "B", "C", "D"]
        correcta_upper = correcta.upper()

        for letra, texto in zip(letras, opciones):
            cursor.execute(
                "INSERT INTO respuestas (pregunta_id, texto, es_correcta) VALUES (%s, %s, %s)",
                (pregunta_id, texto, letra == correcta_upper)
            )

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB_PREGUNTAS ERROR] Error al agregar pregunta: {e}")
        return False


def actualizar_pregunta(pregunta_id: int, nivel: str, tema: str, enunciado: str,
                         opcion_a: str, opcion_b: str, opcion_c: str, opcion_d: str, correcta: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM niveles WHERE LOWER(nombre) = LOWER(%s)", (nivel,))
        row_nivel = cursor.fetchone()
        cursor.execute("SELECT id FROM temas WHERE LOWER(nombre) = LOWER(%s)", (tema,))
        row_tema = cursor.fetchone()

        if not row_nivel or not row_tema:
            cursor.close()
            conn.close()
            return False

        nivel_id, tema_id = row_nivel[0], row_tema[0]

        cursor.execute(
            "UPDATE preguntas SET nivel_id = %s, tema_id = %s, enunciado = %s WHERE id = %s",
            (nivel_id, tema_id, enunciado, pregunta_id)
        )

        # Borramos las respuestas viejas y creamos las nuevas (más simple que hacer UPDATE una por una)
        cursor.execute("DELETE FROM respuestas WHERE pregunta_id = %s", (pregunta_id,))

        opciones = [opcion_a, opcion_b, opcion_c, opcion_d]
        letras = ["A", "B", "C", "D"]
        correcta_upper = correcta.upper()

        for letra, texto in zip(letras, opciones):
            cursor.execute(
                "INSERT INTO respuestas (pregunta_id, texto, es_correcta) VALUES (%s, %s, %s)",
                (pregunta_id, texto, letra == correcta_upper)
            )

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB_PREGUNTAS ERROR] Error al actualizar pregunta: {e}")
        return False


def eliminar_pregunta(pregunta_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE en la FK de respuestas se encarga de borrar las opciones asociadas
        cursor.execute("DELETE FROM preguntas WHERE id = %s", (pregunta_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB_PREGUNTAS ERROR] Error al eliminar pregunta: {e}")
        return False


def obtener_niveles():
    """Retorna la lista de nombres de nivel disponibles."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM niveles ORDER BY id")
        niveles = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return niveles
    except Exception as e:
        print(f"[DB_PREGUNTAS ERROR] Error al obtener niveles: {e}")
        return []


def obtener_temas():
    """Retorna la lista de nombres de tema disponibles."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM temas ORDER BY id")
        temas = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return temas
    except Exception as e:
        print(f"[DB_PREGUNTAS ERROR] Error al obtener temas: {e}")
        return []
