import keyboard
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wavfile
import speech_recognition as sr
import threading
import os
import requests
import subprocess  # <-- importamos subprocess para ejecutar comandos

rai_activado = False
grabando = False
fs = 16000  # Frecuencia de muestreo
audio_data = []
audio_file = "temp_audio.wav"

SERVER_URL = "http://127.0.0.1:5000/orden"  # Asegurate que la URL coincida con la del servidor

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

def grabar_audio():
    global audio_data, grabando
    audio_data = []
    print("🎤 Grabando audio...")

    def callback(indata, frames, time_info, status):
        if grabando:
            audio_data.append(indata.copy())

    with sd.InputStream(samplerate=fs, channels=1, callback=callback):
        while grabando:
            sd.sleep(100)

def detener_y_procesar():
    print("⏹️ Audio capturado, procesando...")
    if not audio_data:
        print("⚠️ No se grabó nada.")
        return

    audio_np = np.concatenate(audio_data, axis=0)
    audio_int16 = (audio_np * 32767).astype(np.int16)
    wavfile.write(audio_file, fs, audio_int16)

    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source)

    try:
        texto = r.recognize_google(audio, language="es-AR")
        print(f"📦 Comando capturado: {texto}")

        # Enviar el texto al servidor
        try:
            response = requests.post(SERVER_URL, json={"command": texto})
            if response.ok:
                respuesta_servidor = response.json().get("response", "")
                print(f"🧠 Respuesta del servidor: {respuesta_servidor}")

                # Ejecutar el comando CMD que devuelve el servidor
                ejecutar_comando_cmd(respuesta_servidor)

            else:
                print(f"❌ Error en servidor: {response.status_code}")
        except Exception as e:
            print(f"❌ Error comunicando con servidor: {e}")

    except sr.UnknownValueError:
        print("🤷‍♂️ No entendí lo que dijiste.")
    except sr.RequestError as e:
        print(f"❌ Error de reconocimiento: {e}")

    os.remove(audio_file)

def al_presionar_v(e):
    global grabando
    if rai_activado and not grabando:
        grabando = True
        threading.Thread(target=grabar_audio).start()

def al_soltar_v(e):
    global grabando
    if rai_activado and grabando:
        grabando = False
        threading.Thread(target=detener_y_procesar).start()

def toggle_rai():
    global rai_activado
    rai_activado = not rai_activado
    if rai_activado:
        print("🔹 RAI ACTIVADO (mantené 'V' para hablar)")
    else:
        print("🔌 RAI DESACTIVADO")

def main():
    print("🕶️ Esperando activación con ALT+G (toggle on/off)")
    keyboard.add_hotkey('alt+g', toggle_rai)
    keyboard.on_press_key('v', al_presionar_v)
    keyboard.on_release_key('v', al_soltar_v)
    keyboard.wait()

if __name__ == "__main__":
    main()
