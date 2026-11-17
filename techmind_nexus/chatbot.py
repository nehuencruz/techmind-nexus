"""
chatbot.py - Cerebro de TECHMIND Nexus.

Une todas las piezas:
  mensaje -> ¿comando? -> ¿diagnóstico activo (árbol)? -> NLP (TF-IDF + SVM)
          -> base de conocimiento (SQLite) -> respuesta + LEDs + LCD

Conceptos de la materia que se usan acá:
  • Decorador ............ @registrar_log
  • Closure .............. crear_alerta()
  • Funciones anidadas ... dentro de procesar()
  • Lambda ............... para ordenar y filtrar
  • Pila ................. historial y botón "volver"
  • Árbol de decisión .... diagnósticos guiados
"""

import functools
import logging
import os
import re
import threading
import time

import config
from base_conocimiento import BaseConocimiento
from estructuras import Pila, crear_arboles
from nlp.clasificador import ClasificadorIntenciones
from nlp.procesamiento import normalizar

# --------------------------------------------------------------------- log
os.makedirs(os.path.dirname(config.LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=config.LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)
log = logging.getLogger("techmind")


def registrar_log(funcion):
    """DECORADOR: registra en logs/techmind.log cada llamada y cuánto tardó."""

    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        inicio = time.perf_counter()
        resultado = funcion(*args, **kwargs)
        ms = (time.perf_counter() - inicio) * 1000
        log.info("%s(%s) -> %.1f ms", funcion.__name__,
                 ", ".join(repr(a)[:40] for a in args[1:]), ms)
        return resultado

    return envoltura


def crear_alerta(umbral, mensaje):
    """
    CLOSURE: devuelve una función que recuerda 'umbral' y 'mensaje'.

        alerta_calor = crear_alerta(30, "Hace calor")
        alerta_calor(32)  -> "⚠️ Hace calor (32 > 30)"
        alerta_calor(25)  -> None
    """

    def verificar(valor):
        if valor is not None and valor > umbral:
            return f"⚠️ {mensaje} ({valor} > {umbral})"
        return None

    return verificar


# Nombres cortos para mostrar en pantalla y en la LCD (16 caracteres)
TITULOS = {
    "saludo": "Saludo", "despedida": "Despedida", "agradecimiento": "Agradecimiento",
    "capacidades": "Ayuda", "pc_no_enciende": "PC no enciende", "sin_internet": "Sin internet",
    "wifi_lento": "WiFi lento", "pc_lenta": "PC lenta", "pantalla_azul": "Pantalla azul",
    "virus_malware": "Virus/Malware", "impresora": "Impresora", "sobrecalentamiento": "Temperatura PC",
    "disco_lleno": "Disco lleno", "contrasena_olvidada": "Contrasena", "sin_sonido": "Sin sonido",
    "memoria_ram": "Memoria RAM", "ip_red": "IP y redes", "backup": "Backup",
    "estado_sistema": "Estado lab", "fuera_de_tema": "Fuera de tema", "seguimiento": "Seguimiento",
}

RESPUESTAS_SI = {"si", "s", "sip", "dale", "claro", "correcto", "afirmativo", "obvio", "yes", "exacto"}
RESPUESTAS_NO = {"no", "n", "nop", "nope", "negativo", "para nada", "nada"}


class EstadoSesion:
    """Lo que el bot recuerda de cada usuario conectado."""

    def __init__(self):
        self.historial = Pila(capacidad_maxima=50)  # últimos 50 intercambios
        self.arbol = None      # árbol de diagnóstico activo
        self.arbol_tag = None  # intención que lo activó
        self.nodo = None       # pregunta actual dentro del árbol
        self.camino = Pila()   # preguntas anteriores (para /volver)

    def salir_del_arbol(self):
        self.arbol, self.arbol_tag, self.nodo = None, None, None
        self.camino.vaciar()


class Chatbot:
    """Chatbot de soporte técnico TECHMIND Nexus."""

    def __init__(self, ruta_db=config.DB_PATH, hardware=None):
        self.db = BaseConocimiento(ruta_db)
        if self.db.esta_vacia():
            cantidad = self.db.cargar_desde_json(config.INTENCIONES_PATH)
            print(f"[DB] Base de conocimiento creada con {cantidad} intenciones")
        self.clasificador = ClasificadorIntenciones(umbral=config.UMBRAL_CONFIANZA)
        self.arboles = crear_arboles()
        self.hardware = hardware
        self.sesiones = {}
        self._candado = threading.Lock()
        self.alerta_temperatura = crear_alerta(config.TEMP_ALERTA, "Temperatura alta en el laboratorio")
        self.alerta_humedad = crear_alerta(config.HUMEDAD_ALERTA, "Humedad alta en el laboratorio")
        self.reentrenar()

    # ------------------------------------------------------------ utilidades
    @registrar_log
    def reentrenar(self):
        """Vuelve a entrenar el SVM con todos los ejemplos de la base."""
        with self._candado:
            cantidad = self.clasificador.entrenar(self.db.ejemplos_entrenamiento())
        print(f"[NLP] Modelo entrenado con {cantidad} frases y "
              f"{len(self.clasificador.etiquetas)} intenciones")
        return cantidad

    def obtener_sesion(self, sesion_id):
        if sesion_id not in self.sesiones:
            self.sesiones[sesion_id] = EstadoSesion()
        return self.sesiones[sesion_id]

    def _hw(self, metodo, *args):
        """Llama al hardware solo si existe (así el bot funciona sin placas)."""
        if self.hardware:
            getattr(self.hardware, metodo)(*args)

    def alertas_activas(self):
        estado = self.hardware.estado() if self.hardware else {}
        posibles = [self.alerta_temperatura(estado.get("temperatura")),
                    self.alerta_humedad(estado.get("humedad"))]
        return list(filter(lambda a: a is not None, posibles))  # filter + lambda

    # ------------------------------------------------------- punto de entrada
    @registrar_log
    def procesar(self, sesion_id, mensaje):
        """
        Procesa un mensaje del usuario y devuelve un diccionario:
          respuesta (str), intencion (str|None), confianza (float),
          opciones (list[str]) -> botones rápidos (ej. Sí / No),
          sugerencias (list[dict]) -> '¿Quisiste decir...?'
        """
        sesion = self.obtener_sesion(sesion_id)
        mensaje = (mensaje or "").strip()[:500]

        def armar(respuesta, intencion=None, confianza=1.0, opciones=None, sugerencias=None):
            """Función anidada: arma la respuesta final, la guarda y avisa al hardware."""
            resultado = {
                "respuesta": respuesta,
                "intencion": intencion,
                "titulo": TITULOS.get(intencion, intencion or "No entendido"),
                "confianza": round(confianza, 3),
                "opciones": opciones or [],
                "sugerencias": sugerencias or [],
                "en_diagnostico": sesion.arbol is not None,
            }
            sesion.historial.apilar({
                "hora": time.strftime("%H:%M"), "usuario": mensaje,
                "intencion": resultado["titulo"], "confianza": resultado["confianza"],
            })
            self.db.registrar_conversacion(sesion_id, mensaje, intencion, confianza, respuesta)
            self._actualizar_hardware(resultado)
            return resultado

        if not mensaje:
            return armar("No recibí ningún mensaje. ¿Qué problema tenés?", "vacio", 0.0)

        self._hw("set_led", "A")  # amarillo: procesando

        # 1) Comandos con barra
        if mensaje.startswith("/"):
            return armar(*self._ejecutar_comando(sesion, mensaje))

        texto = normalizar(mensaje)

        if texto == "sigue sin funcionar":  # botón que aparece al final de un diagnóstico
            return armar("Lamento que siga fallando 😕. Contame el síntoma exacto con otras palabras "
                         "(qué ves, qué mensaje aparece, desde cuándo pasa). Si es un problema físico, "
                         "lo mejor es que lo revise el técnico del laboratorio.", "seguimiento")

        # 2) Si hay un diagnóstico activo, interpretamos Sí / No / volver / cancelar
        if sesion.arbol:
            if texto in ("volver", "atras"):
                return armar(*self._comando_volver(sesion))
            if texto in ("cancelar", "salir", "terminar"):
                sesion.salir_del_arbol()
                return armar("Diagnóstico cancelado. ¿En qué más te ayudo?", "/cancelar")
            if texto in RESPUESTAS_SI or texto in RESPUESTAS_NO:
                return armar(*self._avanzar_arbol(sesion, texto in RESPUESTAS_SI))

        # 3) Clasificación NLP
        with self._candado:
            prediccion = self.clasificador.predecir(mensaje)
        intencion, confianza = prediccion["intencion"], prediccion["confianza"]

        if sesion.arbol and (intencion is None or intencion == sesion.arbol_tag):
            return armar(f"Respondé Sí o No, por favor 🙂\n\n{sesion.nodo.texto()}",
                         sesion.arbol_tag, 1.0, opciones=["Sí", "No", "Volver", "Cancelar"])
        sesion.salir_del_arbol()  # el usuario cambió de tema

        if intencion is None:
            return armar(*self._no_entendido(prediccion))

        datos = self.db.obtener_intencion(intencion) or {}
        respuesta = self.db.obtener_respuesta(intencion) or "Tengo ese tema registrado pero sin respuesta."

        # 4) Intenciones con árbol de diagnóstico
        if datos.get("arbol") in self.arboles:
            arbol = self.arboles[datos["arbol"]]
            sesion.arbol, sesion.arbol_tag, sesion.nodo = arbol, intencion, arbol.raiz
            respuesta = f"{respuesta}\n\n{arbol.raiz.texto()}"
            return armar(respuesta, intencion, confianza, opciones=["Sí", "No", "Cancelar"])

        # 5) Intención dinámica: datos del sensor
        if intencion == "estado_sistema":
            respuesta = self._respuesta_estado(respuesta)

        return armar(respuesta, intencion, confianza)

    # ------------------------------------------------------- árbol de decisión
    def _avanzar_arbol(self, sesion, respuesta_si):
        sesion.camino.apilar(sesion.nodo)
        sesion.nodo = sesion.arbol.siguiente(sesion.nodo, respuesta_si)
        tag = sesion.arbol_tag
        if sesion.nodo.es_hoja():
            solucion = sesion.nodo.solucion
            sesion.salir_del_arbol()
            return (f"✅ Diagnóstico:\n{solucion}\n\n¿Se solucionó? Si no, contame qué pasa.",
                    tag, 1.0, ["Gracias, se solucionó", "Sigue sin funcionar"])
        return sesion.nodo.pregunta, tag, 1.0, ["Sí", "No", "Volver", "Cancelar"]

    def _comando_volver(self, sesion):
        if not sesion.arbol:
            return "No hay un diagnóstico activo para volver atrás.", "/volver"
        anterior = sesion.camino.desapilar()
        if anterior is None:
            return (f"Ya estás en la primera pregunta.\n\n{sesion.nodo.pregunta}", "/volver",
                    1.0, ["Sí", "No", "Cancelar"])
        sesion.nodo = anterior
        return f"↩️ Volvimos una pregunta:\n\n{anterior.pregunta}", "/volver", 1.0, ["Sí", "No", "Volver", "Cancelar"]

    # ---------------------------------------------------------- respuestas
    def _no_entendido(self, prediccion):
        # Sugerimos temas con algo de probabilidad (filter + lambda)
        posibles = filter(lambda c: c[1] >= 0.10 and c[0] != "fuera_de_tema", prediccion["candidatas"])
        sugerencias = [{"texto": TITULOS.get(tag, tag), "mensaje": self.db.ejemplo_de(tag)}
                       for tag, _ in posibles]
        texto = "No estoy seguro de haber entendido 🤔."
        if sugerencias:
            texto += " ¿Te referís a alguno de estos temas?"
        else:
            texto += " Probá describir el problema con otras palabras o escribí /ayuda."
        return texto, None, prediccion["confianza"], [], sugerencias

    def _respuesta_estado(self, plantilla):
        estado = self.hardware.estado() if self.hardware else {}

        def fmt(valor, unidad):
            return f"{valor} {unidad}" if valor is not None else "sin datos"

        texto = plantilla.format(
            temperatura=fmt(estado.get("temperatura"), "°C"),
            humedad=fmt(estado.get("humedad"), "%"),
            estado_uno=estado.get("uno", "no configurado"),
            estado_esp32=estado.get("esp32", "no configurado"),
        )
        alertas = self.alertas_activas()
        if estado.get("error_sensor"):
            alertas.append("⚠️ El DHT22 no responde: revisá el cableado del pin DATA.")
        return texto + ("\n\n" + "\n".join(alertas) if alertas else "\n\n✅ Todo en rango normal.")

    # ------------------------------------------------------------ comandos
    def _ejecutar_comando(self, sesion, mensaje):
        comando = mensaje.split()[0].lower()
        comandos = {  # diccionario de funciones (despacho)
            "/ayuda": lambda: (self.db.obtener_respuesta("capacidades"), "/ayuda"),
            "/historial": lambda: (self._texto_historial(sesion), "/historial"),
            "/volver": lambda: self._comando_volver(sesion),
            "/cancelar": lambda: (sesion.salir_del_arbol() or "Listo, cancelé el diagnóstico.", "/cancelar"),
            "/estado": lambda: (self._respuesta_estado(self.db.obtener_respuesta("estado_sistema")), "/estado"),
            "/stats": lambda: (self._texto_estadisticas(), "/stats"),
        }
        accion = comandos.get(comando)
        if accion is None:
            return f"Comando desconocido: {comando}. Disponibles: {', '.join(comandos)}", None, 0.0
        return accion()

    @staticmethod
    def _texto_historial(sesion):
        if sesion.historial.esta_vacia():
            return "Todavía no hay mensajes en el historial."
        lineas = [f"{h['hora']} · {h['usuario'][:40]} → {h['intencion']}"
                  for h in sesion.historial.a_lista()[:10]]
        return "📜 Últimos mensajes (del más nuevo al más viejo):\n" + "\n".join(lineas)

    def _texto_estadisticas(self):
        st = self.db.estadisticas()
        temas = "\n".join(f"  • {TITULOS.get(t['intencion'], t['intencion'])}: {t['veces']}"
                          for t in st["temas_mas_consultados"]) or "  (sin datos)"
        return (f"📊 Estadísticas\nMensajes totales: {st['total_mensajes']}\n"
                f"No entendidos: {st['no_entendidos']}\nTemas más consultados:\n{temas}")

    # ------------------------------------------------------------ hardware
    def _actualizar_hardware(self, resultado):
        if not self.hardware:
            return
        entendido = resultado["intencion"] is not None
        self.hardware.set_led("V" if entendido else "R")
        estado = self.hardware.estado()
        temp = estado.get("temperatura")
        linea2 = f"Conf {int(resultado['confianza'] * 100)}%"
        if temp is not None:
            linea2 += f" T{temp:.0f}C"
        self.hardware.mostrar_lcd(resultado["titulo"], linea2)

    # ------------------------------------------------------------ enseñar
    @registrar_log
    def ensenar(self, nombre, ejemplos, respuesta, categoria="general"):
        """
        Agrega conocimiento nuevo desde la web y reentrena el modelo.
        'ejemplos' puede ser una lista o un texto con una frase por línea.
        """
        if isinstance(ejemplos, str):
            ejemplos = ejemplos.splitlines()
        ejemplos = [e.strip() for e in ejemplos if e.strip()]
        tag = re.sub(r"[^a-z0-9]+", "_", normalizar(nombre)).strip("_")
        if not tag:
            raise ValueError("El nombre del tema no puede estar vacío.")
        if len(ejemplos) < 3:
            raise ValueError("Escribí al menos 3 frases de ejemplo (una por línea).")
        if not respuesta.strip():
            raise ValueError("La respuesta no puede estar vacía.")
        self.db.agregar_intencion(tag, ejemplos, [respuesta], categoria)
        TITULOS.setdefault(tag, nombre.strip()[:16])
        self.reentrenar()
        return tag
