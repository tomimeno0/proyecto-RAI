import sqlite3
from datetime import datetime
import subprocess

DB_PATH = "rai.db"

def obtener_info_app(nombre_busqueda):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, ruta_exe, ultima_vez_abierto FROM apps WHERE LOWER(nombre) LIKE ?", (f"%{nombre_busqueda.lower()}%",))
    resultado = cursor.fetchall()
    conn.close()

    if not resultado:
        return f"🔍 No encontré ninguna app con el nombre '{nombre_busqueda}'."

    respuesta = "📦 Aplicaciones encontradas:\n"
    for nombre, ruta, ultima_vez in resultado:
        dias = "nunca" if not ultima_vez else calcular_dias(ultima_vez)
        respuesta += f" - {nombre} → Ruta: {ruta} | Última vez abierto: {dias}\n"
    return respuesta.strip()

def calcular_dias(fecha_iso):
    try:
        dt = datetime.fromisoformat(fecha_iso)
        ahora = datetime.now()
        diferencia = (ahora - dt).days
        if diferencia == 0:
            return "hoy"
        elif diferencia == 1:
            return "ayer"
        else:
            return f"hace {diferencia} días"
    except:
        return "fecha inválida"

def sugerir_eliminacion(nombre_busqueda):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, ruta_exe, ultima_vez_abierto FROM apps WHERE LOWER(nombre) LIKE ?", (f"%{nombre_busqueda.lower()}%",))
    resultado = cursor.fetchone()
    conn.close()

    if not resultado:
        return f"❌ No encontré ninguna app llamada '{nombre_busqueda}'."

    nombre, ruta, ultima_vez = resultado
    dias = calcular_dias(ultima_vez)
    if isinstance(dias, str) and dias.startswith("hace"):
        dias_num = int(dias.replace("hace", "").replace("días", "").strip())
        if dias_num > 20:
            return f"🧹 No usás '{nombre}' hace {dias_num} días. ¿Querés que te sugiera desinstalarla?"
        else:
            return f"✅ '{nombre}' se usó hace poco ({dias_num} días). No es necesario desinstalarla."
    else:
        return f"ℹ️ No hay suficiente info para evaluar si '{nombre}' debería desinstalarse."
    
def buscar_ruta_por_nombre(nombre_app):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, ruta_exe FROM apps WHERE LOWER(nombre) LIKE ?", ('%' + nombre_app.lower() + '%',))
    resultado = cursor.fetchone()
    conn.close()
    return resultado  # None si no encontró

def actualizar_ultima_vez(nombre_app):
    ahora = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE apps SET ultima_vez_abierto = ? WHERE LOWER(nombre) LIKE ?", (ahora, '%' + nombre_app.lower() + '%'))
    conn.commit()
    conn.close()

def crear_tabla_uwp():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apps_uwp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        package_family_name TEXT,
        comando_abrir TEXT,
        ultima_vez_abierto TEXT
    )
    """)
    conn.commit()
    conn.close()

def obtener_apps_uwp():
    cmd = 'powershell "Get-AppxPackage | Select-Object Name, PackageFamilyName | ConvertTo-Json"'
    resultado = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if resultado.returncode != 0:
        print("❌ Error al ejecutar PowerShell para obtener apps UWP")
        return []

    import json
    apps = json.loads(resultado.stdout)
    lista_apps = []
    for app in apps:
        nombre = app.get('Name', '')
        pkg_family = app.get('PackageFamilyName', '')
        if nombre and pkg_family:
            comando_abrir = f'explorer shell:AppsFolder\\{pkg_family}!App'
            lista_apps.append({
                'nombre': nombre,
                'package_family_name': pkg_family,
                'comando_abrir': comando_abrir
            })
    return lista_apps

def insertar_o_actualizar_uwp(nombre, pkg_family, comando):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apps_uwp WHERE package_family_name = ?", (pkg_family,))
    existe = cursor.fetchone()
    ahora = datetime.datetime.now().isoformat()
    if existe:
        cursor.execute("""
            UPDATE apps_uwp SET nombre = ?, comando_abrir = ?, ultima_vez_abierto = ?
            WHERE package_family_name = ?
        """, (nombre, comando, ahora, pkg_family))
    else:
        cursor.execute("""
            INSERT INTO apps_uwp (nombre, package_family_name, comando_abrir, ultima_vez_abierto)
            VALUES (?, ?, ?, ?)
        """, (nombre, pkg_family, comando, ahora))
    conn.commit()
    conn.close()

def escanear_apps_uwp():
    print("🔍 Escaneando apps UWP de Microsoft Store...")
    crear_tabla_uwp()
    apps = obtener_apps_uwp()
    for app in apps:
        insertar_o_actualizar_uwp(app['nombre'], app['package_family_name'], app['comando_abrir'])
        print(f"✅ Registrada UWP: {app['nombre']}")
    print("🏁 Escaneo UWP finalizado.")

def buscar_uwp_por_nombre(nombre_app):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, comando_abrir FROM apps_uwp WHERE LOWER(nombre) LIKE ?", ('%' + nombre_app.lower() + '%',))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

