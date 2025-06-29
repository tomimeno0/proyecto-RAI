import keyboard
import speech_recognition as sr
import threading
import os
import requests
import subprocess
from prompt_toolkit import prompt
import pygetwindow as gw
import pyautogui
import psutil
import re
import time

usuario = os.getlogin()
texto_acumulado = ""
SERVER_URL = "http://127.0.0.1:5000/orden"

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
            letra = "TODOS"
            partes = tipo.split(":")
            if len(partes) == 2:
                letra = partes[1].upper()

            print("💽 Estado del disco:")
            if letra == "TODOS":
                particiones = psutil.disk_partitions()
            else:
                particiones = [p for p in psutil.disk_partitions() if p.device.upper().startswith(letra + ":")]

            for p in particiones:
                try:
                    uso = psutil.disk_usage(p.mountpoint)
                    print(f"🗂️ Disco {p.device} ({p.mountpoint}):")
                    print(f" - Total: {uso.total / (1024**3):.2f} GB")
                    print(f" - Usado: {uso.used / (1024**3):.2f} GB")
                    print(f" - Libre: {uso.free / (1024**3):.2f} GB")
                    print(f" - Porcentaje usado: {uso.percent}%\n")
                except PermissionError:
                    continue

        else:
            print(f"❓ Tipo de escaneo no reconocido: {tipo}")
    except Exception as e:
        print(f"⚠️ Error en escaneo: {e}")




