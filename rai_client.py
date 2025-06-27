import keyboard
import speech_recognition as sr
import threading
import os
import requests
import subprocess
from prompt_toolkit import prompt
import pygetwindow as gw  # Para controlar ventanas
import pyautogui  # Para atajos de teclado

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
                print("❌ Acción no reconocida.")
        else:
            print("🚫 No se encontró una ventana con ese nombre.")
    except Exception as e:
        print(f"⚠️ Error en acción de ventana: {e}")

def ejecutar_comando_cmd(comando):
    try:
        comando = comando.replace("TuUsuario", usuario)  # Reemplaza placeholder

        # Atajo de teclado
        if comando.startswith("tecla:"):
            partes = comando.split(":")
            if len(partes) >= 2:
                combinacion = partes[1].split("+")
                pyautogui.hotkey(*combinacion)
                print(f"✅ Ejecutado atajo: {partes[1]}")
                return

        # Control de ventanas
        if comando.startswith("ventana:"):
            partes = comando.split(":")
            if len(partes) == 3:
                _, accion, nombre_ventana = partes
                ejecutar_accion_ventana(accion.lower(), nombre_ventana)
                return

        # Bloquear cámara
        if comando.strip().lower() == "bloquear_camara":
            ps = 'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" -Name Value -Value Deny'
            subprocess.run(["powershell", "-Command", ps], check=True)
            print("🔒 Cámara bloqueada con éxito.")
            return

        # Desbloquear cámara
        if comando.strip().lower() == "desbloquear_camara":
            ps = 'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam" -Name Value -Value Allow'
            subprocess.run(["powershell", "-Command", ps], check=True)
            print("🔓 Cámara desbloqueada con éxito.")
            return

        # Bloquear micrófono
        if comando.strip().lower() == "bloquear_microfono":
            ps = 'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone" -Name Value -Value Deny'
            subprocess.run(["powershell", "-Command", ps], check=True)
            print("🔇 Micrófono bloqueado con éxito.")
            return

        # Desbloquear micrófono
        if comando.strip().lower() == "desbloquear_microfono":
            ps = 'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone" -Name Value -Value Allow'
            subprocess.run(["powershell", "-Command", ps], check=True)
            print("🎙️ Micrófono desbloqueado con éxito.")
            return

        # Comando CMD normal
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if resultado.returncode == 0:
            print("✅ Comando ejecutado con éxito")
            if resultado.stdout.strip():
                print("Salida:\n", resultado.stdout)
        else:
            print("❌ Error al ejecutar comando")
            if resultado.stderr.strip():
                print("Error:\n", resultado.stderr)
    except Exception as e:
        print(f"⚠️ Error ejecutando comando: {e}")

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

def enviar_mensaje_final():
    global texto_acumulado
    if not texto_acumulado:
        print("⚠️ No hay texto para enviar.")
        return

    try:
        response = requests.post(SERVER_URL, json={"command": texto_acumulado})
        if response.ok:
            respuesta_servidor = response.json().get("response", "")
            print(f"🧠 Respuesta del servidor: {respuesta_servidor}")
            ejecutar_comando_cmd(respuesta_servidor)
        else:
            print(f"❌ Error en servidor: {response.status_code}")
    except Exception as e:
        print(f"❌ Error comunicando con servidor: {e}")

    texto_acumulado = ""

def escucha_hotword():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("👂 Decí 'okey rey' para dar una orden...")

        while True:
            try:
                audio = r.listen(source, phrase_time_limit=2)
                texto = r.recognize_google(audio, language="es-AR").lower()
                print(f"🗣️ Escuchado: {texto}")
                # Verifica si se ha detectado la hotword
                if "okey rey" in texto or "okay rey" in texto:
                    print("🎯 Hotword detectada → escuchando orden...")
                    grabar_y_procesar_orden()
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"❌ Error con el reconocimiento de voz: {e}")

def main():
    print("🕶️ Decí 'okey rey' para activar y dar una orden.")
    threading.Thread(target=escucha_hotword, daemon=True).start()
    keyboard.wait()

if __name__ == "__main__":
    main()
