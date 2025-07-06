import os
import sqlite3
import subprocess
import json
import hashlib
import mimetypes
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rai.db")

RUTAS_EXE = [
    os.environ.get("ProgramFiles", r"C:\\Program Files"),
    os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"),
    os.path.expandvars(r"%LocalAppData%\\Programs"),
    os.path.expandvars(r"%AppData%\\Microsoft\\Windows\\Start Menu\\Programs"),
    os.path.expandvars(r"%LocalAppData%")
]

def crear_tablas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # apps EXE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            ruta_exe TEXT NOT NULL UNIQUE,
            tipo TEXT,
            categoria TEXT,
            ultima_vez_abierto TEXT,
            proceso_cierre TEXT
        )
    """)

    # apps UWP
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apps_uwp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            package_family_name TEXT,
            comando_abrir TEXT NOT NULL UNIQUE,
            ultima_vez_abierto TEXT
        )
    """)

    # tabla unificada para apps y comandos generales
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aplicaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('EXE', 'UWP', 'CMD')),
            comando TEXT NOT NULL,
            comando_cerrar TEXT,
            ultima_vez TEXT
        )
    """)

    # comandos generales sin nombre de app
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comandos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            comando TEXT NOT NULL UNIQUE,
            comando_cerrar TEXT
        )
    """)

    # Tabla para acciones como abrir, cerrar, reiniciar, etc.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_app TEXT NOT NULL,
            accion TEXT NOT NULL,
            comando TEXT NOT NULL,
            UNIQUE(nombre_app, accion)
        )
    """)

    # Tabla para archivos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS archivos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        ruta TEXT NOT NULL UNIQUE,
        extension TEXT,
        tamano INTEGER,
        ultima_modificacion TEXT,
        tipo_mime TEXT,
        hash_sha256 TEXT
    );
""")


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
                    proceso_cierre = file  # proceso para taskkill
                    apps_encontradas.append((nombre_app, ruta_completa, "EXE", proceso_cierre))
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

    for nombre, ruta_exe, tipo, proceso_cierre in apps_exe:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO apps (nombre, ruta_exe, tipo, proceso_cierre) VALUES (?, ?, ?, ?)",
                (nombre, ruta_exe, tipo, proceso_cierre)
            )
        except Exception as e:
            print(f"⚠️ Error insertando EXE: {nombre} - {e}")

    for nombre, comando_abrir, tipo in apps_uwp:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO apps_uwp (nombre, comando_abrir) VALUES (?, ?)",
                (nombre, comando_abrir)
            )
        except Exception as e:
            print(f"⚠️ Error insertando UWP: {nombre} - {e}")

    conn.commit()
    conn.close()


def insertar_comandos_generales():
    comandos = [
        ("Administrador de tareas", "taskmgr", "taskkill /IM taskmgr.exe /F"),
        ("Símbolo del sistema", "cmd", "taskkill /IM cmd.exe /F"),
        ("Calculadora", "calc", "taskkill /IM Calculator.exe /F"),
        ("Bloc de notas", "notepad", "taskkill /IM notepad.exe /F"),
        ("Explorador de archivos", "explorer", "taskkill /IM explorer.exe /F"),
        ("Centro de movilidad", "mblctr", None),
        ("Configuración", "start ms-settings:", None),
        ("Panel de control", "control", None),
        ("Desinstalar programas", "appwiz.cpl", None),
        ("Ejecutar", "explorer shell:AppsFolder\\Microsoft.Windows.Run_8wekyb3d8bbwe!App", None),
        ("Windows Update", "control update", None),
        ("Servicios", "services.msc", None),
        ("Visor de eventos", "eventvwr", None),
        ("Monitor de recursos", "resmon", None),
        ("Administrador de dispositivos", "devmgmt.msc", None),
        ("Windows Defender", "start windowsdefender:", None),
        ("Centro de seguridad de Windows Defender", "windowsdefender:", None),
        ("Windows PowerShell", "powershell", "taskkill /IM powershell.exe /F"),
        ("Bloc de notas++", "notepad++", "taskkill /IM notepad++.exe /F"),
        ("Reproductor de Windows Media", "wmplayer", "taskkill /IM wmplayer.exe /F"),
        ("Microsoft Edge", "start msedge", None),
        ("Google Chrome", "start chrome", None),
        ("Mozilla Firefox", "start firefox", None),
        ("Microsoft Word", "start winword", None),
        ("Microsoft Excel", "start excel", None),
        ("Microsoft PowerPoint", "start powerpnt", None),
        ("Spotify", "start spotify", "taskkill /IM spotify.exe /F"),
        ("Skype", "start skype", "taskkill /IM skype.exe /F"),
        ("Discord", "start discord", "taskkill /IM discord.exe /F"),
        ("Zoom", "start zoom", "taskkill /IM zoom.exe /F"),
        ("Teams", "start teams", "taskkill /IM Teams.exe /F"),
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for desc, cmd_abrir, cmd_cerrar in comandos:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO comandos (descripcion, comando, comando_cerrar) VALUES (?, ?, ?)",
                (desc, cmd_abrir, cmd_cerrar)
            )
        except Exception as e:
            print(f"Error insertando comando {desc}: {e}")

    conn.commit()
    conn.close()


