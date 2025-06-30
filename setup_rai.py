import os
import sqlite3
import datetime
import subprocess

usuario = os.getlogin()
BASES = [
    f"C:\\Users\\{usuario}\\AppData\\Local",
    "C:\\Program Files",
    "C:\\Program Files (x86)"
]

DB_PATH = "rai.db"

def crear_tabla_si_no_existe():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        ruta_exe TEXT,
        tipo TEXT,
        categoria TEXT,
        ultima_vez_abierto TEXT
    )
    """)
    conn.commit()
    conn.close()

def clasificar(nombre, ruta):
    nombre_lower = nombre.lower()
    if "game" in ruta or "steam" in ruta or "epic" in ruta or "riot" in ruta:
        return ("juego", "entretenimiento")
    elif "chrome" in nombre_lower or "firefox" in nombre_lower or "edge" in nombre_lower:
        return ("navegador", "comunicación")
    elif "office" in ruta or "word" in nombre_lower or "excel" in nombre_lower:
        return ("ofimática", "productividad")
    else:
        return ("desconocido", "otro")

def insertar_si_no_existe(nombre, ruta, tipo, categoria):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apps WHERE ruta_exe = ?", (ruta,))
    existente = cursor.fetchone()

    if not existente:
        ahora = datetime.datetime.now().isoformat()
        cursor.execute("INSERT INTO apps (nombre, ruta_exe, tipo, categoria, ultima_vez_abierto) VALUES (?, ?, ?, ?, ?)",
                       (nombre, ruta, tipo, categoria, ahora))
        print(f"✅ Registrada: {nombre} ({ruta})")
    conn.commit()
    conn.close()

def escanear():
    print("🔍 Escaneando carpetas para encontrar .exe...")
    for base in BASES:
        for root, dirs, files in os.walk(base):
            for file in files:
                if file.lower().endswith(".exe"):
                    ruta_completa = os.path.join(root, file)
                    tipo, categoria = clasificar(file, ruta_completa)
                    insertar_si_no_existe(file, ruta_completa, tipo, categoria)
    print("🏁 Escaneo finalizado.")

if __name__ == "__main__":
    crear_tabla_si_no_existe()
    escanear()
