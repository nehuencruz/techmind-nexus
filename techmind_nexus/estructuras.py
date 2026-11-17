"""
estructuras.py - Estructuras de datos dinámicas de TECHMIND Nexus.

  • Pila (LIFO)          -> historial de la conversación y botón "volver"
  • Árbol de decisión    -> diagnósticos guiados con preguntas Sí / No

Están implementadas "a mano" con nodos enlazados, sin usar list,
para practicar estructuras dinámicas (como pide la materia).
"""


# =========================================================================
#  PILA (Stack) - Último en entrar, primero en salir (LIFO)
# =========================================================================
class _NodoPila:
    """Nodo de la pila: guarda un dato y apunta al nodo de abajo."""

    def __init__(self, dato, siguiente=None):
        self.dato = dato
        self.siguiente = siguiente


class Pila:
    """
    Pila enlazada.

    Ejemplo:
        p = Pila()
        p.apilar("hola"); p.apilar("mi pc no enciende")
        p.desapilar()  -> "mi pc no enciende"
    """

    def __init__(self, capacidad_maxima=None):
        self._tope = None
        self._tamanio = 0
        self.capacidad_maxima = capacidad_maxima  # None = sin límite

    def apilar(self, dato):
        """Agrega un elemento arriba de todo. Si se llenó, descarta el más viejo."""
        self._tope = _NodoPila(dato, self._tope)
        self._tamanio += 1
        if self.capacidad_maxima and self._tamanio > self.capacidad_maxima:
            self._eliminar_fondo()

    def desapilar(self):
        """Saca y devuelve el elemento de arriba. Devuelve None si está vacía."""
        if self.esta_vacia():
            return None
        dato = self._tope.dato
        self._tope = self._tope.siguiente
        self._tamanio -= 1
        return dato

    def ver_tope(self):
        """Devuelve el elemento de arriba sin sacarlo."""
        return None if self.esta_vacia() else self._tope.dato

    def esta_vacia(self):
        return self._tope is None

    def vaciar(self):
        self._tope = None
        self._tamanio = 0

    def a_lista(self):
        """Devuelve los elementos del más nuevo al más viejo (para mostrarlos)."""
        elementos, actual = [], self._tope
        while actual:
            elementos.append(actual.dato)
            actual = actual.siguiente
        return elementos

    def _eliminar_fondo(self):
        """Quita el nodo de más abajo (el más antiguo)."""
        if self._tope is None or self._tope.siguiente is None:
            self.vaciar()
            return
        actual = self._tope
        while actual.siguiente.siguiente:
            actual = actual.siguiente
        actual.siguiente = None
        self._tamanio -= 1

    def __len__(self):
        return self._tamanio

    def __repr__(self):
        return f"Pila({self.a_lista()})"


# =========================================================================
#  ÁRBOL DE DECISIÓN binario (Sí / No)
# =========================================================================
class NodoDecision:
    """
    Nodo del árbol.
      - Nodo pregunta: tiene 'pregunta', 'si' y 'no' (hijos).
      - Nodo hoja:     tiene 'solucion' (fin del diagnóstico).
    """

    def __init__(self, pregunta=None, si=None, no=None, solucion=None):
        self.pregunta = pregunta
        self.si = si
        self.no = no
        self.solucion = solucion

    def es_hoja(self):
        return self.solucion is not None

    def texto(self):
        return self.solucion if self.es_hoja() else self.pregunta


class ArbolDecision:
    """Árbol de diagnóstico. Se recorre desde la raíz respondiendo Sí o No."""

    def __init__(self, nombre, raiz):
        self.nombre = nombre
        self.raiz = raiz

    def siguiente(self, nodo, respuesta_si):
        """Devuelve el hijo según la respuesta (True = Sí, False = No)."""
        if nodo.es_hoja():
            return None
        return nodo.si if respuesta_si else nodo.no

    def profundidad(self, nodo="raiz"):
        """Cantidad máxima de preguntas hasta una solución (recursiva)."""
        nodo = self.raiz if nodo == "raiz" else nodo
        if nodo is None or nodo.es_hoja():
            return 0
        return 1 + max(self.profundidad(nodo.si), self.profundidad(nodo.no))

    def contar_soluciones(self, nodo="raiz"):
        """Cuenta las hojas del árbol (recursiva)."""
        nodo = self.raiz if nodo == "raiz" else nodo
        if nodo is None:
            return 0
        if nodo.es_hoja():
            return 1
        return self.contar_soluciones(nodo.si) + self.contar_soluciones(nodo.no)


def _p(pregunta, si, no):
    """Atajo para crear un nodo pregunta."""
    return NodoDecision(pregunta=pregunta, si=si, no=no)


def _s(solucion):
    """Atajo para crear un nodo solución (hoja)."""
    return NodoDecision(solucion=solucion)


