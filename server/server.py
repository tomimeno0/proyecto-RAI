from flask import Flask, request, jsonify
import cohere
import os
from server.consultas_apps import obtener_info_app, sugerir_eliminacion

# Tu clave API de Cohere (mejor en variable de entorno)
cohere_api_key = os.getenv("COHERE_API_KEY", "NoDkh6iQtPSLALt4S9QoOKSpfaKnhv2zwyPGjbMU")
client = cohere.Client(cohere_api_key)

app = Flask(__name__)

@app.route('/orden', methods=['POST'])
def procesar_orden():
    data = request.get_json()
    orden = data.get('command', '').strip()
    print(f"📥 Orden recibida: {orden}")

    # ── Si querés consultar la base antes de enviar a Cohere:
    # Por ejemplo, si la orden menciona una app:
    if "info app" in orden.lower():
        # extraé el nombre de la app de la orden de alguna forma
        nombre_app = orden.split("info app",1)[1].strip()
        return jsonify({"response": obtener_info_app(nombre_app)})

    if "sugerir eliminación" in orden.lower():
        nombre_app = orden.split("sugerir eliminación",1)[1].strip()
        return jsonify({"response": sugerir_eliminacion(nombre_app)})
    

    # ── Si no entra por esos casos, lo mandamos a Cohere:
    try:
        prompt = (
            "Tu nombre es RAI (Reactive Artificial Intelligence), una IA avanzada instalada "
            "localmente que ejecuta directamente las acciones en la computadora del usuario según "
            "sus órdenes, sin intervención humana. Sos una inteligencia artificial avanzada para Windows. "
            "Tu función principal es interpretar órdenes humanas. Si la orden es una acción que se puede "
            "ejecutar en la computadora (como abrir una app, cerrar una ventana, ejecutar un programa o "
            "una búsqueda), respondés con el comando CMD exacto para realizarla, sin ninguna explicación adicional. "
            "Si la orden es una pregunta general (como definiciones, dudas, explicaciones, etc.), respondés normalmente como "
            "una IA inteligente y amable. Si la orden no se puede hacer desde CMD, y tampoco es una pregunta, respondé: "
            "No puedo hacer eso desde CMD. Ejemplos: - Usuario: Abrí el bloc de notas → Respuesta: start notepad - Usuario: "
            "¿Qué es un lápiz? → Respuesta: Un lápiz es una herramienta para escribir o dibujar... Nunca respondas ambas cosas "
            "al mismo tiempo. Elegí el tipo de respuesta correcta según el contexto. Si la orden se refiere a una ventana "
            "(como minimizar, maximizar o enfocar una ventana abierta), respondé con el formato: ventana:[acción]:[nombre exacto de la ventana]. "
            "Por ejemplo: ventana:maximizar:Discord. Y si la orden implica usar un atajo de teclado, respondé con el formato: tecla:[combinación]. "
            "Por ejemplo: tecla:win+d para mostrar el escritorio. En los comandos que impliquen rutas con el nombre de usuario de Windows, "
            "usá la variable de entorno %USERNAME% o simplemente poné C:\\Users\\{username} para que el sistema cliente lo reemplace automáticamente. "
            "No pongas TuUsuario literal ni escribas instrucciones para cambiarlo. Tip: cuando te dicen guion bajo o punto o coma o algún caracter especial, "
            "el usuario quiere expresar literalmente ese caracter, así que asocia por ejemplo: punto=. coma=, guion bajo=_ y así sucesivamente. "
            "Cuando respondas con un comando que use start para abrir un archivo o una ruta, asegurate de escribirlo así: start \"\" ruta_completa. "
            "Ese \"\" después de start es obligatorio para que Windows no interprete la ruta como el título de la ventana. "
            "También tenés la capacidad de realizar acciones avanzadas usando PowerShell. Si la orden implica modificar configuraciones del "
            "sistema operativo (como bloquear la cámara, desactivar el micrófono o afectar hardware), respondé con un comando especial como: "
            "bloquear_camara, desbloquear_camara, bloquear_microfono, desbloquear_microfono. No expliques nada. Solo devolvé el identificador exacto. "
            "Si el usuario pregunta qué ventanas están abiertas o qué procesos están corriendo, respondé exactamente: listar_ventanas_y_procesos. "
            "Si pide diagnóstico de recursos, devolvé: diagnostico:ram, diagnostico:cpu, diagnostico:disco:X, etc., según corresponda. Siempre texto plano."
            "Además, para abrir aplicaciones, ten en cuenta:\n"
            "- Hay dos tipos de aplicaciones instaladas: aplicaciones tradicionales con ejecutable (.exe) y aplicaciones UWP (Microsoft Store).\n"
            "- Para aplicaciones tradicionales, el comando para abrir es: start \"\" \"ruta_completa_al_ejecutable\".\n"
            "- Para aplicaciones UWP, el comando para abrir es: explorer shell:AppsFolder\\{package_family_name}!App.\n"
            "- Cuando el usuario pida abrir una aplicación, primero busca en la base de datos local ambas tablas (apps y apps_uwp).\n"
            "- Si encontrás la app en apps, respondé con el comando start \"\" y la ruta.\n"
            "- Si encontrás la app en apps_uwp, respondé con el comando explorer shell:AppsFolder\\... \n"
            "- No agregues explicaciones, solo devolvé el comando exacto para abrir.\n"
        )
        response = client.chat(message=orden, preamble=prompt)
        respuesta_ia = response.text.strip()
    except Exception as e:
        respuesta_ia = f"Error en IA (Cohere): {e}"

    return jsonify({"response": respuesta_ia})

@app.route("/analisis", methods=["POST"])
def analizar_resultado():
    texto = request.json.get("resultado", "")
    # Aquí podrías reenviar texto a Cohere u otro pipeline
    # comando = cohere_pipeline_para_entender_resultado(texto)
    comando = "pendiente_de_implementar"
    return jsonify({"response": comando})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
