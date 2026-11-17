/*
  TECHMIND Nexus - ESP32-S3 DevKit + LCD 1602 I2C
  ------------------------------------------------
  Se conecta al WiFi, abre un servidor WebSocket en el puerto 81 y muestra
  en la LCD lo que le manda Python (tema detectado, confianza, temperatura).

  Conexiones (LCD 1602 con módulo I2C PCF8574):
    LCD GND -> GND
    LCD VCC -> 5V   (pin "5V" o "VBUS" del DevKit; con 3.3V el texto casi no se ve)
    LCD SDA -> GPIO 8
    LCD SCL -> GPIO 9
    ⚠️ El módulo I2C tiene resistencias pull-up a 5V. Para cuidar el ESP32-S3
       (que trabaja a 3.3V) lo ideal es usar un conversor de nivel lógico
       bidireccional entre SDA/SCL. Ver docs/investigacion.md.

  Librerías (Arduino IDE > Administrar bibliotecas):
    - "WebSockets" de Markus Sattler (Links2004)
    - "LiquidCrystal I2C" de Frank de Brabander
  Placa: Herramientas > Placa > esp32 > "ESP32S3 Dev Module"
         (instalar antes el paquete "esp32 by Espressif Systems" en el Gestor de placas)

  Protocolo: Python envía texto "linea1|linea2" (máx. 16 caracteres por línea).
*/

#include <WiFi.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <WebSocketsServer.h>

// ====== CAMBIAR ESTOS DATOS ======
const char* WIFI_SSID = "NOMBRE_DE_TU_RED";
const char* WIFI_PASS = "CLAVE_DE_TU_RED";
// =================================

const int PIN_SDA = 8;
const int PIN_SCL = 9;
const uint8_t DIRECCION_LCD = 0x27;   // si no muestra nada, probá 0x3F (ver escáner I2C en docs)

LiquidCrystal_I2C lcd(DIRECCION_LCD, 16, 2);
WebSocketsServer servidor(81);
unsigned long ultimoMensaje = 0;
bool mostrandoReposo = false;

void mostrar(const String& linea1, const String& linea2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(linea1.substring(0, 16));
  lcd.setCursor(0, 1);
  lcd.print(linea2.substring(0, 16));
}

void conectarWiFi() {
  mostrar("Conectando WiFi", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 40) {  // 20 segundos
    delay(500);
    lcd.setCursor(15, 0);
    lcd.print(intentos % 2 ? "." : " ");
    intentos++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    // ¡Esta IP va en config.py como ESP32_WS_URL = "ws://IP:81"!
    mostrar("IP para Python:", WiFi.localIP().toString());
    Serial.print("Conectado. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    mostrar("Error de WiFi", "Revisar SSID/PASS");
    Serial.println("No se pudo conectar al WiFi");
  }
}

void alRecibirEvento(uint8_t cliente, WStype_t tipo, uint8_t* datos, size_t largo) {
  switch (tipo) {
    case WStype_CONNECTED:
      mostrar("PC conectada", "TECHMIND Nexus");
      ultimoMensaje = millis();
      mostrandoReposo = false;
      break;

    case WStype_DISCONNECTED:
      mostrar("PC desconectada", WiFi.localIP().toString());
      break;

    case WStype_TEXT: {
      String texto = "";
      for (size_t i = 0; i < largo; i++) texto += (char)datos[i];
      int separador = texto.indexOf('|');
      String l1 = separador >= 0 ? texto.substring(0, separador) : texto;
      String l2 = separador >= 0 ? texto.substring(separador + 1) : "";
      mostrar(l1, l2);
      servidor.sendTXT(cliente, "OK");
      ultimoMensaje = millis();
      mostrandoReposo = false;
      break;
    }

    default:
      break;
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(PIN_SDA, PIN_SCL);
  lcd.init();
  lcd.backlight();
  mostrar("TECHMIND Nexus", "Iniciando...");
  delay(1000);

  conectarWiFi();
  servidor.begin();
  servidor.onEvent(alRecibirEvento);
}

void loop() {
  servidor.loop();

  // Si se corta el WiFi, reconecta
  if (WiFi.status() != WL_CONNECTED) {
    conectarWiFi();
  }

  // Tras 60 s sin mensajes vuelve a la pantalla de reposo (muestra la IP)
  if (!mostrandoReposo && millis() - ultimoMensaje > 60000) {
    mostrar("TECHMIND Nexus", WiFi.localIP().toString());
    mostrandoReposo = true;
  }
}
