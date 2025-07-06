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
from rai_logger import logger
import hud 
from hud import log

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

            logger.info(f"🚀 Abrí la app '{nombre_app}' desde la base de datos.")
            return True
        else:
            logger.warning(f"❌ No encontré '{nombre_app}' en la base de datos.")
            return False

    except Exception as e:
        logger.error(f"⚠️ Error abriendo app desde DB: {e}")
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

            logger.info(f"🚀 Abrí la app UWP '{nombre_app}' desde la base de datos.")
            return True
        else:
            logger.warning(f"❌ No encontré '{nombre_app}' o no tiene comando válido en apps_uwp.")
            return False

    except Exception as e:
        logger.error(f"⚠️ Error abriendo app UWP desde DB: {e}")
        return False

def cerrar_app_desde_db(nombre_busqueda):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT ruta_exe FROM apps WHERE LOWER(nombre) LIKE ?", (f"%{nombre_busqueda.lower()}%",))
        resultado = cursor.fetchone()
        conn.close()

        if not resultado:
            logger.warning(f"❌ No encontré ninguna app llamada '{nombre_busqueda}' en la base de datos.")
            return False

        ruta_exe = resultado[0]
        nombre_proceso = os.path.basename(ruta_exe)
        subprocess.run(["taskkill", "/f", "/im", nombre_proceso], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"❌ Cerrada la app: {nombre_proceso}")
        return True

    except Exception as e:
        logger.error(f"⚠️ No se pudo cerrar la app: {e}")
        return False

def escaner_inteligente(tipo):
    try:
        if tipo == "ram":
            procesos = sorted(psutil.process_iter(['pid', 'name', 'memory_info']), key=lambda p: p.info['memory_info'].rss, reverse=True)
            logger.info("🧠 Procesos con mayor uso de RAM:")
            for proc in procesos[:10]:
                logger.info(f" - {proc.info['name']} (PID: {proc.info['pid']}) - {proc.info['memory_info'].rss / (1024*1024):.2f} MB")
        elif tipo == "cpu":
            procesos = sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), key=lambda p: p.info['cpu_percent'], reverse=True)
            logger.info("🔥 Procesos con más uso de CPU:")
            for proc in procesos[:10]:
                logger.info(f" - {proc.info['name']} (PID: {proc.info['pid']}) - {proc.info['cpu_percent']}%")
        elif tipo.startswith("disco"):
            letra = tipo.split(":")[1].upper() if ":" in tipo else "TODOS"
            particiones = psutil.disk_partitions() if letra == "TODOS" else [p for p in psutil.disk_partitions() if p.device.upper().startswith(letra + ":")]
            logger.info("💽 Estado del disco:")
            for p in particiones:
                try:
                    uso = psutil.disk_usage(p.mountpoint)
                    logger.info(f"🗂️ Disco {p.device} ({p.mountpoint}): Total: {uso.total / (1024**3):.2f} GB | Usado: {uso.used / (1024**3):.2f} GB | Libre: {uso.free / (1024**3):.2f} GB | {uso.percent}% usado\n")
                except PermissionError:
                    continue
        else:
            logger.warning(f"❓ Tipo de escaneo no reconocido: {tipo}")
    except Exception as e:
        logger.error(f"⚠️ Error en escaneo: {e}")

def ejecutar_accion_ventana(accion, nombre_ventana):
    try:
        ventana = next((w for w in gw.getWindowsWithTitle(nombre_ventana)), None)
        if ventana:
            if accion == "maximizar": ventana.maximize()
            elif accion == "minimizar": ventana.minimize()
            elif accion == "enfocar": ventana.activate()
            logger.info(f"🎯 Acción '{accion}' ejecutada sobre '{nombre_ventana}'.")
        else:
            raise ValueError("ventana_no_encontrada")
    except Exception as e:
        raise RuntimeError(f"Error en acción de ventana: {e}")

def listar_ventanas_y_procesos():
    logger.info("🪟 Ventanas abiertas:")
    for w in gw.getAllWindows():
        if w.title:
            logger.info(f" - {w.title}")
    logger.info("\n⚙️ Procesos activos:")
    for proc in psutil.process_iter(['name']):
        nombre = proc.info['name']
        if nombre:
            logger.info(f" - {nombre}")

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
    from hud import mostrar, ocultar, set_estado, set_texto_animado
    global texto_acumulado
    mostrar(es_bienvenida=True)
    set_estado("procesando", "")  # Limpio color antes del texto

    def despues_del_typing():
        global texto_acumulado  
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            # Acá esperamos hasta que se escuche algo REAL
            audio = recognizer.listen(source, timeout=None)
            set_estado("escuchando", "Escuchando...")
        log("⏹️ Procesando orden...")

        try:
            texto = recognizer.recognize_google(audio, language="es-AR")
            texto = procesar_emocion_y_puntuacion(texto)
            log(f'🧩 Fragmento capturado: "{texto}"')
            texto_acumulado += " " + texto
            texto_acumulado = texto_acumulado.strip()
            log(f'📦 Mensaje acumulado: "{texto_acumulado}"')
        except sr.UnknownValueError:
            log("🤷‍♂️ No entendí lo que dijiste.")
        except sr.RequestError as e:
            log(f"❌ Error de reconocimiento: {e}")

        enviar_mensaje_final()

    set_texto_animado(
        "Hola, soy RAI. ¿En qué puedo ayudarte?",
        estado="procesando",
        after=despues_del_typing
    )




