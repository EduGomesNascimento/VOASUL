#include "receiver.h"
#include "config.h"
#include "platform.h"
#include "websocket.h"
#include "webui.h"

#include <WiFi.h>
#include <WiFiUdp.h>
#if PLATFORM_ESP32
  #include <esp_now.h>
#endif

static WiFiServer      *gHttp = nullptr;
static WebSocketServer  gWs;
static WiFiUDP          gUdp;
static Receiver        *gSelf = nullptr;

static void onWsText(const char *line) {
  if (gSelf) gSelf->handlePacket(line);
}

// ---- estacao terra (ESP-NOW): o callback roda na tarefa do WiFi; so copia o pacote ----
static plat_lock_t   gRadioMux;
static char          gRadioBuf[96];
static volatile bool gRadioNovo = false;
static uint8_t       gTerraMac[6];
static bool          gTerraConhecida = false;

#if PLATFORM_ESP32
static void radioRecebe(const uint8_t *mac, const uint8_t *data, int len) {
  const int n = (int)strlen(RADIO_ID);
  if (len <= n || len >= (int)sizeof(gRadioBuf) || memcmp(data, RADIO_ID, n) != 0) return;
  platLock(gRadioMux);
  memcpy(gRadioBuf, data + n, len - n);
  gRadioBuf[len - n] = '\0';
  gRadioNovo = true;
  if (mac) { memcpy(gTerraMac, mac, 6); }
  platUnlock(gRadioMux);
}
#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void onEspNow(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  radioRecebe(info ? info->src_addr : nullptr, data, len);
}
#else
static void onEspNow(const uint8_t *mac, const uint8_t *data, int len) { radioRecebe(mac, data, len); }
#endif

// telemetria de volta para a terra que mandou o ultimo comando
static void radioEnvia(const char *json) {
  uint8_t mac[6];
  platLock(gRadioMux);
  memcpy(mac, gTerraMac, 6);
  platUnlock(gRadioMux);
  if (!gTerraConhecida || memcmp(mac, gTerraMac, 6) != 0) {
    if (gTerraConhecida) esp_now_del_peer(gTerraMac);
    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, mac, 6);
    peer.channel = WIFI_CHANNEL;
    peer.ifidx = WIFI_IF_AP;          // o drone so tem o AP ligado
    gTerraConhecida = esp_now_add_peer(&peer) == ESP_OK;
    memcpy(gTerraMac, mac, 6);
  }
  char buf[260];
  const int n = snprintf(buf, sizeof(buf), TELE_ID "%s", json);
  if (n > 0 && n < (int)sizeof(buf)) esp_now_send(mac, (const uint8_t *)buf, n);
}
#endif

void Receiver::begin() {
  gSelf = this;

  platStartAP(WIFI_AP_SSID, WIFI_AP_PASS);
  Serial.printf("[WIFI] AP \"%s\"  ->  http://%s\n",
                WIFI_AP_SSID, platApIP().c_str());

  gHttp = new WiFiServer(HTTP_PORT);
  gHttp->begin();

  gWs.begin(WS_PORT);
  gWs.onText(onWsText);

  gUdp.begin(UDP_PORT);

  platLockInit(gRadioMux);
#if PLATFORM_ESP32
  if (esp_now_init() == ESP_OK && esp_now_register_recv_cb(onEspNow) == ESP_OK) {
    Serial.printf("[TERRA] ESP-NOW ouvindo no canal %d\n", WIFI_CHANNEL);
  } else {
    Serial.println("[TERRA] ESP-NOW nao iniciou: so o celular direto no drone controla");
  }
#endif
}

