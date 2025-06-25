from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/orden', methods=['POST'])
def procesar_orden():
    data = request.get_json()
    orden = data.get('orden')

    print(f"📥 Orden recibida: {orden}")

    # Acá podrías agregar procesamiento real
    respuesta = {
        "respuesta": f"Recibí tu orden: '{orden}' y ya la estoy procesando."
    }

    return jsonify(respuesta)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