def crear_arboles():
    """Construye y devuelve los árboles de diagnóstico disponibles."""
    no_enciende = _p(
        "¿Se enciende alguna luz o gira algún ventilador al apretar el botón?",
        si=_p(
            "¿Ves algo en el monitor (logo del fabricante, BIOS o Windows)?",
            si=_p(
                "¿Se queda trabado en el logo o se reinicia una y otra vez?",
                si=_s("Problema de arranque del sistema.\n1. Desconectá USB y discos externos y reiniciá.\n2. Reiniciá 3 veces seguidas durante el logo para abrir la Reparación automática de Windows.\n3. Probá 'Restaurar sistema' o 'Reparación de inicio'.\n4. Si sigue igual, el disco puede estar fallando: revisalo con CrystalDiskInfo desde otra PC."),
                no=_s("La PC enciende y muestra imagen: el hardware básico funciona. Si se apaga después de un rato, puede ser recalentamiento. Preguntame '¿por qué se calienta mi PC?'."),
            ),
            no=_p(
                "¿El monitor tiene la luz encendida y el cable de video bien conectado?",
                si=_p(
                    "¿Escuchás pitidos (beeps) al encender?",
                    si=_s("Los pitidos son códigos de error de la placa madre.\n• Pitidos largos repetidos: casi siempre RAM. Sacá las memorias, limpiá los contactos con goma de borrar y volvé a colocarlas de a una.\n• 1 largo + 2 o 3 cortos: placa de video. Revisá que esté bien insertada y con su cable de alimentación.\nBuscá el significado exacto según la marca del BIOS (AMI, Award, Phoenix)."),
                    no=_s("Sin imagen ni pitidos.\n1. Si tenés placa de video, conectá el monitor a ELLA y no a la placa madre.\n2. Probá con otro cable o monitor.\n3. Reacomodá la RAM.\n4. Hacé un 'clear CMOS': sacá la pila de la placa madre 1 minuto con la PC desenchufada."),
                ),
                no=_s("Conectá bien el cable de video (HDMI/DisplayPort/VGA), verificá que el monitor esté encendido y que tenga seleccionada la entrada correcta (botón 'Input' o 'Source')."),
            ),
        ),
        no=_p(
            "¿Es una notebook?",
            si=_s("Notebook sin señales:\n1. Conectá el cargador y fijate si se enciende el LED de carga.\n2. Mantené apretado el botón de encendido 30 segundos (descarga la estática) y volvé a intentar.\n3. Si la batería es extraíble, sacala y probá solo con el cargador.\n4. Si el cargador no prende ninguna luz, probalo en otro enchufe o conseguí otro compatible."),
            no=_p(
                "¿La fuente tiene interruptor atrás y está en posición 'I' (encendido)?",
                si=_s("Revisá la alimentación:\n1. Probá otro cable de 220V y otro enchufe (o sacá la zapatilla).\n2. Verificá que el cable del botón frontal (POWER SW) esté conectado a la placa madre.\n3. Revisá que el conector de 24 pines y el de 4/8 pines del CPU estén bien puestos.\n4. Si nada funciona, la fuente puede estar quemada: probala con un tester o en otra PC. ⚠️ Nunca abras la fuente: guarda tensión peligrosa."),
                no=_s("Poné el interruptor trasero de la fuente en 'I', esperá 10 segundos y volvé a apretar el botón de encendido."),
            ),
        ),
    )

    sin_internet = _p(
        "¿Las luces del router/módem están encendidas y sin ninguna en rojo?",
        si=_p(
            "¿Otros dispositivos (por ejemplo tu celular) tienen internet en la misma red?",
            si=_p(
                "¿Tu PC está conectada por cable de red?",
                si=_s("El problema está en tu PC o en el cable.\n1. Probá con otro cable de red y otro puerto del router.\n2. En CMD como administrador, ejecutá:\n   ipconfig /release\n   ipconfig /renew\n   ipconfig /flushdns\n3. Configuración > Red e Internet > Configuración de red avanzada > Restablecer red.\n4. Actualizá el driver de la placa de red."),
                no=_s("El problema está en el WiFi de tu PC.\n1. Verificá que el WiFi no esté apagado ni en Modo avión.\n2. Olvidá la red y volvé a conectarte escribiendo la clave.\n3. En CMD como administrador: 'netsh winsock reset' y reiniciá.\n4. Administrador de dispositivos > Adaptadores de red > reinstalá el adaptador WiFi."),
            ),
            no=_p(
                "¿Ya reiniciaste el router (desenchufado al menos 30 segundos)?",
                si=_s("Si reiniciaste y ningún dispositivo tiene internet, el problema es del proveedor. Llamá a tu ISP con el número de cliente a mano y preguntá si hay un corte en tu zona."),
                no=_s("Desenchufá el router y el módem, esperá 30 segundos, enchufá primero el módem y después el router. Esperá 2 minutos a que se enciendan todas las luces y probá de nuevo."),
            ),
        ),
        no=_p(
            "¿El router está enchufado y con la luz de encendido (POWER) prendida?",
            si=_s("Una luz roja o apagada en 'Internet', 'PON' o 'LOS' indica que no llega señal del proveedor.\n1. Revisá que el cable de fibra/coaxial esté bien conectado y no esté doblado.\n2. Reiniciá el equipo.\n3. Si la luz LOS está en rojo, es un problema de la línea: comunicate con tu proveedor."),
            no=_s("Revisá el enchufe y la fuente del router. Probá en otro tomacorriente. Si sigue sin encender, la fuente del router puede estar quemada: pedile un reemplazo a tu proveedor."),
        ),
    )

    return {
        "pc_no_enciende": ArbolDecision("PC no enciende", no_enciende),
        "sin_internet": ArbolDecision("Sin internet", sin_internet),
    }