def escucha_hotword():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        logger.info("👂 Decí 'okey RAI' para dar una orden...")
        while True:
            try:
                audio = r.listen(source, phrase_time_limit=2)
                texto = r.recognize_google(audio, language="es-AR").lower()
                logger.info(f"🗣️ Escuchado: {texto}")
                if any(h in texto for h in ["okey rey", "okey ray", "okay rey", "okey real", "hey rey", "hola rey"]):
                    logger.info("🧠 Hola, soy RAI. ¿Cómo puedo ayudarte?")
                    grabar_y_procesar_orden()
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                logger.error(f"❌ Error con el reconocimiento de voz: {e}")

def ejecutar_comando_cmd(comando):
    try:
        comando = comando.replace("TuUsuario", usuario)
        comando = comando.replace("%USERNAME%", usuario)

        # Si el comando es abrir una app UWP con explorer.exe, lo tratamos como éxito
        if comando.startswith("explorer.exe shell:appsFolder\\"):
            subprocess.Popen(comando, shell=True)
            logger.info("✅ Comando UWP ejecutado con Popen (no se espera salida)")
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
            logger.info("✅ Comando ejecutado con éxito")
            if resultado.stdout.strip():
                logger.info(resultado.stdout)
            return True
        else:
            logger.error(f"❌ Error en comando: {resultado.stderr}")
            return False
    except Exception as e:
        logger.error(f"⚠️ Error ejecutando comando: {e}")
        return False


def ejecutar_comandos_en_cadena(comandos):
    comandos_lista = [cmd.strip() for cmd in comandos.replace('\n', ';').split(';') if cmd.strip()]
    for comando in comandos_lista:
        logger.info(f"🔁 Ejecutando: {comando}")
        if not ejecutar_comando_cmd(comando):
            break

def es_pregunta_larga(texto):
    palabras_largas = ["buscar", "explicar", "describir", "resumir", "qué es", "cómo", "quién", "dónde", "por qué"]
    texto_lower = texto.lower()
    return any(p in texto_lower for p in palabras_largas)

def enviar_mensaje_final(timeout=5):
    global texto_acumulado
    if not texto_acumulado:
        logger.warning("⚠️ No hay texto para enviar.")
        return

    intentos = 0
    while intentos < 3:
        try:
            mensaje = texto_acumulado if intentos == 0 else f"{texto_acumulado} ⚠️ Error en el comando anterior. Reintentalo."
            response = requests.post(SERVER_URL, json={"command": mensaje}, timeout=30)
            if response.ok:
                comando = response.json().get("response", "").strip()
                logger.info(f"🧠 Respuesta del servidor: {comando}")

                if comando == "ERROR: no entendí":
                    hud.log("❌ No entendí la orden.")
                    break

                if not any(comando.lower().startswith(prefix) for prefix in [
                    "abrir ", "cerrar ", "tecla:", "ventana:", "bloquear_", "desbloquear_",
                    "listar_ventanas_y_procesos", "diagnostico:"
                ]):
                    hud.mostrar_respuesta_final(comando)
                    break

                nombre_app = None
                if comando.lower().startswith("abrir "):
                    nombre_app = comando[6:].strip()
                elif comando.lower().startswith("iniciar "):
                    nombre_app = comando[7:].strip()

                if nombre_app:
                    resultado = buscar_comando_por_nombre(nombre_app)
                    logger.debug(f"DEBUG - resultado buscar_comando_por_nombre: {resultado}")
                    if not resultado or any(r is None for r in resultado):
                        logger.warning(f"❌ Comando inválido para '{nombre_app}', valores incompletos: {resultado}")
                        break

                    nombre, comando_db, tipo = resultado
                    if tipo == "exe":
                        comando_final = f'start "" "{comando_db.replace("%USERNAME%", usuario)}"'
                    elif tipo == "uwp":
                        comando_final = comando_db
                    else:
                        comando_final = "app_no_encontrada"

                    hud.log(f"⚙️ Ejecutando [ {nombre_app} ]...")
                    logger.info(f"🔁 Ejecutando comando desde DB: {comando_final}")
                    if ejecutar_comando_cmd(comando_final):
                        hud.log(f"✅ ¡Listo! [ {nombre_app} ] fue abierto.")
                        actualizar_ultima_vez(nombre_app)
                        threading.Timer(2, hud.ocultar).start()
                        break
                    else:
                        hud.log(f"❌ No se pudo cerrar [ {nombre_app} ]")
                        logger.warning(f"❌ No se pudo cerrar la app '{nombre_app}'")
                else:
                    ejecutar_comandos_en_cadena(comando)
                    threading.Timer(2, hud.ocultar).start()
                    break
            else:
                logger.error(f"❌ Error en servidor: {response.status_code}")
                break

        except requests.Timeout:
            logger.error("❌ Timeout excedido al comunicarse con el servidor.")
            break
        except Exception as e:
            logger.error(f"❌ Error comunicando con servidor: {e}")
            break

        intentos += 1

    texto_acumulado = ""

# Donde llames a enviar_mensaje_final(), antes detectá el timeout y pásalo así:

def enviar_mensaje_final_automatico():
    timeout = 60 if es_pregunta_larga(texto_acumulado) else 5
    enviar_mensaje_final(timeout=timeout)



def iniciar_escucha_segura():
    reinicios = 0
    while True:
        try:
            escucha_hotword()
        except Exception as e:
            reinicios += 1
            logger.error(f"🧨 Error en escucha_hotword: {e} — Reinicio #{reinicios} en 3 segundos...")
            time.sleep(3)


def main():
    crear_tablas_si_no_existen()
    try:
        print("Iniciando thread de escucha hotword segura...")
        escucha_thread = threading.Thread(target=iniciar_escucha_segura, daemon=True)
        escucha_thread.start()
        print("Iniciando HUD (mainloop)...")
        hud.iniciar_hud()
    except Exception as e:
        print(f"ERROR EN MAIN: {e}")



if __name__ == "__main__":
    main()
