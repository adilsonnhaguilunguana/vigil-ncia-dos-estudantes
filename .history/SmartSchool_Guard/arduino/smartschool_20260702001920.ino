/*
 * SmartSchool Guard - ESP8266
 * Sistema de controlo de porta com reconhecimento facial
 * 
 * Hardware:
 * - ESP8266 (NodeMCU ou Wemos D1)
 * - Relé para trava electromagnética (GPIO5/D1)
 * - LED Verde (GPIO4/D2)
 * - LED Vermelho (GPIO0/D3)
 * - Buzzer (GPIO14/D5)
 * - DHT22 (GPIO12/D6)
 * 
 * Endpoints HTTP:
 * - GET /porta/abrir      → Abre a trava (2 segundos)
 * - GET /porta/fechar     → Fecha a trava
 * - GET /led/verde        → Acende LED verde
 * - GET /led/vermelho     → Acende LED vermelho
 * - GET /led/desligar     → Desliga todos os LEDs
 * - GET /buzzer/ok        → Beep curto (1x)
 * - GET /buzzer/alerta    → Beep longo (3x)
 * - GET /buzzer/desligar  → Desliga o buzzer
 * - GET /temperatura      → Retorna JSON com temp e humidade
 * - GET /status           → Retorna status geral
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <DHT.h>

// ============================================================
// CONFIGURAÇÃO DE REDE WI-FI
// ============================================================
const char* ssid = "NOME_DA_REDE";
const char* password = "SENHA_DA_REDE";

// ============================================================
// CONFIGURAÇÃO DOS PINOS
// ============================================================
#define PIN_RELE       5   // D1 - Trava electromagnética
#define PIN_LED_VERDE  4   // D2 - LED Verde
#define PIN_LED_VERMELHO 0 // D3 - LED Vermelho
#define PIN_BUZZER     14  // D5 - Buzzer
#define PIN_DHT        12  // D6 - Sensor DHT22

// ============================================================
// CONFIGURAÇÃO DO SENSOR DHT
// ============================================================
#define DHTTYPE DHT22
DHT dht(PIN_DHT, DHTTYPE);

// ============================================================
// CONFIGURAÇÃO DO SERVIDOR WEB
// ============================================================
ESP8266WebServer server(80);

// ============================================================
// VARIÁVEIS GLOBAIS
// ============================================================
unsigned long tempoInicio = 0;
bool portaAberta = false;
bool ledVerdeEstado = false;
bool ledVermelhoEstado = false;
bool buzzerEstado = false;
float temperatura = 0;
float humidade = 0;
unsigned long ultimaLeituraDHT = 0;
unsigned long tempoPortaAberta = 0;

// ============================================================
// SETUP INICIAL
// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("=========================================");
  Serial.println("  SmartSchool Guard - ESP8266");
  Serial.println("=========================================");
  
  // Configurar pinos
  pinMode(PIN_RELE, OUTPUT);
  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_VERMELHO, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  
  // Estado inicial: tudo desligado
  digitalWrite(PIN_RELE, HIGH);       // Relé desligado (ativo baixo)
  digitalWrite(PIN_LED_VERDE, LOW);
  digitalWrite(PIN_LED_VERMELHO, LOW);
  digitalWrite(PIN_BUZZER, LOW);
  
  // Inicializar sensor DHT
  dht.begin();
  
  // Conectar ao Wi-Fi
  conectarWiFi();
  
  // Configurar rotas do servidor web
  configurarRotas();
  
  // Iniciar servidor
  server.begin();
  Serial.println("✅ Servidor HTTP iniciado na porta 80");
  
  tempoInicio = millis();
}

// ============================================================
// LOOP PRINCIPAL
// ============================================================
void loop() {
  server.handleClient();
  
  // Verificar se a porta deve fechar (após 2 segundos)
  if (portaAberta && (millis() - tempoPortaAberta > 2000)) {
    fecharPorta();
  }
  
  // Ler sensor DHT a cada 10 segundos
  if (millis() - ultimaLeituraDHT > 10000) {
    lerSensorDHT();
    ultimaLeituraDHT = millis();
  }
}

// ============================================================
// CONEXÃO WI-FI
// ============================================================
void conectarWiFi() {
  Serial.print("📶 A conectar ao Wi-Fi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED && tentativas < 30) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("✅ Wi-Fi conectado!");
    Serial.print("   IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("   Sinal: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println();
    Serial.println("❌ Falha na conexão Wi-Fi!");
  }
}

// ============================================================
// CONFIGURAÇÃO DAS ROTAS HTTP
// ============================================================
void configurarRotas() {
  
  // Porta
  server.on("/porta/abrir", HTTP_GET, []() {
    abrirPorta();
    server.send(200, "text/plain", "PORTA ABERTA");
  });
  
  server.on("/porta/fechar", HTTP_GET, []() {
    fecharPorta();
    server.send(200, "text/plain", "PORTA FECHADA");
  });
  
  // LEDs
  server.on("/led/verde", HTTP_GET, []() {
    ligarLEDVerde();
    server.send(200, "text/plain", "LED VERDE LIGADO");
  });
  
  server.on("/led/vermelho", HTTP_GET, []() {
    ligarLEDVermelho();
    server.send(200, "text/plain", "LED VERMELHO LIGADO");
  });
  
  server.on("/led/desligar", HTTP_GET, []() {
    desligarLEDs();
    server.send(200, "text/plain", "LEDS DESLIGADOS");
  });
  
  // Buzzer
  server.on("/buzzer/ok", HTTP_GET, []() {
    beepOK();
    server.send(200, "text/plain", "BUZZER OK");
  });
  
  server.on("/buzzer/alerta", HTTP_GET, []() {
    beepAlerta();
    server.send(200, "text/plain", "BUZZER ALERTA");
  });
  
  server.on("/buzzer/desligar", HTTP_GET, []() {
    desligarBuzzer();
    server.send(200, "text/plain", "BUZZER DESLIGADO");
  });
  
  // Sensores
  server.on("/temperatura", HTTP_GET, []() {
    lerSensorDHT();
    String json = "{";
    json += "\"temperatura\":" + String(temperatura, 1) + ",";
    json += "\"humidade\":" + String(humidade, 1) + ",";
    json += "\"indice_calor\":" + String(calcularIndiceCalor(temperatura, humidade), 1);
    json += "}";
    server.send(200, "application/json", json);
  });
  
  // Status geral
  server.on("/status", HTTP_GET, []() {
    String json = "{";
    json += "\"online\":true,";
    json += "\"porta_aberta\":" + String(portaAberta ? "true" : "false") + ",";
    json += "\"led_verde\":" + String(ledVerdeEstado ? "true" : "false") + ",";
    json += "\"led_vermelho\":" + String(ledVermelhoEstado ? "true" : "false") + ",";
    json += "\"buzzer\":" + String(buzzerEstado ? "true" : "false") + ",";
    json += "\"temperatura\":" + String(temperatura, 1) + ",";
    json += "\"humidade\":" + String(humidade, 1) + ",";
    json += "\"wifi_sinal\":" + String(WiFi.RSSI()) + ",";
    json += "\"uptime\":" + String((millis() - tempoInicio) / 1000);
    json += "}";
    server.send(200, "application/json", json);
  });
  
  // Rota não encontrada
  server.onNotFound([]() {
    server.send(404, "text/plain", "Rota não encontrada");
  });
}

// ============================================================
// CONTROLO DA PORTA (TRAVA ELECTROMAGNÉTICA)
// ============================================================
void abrirPorta() {
  Serial.println("🔓 Abrindo porta...");
  digitalWrite(PIN_RELE, LOW);  // Ativar relé (ativo baixo)
  portaAberta = true;
  tempoPortaAberta = millis();
}

void fecharPorta() {
  Serial.println("🔒 Fechando porta...");
  digitalWrite(PIN_RELE, HIGH);  // Desativar relé
  portaAberta = false;
}

// ============================================================
// CONTROLO DOS LEDS
// ============================================================
void ligarLEDVerde() {
  Serial.println("🟢 LED Verde ligado");
  digitalWrite(PIN_LED_VERDE, HIGH);
  digitalWrite(PIN_LED_VERMELHO, LOW);
  ledVerdeEstado = true;
  ledVermelhoEstado = false;
  
  // Auto-desligar após 3 segundos
  delay(3000);
  digitalWrite(PIN_LED_VERDE, LOW);
  ledVerdeEstado = false;
}

void ligarLEDVermelho() {
  Serial.println("🔴 LED Vermelho ligado");
  digitalWrite(PIN_LED_VERMELHO, HIGH);
  digitalWrite(PIN_LED_VERDE, LOW);
  ledVermelhoEstado = true;
  ledVerdeEstado = false;
  
  // Auto-desligar após 5 segundos
  delay(5000);
  digitalWrite(PIN_LED_VERMELHO, LOW);
  ledVermelhoEstado = false;
}

void desligarLEDs() {
  Serial.println("⚫ LEDs desligados");
  digitalWrite(PIN_LED_VERDE, LOW);
  digitalWrite(PIN_LED_VERMELHO, LOW);
  ledVerdeEstado = false;
  ledVermelhoEstado = false;
}

// ============================================================
// CONTROLO DO BUZZER
// ============================================================
void beepOK() {
  Serial.println("🔔 Beep OK (1x curto)");
  buzzerEstado = true;
  digitalWrite(PIN_BUZZER, HIGH);
  delay(200);
  digitalWrite(PIN_BUZZER, LOW);
  delay(100);
  buzzerEstado = false;
}

void beepAlerta() {
  Serial.println("🚨 Beep Alerta (3x longo)");
  buzzerEstado = true;
  for (int i = 0; i < 3; i++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(500);
    digitalWrite(PIN_BUZZER, LOW);
    delay(200);
  }
  buzzerEstado = false;
}

void desligarBuzzer() {
  Serial.println("🔇 Buzzer desligado");
  digitalWrite(PIN_BUZZER, LOW);
  buzzerEstado = false;
}

// ============================================================
// SENSOR DHT22
// ============================================================
void lerSensorDHT() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  
  if (!isnan(t) && !isnan(h)) {
    temperatura = t;
    humidade = h;
    Serial.print("🌡️ Temp: ");
    Serial.print(temperatura);
    Serial.print("°C | Hum: ");
    Serial.print(humidade);
    Serial.println("%");
  } else {
    Serial.println("❌ Erro ao ler DHT22!");
  }
}

// ============================================================
// CÁLCULO DO ÍNDICE DE CALOR (SENSAÇÃO TÉRMICA)
// ============================================================
float calcularIndiceCalor(float temp, float hum) {
  // Fórmula simplificada do índice de calor
  // Válida para temperaturas > 27°C e humidade > 40%
  if (temp < 27 || hum < 40) {
    return temp;
  }
  
  float hi = 0.5 * (temp + 61.0 + ((temp - 68.0) * 1.2) + (hum * 0.094));
  
  if (hi < 27) {
    return temp;
  }
  
  return hi;
}