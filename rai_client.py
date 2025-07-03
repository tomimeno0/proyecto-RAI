# rai_client.py

import os
import re
import time
import json
import psutil
import sqlite3
import datetime
import threading
import subprocess
import requests
import pygetwindow as gw
import pyautogui
import speech_recognition as sr
import keyboard
from consultas_apps import buscar_comando_por_nombre, actualizar_ultima_vez

DB_NAME = "rai.db"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)
SERVER_URL = "http://127.0.0.1:5000/orden"
usuario = os.getlogin()
texto_acumulado = ""

def crear_tablas_si_no_existen():
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

def abrir_app_desde_db(nombre_app):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT ruta_exe FROM apps WHERE LOWER(nombre) LIKE ?", (f"%{nombre_app.lower()}%",))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            ruta = resultado[0]
            subprocess.Popen(f'start "" "{ruta}"', shell=True)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            ahora = datetime.datetime.now().isoformat()
            cursor.execute("UPDATE apps SET ultima_vez_abierto = ? WHERE ruta_exe = ?", (ahora, ruta))
            conn.commit()
            conn.close()

            print(f"🚀 Abrí la app '{nombre_app}' desde la base de datos.")
            return True
        else:
            print(f"❌ No encontré '{nombre_app}' en la base de datos.")
            return False

    except Exception as e:
        print(f"⚠️ Error abriendo app desde DB: {e}")
        return False

def abrir_app_uwp_desde_db(nombre_app):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT comando_abrir FROM apps_uwp WHERE LOWER(nombre) LIKE ?", (f"%{nombre_app.lower()}%",))
        resultado = cursor.fetchone()
        conn.close()

        if resultado and resultado[0]:
            comando = resultado[0]
            subprocess.Popen(comando, shell=True)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            ahora = datetime.datetime.now().isoformat()
            cursor.execute("UPDATE apps_uwp SET ultima_vez_abierto = ? WHERE comando_abrir = ?", (ahora, comando))
            conn.commit()
            conn.close()

            print(f"🚀 Abrí la app UWP '{nombre_app}' desde la base de datos.")
            return True
        else:
            print(f"❌ No encontré '{nombre_app}' o no tiene comando válido en apps_uwp.")
            return False

    except Exception as e:
        print(f"⚠️ Error abriendo app UWP desde DB: {e}")
        return False

def cerrar_app_desde_db(nombre_busqueda):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT ruta_exe FROM apps WHERE LOWER(nombre) LIKE ?", (f"%{nombre_busqueda.lower()}%",))
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            print(f"❌ No encontré ninguna app llamada '{nombre_busqueda}' en la base de datos.")
            return False

        ruta_exe = resultado[0]
        nombre_proceso = os.path.basename(ruta_exe)
        subprocess.run(["taskkill", "/f", "/im", nombre_proceso], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"❌ Cerrada la app: {nombre_proceso}")
        return True

    except Exception as e:
        print(f"⚠️ No se pudo cerrar la app: {e}")
        return False

def escaner_inteligente(tipo):
    try:
        if tipo == "ram":
            procesos = sorted(psutil.process_iter(['pid', 'name', 'memory_info']), key=lambda p: p.info['memory_info'].rss, reverse=True)
            print("🧠 Procesos con mayor uso de RAM:")
            for proc in procesos[:10]:
                print(f" - {proc.info['name']} (PID: {proc.info['pid']}) - {proc.info['memory_info'].rss / (1024*1024):.2f} MB")
        elif tipo == "cpu":
            procesos = sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), key=lambda p: p.info['cpu_percent'], reverse=True)
            print("🔥 Procesos con más uso de CPU:")
            for proc in procesos[:10]:
                print(f" - {proc.info['name']} (PID: {proc.info['pid']}) - {proc.info['cpu_percent']}%")
        elif tipo.startswith("disco"):
            letra = tipo.split(":")[1].upper() if ":" in tipo else "TODOS"
            particiones = psutil.disk_partitions() if letra == "TODOS" else [p for p in psutil.disk_partitions() if p.device.upper().startswith(letra + ":")]
            print("💽 Estado del disco:")
            for p in particiones:
                try:
                    uso = psutil.disk_usage(p.mountpoint)
                    print(f"🗂️ Disco {p.device} ({p.mountpoint}): Total: {uso.total / (1024**3):.2f} GB | Usado: {uso.used / (1024**3):.2f} GB | Libre: {uso.free / (1024**3):.2f} GB | {uso.percent}% usado\n")
                except PermissionError:
                    continue
        else:
            print(f"❓ Tipo de escaneo no reconocido: {tipo}")
    except Exception as e:
        print(f"⚠️ Error en escaneo: {e}")

