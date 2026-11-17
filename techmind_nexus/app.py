"""
app.py - Servidor web de TECHMIND Nexus (Flask).

Ejecutar:   python app.py
Abrir:      http://127.0.0.1:5000

API:
  POST /api/chat          {"mensaje": "..."}            -> respuesta del bot
  GET  /api/estado                                      -> sensores, placas y alertas
  GET  /api/historial                                   -> historial de la sesión (pila)
  GET  /api/estadisticas                                -> resumen de uso
  GET  /api/intenciones                                 -> temas que conoce el bot
  POST /api/ensenar       {"nombre","ejemplos","respuesta"} -> agrega conocimiento
"""

import time
import uuid

from flask import Flask, jsonify, render_template, request, session

import config
from chatbot import Chatbot
from hardware import GestorHardware


def crear_app(ruta_db=config.DB_PATH, usar_hardware=True):
    """Fábrica de la app (permite crear una app de prueba en los tests)."""
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.json.ensure_ascii = False

    hardware = None
    bot = Chatbot(ruta_db=ruta_db)

    if usar_hardware:
        ultimo_guardado = {"t": 0.0}

        def guardar_lectura(temperatura, humedad, origen):
            """Callback del hardware: guarda en SQLite como mucho cada 30 segundos."""
            if time.time() - ultimo_guardado["t"] >= 30:
                ultimo_guardado["t"] = time.time()
                bot.db.registrar_lectura(temperatura, humedad, origen)

        hardware = GestorHardware(config.SERIAL_PORT, config.SERIAL_BAUD,
                                  config.ESP32_WS_URL, al_recibir_lectura=guardar_lectura)
        hardware.iniciar()
        bot.hardware = hardware

    def id_sesion():
        if "id" not in session:
            session["id"] = uuid.uuid4().hex[:12]
        return session["id"]

    @app.route("/")
    def inicio():
        return render_template("index.html")

    @app.post("/api/chat")
    def chat():
        datos = request.get_json(silent=True) or {}
        mensaje = str(datos.get("mensaje", ""))
        return jsonify(bot.procesar(id_sesion(), mensaje))

    @app.get("/api/estado")
    def estado():
        info = hardware.estado() if hardware else {"uno": "sin hardware", "esp32": "sin hardware"}
        info["alertas"] = bot.alertas_activas()
        info["lecturas"] = bot.db.ultimas_lecturas(20)
        return jsonify(info)

    @app.get("/api/historial")
    def historial():
        sesion = bot.obtener_sesion(id_sesion())
        return jsonify(sesion.historial.a_lista())

    @app.get("/api/estadisticas")
    def estadisticas():
        return jsonify(bot.db.estadisticas())

    @app.get("/api/intenciones")
    def intenciones():
        return jsonify(bot.db.listar_intenciones())

    @app.post("/api/ensenar")
    def ensenar():
        datos = request.get_json(silent=True) or {}
        try:
            tag = bot.ensenar(datos.get("nombre", ""), datos.get("ejemplos", ""),
                              datos.get("respuesta", ""), datos.get("categoria", "general"))
        except ValueError as error:
            return jsonify({"ok": False, "error": str(error)}), 400
        return jsonify({"ok": True, "tag": tag})

    app.bot = bot
    app.hardware = hardware
    return app


if __name__ == "__main__":
    aplicacion = crear_app()
    print(f"\n  TECHMIND Nexus listo en http://{config.HOST}:{config.PUERTO}\n")
    # use_reloader=False: evita que Flask abra el puerto serie dos veces
    aplicacion.run(host=config.HOST, port=config.PUERTO, debug=True, use_reloader=False)