def procesar_emocion_y_puntuacion(texto):
    texto = texto.strip()

    if texto.endswith(("que", "qué", "como", "cómo", "donde", "dónde", "cuando", "cuándo", "por qué", "porque")) or texto.lower().startswith(("qué ", "cómo ", "cuándo ", "dónde ", "por qué ")):
        texto = texto[0].upper() + texto[1:] + "?"
        return texto

    emocion = ["dale", "vamos", "sí", "listo", "buenísimo", "perfecto", "increíble", "genial", "me encanta", "de una"]
    for palabra in emocion:
        if re.search(rf"\b{palabra}\b", texto.lower()):
            texto = texto[0].upper() + texto[1:] + "!"
            return texto

    texto = re.sub(r"\b(osea|oseas|eh|emm|mm+)\b", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s{2,}", " ", texto).strip()

    texto = texto[0].upper() + texto[1:]
    if not texto.endswith((".", "!", "?")):
        texto += "."

    return texto

def ejecutar_accion_ventana(accion, nombre_ventana):
    try:
        ventana = next((w for w in gw.getWindowsWithTitle(nombre_ventana)), None)
        if ventana:
            if accion == "maximizar":
                ventana.maximize()
                print("🔼 Ventana maximizada.")
            elif accion == "minimizar":
                ventana.minimize()
                print("🔽 Ventana minimizada.")
            elif accion == "enfocar":
                try:
                    ventana.activate()
                    print("🎯 Ventana enfocada.")
                except Exception as e:
                    if "Error code from Windows: 0" in str(e):
                        print("🎯 Ventana enfocada (con advertencia irrelevante).")
                    else:
                        raise e
            else:
                raise ValueError("acción_de_ventana_no_valida")
        else:
            raise ValueError("ventana_no_encontrada")
    except Exception as e:
        raise RuntimeError(f"Error en acción de ventana: {e}")

def listar_ventanas_y_procesos():
    try:
        print("🪟 Ventanas abiertas:")
        for w in gw.getAllWindows():
            if w.title:
                print(f" - {w.title}")
        print("\n⚙️ Procesos activos:")
        for proc in psutil.process_iter(['name']):
            nombre = proc.info['name']
            if nombre:
                print(f" - {nombre}")
    except Exception as e:
        raise RuntimeError(f"Error al obtener ventanas o procesos: {e}")

def ejecutar_comando_cmd(comando):
    try:
        comando = comando.replace("TuUsuario", usuario)

        if comando.strip().lower() == "listar_ventanas_y_procesos":
            listar_ventanas_y_procesos()
            return True

        if comando.startswith("tecla:"):
            partes = comando.split(":")
            if len(partes) >= 2:
                combinacion = partes[1].split("+")
                pyautogui.hotkey(*combinacion)
                print(f"✅ Ejecutado atajo: {partes[1]}")
                return True

        if comando.startswith("ventana:"):
            partes = comando.split(":")
            if len(partes) == 3:
                _, accion, nombre_ventana = partes
                ejecutar_accion_ventana(accion.lower(), nombre_ventana)
                return True
            else:
                raise ValueError("formato_invalido")

        if comando.strip().lower() == "bloquear_camara":
            ps = 'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" -Name Value -Value Deny'
            subprocess.run(["powershell", "-Command", ps], check=True)
            print("🔒 Cámara bloqueada con éxito.")
            return True

        if comando.strip().lower() == "desbloquear_camara":
            ps = 'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" -Name Value -Value Allow'
            subprocess.run(["powershell", "-Command", ps], check=True)
            print("🔓 Cámara desbloqueada con éxito.")
            return True

        if comando.strip().lower() == "bloquear_microfono":
            ps = 'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone" -Name Value -Value Deny'
            subprocess.run(["powershell", "-Command", ps], check=True)
            print("🔇 Micrófono bloqueado con éxito.")
            return True

        if comando.strip().lower() == "desbloquear_microfono":
            ps = 'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone" -Name Value -Value Allow'
            subprocess.run(["powershell", "-Command", ps], check=True)
            print("🎙️ Micrófono desbloqueado con éxito.")
            return True

        if comando.startswith("diagnostico:"):
            tipo = comando[len("diagnostico:"):]  # toma todo lo que sigue a 'diagnostico:'
            escaner_inteligente(tipo)
            return True


        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if resultado.returncode == 0:
            print("✅ Comando ejecutado con éxito")
            if resultado.stdout.strip():
                print("Salida:\n", resultado.stdout)
            return True

        if comando.startswith("diagnostico:disco"):
            partes = comando.split(":")
            if len(partes) == 3:
                escaner_inteligente("disco", disco=partes[2])
            else:
                escaner_inteligente("disco")
            return True


        else:
            print("❌ Error al ejecutar comando")
            if resultado.stderr.strip():
                print("Error:\n", resultado.stderr)
            return False

    except Exception as e:
        print(f"⚠️ Error ejecutando comando: {e}")
        return False

def enviar_mensaje_final():
    global texto_acumulado
    if not texto_acumulado:
        print("⚠️ No hay texto para enviar.")
        return

    intentos = 0
    comando = ""
    while intentos < 3:
        try:
            # Si hay error, le manda ese aviso a la IA para que corrija el comando
            mensaje_a_enviar = texto_acumulado if intentos == 0 else f"{texto_acumulado} ⚠️ Error en el comando anterior. Reintentalo de nuevo corrigiéndolo."
            response = requests.post(SERVER_URL, json={"command": mensaje_a_enviar})
            if response.ok:
                comando = response.json().get("response", "")
                print(f"🧠 Respuesta del servidor: {comando}")
                exitoso = ejecutar_comando_cmd(comando)
                if exitoso:
                    break
                else:
                    intentos += 1
            else:
                print(f"❌ Error en servidor: {response.status_code}")
                break
        except Exception as e:
            print(f"❌ Error comunicando con servidor: {e}")
            break

    if intentos == 3:
        print("🚫 Falló la ejecución tras 3 intentos. Requiere revisión manual.")

    texto_acumulado = ""

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
        return
    except sr.RequestError as e:
        print(f"❌ Error de reconocimiento: {e}")
        return

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
                # Varias formas de hotword para evitar fallos
                if "okey rey" in texto or "okay rey" in texto or "okey ray" in texto or "okay ray" in texto or "ok ray" in texto or "ok rey" in texto or "okey real" in texto or "okay re" in texto or "ok israel" in texto or "okay israel" in texto or "ok rail" in texto or "okay r" in texto or "okay rail" in texto or "hey ray" in texto or "hey rey" in texto or "hey re" in texto or "hey real" in texto or "hey israel" in texto or "hola rey" in texto:
                    print("🧠 Hola, soy RAI. ¿Cómo puedo ayudarte?")
                    grabar_y_procesar_orden()
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"❌ Error con el reconocimiento de voz: {e}")

def main():
    threading.Thread(target=escucha_hotword, daemon=True).start()
    keyboard.wait()

if __name__ == "__main__":
    main()
