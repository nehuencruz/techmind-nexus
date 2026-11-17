"""
base_conocimiento.py - Base de datos SQLite de TECHMIND Nexus.

Tablas:
  intenciones     (tag, categoria, arbol)
  ejemplos        frases de entrenamiento de cada intención
  respuestas      respuestas posibles de cada intención
  conversaciones  registro de todo lo que se habló (para estadísticas)
  lecturas        lecturas del sensor DHT22

La primera vez se llena con datos/intenciones.json. Después todo se lee
de la base, así lo que se "enseña" desde la web queda guardado.
"""

import json
import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime

ESQUEMA = """
CREATE TABLE IF NOT EXISTS intenciones (
    tag        TEXT PRIMARY KEY,
    categoria  TEXT NOT NULL DEFAULT 'general',
    arbol      TEXT
);
CREATE TABLE IF NOT EXISTS ejemplos (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    tag    TEXT NOT NULL REFERENCES intenciones(tag),
    frase  TEXT NOT NULL,
    UNIQUE(tag, frase)
);
CREATE TABLE IF NOT EXISTS respuestas (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    tag    TEXT NOT NULL REFERENCES intenciones(tag),
    texto  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversaciones (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha      TEXT NOT NULL,
    sesion     TEXT,
    mensaje    TEXT NOT NULL,
    intencion  TEXT,
    confianza  REAL,
    respuesta  TEXT
);
CREATE TABLE IF NOT EXISTS lecturas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha        TEXT NOT NULL,
    temperatura  REAL,
    humedad      REAL,
    origen       TEXT
);
"""


class BaseConocimiento:
    """Acceso a la base SQLite. Cada método abre y cierra su conexión (seguro con Flask)."""

    def __init__(self, ruta_db):
        self.ruta_db = ruta_db
        with self._conexion() as con:
            con.executescript(ESQUEMA)

    @contextmanager
    def _conexion(self):
        """Abre una conexión, hace commit al final y la cierra siempre."""
        con = sqlite3.connect(self.ruta_db)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    @staticmethod
    def _ahora():
        return datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------ carga
    def esta_vacia(self):
        with self._conexion() as con:
            return con.execute("SELECT COUNT(*) FROM intenciones").fetchone()[0] == 0

    def cargar_desde_json(self, ruta_json):
        """Llena la base con el archivo JSON inicial. Devuelve cuántas intenciones cargó."""
        with open(ruta_json, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        for intencion in datos["intenciones"]:
            self.agregar_intencion(
                tag=intencion["tag"],
                ejemplos=intencion["ejemplos"],
                respuestas=intencion["respuestas"],
                categoria=intencion.get("categoria", "general"),
                arbol=intencion.get("arbol"),
            )
        return len(datos["intenciones"])

    def agregar_intencion(self, tag, ejemplos, respuestas, categoria="general", arbol=None):
        """Crea una intención nueva o le suma ejemplos/respuestas si ya existe."""
        with self._conexion() as con:
            con.execute(
                "INSERT INTO intenciones(tag, categoria, arbol) VALUES (?, ?, ?) "
                "ON CONFLICT(tag) DO NOTHING",
                (tag, categoria, arbol),
            )
            con.executemany(
                "INSERT OR IGNORE INTO ejemplos(tag, frase) VALUES (?, ?)",
                [(tag, e.strip()) for e in ejemplos if e.strip()],
            )
            existentes = {r["texto"] for r in con.execute(
                "SELECT texto FROM respuestas WHERE tag = ?", (tag,))}
            con.executemany(
                "INSERT INTO respuestas(tag, texto) VALUES (?, ?)",
                [(tag, r.strip()) for r in respuestas if r.strip() and r.strip() not in existentes],
            )

    # -------------------------------------------------------------- consultas
    def ejemplos_entrenamiento(self):
        """Devuelve [(frase, tag), ...] para entrenar el clasificador."""
        with self._conexion() as con:
            return [(r["frase"], r["tag"]) for r in con.execute("SELECT frase, tag FROM ejemplos")]

    def obtener_respuesta(self, tag):
        """Devuelve una respuesta al azar de la intención (o None)."""
        with self._conexion() as con:
            filas = con.execute("SELECT texto FROM respuestas WHERE tag = ?", (tag,)).fetchall()
        return random.choice(filas)["texto"] if filas else None

    def ejemplo_de(self, tag):
        """Devuelve la primera frase de ejemplo de una intención (para las sugerencias)."""
        with self._conexion() as con:
            fila = con.execute("SELECT frase FROM ejemplos WHERE tag = ? ORDER BY id LIMIT 1",
                               (tag,)).fetchone()
        return fila["frase"] if fila else tag

    def obtener_intencion(self, tag):
        with self._conexion() as con:
            fila = con.execute("SELECT * FROM intenciones WHERE tag = ?", (tag,)).fetchone()
        return dict(fila) if fila else None

    def listar_intenciones(self):
        """Lista de intenciones con cantidad de ejemplos (para el panel de la web)."""
        with self._conexion() as con:
            filas = con.execute(
                "SELECT i.tag, i.categoria, COUNT(e.id) AS ejemplos "
                "FROM intenciones i LEFT JOIN ejemplos e ON e.tag = i.tag "
                "GROUP BY i.tag ORDER BY i.categoria, i.tag"
            ).fetchall()
        return [dict(f) for f in filas]

    # -------------------------------------------------------------- registros
    def registrar_conversacion(self, sesion, mensaje, intencion, confianza, respuesta):
        with self._conexion() as con:
            con.execute(
                "INSERT INTO conversaciones(fecha, sesion, mensaje, intencion, confianza, respuesta) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self._ahora(), sesion, mensaje, intencion, confianza, respuesta),
            )

    def registrar_lectura(self, temperatura, humedad, origen):
        with self._conexion() as con:
            con.execute(
                "INSERT INTO lecturas(fecha, temperatura, humedad, origen) VALUES (?, ?, ?, ?)",
                (self._ahora(), temperatura, humedad, origen),
            )

    def ultimas_lecturas(self, cantidad=30):
        with self._conexion() as con:
            filas = con.execute(
                "SELECT fecha, temperatura, humedad FROM lecturas ORDER BY id DESC LIMIT ?",
                (cantidad,),
            ).fetchall()
        return [dict(f) for f in reversed(filas)]

    def estadisticas(self):
        """Resumen para mostrar en la ExpoTécnica."""
        with self._conexion() as con:
            total = con.execute("SELECT COUNT(*) FROM conversaciones").fetchone()[0]
            no_entendidas = con.execute(
                "SELECT COUNT(*) FROM conversaciones WHERE intencion IS NULL").fetchone()[0]
            top = con.execute(
                "SELECT intencion, COUNT(*) AS veces FROM conversaciones "
                "WHERE intencion IS NOT NULL AND intencion NOT LIKE '/%' "
                "GROUP BY intencion ORDER BY veces DESC LIMIT 5"
            ).fetchall()
            sin_respuesta = con.execute(
                "SELECT mensaje FROM conversaciones WHERE intencion IS NULL "
                "ORDER BY id DESC LIMIT 10"
            ).fetchall()
        return {
            "total_mensajes": total,
            "no_entendidos": no_entendidas,
            "temas_mas_consultados": [dict(f) for f in top],
            "ultimas_no_entendidas": [f["mensaje"] for f in sin_respuesta],
        }
