/*
  TECHMIND Nexus - Arduino UNO R3
  --------------------------------
  Lee el sensor DHT22 y lo envía a la PC por USB (Serial).
  Recibe comandos de la PC para encender los LEDs de estado.

  Conexiones:
    DHT22  VCC  -> 5V
    DHT22  DATA -> Pin 2   (+ resistencia de 10k entre DATA y 5V si el módulo no la trae)
    DHT22  GND  -> GND
    LED verde    -> Pin 9  (con resistencia de 220 ohm a GND)
    LED amarillo -> Pin 10 (con resistencia de 220 ohm a GND)
    LED rojo     -> Pin 11 (con resistencia de 220 ohm a GND)

  Librería necesaria (Arduino IDE > Herramientas > Administrar bibliotecas):
    "DHT sensor library" de Adafruit (instala también "Adafruit Unified Sensor")

  Protocolo (9600 baudios, una línea por mensaje):
    UNO -> PC :  T:23.5;H:48.2      cada 2 segundos
                 E:DHT              si falla la lectura
    PC  -> UNO:  L:V  verde | L:A  amarillo | L:R  rojo | L:0  apagar
*/

#include <DHT.h>

#define PIN_DHT 2
#define TIPO_DHT DHT22

const int LED_VERDE = 9;
const int LED_AMARILLO = 10;
const int LED_ROJO = 11;
const unsigned long INTERVALO_MS = 2000;  // el DHT22 no se puede leer más rápido que cada 2 s

DHT dht(PIN_DHT, TIPO_DHT);
unsigned long ultimaLectura = 0;
String bufferEntrada = "";

void apagarLeds() {
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_AMARILLO, LOW);
  digitalWrite(LED_ROJO, LOW);
}

void secuenciaInicio() {
  // Prueba visual: enciende cada LED al arrancar
  int leds[] = {LED_VERDE, LED_AMARILLO, LED_ROJO};
  for (int i = 0; i < 3; i++) {
    digitalWrite(leds[i], HIGH);
    delay(200);
    digitalWrite(leds[i], LOW);
  }
}

void procesarComando(String comando) {
  comando.trim();
  if (!comando.startsWith("L:") || comando.length() < 3) return;

  apagarLeds();
  switch (comando.charAt(2)) {
    case 'V': digitalWrite(LED_VERDE, HIGH); break;
    case 'A': digitalWrite(LED_AMARILLO, HIGH); break;
    case 'R': digitalWrite(LED_ROJO, HIGH); break;
    default: break;  // 'L:0' o desconocido: quedan apagados
  }
}

void leerSensor() {
  float humedad = dht.readHumidity();
  float temperatura = dht.readTemperature();  // en °C

  if (isnan(humedad) || isnan(temperatura)) {
    Serial.println("E:DHT");
    return;
  }
  Serial.print("T:");
  Serial.print(temperatura, 1);
  Serial.print(";H:");
  Serial.println(humedad, 1);
}

void setup() {
  Serial.begin(9600);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AMARILLO, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);
  dht.begin();
  secuenciaInicio();
}

void loop() {
  // 1) Lectura del sensor sin usar delay() (así no se bloquean los comandos)
  if (millis() - ultimaLectura >= INTERVALO_MS) {
    ultimaLectura = millis();
    leerSensor();
  }

  // 2) Comandos que llegan desde la PC
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      procesarComando(bufferEntrada);
      bufferEntrada = "";
    } else if (c != '\r' && bufferEntrada.length() < 20) {
      bufferEntrada += c;
    }
  }
}