def sincronizar_tabla_aplicaciones():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Limpiar tabla unificada aplicaciones
    cursor.execute("DELETE FROM aplicaciones")
    # Limpiar tabla acciones
    cursor.execute("DELETE FROM acciones")

    # Insertar UWP en aplicaciones
    cursor.execute("""
        INSERT INTO aplicaciones (nombre, tipo, comando, ultima_vez)
        SELECT nombre, 'UWP', comando_abrir, ultima_vez_abierto FROM apps_uwp
    """)

    # Insertar EXE en aplicaciones con comando abrir y cerrar
    cursor.execute("""
        INSERT INTO aplicaciones (nombre, tipo, comando, comando_cerrar, ultima_vez)
        SELECT 
            nombre,
            'EXE',
            ruta_exe,
            'taskkill /IM ' || proceso_cierre || ' /F',
            ultima_vez_abierto
        FROM apps
        WHERE NOT EXISTS (
            SELECT 1 FROM apps_uwp u WHERE LOWER(u.nombre) = LOWER(apps.nombre)
        )
    """)

    # Insertar CMD en aplicaciones desde tabla comandos
    cursor.execute("""
        INSERT INTO aplicaciones (nombre, tipo, comando, comando_cerrar)
        SELECT descripcion, 'CMD', comando, comando_cerrar FROM comandos
    """)

    # Insertar acciones para UWP (solo abrir)
    cursor.execute("""
        INSERT OR IGNORE INTO acciones (nombre_app, accion, comando)
        SELECT nombre, 'abrir', comando_abrir FROM apps_uwp
    """)

    # Insertar acciones para EXE (abrir y cerrar)
    cursor.execute("""
        INSERT OR IGNORE INTO acciones (nombre_app, accion, comando)
        SELECT nombre, 'abrir', ruta_exe FROM apps
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO acciones (nombre_app, accion, comando)
        SELECT nombre, 'cerrar', 'taskkill /IM ' || proceso_cierre || ' /F' FROM apps
    """)

    # Insertar acciones para CMD (abrir y cerrar si existe)
    cursor.execute("""
        INSERT OR IGNORE INTO acciones (nombre_app, accion, comando)
        SELECT descripcion, 'abrir', comando FROM comandos
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO acciones (nombre_app, accion, comando)
        SELECT descripcion, 'cerrar', comando_cerrar FROM comandos WHERE comando_cerrar IS NOT NULL
    """)

    conn.commit()
    conn.close()

def crear_tabla_acciones():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_app TEXT NOT NULL,
            accion TEXT NOT NULL CHECK(accion IN (
                'abrir', 'cerrar', 'reiniciar', 'cerrar_suavemente',
                'terminar_proceso', 'minimizar', 'maximizar', 'restaurar',
                'ocultar', 'mostrar', 'enfocar', 'suspender', 'reanudar',
                'desinstalar', 'actualizar'
            )),
            comando TEXT NOT NULL,
            UNIQUE(nombre_app, accion)
        )
    """)
    conn.commit()
    conn.close()

def insertar_acciones_exe():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT nombre, ruta_exe, proceso_cierre FROM apps")
    apps = cursor.fetchall()

    for nombre, ruta, proceso in apps:
        acciones = {
            "abrir": f'start "" "{ruta}"',
            "cerrar": f'taskkill /IM {proceso} /F',
            "cerrar_suavemente": f'taskkill /IM {proceso}',
            "reiniciar": f'taskkill /IM {proceso} /F && start "" "{ruta}"',
            "terminar_proceso": f'taskkill /IM {proceso} /T /F'
        }

        for accion, comando in acciones.items():
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO acciones (nombre_app, accion, comando)
                    VALUES (?, ?, ?)
                """, (nombre, accion, comando))
            except Exception as e:
                print(f"⚠️ Error insertando acción {accion} para {nombre}: {e}")

    conn.commit()
    conn.close()

