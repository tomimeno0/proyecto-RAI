import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rai.db")

def calcular_dias(fecha_iso):
    try:
        dt_fecha = datetime.fromisoformat(fecha_iso)
        ahora = datetime.now()
        diferencia = (ahora - dt_fecha).days
        if diferencia == 0:
            return "hoy"
        elif diferencia == 1:
            return "ayer"
        else:
            return f"hace {diferencia} días"
    except Exception:
        return "fecha inválida"

def buscar_comando_por_nombre(nombre_app):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Buscar en apps (tipo EXE)
    cursor.execute("""
        SELECT nombre, ruta_exe, 'exe' as tipo 
        FROM apps 
        WHERE LOWER(nombre) LIKE ?
    """, (f"%{nombre_app.lower()}%",))
    resultado = cursor.fetchone()
    if resultado:
        conn.close()
        return resultado  # (nombre, ruta_exe, 'exe')

    # Buscar en apps_uwp (tipo UWP)
    cursor.execute("""
        SELECT nombre, comando_abrir, 'uwp' as tipo 
        FROM apps_uwp 
        WHERE LOWER(nombre) LIKE ?
    """, (f"%{nombre_app.lower()}%",))
    resultado = cursor.fetchone()
    conn.close()
    if resultado:
        return resultado  # (nombre, comando_abrir, 'uwp')

    return None

def actualizar_ultima_vez(nombre_app):
    ahora = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Intentar actualizar apps (exe)
    cursor.execute("""
        UPDATE apps 
        SET ultima_vez_abierto = ? 
        WHERE LOWER(nombre) LIKE ?
    """, (ahora, f"%{nombre_app.lower()}%"))
    if cursor.rowcount == 0:
        # Si no se actualizó nada, probar apps_uwp (uwp)
        cursor.execute("""
            UPDATE apps_uwp 
            SET ultima_vez_abierto = ? 
            WHERE LOWER(nombre) LIKE ?
        """, (ahora, f"%{nombre_app.lower()}%"))

    conn.commit()
    conn.close()