def ejecutar_accion_ventana(accion, nombre_ventana):
    try:
        ventana = next((w for w in gw.getWindowsWithTitle(nombre_ventana)), None)
        if ventana:
            if accion == "maximizar": ventana.maximize()
            elif accion == "minimizar": ventana.minimize()
            elif accion == "enfocar": ventana.activate()
            print(f"🎯 Acción '{accion}' ejecutada sobre '{nombre_ventana}'.")
        else:
            raise ValueError("ventana_no_encontrada")
    except Exception as e:
        raise RuntimeError(f"Error en acción de ventana: {e}")

def listar_ventanas_y_procesos():
    print("🪟 Ventanas abiertas:")
    for w in gw.getAllWindows():
        if w.title: print(f" - {w.title}")
    print("\n⚙️ Procesos activos:")
    for proc in psutil.process_iter(['name']):
        nombre = proc.info['name']
        if nombre: print(f" - {nombre}")

def procesar_emocion_y_puntuacion(texto):
    texto = texto.strip()
    if texto.endswith(("que", "como", "donde", "cuando", "por qué")) or texto.lower().startswith(("qué ", "cómo ", "cuándo ", "dónde ", "por qué ")):
        return texto[0].upper() + texto[1:] + "?"
    emocion = ["dale", "vamos", "sí", "listo", "buenísimo", "perfecto", "increíble", "genial", "me encanta", "de una"]
    for palabra in emocion:
        if re.search(rf"\b{palabra}\b", texto.lower()):
            return texto[0].upper() + texto[1:] + "!"
    texto = re.sub(r"\b(osea|oseas|eh|emm|mm+)\b", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s{2,}", " ", texto).strip()
    return texto[0].upper() + texto[1:] + ("." if not texto.endswith((".", "!", "?")) else "")

def grabar_y_procesar_orden():
    global texto_acumulado
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("🎤 Escuchando tu orden (hablá)...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=None)
    print("⏹️ Procesando orden...")
    try:
        texto = recognizer.recognize_google(audio, language="es-AR")
        texto = procesar_emocion_y_puntuacion(texto)
        print(f'🧩 Fragmento capturado: "{texto}"')
        texto_acumulado += " " + texto
        texto_acumulado = texto_acumulado.strip()
        print(f'📦 Mensaje acumulado: "{texto_acumulado}"')
    except sr.UnknownValueError:
        print("🤷‍♂️ No entendí lo que dijiste.")
    except sr.RequestError as e:
        print(f"❌ Error de reconocimiento: {e}")
    enviar_mensaje_final()

def escucha_hotword():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("👂 Decí 'okey RAI' para dar una orden...")
        while True:
            try:
                audio = r.listen(source, phrase_time_limit=2)
                texto = r.recognize_google(audio, language="es-AR").lower()
                print(f"🗣️ Escuchado: {texto}")
                if any(h in texto for h in ["okey rey", "okey ray", "okay rey", "okey real", "hey rey", "hola rey"]):
                    print("🧠 Hola, soy RAI. ¿Cómo puedo ayudarte?")
                    grabar_y_procesar_orden()
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"❌ Error con el reconocimiento de voz: {e}")

def ejecutar_comando_cmd(comando):
    try:
        comando = comando.replace("TuUsuario", usuario)
        comando = comando.replace("%USERNAME%", usuario)

        # Si el comando es abrir una app UWP con explorer.exe, lo tratamos como éxito
        if comando.startswith("explorer.exe shell:appsFolder\\"):
            subprocess.Popen(comando, shell=True)
            print("✅ Comando UWP ejecutado con Popen (no se espera salida)")
            return True

        # Comandos especiales del sistema
        if comando.strip().lower() == "listar_ventanas_y_procesos":
            listar_ventanas_y_procesos()
            return True
        if comando.startswith("tecla:"):
            pyautogui.hotkey(*comando.split(":")[1].split("+"))
            return True
        if comando.startswith("ventana:"):
            _, accion, nombre = comando.split(":")
            ejecutar_accion_ventana(accion, nombre)
            return True
        if comando.lower() in ["bloquear_camara", "desbloquear_camara", "bloquear_microfono", "desbloquear_microfono"]:
            valor = "Deny" if "bloquear" in comando else "Allow"
            target = "webcam" if "camara" in comando else "microphone"
            ps = f'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\{target}" -Name Value -Value {valor}'
            subprocess.run(["powershell", "-Command", ps], check=True)
            return True
        if comando.startswith("diagnostico:"):
            escaner_inteligente(comando)
            return True

        # Comandos CMD normales
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if resultado.returncode == 0:
            print("✅ Comando ejecutado con éxito")
            if resultado.stdout.strip():
                print(resultado.stdout)
            return True
        else:
            print("❌ Error en comando:", resultado.stderr)
            return False
    except Exception as e:
        print(f"⚠️ Error ejecutando comando: {e}")
        return False


def ejecutar_comandos_en_cadena(comandos):
    comandos_lista = [cmd.strip() for cmd in comandos.replace('\n', ';').split(';') if cmd.strip()]
    for comando in comandos_lista:
        print(f"🔁 Ejecutando: {comando}")
        if not ejecutar_comando_cmd(comando):
            break

def enviar_mensaje_final():
    global texto_acumulado
    if not texto_acumulado:
        print("⚠️ No hay texto para enviar.")
        return

    intentos = 0
    while intentos < 3:
        try:
            mensaje = texto_acumulado if intentos == 0 else f"{texto_acumulado} ⚠️ Error en el comando anterior. Reintentalo."
            response = requests.post(SERVER_URL, json={"command": mensaje})
            if response.ok:
                comando = response.json().get("response", "").strip()
                print(f"🧠 Respuesta del servidor: {comando}")

                nombre_app = None
                if comando.lower().startswith("abrir "):
                    nombre_app = comando[6:].strip()
                elif comando.lower().startswith("iniciar "):
                    nombre_app = comando[7:].strip()

                if nombre_app:
                    resultado = buscar_comando_por_nombre(nombre_app)
                    print(f"DEBUG - resultado buscar_comando_por_nombre: {resultado}")
                    if not resultado or any(r is None for r in resultado):
                        print(f"❌ Comando inválido para '{nombre_app}', valores incompletos: {resultado}")
                        break
                    nombre, comando_db, tipo = resultado
                    if tipo == "exe":
                        comando_final = f'start "" "{comando_db.replace("%USERNAME%", usuario)}"'
                    elif tipo == "uwp":
                        comando_final = comando_db
                    else:
                        comando_final = "app_no_encontrada"

                    print(f"🔁 Ejecutando comando desde DB: {comando_final}")
                    if ejecutar_comando_cmd(comando_final):
                        actualizar_ultima_vez(nombre_app)
                        break
                    else:
                        print(f"❌ Error ejecutando comando de la app '{nombre_app}'")
                elif comando.lower().startswith("cerrar "):
                    nombre_cerrar = comando[7:].strip()
                    if cerrar_app_desde_db(nombre_cerrar):
                        break
                    else:
                        print(f"❌ No se pudo cerrar la app '{nombre_cerrar}'")
                else:
                    ejecutar_comandos_en_cadena(comando)
                    break
            else:
                print(f"❌ Error en servidor: {response.status_code}")
                break
        except Exception as e:
            print(f"❌ Error comunicando con servidor: {e}")
            break
        intentos += 1

    texto_acumulado = ""

def main():
    crear_tablas_si_no_existen()
    threading.Thread(target=escucha_hotword, daemon=True).start()
    keyboard.wait()

if __name__ == "__main__":
    main()
