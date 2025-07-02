import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rai.db")

def crear_tabla_aplicaciones():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aplicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            comando TEXT NOT NULL,
            ultima_vez TEXT
        )
    """)
    conn.commit()
    conn.close()

def migrar_datos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Migrar apps tradicionales (EXE)
    cursor.execute("SELECT nombre, tipo, ruta_exe, ultima_vez_abierto FROM apps")
    apps = cursor.fetchall()
    for nombre, tipo, ruta_exe, ultima_vez in apps:
        comando = ruta_exe
        cursor.execute("""
            INSERT OR REPLACE INTO aplicaciones (nombre, tipo, comando, ultima_vez)
            VALUES (?, ?, ?, ?)
        """, (nombre, tipo, comando, ultima_vez))

    # Migrar apps UWP
    cursor.execute("SELECT nombre, tipo, comando_abrir, ultima_vez_abierto FROM apps_uwp")
    apps_uwp = cursor.fetchall()
    for nombre, tipo, comando_abrir, ultima_vez in apps_uwp:
        comando = comando_abrir
        cursor.execute("""
            INSERT OR REPLACE INTO aplicaciones (nombre, tipo, comando, ultima_vez)
            VALUES (?, ?, ?, ?)
        """, (nombre, tipo, comando, ultima_vez))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    crear_tabla_aplicaciones()
    migrar_datos()
    print("Migración completada.")
