import keyboard
import speech_recognition as sr
import threading
import os
import requests
import subprocess
from prompt_toolkit import prompt

texto_acumulado = ""
SERVER_URL = "http://127.0.0.1:5000/orden"

def ejecutar_comando_cmd(comando):
    try:
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

    texto_editado = prompt("✍️ Revisá o modificá el comando (ENTER para confirmar):\n", default=texto_acumulado).strip()
    texto_acumulado = texto_editado

    if not texto_acumulado:
        print("⚠️ No se envió ningún comando porque el texto está vacío.")
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
