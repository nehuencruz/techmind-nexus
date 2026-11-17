"""
hardware.py - Comunicación con las placas.

  PC  <── USB / Serial ──>  Arduino UNO   (DHT22 + 3 LEDs)
  PC  ─── WiFi / WebSocket ─>  ESP32-S3   (LCD 1602 I2C)

Protocolo Serial (texto, una línea por mensaje, 9600 baudios):
  UNO -> PC :  "T:23.5;H:48.2"   lectura del DHT22 (cada 2 s)
               "E:DHT"           error de lectura del sensor
  PC  -> UNO:  "L:V"  LED verde (entendí)      "L:A"  LED amarillo (procesando)
               "L:R"  LED rojo (no entendí)     "L:0"  apagar LEDs

Protocolo WebSocket (PC -> ESP32-S3):
  "linea1|linea2"   (16 caracteres por línea, sin tildes)

Si no hay placas o librerías, todo funciona en MODO SIMULADO.
"""

import random
import threading
import time

from nlp.procesamiento import quitar_acentos

try:
    import serial  # pyserial
except ImportError:  # pragma: no cover
    serial = None

try:
    import websocket  # websocket-client
except ImportError:  # pragma: no cover
    websocket = None


def parsear_linea_serial(linea):
    """
    Convierte "T:23.5;H:48.2" en {"T": 23.5, "H": 48.2}.
    Devuelve None si la línea no tiene el formato esperado.
    """
    try:
        partes = dict(p.split(":", 1) for p in linea.strip().split(";"))
        return {"T": float(partes["T"]), "H": float(partes["H"])}
    except (ValueError, KeyError):
        return None


def formatear_lcd(texto):
    """Deja el texto listo para la LCD: sin tildes ni emojis y en 16 caracteres."""
    limpio = quitar_acentos(texto)
    limpio = "".join(c for c in limpio if 32 <= ord(c) < 127 and c != "|")
    return limpio[:16].ljust(16)


