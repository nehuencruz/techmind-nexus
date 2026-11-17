# Investigación – TECHMIND Nexus

Respuestas a las preguntas de investigación del proyecto 3.

---

## 1. ¿Qué es TF-IDF y cómo se usa en NLP?

Un modelo de aprendizaje automático no entiende palabras, solo números. **TF-IDF** (*Term Frequency – Inverse Document Frequency*) convierte cada frase en un vector de números en el que cada palabra tiene un **peso** según lo importante que es.

- **TF (frecuencia del término):** cuántas veces aparece la palabra en la frase. Si aparece más, pesa más.
- **IDF (frecuencia inversa en documentos):** qué tan rara es la palabra en el conjunto de frases. Las palabras que aparecen en todas partes ("la", "de", "mi") pesan poco. Las que aparecen en pocas frases ("impresora", "bsod") pesan mucho.

Fórmula:

```
TF-IDF(t, d) = TF(t, d) × log( N / (1 + DF(t)) )

N     = cantidad total de frases
DF(t) = cantidad de frases que contienen la palabra t
```

**Ejemplo con 3 frases de entrenamiento (valores ilustrativos):**

| Frase | "pc" | "no" | "enciend" | "lent" |
|---|---|---|---|---|
| mi pc no enciende | 0.41 | 0.41 | **0.81** | 0 |
| mi pc está lenta | 0.47 | 0 | 0 | **0.88** |
| no tengo internet | 0 | 0.52 | 0 | 0 |

"enciend" y "lent" aparecen en una sola frase, así que son las palabras que **identifican** el problema y reciben más peso.

**Cómo lo usamos en TECHMIND Nexus** (`nlp/clasificador.py`):
1. Se limpia el texto: minúsculas, sin tildes ni signos (`normalizar`).
2. Se quitan las *stopwords* y se reducen las palabras a su raíz con el stemmer Snowball de NLTK: "enciende", "encender" y "encendió" quedan como "enciend" (`tokenizar`). La palabra **"no" se conserva** porque cambia el sentido.
3. Se agregan **bigramas** ("no_enciend") para captar frases de dos palabras.
4. Un segundo TF-IDF trabaja con **trozos de 3 a 5 caracteres**. Así el bot entiende aunque haya errores de tipeo ("conputadora").

---

## 2. ¿Cómo funciona el algoritmo SVM?

**SVM** (*Support Vector Machine*, máquina de vectores de soporte) es un algoritmo de **clasificación supervisada**: aprende a partir de ejemplos que ya tienen su etiqueta.

**Idea central:** cada frase es un punto en un espacio de muchas dimensiones (una por cada palabra del vocabulario TF-IDF). El SVM busca el **hiperplano** (una "pared") que separa los puntos de dos clases dejando el **margen más ancho posible**.

```
     clase A            │            clase B
   ●    ●               │                ▲   ▲
       ●   ●  ← margen →│← margen →  ▲      ▲
   ●      [●]           │           [▲]   ▲
                    hiperplano
   [ ] = vectores de soporte (los puntos más cercanos a la pared)
```

- Los **vectores de soporte** son los ejemplos más cercanos a la frontera y son los únicos que definen el hiperplano.
- Un margen ancho hace que el modelo **generalice mejor** a frases nuevas.
- El parámetro **C** controla cuántos errores se toleran: un C alto se ajusta más a los datos (y corre riesgo de sobreajuste), un C bajo da un margen más ancho.
- **Varias clases:** con 20 intenciones, `LinearSVC` usa la estrategia *uno contra el resto*: entrena 20 SVM ("¿es saludo o no?", "¿es pantalla azul o no?"...) y gana la que da el puntaje más alto.
- **Kernel lineal:** para texto con TF-IDF los datos ya tienen tantas dimensiones que casi siempre se separan bien con un hiperplano recto. Es rápido y preciso.
- **Probabilidades:** el SVM da distancias, no porcentajes. `CalibratedClassifierCV` aprende a convertir esas distancias en una probabilidad de 0 a 1, que el bot muestra como **confianza**. Si es menor a `UMBRAL_CONFIANZA` (0.30), el bot no adivina y ofrece sugerencias.

