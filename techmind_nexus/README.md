# TECHMIND Nexus – Chatbot de Soporte Técnico con NLP

**Proyecto 3 · Laboratorio de Programación · 6° año · EEST N° 3 San Fernando**

TECHMIND Nexus es un chatbot que responde consultas técnicas sobre hardware, software y redes. Clasifica lo que escribe el usuario con **TF-IDF + SVM**, busca la respuesta en una **base de conocimiento SQLite** y guía diagnósticos paso a paso con un **árbol de decisión**. El estado se muestra con LEDs en un **Arduino UNO** (que además lee un **DHT22**) y en una **LCD 1602 I2C** conectada a un **ESP32-S3** por WiFi.

---

## Funcionalidades

- 💬 Chat web con 20 temas (PC no enciende, sin internet, pantalla azul, virus, impresora, RAM, IP, backup y más).
- 🧠 NLP: TF-IDF por palabras y por caracteres + SVM lineal con nivel de confianza. Tolera errores de tipeo.
- 🌳 Diagnóstico guiado con preguntas Sí / No (árbol de decisión), con opción de **volver** atrás (pila).
- 📜 Historial de la conversación guardado en una **pila**.
- 🗄️ Base de conocimiento ampliable: desde la web se le pueden **enseñar temas nuevos** y el modelo se reentrena solo.
- 🌡️ Lectura de temperatura y humedad del laboratorio con alertas, gráfico e historial en SQLite.
- 🚦 LEDs: amarillo = procesando, verde = entendió, rojo = no entendió.
- 📟 LCD: tema detectado, confianza y temperatura.
- 🧪 Modo simulado: **funciona sin placas** para programar y probar desde casa.

**Comandos del chat:** `/ayuda` · `/historial` · `/volver` · `/cancelar` · `/estado` · `/stats`

---

## Puesta en marcha en VS Code