def insertar_acciones_complejas():
    acciones = [
        # nombre_app, accion, comando
        ("Discord", "abrir", "start discord"),
        ("Discord", "cerrar", "taskkill /IM discord.exe /F"),
        ("Discord", "reiniciar", "taskkill /IM discord.exe /F && start discord"),

        ("Spotify", "abrir", "start spotify"),
        ("Spotify", "cerrar", "taskkill /IM spotify.exe /F"),
        ("Spotify", "reiniciar", "taskkill /IM spotify.exe /F && start spotify"),

        ("Zoom", "abrir", "start zoom"),
        ("Zoom", "cerrar", "taskkill /IM zoom.exe /F"),
        ("Zoom", "desinstalar", 'powershell "Get-AppxPackage *zoom* | Remove-AppxPackage"'),

        ("Calculadora", "cerrar", "taskkill /IM Calculator.exe /F"),
        ("Calculadora", "reiniciar", "taskkill /IM Calculator.exe /F && start calc"),

        ("WhatsApp", "abrir", "start whatsapp"),
        ("WhatsApp", "cerrar", "taskkill /IM whatsapp.exe /F"),
        ("WhatsApp", "reiniciar", "taskkill /IM whatsapp.exe /F && start whatsapp"),

        ("Google Chrome", "cerrar", "taskkill /IM chrome.exe /F"),
        ("Google Chrome", "reiniciar", "taskkill /IM chrome.exe /F && start chrome"),

        ("Bloc de notas", "cerrar", "taskkill /IM notepad.exe /F"),
        ("Bloc de notas", "reiniciar", "taskkill /IM notepad.exe /F && start notepad"),

        ("Visual Studio Code", "cerrar", "taskkill /IM Code.exe /F"),
        ("Visual Studio Code", "reiniciar", "taskkill /IM Code.exe /F && start code"),

        ("Teams", "cerrar", "taskkill /IM Teams.exe /F"),
        ("Teams", "reiniciar", "taskkill /IM Teams.exe /F && start teams"),

        ("Skype", "cerrar", "taskkill /IM skype.exe /F"),
        ("Skype", "reiniciar", "taskkill /IM skype.exe /F && start skype"),
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for nombre_app, accion, comando in acciones:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO acciones (nombre_app, accion, comando) VALUES (?, ?, ?)",
                (nombre_app, accion, comando)
            )
        except Exception as e:
            print(f"⚠️ Error insertando acción '{accion}' para '{nombre_app}': {e}")
    conn.commit()
    conn.close()

# ========================
# 🔍 ESCANEO DE ARCHIVOS
# ========================


CARPETAS_POR_DEFECTO = [
    os.path.expandvars(r"%UserProfile%\Desktop"),
    os.path.expandvars(r"%UserProfile%\Documents"),
    os.path.expandvars(r"%UserProfile%\Downloads"),
    # podés agregar más carpetas o discos enteros si querés
]

def crear_tabla_archivos_completa():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS archivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            ruta TEXT NOT NULL UNIQUE,
            extension TEXT,
            tamano INTEGER,
            ultima_modificacion TEXT,
            tipo_mime TEXT,
            hash_sha256 TEXT
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_archivos_nombre ON archivos(nombre);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_archivos_extension ON archivos(extension);")
    conn.commit()
    conn.close()

def calcular_hash_sha256(ruta_archivo, bloque_tamano=65536):
    sha256 = hashlib.sha256()
    try:
        with open(ruta_archivo, "rb") as f:
            while True:
                bloque = f.read(bloque_tamano)
                if not bloque:
                    break
                sha256.update(bloque)
        return sha256.hexdigest()
    except Exception:
        return None

def escanear_carpeta(ruta_base, extensiones=None):
    archivos_encontrados = []
    for root, dirs, files in os.walk(ruta_base, topdown=True):
        for file in files:
            ruta_completa = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            if extensiones and ext not in extensiones:
                continue
            try:
                tamano = os.path.getsize(ruta_completa)
                mod_time = os.path.getmtime(ruta_completa)
                fecha_mod = datetime.fromtimestamp(mod_time).isoformat()
                tipo_mime, _ = mimetypes.guess_type(ruta_completa)
                archivos_encontrados.append({
                    "nombre": file,
                    "ruta": ruta_completa,
                    "extension": ext,
                    "tamano": tamano,
                    "ultima_modificacion": fecha_mod,
                    "tipo_mime": tipo_mime or "desconocido"
                })
            except Exception:
                continue
    return archivos_encontrados

