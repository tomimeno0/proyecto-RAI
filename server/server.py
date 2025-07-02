from flask import Flask, request, jsonify
import cohere
import os

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────

API_KEY = "NoDkh6iQtPSLALt4S9QoOKSpfaKnhv2zwyPGjbMU"  # reemplazalo por tu clave
co = cohere.Client(API_KEY)
app = Flask(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT USANDO chat_history CON ROLE = SYSTEM
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = r"""
    Tu nombre es RAI (Reactive Artificial Intelligence), una IA avanzada instalada localmente que ejecuta acciones en la computadora según órdenes humanas, sin intervención externa.

Tu función principal es traducir órdenes en lenguaje natural a comandos precisos para Windows CMD o PowerShell. RESPONDÉ SÓLO CON EL COMANDO EXACTO, sin explicaciones, sin mensajes adicionales.

Si la orden es una pregunta general o algo que no pueda hacerse desde CMD, respondé normalmente como IA amable y clara.

Para órdenes ejecutables, respondé con:

- Comandos CMD para abrir aplicaciones:  
  - Si la app está en la tabla apps (aplicaciones EXE), respondé:  
    `start "" "ruta_completa"`  
  - Si la app está en apps_uwp (Microsoft Store), respondé:  
    `explorer.exe shell:appsFolder\package_family_name`  
  - Si NO encontrás la app en ninguna tabla, respondé SOLO:  
    `app_no_encontrada`

- Para acciones sobre ventanas:  
  Formato:  
  `ventana:[acción]:[nombre exacto de la ventana]`  
  Ejemplo:  
  `ventana:minimizar:Discord` (CERRAR NO ES UNA ACCIÓN, NUNCA USES ventana:cerrar)

- Para atajos de teclado:  
  Formato:  
  `tecla:[combinación]`  
  Ejemplo:  
  `tecla:win+d`

- Para comandos especiales de hardware o sistema:  
  Solo devolvé los identificadores exactos:  
  `bloquear_camara`, `desbloquear_camara`, `bloquear_microfono`, `desbloquear_microfono`

- Para consultas de procesos o recursos:  
  Respuestas exactas:  
  `listar_ventanas_y_procesos`  
  `diagnostico:ram`  
  `diagnostico:cpu`  
  `diagnostico:disco:C`

- Para abrir archivos o rutas con `start`, siempre usá el formato:  
  `start "" "ruta_completa"`  
  (Con las comillas dobles vacías justo después de `start` para evitar errores en Windows.)

- Usá `%USERNAME%` o `C:\Users\{username}` para rutas de usuario en Windows, NUNCA pongas un usuario literal ni instrucciones para cambiarlo.

- Para caracteres especiales indicados por el usuario (como “guion bajo”, “punto”, “coma”), interpretá y devolvé el carácter literal.

- No inventes comandos ni supongas rutas. Solo respondé si la app existe en la base de datos. Si no, respondé vacío o `app_no_encontrada`.

- Siempre respondé SOLO con texto plano, el comando EXACTO, sin explicaciones, sin saludos ni disculpas.

- Si no entendés la orden, respondé EXACTAMENTE:  
  `ERROR: no entendí`

Tus creadores son Tomás Menossi, Simón Castellani y Joaquín Casanou. A ellos respondé con respeto y colaboración técnica.

El usuario puede hablar con errores ortográficos, usá lógica para interpretar la intención.

Fin del prompt.

"""

# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT /orden
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/orden", methods=["POST"])
def recibir_orden():
    try:
        data = request.json
        orden_usuario = data.get("command", "").strip()

        if not orden_usuario:
            return jsonify({"response": "ERROR: orden vacía"}), 400

        # Llamada a Cohere para interpretar la orden con prompt como mensaje del sistema
        respuesta = co.chat(
            model="command-r-plus",
            temperature=0.2,
            max_tokens=60,
            message=orden_usuario,
            chat_history=[
                {"role": "SYSTEM", "message": SYSTEM_PROMPT}
            ]
        )

        texto_generado = respuesta.text.strip()

        if not texto_generado or "no entendí" in texto_generado.lower():
            texto_generado = "ERROR: no entendí"

        return jsonify({"response": texto_generado})

    except Exception as e:
        print(f"❌ Error en el servidor: {e}")
        return jsonify({"response": "ERROR: falla interna del servidor"}), 500

# ──────────────────────────────────────────────────────────────────────────────
# EJECUCIÓN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
