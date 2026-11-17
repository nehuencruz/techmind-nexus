"""
config.py - Configuración central de TECHMIND Nexus.

Editá los valores de la sección HARDWARE según tu equipo.
Si dejás SERIAL_PORT o ESP32_WS_URL vacíos, el sistema funciona
en MODO SIMULADO (sirve para programar y probar sin las placas).
"""

import os

# --- Rutas ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
DB_PATH = os.path.join(DATOS_DIR, "techmind.db")
INTENCIONES_PATH = os.path.join(DATOS_DIR, "intenciones.json")
LOG_PATH = os.path.join(BASE_DIR, "logs", "techmind.log")

# --- HARDWARE ------------------------------------------------------------
# Puerto del Arduino UNO (DHT22 + LEDs).
#   Windows: "COM3", "COM4"...   (Administrador de dispositivos > Puertos)
#   Linux:   "/dev/ttyACM0"      Mac: "/dev/cu.usbmodem1101"
SERIAL_PORT = os.environ.get("TECHMIND_SERIAL", "")
SERIAL_BAUD = 9600

# Dirección del WebSocket del ESP32-S3 (la IP aparece en la LCD al encenderlo).
#   Ejemplo: "ws://192.168.0.50:81"
ESP32_WS_URL = os.environ.get("TECHMIND_ESP32", "")

# --- NLP -----------------------------------------------------------------
# Si la confianza del SVM es menor a este valor, el bot pide aclaración.
UMBRAL_CONFIANZA = 0.30

# --- Alertas -------------------------------------------------------------
TEMP_ALERTA = 30.0      # °C: por encima se muestra alerta de temperatura
HUMEDAD_ALERTA = 70.0   # %

# --- Servidor web --------------------------------------------------------
HOST = "127.0.0.1"      # usá "0.0.0.0" para abrirlo desde otros equipos de la red
PUERTO = 5000
SECRET_KEY = os.environ.get("TECHMIND_SECRET", "techmind-nexus-expotecnica")
