from flask import Flask, request, jsonify
import cohere
import os

# Tu clave API de Cohere (lo ideal es usar variables de entorno)
cohere_api_key = "NoDkh6iQtPSLALt4S9QoOKSpfaKnhv2zwyPGjbMU"  # Asegúrate de no exponer tu clave API en el código fuente

client = cohere.Client(cohere_api_key)
app = Flask(__name__)

@app.route('/orden', methods=['POST'])
def procesar_orden():
    data = request.get_json()
    orden = data.get('command', '')
    print(f"📥 Orden recibida: {orden}")

    try:
        response = client.chat(message=orden,preamble="Sos una IA que traduce órdenes humanas a comandos de CMD para ejecutarlos en Windows. Respondé solo con el comando.")
        respuesta_ia = response.text.strip()
    except Exception as e:
        respuesta_ia = f"Error en IA (Cohere): {e}"

    return jsonify({"response": respuesta_ia})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