class GestorHardware:
    """Maneja el Arduino UNO (serial) y el ESP32-S3 (websocket) en segundo plano."""

    def __init__(self, puerto_serial="", baudios=9600, url_esp32="", al_recibir_lectura=None):
        self.puerto_serial = puerto_serial
        self.baudios = baudios
        self.url_esp32 = url_esp32
        self.al_recibir_lectura = al_recibir_lectura  # callback(temp, hum, origen)

        self.temperatura = None
        self.humedad = None
        self.ultima_lectura = None
        self.error_sensor = False

        self._serial = None
        self._ws = None
        self._candado = threading.Lock()
        self._activo = False
        self._proximo_intento_ws = 0  # para no reintentar conectar el ESP32 a cada mensaje

    # ---------------------------------------------------------------- estado
    @property
    def uno_conectado(self):
        return self._serial is not None

    @property
    def esp32_conectado(self):
        return self._ws is not None

    @property
    def simulado(self):
        return not self.uno_conectado

    def estado(self):
        """Diccionario con el estado actual (lo usa la web y el chatbot)."""
        return {
            "temperatura": self.temperatura,
            "humedad": self.humedad,
            "ultima_lectura": self.ultima_lectura,
            "error_sensor": self.error_sensor,
            "uno": "conectado" if self.uno_conectado else "simulado",
            "esp32": "conectado" if self.esp32_conectado else (
                "desconectado" if self.url_esp32 else "simulado"),
        }

    # --------------------------------------------------------------- arranque
    def iniciar(self):
        """Intenta conectar las placas y arranca el hilo de lectura."""
        self._activo = True
        self._conectar_serial()
        self._conectar_esp32()
        objetivo = self._bucle_serial if self.uno_conectado else self._bucle_simulado
        threading.Thread(target=objetivo, daemon=True, name="lector-sensores").start()
        self.mostrar_lcd("TECHMIND Nexus", "Sistema listo")
        self.set_led("V")
        return self

    def detener(self):
        self._activo = False
        self.set_led("0")
        if self._serial:
            self._serial.close()
        if self._ws:
            self._ws.close()

    def _conectar_serial(self):
        if not (self.puerto_serial and serial):
            if self.puerto_serial and not serial:
                print("[HW] Falta pyserial: pip install pyserial")
            print("[HW] Arduino UNO en modo SIMULADO")
            return
        try:
            self._serial = serial.Serial(self.puerto_serial, self.baudios, timeout=1)
            time.sleep(2)  # el UNO se reinicia al abrir el puerto: hay que esperarlo
            self._serial.reset_input_buffer()
            print(f"[HW] Arduino UNO conectado en {self.puerto_serial}")
        except Exception as error:  # serial.SerialException y otros
            print(f"[HW] No se pudo abrir {self.puerto_serial}: {error}. Paso a modo SIMULADO")
            self._serial = None

    def _conectar_esp32(self):
        if not (self.url_esp32 and websocket):
            if self.url_esp32 and not websocket:
                print("[HW] Falta websocket-client: pip install websocket-client")
            return False
        if time.time() < self._proximo_intento_ws:
            return False
        self._proximo_intento_ws = time.time() + 15  # reintenta como mucho cada 15 s
        try:
            self._ws = websocket.create_connection(self.url_esp32, timeout=3)
            print(f"[HW] ESP32-S3 conectado en {self.url_esp32}")
            return True
        except Exception as error:
            print(f"[HW] No se pudo conectar al ESP32-S3 ({error})")
            self._ws = None
            return False

    # ---------------------------------------------------------------- lectura
    def _guardar_lectura(self, temperatura, humedad, origen):
        self.temperatura = round(temperatura, 1)
        self.humedad = round(humedad, 1)
        self.ultima_lectura = time.strftime("%H:%M:%S")
        self.error_sensor = False
        if self.al_recibir_lectura:
            self.al_recibir_lectura(self.temperatura, self.humedad, origen)

    def _bucle_serial(self):
        """Hilo: lee líneas del Arduino UNO todo el tiempo."""
        while self._activo and self._serial:
            try:
                linea = self._serial.readline().decode("utf-8", errors="ignore").strip()
            except Exception as error:
                print(f"[HW] Se perdió el Arduino UNO: {error}")
                self._serial = None
                break
            if not linea:
                continue
            if linea.startswith("E:"):
                self.error_sensor = True
                continue
            datos = parsear_linea_serial(linea)
            if datos:
                self._guardar_lectura(datos["T"], datos["H"], "dht22")

    def _bucle_simulado(self):
        """Hilo: genera lecturas falsas realistas (caminata aleatoria)."""
        temperatura, humedad = 24.0, 50.0
        while self._activo:
            temperatura = min(max(temperatura + random.uniform(-0.3, 0.3), 18), 34)
            humedad = min(max(humedad + random.uniform(-1, 1), 30), 80)
            self._guardar_lectura(temperatura, humedad, "simulado")
            time.sleep(2)

    # ---------------------------------------------------------------- salidas
    def set_led(self, color):
        """color: 'V' verde, 'A' amarillo, 'R' rojo, '0' apagar."""
        if not self._serial:
            return False
        try:
            with self._candado:
                self._serial.write(f"L:{color}\n".encode())
            return True
        except Exception:
            return False

    def mostrar_lcd(self, linea1, linea2=""):
        """Envía dos líneas al LCD del ESP32-S3. Reintenta conectar una vez si se cortó."""
        mensaje = f"{formatear_lcd(linea1)}|{formatear_lcd(linea2)}"
        if not self.url_esp32:
            return False
        for _ in range(2):
            if self._ws is None and not self._conectar_esp32():
                return False
            try:
                with self._candado:
                    self._ws.send(mensaje)
                return True
            except Exception:
                self._ws = None  # se cortó: el próximo intento reconecta
        return False
