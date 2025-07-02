import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

def obtener_info_app(nombre_busqueda):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT nombre, tipo, comando, ultima_vez
        FROM aplicaciones
        WHERE LOWER(nombre) LIKE ?
        """,
        (f"%{nombre_busqueda.lower()}%",)
    )
    resultados = cursor.fetchall()
    conn.close()

    if not resultados:
        return f"🔍 No encontré ninguna app con el nombre '{nombre_busqueda}'."

    respuesta = "📦 Aplicaciones encontradas:\n"
    for nombre, tipo, comando, ultima_vez in resultados:
        dias = "nunca" if not ultima_vez else calcular_dias(ultima_vez)
        respuesta += f" - {nombre} ({tipo}) → Última vez abierto: {dias}\n"
    return respuesta.strip()

def sugerir_eliminacion(nombre_busqueda):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nombre, ultima_vez FROM aplicaciones WHERE LOWER(nombre) LIKE ?",
        (f"%{nombre_busqueda.lower()}%",)
    )
    resultado = cursor.fetchone()
    conn.close()

    if not resultado:
        return f"❌ No encontré ninguna app llamada '{nombre_busqueda}'."

    nombre, ultima_vez = resultado
    dias = calcular_dias(ultima_vez)
    if isinstance(dias, str) and dias.startswith("hace"):
        dias_num = int(dias.replace("hace", "").replace("días", "").strip())
        if dias_num > 20:
            return f"🧹 No usás '{nombre}' hace {dias_num} días. ¿Querés que te sugiera desinstalarla?"
        else:
            return f"✅ '{nombre}' se usó hace poco ({dias_num} días). No es necesario desinstalarla."
    else:
        return f"ℹ️ No hay suficiente info para evaluar si '{nombre}' debería desinstalarse."

def buscar_comando_por_nombre(nombre_app):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nombre, comando FROM aplicaciones WHERE LOWER(nombre) LIKE ?",
        (f"%{nombre_app.lower()}%",)
    )
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def actualizar_ultima_vez(nombre_app):
    ahora = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE aplicaciones SET ultima_vez = ? WHERE LOWER(nombre) LIKE ?",
        (ahora, f"%{nombre_app.lower()}%")
    )
    conn.commit()
    conn.close()