### 1. Requisitos
- [Python 3.10 o superior](https://www.python.org/downloads/). En Windows, marcá **"Add Python to PATH"** al instalarlo.
- [Visual Studio Code](https://code.visualstudio.com/) con la extensión **Python** de Microsoft.
- [Arduino IDE 2](https://www.arduino.cc/en/software) para cargar el código a las placas.

### 2. Abrir el proyecto
`Archivo > Abrir carpeta…` y elegí la carpeta `techmind_nexus`.

### 3. Crear el entorno virtual e instalar librerías
Abrí la terminal integrada (`Ctrl + ñ` o `Ver > Terminal`):

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Linux / Mac
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Si PowerShell no deja activar el entorno: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
>
> VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → elegí el de `.venv`.
> En Linux/Mac cambiá la ruta en `.vscode/settings.json` a `.venv/bin/python`.

### 4. Ejecutar
```bash
python app.py
```
Abrí **http://127.0.0.1:5000** en el navegador. También podés usar **F5** (Ejecutar y depurar) y elegir la configuración **"TECHMIND: Servidor web"**.

Otras opciones:
```bash
python consola.py                        # chatear desde la terminal
python entrenar.py                       # ver la precisión del modelo
python -m unittest discover tests -v     # correr las 19 pruebas automáticas
```

---

## Conectar el hardware

Detalle de las conexiones, el diagrama y la teoría en **[`docs/investigacion.md`](docs/investigacion.md)**.

### Arduino UNO (DHT22 + LEDs)
1. Arduino IDE → Administrar bibliotecas → instalá **"DHT sensor library"** (Adafruit).
2. Abrí `arduino/uno_sensores/uno_sensores.ino` y cargalo al UNO.
3. Fijate el puerto (`Herramientas > Puerto`, por ejemplo `COM3`) y **cerrá el Monitor Serie** (si queda abierto, Python no puede usar el puerto).
4. En `config.py`: `SERIAL_PORT = "COM3"`

### ESP32-S3 + LCD 1602 I2C
1. Arduino IDE → Gestor de placas → instalá **"esp32 by Espressif Systems"**.
2. Bibliotecas: **"WebSockets"** (Markus Sattler) y **"LiquidCrystal I2C"** (Frank de Brabander).
3. Abrí `arduino/esp32s3_lcd/esp32s3_lcd.ino`, completá `WIFI_SSID` y `WIFI_PASS`.
4. Placa: **ESP32S3 Dev Module** → cargar.
5. La LCD muestra la IP, por ejemplo `192.168.0.50`. En `config.py`: `ESP32_WS_URL = "ws://192.168.0.50:81"`
6. La PC y el ESP32 tienen que estar **en la misma red WiFi**.

Si `SERIAL_PORT` o `ESP32_WS_URL` quedan vacíos, esa parte funciona en **modo simulado**.

---

## Estructura del proyecto

```
techmind_nexus/
├── app.py                  Servidor web Flask + API
├── chatbot.py              Lógica del bot (decorador, closure, árbol, pila)
├── config.py               Configuración (puertos, umbrales)
├── estructuras.py          Pila enlazada y árbol de decisión
├── base_conocimiento.py    Base de datos SQLite
├── hardware.py             Serial (UNO) y WebSocket (ESP32-S3)
├── consola.py              Chat por terminal
├── entrenar.py             Métricas del modelo
├── nlp/
│   ├── procesamiento.py    Normalización, stopwords, stemming, bigramas
│   └── clasificador.py     TF-IDF + SVM
├── datos/intenciones.json  Base de conocimiento inicial (306 frases, 20 temas)
├── templates/index.html    Interfaz web
├── static/                 CSS y JavaScript
├── arduino/
│   ├── uno_sensores/       Código del Arduino UNO
│   └── esp32s3_lcd/        Código del ESP32-S3
├── tests/                  Pruebas automáticas (unittest)
└── docs/investigacion.md   TF-IDF, SVM, conexiones y arquitectura
```

**Dónde está cada tema de la materia:**

| Concepto | Dónde |
|---|---|
| Funciones con docstrings, parámetros por defecto, varios valores de retorno | todo el proyecto |
| Funciones anidadas | `Chatbot.procesar()` → `armar()`, `_respuesta_estado()` → `fmt()` |
| Lambda + `sorted` / `filter` | `clasificador.predecir()`, `Chatbot.alertas_activas()`, `_no_entendido()` |
| Closure | `crear_alerta(umbral, mensaje)` en `chatbot.py` |
| Decorador | `@registrar_log` en `chatbot.py` (escribe en `logs/techmind.log`) |
| Recursividad | `ArbolDecision.profundidad()` y `contar_soluciones()` |
| Diccionario de funciones | comandos en `Chatbot._ejecutar_comando()` |
| Estructuras dinámicas | `Pila` (enlazada) y `ArbolDecision` en `estructuras.py` |
| POO | `Chatbot`, `BaseConocimiento`, `GestorHardware`, `ClasificadorIntenciones` |
| Archivos JSON | `datos/intenciones.json` |
| SQLite | `base_conocimiento.py` (5 tablas) |
| Conjuntos | `STOPWORDS`, `RESPUESTAS_SI`, `RESPUESTAS_NO` |

---

## Alcance

**Incluye:** chat web, clasificación de intenciones con TF-IDF + SVM, base de conocimiento en SQLite ampliable desde la web, 2 árboles de diagnóstico (PC no enciende, sin internet), historial con pila, lectura de DHT22, LEDs de estado, LCD por WebSocket, estadísticas de uso y modo simulado.

**No incluye:** reconocimiento de voz, respuestas generadas por IA tipo ChatGPT, acceso remoto a la PC del usuario, app móvil ni usuarios con login.

## Roles del equipo

| Rol | Responsabilidad en este proyecto |
|---|---|
| Líder de proyecto | Organiza tareas y tiempos, decide el alcance |
| Programador/a Python | `chatbot.py`, `nlp/`, `app.py`, nuevas intenciones |
| Electrónico/a | Armado del UNO + DHT22 + LEDs, ESP32-S3 + LCD |
| Documentador/a | README, `docs/`, póster para la ExpoTécnica |
| Tester | `tests/`, probar frases nuevas y reportar errores |

## Ideas para mejorar
- Agregar más frases a `datos/intenciones.json` (con unas 25 por tema la precisión sube bastante).
- Nuevos árboles de diagnóstico en `estructuras.py` (impresora, sin sonido).
- Página `/admin` con gráficos de las estadísticas.
- Un buzzer en el UNO que suene cuando hay alerta de temperatura.
