"""
Pruebas automáticas de TECHMIND Nexus (rol: Tester).

Ejecutar desde la carpeta del proyecto:
    python -m unittest discover tests -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot import Chatbot, crear_alerta  # noqa: E402
from estructuras import Pila, crear_arboles  # noqa: E402
from hardware import formatear_lcd, parsear_linea_serial  # noqa: E402
from nlp.procesamiento import normalizar, tokenizar  # noqa: E402


class TestPila(unittest.TestCase):
    def test_lifo(self):
        p = Pila()
        for x in (1, 2, 3):
            p.apilar(x)
        self.assertEqual(p.desapilar(), 3)
        self.assertEqual(p.ver_tope(), 2)
        self.assertEqual(len(p), 2)

    def test_vacia(self):
        p = Pila()
        self.assertTrue(p.esta_vacia())
        self.assertIsNone(p.desapilar())

    def test_capacidad_maxima_descarta_el_mas_viejo(self):
        p = Pila(capacidad_maxima=3)
        for x in range(5):
            p.apilar(x)
        self.assertEqual(p.a_lista(), [4, 3, 2])


class TestArbol(unittest.TestCase):
    def test_arboles_completos(self):
        for arbol in crear_arboles().values():
            self.assertGreater(arbol.profundidad(), 1)
            self.assertGreater(arbol.contar_soluciones(), 2)

    def test_recorrido_llega_a_hoja(self):
        arbol = crear_arboles()["pc_no_enciende"]
        nodo = arbol.raiz
        while not nodo.es_hoja():
            nodo = arbol.siguiente(nodo, False)
        self.assertIn("interruptor", nodo.solucion)


class TestProcesamiento(unittest.TestCase):
    def test_normalizar(self):
        self.assertEqual(normalizar("¡Mi PC  NO enciendeee!"), "mi pc no enciende")

    def test_no_se_elimina(self):
        self.assertIn("no", tokenizar("no tengo internet"))


class TestHardware(unittest.TestCase):
    def test_parsear(self):
        self.assertEqual(parsear_linea_serial("T:23.5;H:48.2"), {"T": 23.5, "H": 48.2})
        self.assertIsNone(parsear_linea_serial("basura"))
        self.assertIsNone(parsear_linea_serial("E:DHT"))

    def test_lcd(self):
        texto = formatear_lcd("Contraseña olvidada 🔑")
        self.assertEqual(len(texto), 16)
        self.assertTrue(texto.isascii())

    def test_closure_alerta(self):
        alerta = crear_alerta(30, "Calor")
        self.assertIsNone(alerta(25))
        self.assertIn("Calor", alerta(31))


class TestChatbot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.bot = Chatbot(ruta_db=os.path.join(cls.tmp.name, "test.db"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_intenciones_basicas(self):
        casos = {
            "hola": "saludo",
            "la pantalla se puso azul": "pantalla_azul",
            "creo que me entro un virus": "virus_malware",
            "como veo mi ip": "ip_red",
        }
        for frase, esperado in casos.items():
            with self.subTest(frase=frase):
                self.assertEqual(self.bot.procesar("t1", frase)["intencion"], esperado)

    def test_diagnostico_con_arbol_y_volver(self):
        r = self.bot.procesar("t2", "mi pc no enciende")
        self.assertTrue(r["en_diagnostico"])
        self.assertIn("Sí", r["opciones"])
        primera = self.bot.procesar("t2", "si")["respuesta"]
        self.assertIn("monitor", primera)
        volver = self.bot.procesar("t2", "/volver")["respuesta"]
        self.assertIn("luz", volver)
        self.bot.procesar("t2", "no")          # ¿Se enciende alguna luz? No
        self.bot.procesar("t2", "no")          # ¿Es notebook? No
        final = self.bot.procesar("t2", "no")  # ¿Interruptor en I? No
        self.assertIn("Diagnóstico", final["respuesta"])
        self.assertFalse(final["en_diagnostico"])

    def test_fuera_de_tema_o_no_entendido(self):
        r = self.bot.procesar("t3", "xqzv wplk")
        self.assertIn(r["intencion"], (None, "fuera_de_tema"))

    def test_comandos(self):
        self.bot.procesar("t4", "hola")
        self.assertIn("hola", self.bot.procesar("t4", "/historial")["respuesta"])
        self.assertIn("Comando desconocido", self.bot.procesar("t4", "/xyz")["respuesta"])

    def test_estado_sin_hardware(self):
        r = self.bot.procesar("t5", "que temperatura hace en el laboratorio")
        self.assertEqual(r["intencion"], "estado_sistema")
        self.assertIn("sin datos", r["respuesta"])

    def test_ensenar_tema_nuevo(self):
        tag = self.bot.ensenar(
            "Teclado no funciona",
            "el teclado no anda\nno escribe el teclado\nse traban las teclas del teclado\nel teclado no responde",
            "Probá el teclado en otro puerto USB.",
            "hardware",
        )
        self.assertEqual(tag, "teclado_no_funciona")
        self.assertEqual(self.bot.procesar("t6", "mi teclado no escribe")["intencion"], tag)
        with self.assertRaises(ValueError):
            self.bot.ensenar("Algo", "una sola frase", "respuesta")


class TestAPI(unittest.TestCase):
    def setUp(self):
        from app import crear_app
        self.tmp = tempfile.TemporaryDirectory()
        self.app = crear_app(ruta_db=os.path.join(self.tmp.name, "api.db"), usar_hardware=False)
        self.cliente = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_pagina_y_chat(self):
        self.assertEqual(self.cliente.get("/").status_code, 200)
        r = self.cliente.post("/api/chat", json={"mensaje": "no tengo internet"})
        self.assertEqual(r.get_json()["intencion"], "sin_internet")
        self.assertEqual(len(self.cliente.get("/api/historial").get_json()), 1)

    def test_estado_y_estadisticas(self):
        self.assertIn("alertas", self.cliente.get("/api/estado").get_json())
        self.assertIn("total_mensajes", self.cliente.get("/api/estadisticas").get_json())

    def test_ensenar_invalido(self):
        r = self.cliente.post("/api/ensenar", json={"nombre": "x", "ejemplos": "a", "respuesta": "b"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
