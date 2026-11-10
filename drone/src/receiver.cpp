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

// ---- luva (ESP-NOW): o callback roda na tarefa do WiFi; so copia o pacote ----
static plat_lock_t   gLuvaMux;
static char          gLuvaBuf[96];
static volatile bool gLuvaNovo = false;

#if PLATFORM_ESP32
static void luvaRecebe(const uint8_t *data, int len) {
  const int n = (int)strlen(LUVA_ID);
  if (len <= n || len >= (int)sizeof(gLuvaBuf) || memcmp(data, LUVA_ID, n) != 0) return;
  platLock(gLuvaMux);
  memcpy(gLuvaBuf, data + n, len - n);
  gLuvaBuf[len - n] = '\0';
  gLuvaNovo = true;
  platUnlock(gLuvaMux);
}
#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void onEspNow(const esp_now_recv_info_t *, const uint8_t *data, int len) { luvaRecebe(data, len); }
#else
static void onEspNow(const uint8_t *, const uint8_t *data, int len) { luvaRecebe(data, len); }
#endif
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

  platLockInit(gLuvaMux);
#if PLATFORM_ESP32
  if (esp_now_init() == ESP_OK && esp_now_register_recv_cb(onEspNow) == ESP_OK) {
    Serial.printf("[LUVA] ESP-NOW ouvindo no canal %d\n", WIFI_CHANNEL);
  } else {
    Serial.println("[LUVA] ESP-NOW nao iniciou: so o celular controla");
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

bool Receiver::gloveActive() const {
  return _lastGloveMs != 0 && (millis() - _lastGloveMs) < LUVA_TIMEOUT_MS;
}

void Receiver::handlePacket(const char *line, bool fromGlove) {
  if (line[0] != 'C' || line[1] != ',') return;
  // Dois controles ao mesmo tempo brigariam: enquanto a luva manda, o celular so assiste.
  if (!fromGlove && gloveActive()) return;

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
  if (fromGlove) _lastGloveMs = millis();

  // So marca o link como vivo depois de um pacote inteiro e valido: lixo na
  // rede nao pode segurar o failsafe.
  cmd.lastPacketMs = millis();
}

void Receiver::poll() {
  serveHttp();
  gWs.poll();

  if (gLuvaNovo) {
    char linha[sizeof(gLuvaBuf)];
    platLock(gLuvaMux);
    memcpy(linha, gLuvaBuf, sizeof(linha));
    gLuvaNovo = false;
    platUnlock(gLuvaMux);
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
  if (gWs.clientCount() == 0) return;

  char buf[400];
  snprintf(buf, sizeof(buf),
    "{\"r\":%.1f,\"p\":%.1f,\"y\":%.0f,\"alt\":%.2f,\"vz\":%.2f,"
    "\"g\":%.2f,\"f\":%.2f,\"il\":%d,\"ir\":%d,\"vb\":%.2f,"
    "\"armed\":%d,\"snr\":%d,\"hz\":%u,\"lv\":%d,"
    "\"fl\":%u,\"vf\":%.2f,\"vr\":%.2f,\"sq\":%u,\"st\":\"%s\"}",
    t.roll, t.pitch, t.yaw, t.altitude, t.verticalSpeed,
    t.ground, t.front, t.irL ? 1 : 0, t.irR ? 1 : 0, t.vbat,
    t.armed ? 1 : 0, t.usingSonar ? 1 : 0, t.loopHz, gloveActive() ? 1 : 0,
    t.flow, t.flowVf, t.flowVr, t.flowSq, t.status);

  gWs.broadcast(buf);
}
