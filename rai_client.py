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

usuario = os.getlogin()
texto_acumulado = ""
SERVER_URL = "http://127.0.0.1:5000/orden"

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

        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if resultado.returncode == 0:
            print("✅ Comando ejecutado con éxito")
            if resultado.stdout.strip():
                print("Salida:\n", resultado.stdout)
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
            response = requests.post(SERVER_URL, json={"command": texto_acumulado if intentos == 0 else f"{texto_acumulado} ⚠️ Error en el comando anterior. Reintentalo de nuevo corrigiéndolo."})
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
                if "okey rey" in texto or "okay rey" in texto or "okey ray" in texto or "okay ray" in texto or "ok ray" in texto or "ok rey" in texto or "okey real" in texto or "okay re" in texto or "ok israel" in texto or "okay israel" in texto or "ok rail" in texto or "okay r" in texto or "okay rail" in texto or "hey ray" in texto or "hey rey" in texto or "hey re" in texto or "hey real" in texto or "hey israel" in texto:
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
