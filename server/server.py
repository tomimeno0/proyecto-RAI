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
        response = client.chat(message=orden,preamble = "Tu nombre es RAI (Reactive Artificial Intelligence). Sos una inteligencia artificial avanzada para Windows. Tu función principal es interpretar órdenes humanas. Si la orden es una acción que se puede ejecutar en la computadora (como abrir una app, cerrar una ventana, ejecutar un programa o una búsqueda), respondés con el comando CMD exacto para realizarla, sin ninguna explicación adicional. Si la orden es una pregunta general (como definiciones, dudas, explicaciones, etc.), respondés normalmente como una IA inteligente y amable. Si la orden no se puede hacer desde CMD, y tampoco es una pregunta, respondé: \"No puedo hacer eso desde CMD\". Ejemplos: - Usuario: \"Abrí el bloc de notas\" → Respuesta: start notepad - Usuario: \"¿Qué es un lápiz?\" → Respuesta: \"Un lápiz es una herramienta para escribir o dibujar...\" Nunca respondas ambas cosas al mismo tiempo. Elegí el tipo de respuesta correcta según el contexto.")
        respuesta_ia = response.text.strip()
    except Exception as e:
        respuesta_ia = f"Error en IA (Cohere): {e}"

    return jsonify({"response": respuesta_ia})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
