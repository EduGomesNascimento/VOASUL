// ============================================================================
//  Estacao TERRA: ESP32-C3 Super Mini na capinha do celular.
//
//   celular --Wi-Fi--> terra --ESP-NOW--> drone
//   celular <--Wi-Fi-- terra <--ESP-NOW-- drone (telemetria)
//
//  - Cria a rede "VOASUL-TERRA" e serve a MESMA pagina de pilotagem do drone
//    (http://192.168.4.1). O celular manda os comandos "C,..." para a terra.
//  - Cada comando vai na hora para o drone por ESP-NOW (prefixo RADIO_ID).
//  - A telemetria do drone (prefixo TELE_ID) volta para o celular.
//  - Energia: o proprio celular, por um cabo USB-C OTG.
//  - LED: aceso = drone respondendo; piscando = sem sinal do drone.
//
//  Compila no perfil 'terra' do platformio.ini:  pio run -e terra -t upload
// ============================================================================
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "config.h"
#include "websocket.h"
#include "webui.h"

#define TERRA_SSID   "VOASUL-TERRA"
#define TERRA_PASS   WIFI_AP_PASS
#define PIN_LED      8              // LED azul do C3 Super Mini (acende com LOW)

static const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
static WiFiServer      http(HTTP_PORT);
static WebSocketServer wsServer;

static portMUX_TYPE  mux = portMUX_INITIALIZER_UNLOCKED;
static char          teleBuf[256];
static volatile bool teleNova = false;
static uint8_t       droneMac[6];
static volatile bool droneMacNovo = false;
static bool          droneConhecido = false;
static uint32_t      ultimaTele = 0, cmds = 0, teles = 0;

// ---------------------------------------------------------------- ESP-NOW
static void recebe(const uint8_t *mac, const uint8_t *data, int len) {
  const int n = (int)strlen(TELE_ID);
  if (len <= n || len >= (int)sizeof(teleBuf) || memcmp(data, TELE_ID, n) != 0) return;
  portENTER_CRITICAL(&mux);
  memcpy(teleBuf, data + n, len - n);
  teleBuf[len - n] = '\0';
  teleNova = true;
  if (mac && (!droneConhecido || memcmp(mac, droneMac, 6) != 0)) {
    memcpy(droneMac, mac, 6);
    droneMacNovo = true;
  }
  portEXIT_CRITICAL(&mux);
}
#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void onEspNow(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  recebe(info ? info->src_addr : nullptr, data, len);
}
#else
static void onEspNow(const uint8_t *mac, const uint8_t *data, int len) { recebe(mac, data, len); }
#endif

static void addPeer(const uint8_t *mac) {
  esp_now_peer_info_t p = {};
  memcpy(p.peer_addr, mac, 6);
  p.channel = WIFI_CHANNEL;
  p.ifidx = WIFI_IF_AP;
  esp_now_add_peer(&p);
}

// Comando do celular -> drone. Antes de conhecer o drone vai em broadcast; depois, direto
// para ele (assim o radio confirma a entrega e repete se perder).
static void onWsText(const char *line) {
  if (line[0] != 'C' || line[1] != ',') return;
  char buf[96];
  const int n = snprintf(buf, sizeof(buf), RADIO_ID "%s", line);
  if (n <= 0 || n >= (int)sizeof(buf)) return;
  esp_now_send(droneConhecido ? droneMac : BROADCAST, (const uint8_t *)buf, n);
  cmds++;
}

// ---------------------------------------------------------------- pagina
static void serveHttp() {
  WiFiClient c = http.accept();
  if (!c) return;
  const uint32_t prazo = millis() + 400;
  uint8_t nl = 0;
  while (c.connected() && millis() < prazo) {      // consome os cabecalhos
    if (!c.available()) { delay(1); continue; }
    const char ch = (char)c.read();
    if (ch == '\n') { if (++nl == 2) break; }
    else if (ch != '\r') nl = 0;
  }
  const size_t n = strlen(WEBUI_HTML);
  char head[192];
  const int hn = snprintf(head, sizeof(head),
    "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %u\r\n"
    "Cache-Control: max-age=86400\r\nConnection: close\r\n\r\n", (unsigned)n);
  c.write((const uint8_t *)head, hn);
  size_t enviado = 0;
  while (enviado < n && c.connected()) {
    const size_t bloco = (n - enviado > 1024) ? 1024 : (n - enviado);
    const size_t w = c.write((const uint8_t *)WEBUI_HTML + enviado, bloco);
    if (w == 0) break;
    enviado += w;
    delay(0);
  }
  c.stop();
}

static void led(bool on) { digitalWrite(PIN_LED, on ? LOW : HIGH); }

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  led(false);

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(TERRA_SSID, TERRA_PASS, WIFI_CHANNEL);
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  WiFi.setSleep(false);
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);

  if (esp_now_init() != ESP_OK) Serial.println("[TERRA] ESP-NOW falhou");
  esp_now_register_recv_cb(onEspNow);
  addPeer(BROADCAST);

  http.begin();
  wsServer.begin(WS_PORT);
  wsServer.onText(onWsText);
  Serial.printf("[TERRA] rede \"%s\" -> http://%s  (canal %d)\n", TERRA_SSID,
                WiFi.softAPIP().toString().c_str(), WIFI_CHANNEL);
}

void loop() {
  serveHttp();
  wsServer.poll();

  if (droneMacNovo) {                       // o drone respondeu: passa a falar direto com ele
    uint8_t mac[6];
    portENTER_CRITICAL(&mux);
    memcpy(mac, droneMac, 6);
    droneMacNovo = false;
    portEXIT_CRITICAL(&mux);
    addPeer(mac);
    droneConhecido = true;
    Serial.printf("[TERRA] drone %02X:%02X:%02X:%02X:%02X:%02X\n", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  }
  if (teleNova) {                            // telemetria do drone -> celular
    char json[sizeof(teleBuf)];
    portENTER_CRITICAL(&mux);
    memcpy(json, teleBuf, sizeof(json));
    teleNova = false;
    portEXIT_CRITICAL(&mux);
    ultimaTele = millis();
    teles++;
    if (wsServer.clientCount()) wsServer.broadcast(json);
  }

  const bool droneOk = ultimaTele && millis() - ultimaTele < 1000;
  static uint32_t status = 0;
  if (millis() - status > 500) {             // estado do enlace para a pagina
    status = millis();
    if (wsServer.clientCount()) {
      char s[48];
      snprintf(s, sizeof(s), "{\"terra\":1,\"drone\":%d}", droneOk ? 1 : 0);
      wsServer.broadcast(s);
    }
    Serial.printf("[TERRA] celular %u | comandos %lu | telemetria %lu | drone %s\n", wsServer.clientCount(),
                  (unsigned long)cmds, (unsigned long)teles, droneOk ? "ok" : "sem sinal");
  }
  led(droneOk || (millis() / 250) % 2);
  delay(1);
}
