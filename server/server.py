from flask import Flask, request, jsonify
import cohere
import os

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────

API_KEY = "NoDkh6iQtPSLALt4S9QoOKSpfaKnhv2zwyPGjbMU"  # reemplazalo por tu clave real
co = cohere.Client(API_KEY)
app = Flask(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT COMPLETO Y ACTUALIZADO
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = r"""
Tu nombre es RAI (Reactive Artificial Intelligence), IA avanzada que interpreta órdenes para controlar una PC.

RESPONDÉ SOLO con el comando EXACTO para ejecutar, SIN explicaciones ni saludos.

Sos capaz de interpretar órdenes para:

1. Abrir o cerrar aplicaciones EXE o UWP.  
   RESPONDÉ SOLO así:  
   - abrir nombre_app  
   - cerrar nombre_app  
   (Sin rutas, solo abrir/cerrar y el nombre)

2. Controlar ventanas:  
   Formato: ventana:[acción]:[nombre exacto de ventana]  
   Ejemplo: ventana:minimizar:Discord

3. Atajos de teclado:  
   Formato: tecla:[combinación]  
   Ejemplo: tecla:win+d

4. Comandos especiales hardware o sistema:  
   Solo: bloquear_camara, desbloquear_camara, bloquear_microfono, desbloquear_microfono

5. Consultas de sistema:  
   listar_ventanas_y_procesos, diagnostico:ram, diagnostico:cpu, diagnostico:disco:C

🔎 Si el usuario hace una PREGUNTA o comentario que no se corresponde con un comando (por ejemplo: "¿Qué fue el imperialismo?"), RESPONDÉ con una EXPLICACIÓN DIRECTA Y CLARA como IA, con la respuesta que sepas. NO DIGAS "no entendí".

❌ Solo si el mensaje es ambiguo, muy corto o no se puede entender NADA, respondé exactamente:
ERROR: no entendí

⚠️ No inventes comandos, rutas ni funciones.  
⚠️ No saludos, ni disculpas, ni explicaciones. Solo el comando puro o una respuesta si es pregunta.

Ejemplos:
- "Abrime WhatsApp" → abrir whatsapp  
- "Cerrá Spotify" → cerrar spotify  
- "Minimizá Discord" → ventana:minimizar:Discord  
- "Presioná Win + D" → tecla:win+d  
- "¿Qué fue el imperialismo?" → El imperialismo fue un proceso político, económico y militar...

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