def insertar_o_actualizar_archivo(conn, archivo):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO archivos (nombre, ruta, extension, tamano, ultima_modificacion, tipo_mime, hash_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ruta) DO UPDATE SET
            nombre=excluded.nombre,
            extension=excluded.extension,
            tamano=excluded.tamano,
            ultima_modificacion=excluded.ultima_modificacion,
            tipo_mime=excluded.tipo_mime,
            hash_sha256=excluded.hash_sha256;
    """, (
        archivo["nombre"],
        archivo["ruta"],
        archivo["extension"],
        archivo["tamano"],
        archivo["ultima_modificacion"],
        archivo["tipo_mime"],
        archivo.get("hash_sha256")
    ))
    conn.commit()

def escanear_y_guardar_archivos(carpeta, extensiones=None, calcular_hash=False):
    print(f"📁 Escaneando: {carpeta}")
    archivos = escanear_carpeta(carpeta, extensiones)
    conn = sqlite3.connect(DB_PATH)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futuros = []
        for archivo in archivos:
            if calcular_hash:
                futuros.append(executor.submit(calcular_hash_sha256, archivo["ruta"]))
            else:
                futuros.append(None)

        for i, archivo in enumerate(archivos):
            if calcular_hash and futuros[i]:
                archivo["hash_sha256"] = futuros[i].result()
            insertar_o_actualizar_archivo(conn, archivo)

    conn.close()
    print(f"✅ {len(archivos)} archivos guardados de {carpeta}")

def eliminar_archivos_borrados():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT ruta FROM archivos")
    rutas = cursor.fetchall()

    eliminados = 0
    for (ruta,) in rutas:
        if not os.path.exists(ruta):
            cursor.execute("DELETE FROM archivos WHERE ruta = ?", (ruta,))
            eliminados += 1

    conn.commit()
    conn.close()
    print(f"🗑️ Eliminados {eliminados} archivos inexistentes.")

def escanear_todo_el_sistema_de_archivos():
    crear_tabla_archivos_completa()
    for carpeta in CARPETAS_POR_DEFECTO:
        escanear_y_guardar_archivos(carpeta, extensiones=None, calcular_hash=False)
    eliminar_archivos_borrados()

def verificar_integridad_tablas():
    print("🔍 Verificando integridad de tablas...")

    tablas_necesarias = {
        "apps": ["id", "nombre", "ruta_exe", "tipo", "categoria", "ultima_vez_abierto", "proceso_cierre"],
        "apps_uwp": ["id", "nombre", "package_family_name", "comando_abrir", "ultima_vez_abierto"],
        "aplicaciones": ["id", "nombre", "tipo", "comando", "comando_cerrar", "ultima_vez"],
        "comandos": ["id", "descripcion", "comando", "comando_cerrar"],
        "acciones": ["id", "nombre_app", "accion", "comando"],
        "archivos": ["id", "nombre", "ruta", "extension", "tamano", "ultima_modificacion", "tipo_mime", "hash_sha256"],
    }

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for tabla, columnas_esperadas in tablas_necesarias.items():
        cursor.execute(f"PRAGMA table_info({tabla})")
        columnas_encontradas = [fila[1] for fila in cursor.fetchall()]

        faltantes = [col for col in columnas_esperadas if col not in columnas_encontradas]

        if not columnas_encontradas:
            print(f"❌ ERROR: La tabla '{tabla}' no existe.")
        elif faltantes:
            print(f"⚠️ La tabla '{tabla}' existe pero le faltan columnas: {faltantes}")
        else:
            print(f"✅ Tabla '{tabla}' verificada con columnas correctas.")

    conn.close()




def main():
    print("⏳ Creando tablas...")
    crear_tablas()
    crear_tabla_acciones()
    verificar_integridad_tablas()

    print("🔍 Escaneando apps EXE...")
    apps_exe = escanear_apps_exe()
    print(f"✅ Encontradas {len(apps_exe)} apps EXE.")

    print("🔍 Escaneando apps UWP con PowerShell...")
    apps_uwp = escanear_apps_uwp()
    print(f"✅ Encontradas {len(apps_uwp)} apps UWP.")

    print("💾 Guardando apps en base de datos...")
    guardar_apps(apps_exe, apps_uwp)

    print("🔨 Insertando comandos generales...")
    insertar_comandos_generales()

    print("🔄 Sincronizando tabla unificada 'aplicaciones'...")
    sincronizar_tabla_aplicaciones()

    print("💥 Generando acciones por app EXE...")
    insertar_acciones_exe()

    print("📥 Insertando acciones complejas...")
    insertar_acciones_complejas()

    print("🗂️ Escaneando archivos del sistema...")
    escanear_todo_el_sistema_de_archivos()


    print("🎉 Setup completado.")



if __name__ == "__main__":
    main()