**Por qué TF-IDF + SVM y no una red neuronal:** funciona muy bien con pocos datos (unas 300 frases), entrena en menos de un segundo en cualquier PC, no necesita GPU ni internet, y se puede explicar en una presentación.

---

## 3. ¿Cómo se conecta una LCD 1602 I2C al ESP32-S3?

La LCD 1602 tiene 16 pines, pero el **módulo adaptador I2C (chip PCF8574)** soldado atrás reduce la conexión a **4 cables**.

| LCD (módulo I2C) | ESP32-S3 DevKit | Nota |
|---|---|---|
| GND | GND | |
| VCC | 5V (pin `5V`/`VBUS`) | Con 3.3 V el contraste queda muy bajo |
| SDA | GPIO 8 | Pines I2C por defecto del S3 |
| SCL | GPIO 9 | |

En el código: `Wire.begin(8, 9);` y `LiquidCrystal_I2C lcd(0x27, 16, 2);`

**⚠️ Niveles de tensión:** el ESP32-S3 trabaja a **3.3 V** y sus pines no están garantizados para 5 V. El módulo I2C trae resistencias *pull-up* a VCC (5 V). Opciones, de la más segura a la menos segura:
1. **Recomendada:** un **conversor de nivel lógico bidireccional** (módulo de 4 canales con BSS138). El lado HV va a 5 V con la LCD, el lado LV a 3.3 V con el ESP32.
2. Sacar (desoldar) las resistencias pull-up del módulo y poner pull-ups de 4.7 kΩ a **3.3 V**.
3. Conectar directo. Suele funcionar, pero corre por cuenta del equipo.

**Ajuste de contraste:** si la pantalla se ilumina pero no se ven letras, girá el **potenciómetro azul** del módulo I2C con un destornillador.

**Encontrar la dirección I2C** (casi siempre `0x27` o `0x3F`). Cargá este escáner en el ESP32-S3 y abrí el Monitor Serie a 115200:

```cpp
#include <Wire.h>
void setup() {
  Serial.begin(115200);
  Wire.begin(8, 9);
  for (byte dir = 1; dir < 127; dir++) {
    Wire.beginTransmission(dir);
    if (Wire.endTransmission() == 0) {
      Serial.printf("Dispositivo I2C en 0x%02X\n", dir);
    }
  }
}
void loop() {}
```

---

## 4. Conexión del Arduino UNO (DHT22 + LEDs)

| Componente | Pin del UNO | Detalle |
|---|---|---|
| DHT22 VCC | 5V | |
| DHT22 DATA | D2 | Resistencia de 10 kΩ entre DATA y 5V (los módulos de 3 pines ya la traen) |
| DHT22 GND | GND | |
| LED verde (bot entendió) | D9 | Ánodo al pin, cátodo → 220 Ω → GND |
| LED amarillo (procesando) | D10 | ídem |
| LED rojo (no entendió) | D11 | ídem |

El DHT22 mide de −40 a 80 °C (±0.5 °C) y de 0 a 100 % de humedad (±2 %). **No se puede leer más rápido que cada 2 segundos.**

---

## 5. Arquitectura del sistema

```
 ┌──────────────┐  HTTP/JSON  ┌──────────────────────────────────────────┐
 │  Navegador   │◄───────────►│  PC – Python (app.py / Flask)            │
 │  (index.html)│             │   chatbot.py ─ nlp/ (TF-IDF + SVM)        │
 └──────────────┘             │   estructuras.py (pila, árbol)           │
                              │   base_conocimiento.py ─ SQLite          │
                              │   hardware.py                            │
                              └───────┬──────────────────────┬───────────┘
                         USB Serial   │                      │  WiFi WebSocket
                         9600 baud    ▼                      ▼  ws://IP:81
                       ┌──────────────────┐        ┌───────────────────────┐
                       │  Arduino UNO R3  │        │  ESP32-S3 DevKit      │
                       │  DHT22 · 3 LEDs  │        │  LCD 1602 I2C         │
                       └──────────────────┘        └───────────────────────┘
```
