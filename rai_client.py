import keyboard  # pip install keyboard
import threading
import speech_recognition as sr
from inputimeout import inputimeout, TimeoutOccurred
import requests

SERVER_URL = "http://127.0.0.1:5000/orden"

rai_activo = False
rai_thread = None

def rai_loop():
    global rai_activo

    print("🔹 RAI ACTIVADO")

    while rai_activo:
        try:
            modo = inputimeout(prompt="📥 ¿Usar voz (v) o texto (t)? (ALT+G para apagar) > ", timeout=10).lower()
        except TimeoutOccurred:
            # Cada 10 segundos checa si sigue activo
            if not rai_activo:
                break
            else:
                continue

        if not rai_activo:
            break

        if modo == "t":
            try:
                comando = inputimeout(prompt="🧠 Ingresá tu orden: ", timeout=10)
            except TimeoutOccurred:
                print("⌛ Tiempo de espera agotado. Volviendo a preguntar...")
                continue
            if not rai_activo:
                break
        elif modo == "v":
            try:
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    print("🎤 Escuchando...")
                    audio = r.listen(source, timeout=5, phrase_time_limit=5)
                comando = r.recognize_google(audio, language="es-AR")
            except sr.UnknownValueError:
                print("🤷‍♂️ No entendí lo que dijiste.")
                continue
            except sr.RequestError as e:
                print(f"❌ Error con el servicio de voz: {e}")
                continue
            except sr.WaitTimeoutError:
                print("⌛ No se detectó audio.")
                continue
        else:
            print("❌ Modo no reconocido.")
            continue

        print(f"📦 Comando capturado: {comando}")

        # Enviar la orden al servidor
        try:
            response = requests.post(SERVER_URL, json={"orden": comando})
            if response.status_code == 200:
                data = response.json()
                print(f"🧾 Respuesta del servidor: {data.get('respuesta')}")
            else:
                print(f"❌ Error del servidor: {response.status_code}")
        except Exception as e:
            print(f"❌ No se pudo conectar con el servidor: {e}")

    print("🔌 RAI DESACTIVADO")

def toggle_rai():
    global rai_activo, rai_thread

    if not rai_activo:
        rai_activo = True
        rai_thread = threading.Thread(target=rai_loop, daemon=True)
        rai_thread.start()
    else:
        print("\n⛔ Apagando RAI...")
        rai_activo = False

def main():
    print("🕶️ Esperando activación con ALT+G (toggle on/off)")
    keyboard.add_hotkey('alt+g', toggle_rai)
    keyboard.wait()

if __name__ == "__main__":
    main()