// Serve a pagina de pilotagem. Um cliente por chamada: nao ha motivo para
// otimizar algo que roda uma vez por carregamento de pagina.
void Receiver::serveHttp() {
  WiFiClient c = serverAccept(*gHttp);
  if (!c) return;

  // Consome os cabecalhos ate a linha em branco, com teto de tempo para o
  // caso de um cliente que abre a conexao e nao fala nada.
  const uint32_t deadline = millis() + 400;
  uint8_t nl = 0;
  while (c.connected() && millis() < deadline) {
    if (!c.available()) { delay(1); continue; }
    const char ch = (char)c.read();
    if (ch == '\n') { if (++nl == 2) break; }
    else if (ch != '\r') nl = 0;
  }

  const size_t n = strlen(WEBUI_HTML);
  char head[192];
  const int hn = snprintf(head, sizeof(head),
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Content-Length: %u\r\n"
    "Cache-Control: max-age=86400\r\n"
    "Connection: close\r\n\r\n", (unsigned)n);
  c.write((const uint8_t *)head, hn);

  // Em blocos: a pagina tem alguns KB e nao cabe de uma vez no buffer de TCP.
  size_t sent = 0;
  while (sent < n && c.connected()) {
    const size_t chunk = (n - sent > 1024) ? 1024 : (n - sent);
    const size_t w = c.write((const uint8_t *)WEBUI_HTML + sent, chunk);
    if (w == 0) break;
    sent += w;
    delay(0);
  }
  c.stop();
}

bool Receiver::radioActive() const {
  return _lastRadioMs != 0 && (millis() - _lastRadioMs) < RADIO_TIMEOUT_MS;
}

void Receiver::handlePacket(const char *line, bool fromRadio) {
  if (line[0] != 'C' || line[1] != ',') return;
  // Dois controles ao mesmo tempo brigariam: enquanto a terra manda, o celular direto so assiste.
  if (!fromRadio && radioActive()) return;

  float v[4] = {0, 0, 0, 0};
  const char *p = line + 2;
  char *end;

  for (uint8_t i = 0; i < 4; i++) {
    v[i] = strtof(p, &end);
    if (end == p) return;              // pacote truncado: descarta inteiro
    p = (*end == ',') ? end + 1 : end;
  }
  const long flags = strtol(p, &end, 10);
  if (end == p) return;

  cmd.roll     = constrain(v[0], -1.0f, 1.0f);
  cmd.pitch    = constrain(v[1], -1.0f, 1.0f);
  cmd.yaw      = constrain(v[2], -1.0f, 1.0f);
  cmd.throttle = constrain(v[3],  0.0f, 1.0f);
  cmd.arm      = flags & 1;
  cmd.altHold  = flags & 2;
  cmd.avoid    = flags & 4;
  cmd.land     = flags & 8;
  if (fromRadio) _lastRadioMs = millis();

  // So marca o link como vivo depois de um pacote inteiro e valido: lixo na
  // rede nao pode segurar o failsafe.
  cmd.lastPacketMs = millis();
}

void Receiver::poll() {
  serveHttp();
  gWs.poll();

  if (gRadioNovo) {
    char linha[sizeof(gRadioBuf)];
    platLock(gRadioMux);
    memcpy(linha, gRadioBuf, sizeof(linha));
    gRadioNovo = false;
    platUnlock(gRadioMux);
    handlePacket(linha, true);
  }

  const int sz = gUdp.parsePacket();
  if (sz > 0) {
    char buf[96];
    const int n = gUdp.read(buf, sizeof(buf) - 1);
    if (n > 0) {
      buf[n] = '\0';
      handlePacket(buf);
    }
  }
}

bool Receiver::linkAlive() const {
  return cmd.lastPacketMs != 0 && (millis() - cmd.lastPacketMs) < FAILSAFE_TIMEOUT_MS;
}

void Receiver::sendTelemetry(const Telemetry &t) {
  const uint32_t now = millis();
  if (now - _lastTeleMs < 100) return;   // 10 Hz basta e nao rouba CPU
  _lastTeleMs = now;
  const bool terra = radioActive();
  if (gWs.clientCount() == 0 && !terra) return;

  // So o que a pagina mostra: cabe com folga num pacote ESP-NOW (250 bytes).
  char buf[200];
  snprintf(buf, sizeof(buf),
    "{\"r\":%.1f,\"p\":%.1f,\"y\":%.0f,\"alt\":%.2f,\"vz\":%.2f,\"vb\":%.2f,"
    "\"armed\":%d,\"snr\":%d,\"hz\":%u,\"st\":\"%.48s\"}",
    t.roll, t.pitch, t.yaw, t.altitude, t.verticalSpeed, t.vbat,
    t.armed ? 1 : 0, t.usingSonar ? 1 : 0, t.loopHz, t.status);

  if (gWs.clientCount()) gWs.broadcast(buf);
#if PLATFORM_ESP32
  if (terra) radioEnvia(buf);
#endif
}
