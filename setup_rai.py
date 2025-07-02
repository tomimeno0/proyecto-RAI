import os
import sqlite3
import subprocess
from datetime import datetime
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rai.db")

# ▶️ Carpetas donde está Discord seguro
RUTAS_EXE = [
    os.environ.get("ProgramFiles", r"C:\\Program Files"),
    os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"),
    os.path.expandvars(r"%LocalAppData%\Programs"),
    os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
    os.path.expandvars(r"%LocalAppData%")
]

def crear_tablas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS apps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        ruta_exe TEXT NOT NULL UNIQUE,
        tipo TEXT,
        categoria TEXT,
        ultima_vez_abierto TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS apps_uwp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        package_family_name TEXT,
        comando_abrir TEXT NOT NULL UNIQUE,
        ultima_vez_abierto TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS aplicaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('EXE', 'UWP')),
        comando TEXT NOT NULL,
        ultima_vez TEXT
    )""")
    conn.commit()
    conn.close()

def escanear_apps_exe():
    apps_encontradas = []
    for ruta_base in RUTAS_EXE:
        if not os.path.exists(ruta_base):
            continue
        for root, dirs, files in os.walk(ruta_base):
            for file in files:
                if file.lower().endswith(".exe"):
                    ruta_completa = os.path.join(root, file)
                    nombre_app = os.path.splitext(file)[0]
                    apps_encontradas.append((nombre_app, ruta_completa, "EXE"))
    return apps_encontradas

def escanear_apps_uwp():
    comando_powershell = r'''
    $ErrorActionPreference = "SilentlyContinue"
    $apps = Get-StartApps
    $list = @()

    foreach ($app in $apps) {
        $shell = New-Object -ComObject Shell.Application
        $folder = $shell.Namespace("shell:AppsFolder")
        $items = $folder.Items() | Where-Object { $_.Name -eq $app.Name }
        foreach ($item in $items) {
            $appid = $item.Path
            if ($appid) {
                $list += [PSCustomObject]@{
                    Name = $app.Name
                    AppUserModelID = $appid
                }
            }
        }
    }

    $list | ConvertTo-Json -Compress -Depth 3
    '''
    try:
        salida_bytes = subprocess.check_output(
            ["powershell", "-Command", comando_powershell],
            stderr=subprocess.DEVNULL
        )
        salida = salida_bytes.decode("utf-8", errors="ignore")
        apps = json.loads(salida)
        if isinstance(apps, dict):
            apps = [apps]

        lista_uwp = []
        for app in apps:
            nombre = app.get("Name", "")
            appid = app.get("AppUserModelID", "")
            if nombre and appid:
                comando_abrir = f'explorer.exe shell:appsFolder\\{appid}'
                lista_uwp.append((nombre, comando_abrir, "UWP"))
        return lista_uwp
    except Exception as e:
        print(f"❌ Error escaneando apps UWP: {e}")
        return []

def guardar_apps(apps_exe, apps_uwp):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for nombre, ruta_exe, tipo in apps_exe:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO apps (nombre, ruta_exe, tipo) VALUES (?, ?, ?)",
                (nombre, ruta_exe, tipo)
            )
        except Exception as e:
            print(f"Error insertando EXE: {nombre} - {e}")

    for nombre, comando_abrir, tipo in apps_uwp:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO apps_uwp (nombre, comando_abrir) VALUES (?, ?)",
                (nombre, comando_abrir)
            )
        except Exception as e:
            print(f"Error insertando UWP: {nombre} - {e}")

    conn.commit()
    conn.close()

def sincronizar_tabla_aplicaciones():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Limpiar tabla
    cursor.execute("DELETE FROM aplicaciones")

    # Insertar primero las UWP
    cursor.execute("""
        INSERT INTO aplicaciones (nombre, tipo, comando, ultima_vez)
        SELECT nombre, 'UWP', comando_abrir, ultima_vez_abierto FROM apps_uwp
    """)

    # Insertar EXE solo si no existe ya como UWP
    cursor.execute("""
        INSERT INTO aplicaciones (nombre, tipo, comando, ultima_vez)
        SELECT a.nombre, 'EXE', a.ruta_exe, a.ultima_vez_abierto
        FROM apps a
        WHERE NOT EXISTS (
            SELECT 1 FROM apps_uwp u WHERE LOWER(u.nombre) = LOWER(a.nombre)
        )
    """)

    conn.commit()
    conn.close()

def main():
    print("⏳ Creando tablas...")
    crear_tablas()
    print("🔍 Escaneando apps EXE...")
    apps_exe = escanear_apps_exe()
    print(f"✅ Encontradas {len(apps_exe)} apps EXE.")
    print("🔍 Escaneando apps UWP con PowerShell...")
    apps_uwp = escanear_apps_uwp()
    print(f"✅ Encontradas {len(apps_uwp)} apps UWP.")
    print("💾 Guardando apps en base de datos...")
    guardar_apps(apps_exe, apps_uwp)
    print("🔄 Sincronizando tabla unificada 'aplicaciones'...")
    sincronizar_tabla_aplicaciones()
    print("🎉 Setup completado.")

if __name__ == "__main__":
    main()
