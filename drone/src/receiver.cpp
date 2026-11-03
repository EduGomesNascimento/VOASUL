#include "receiver.h"
#include "config.h"
#include "platform.h"
#include "websocket.h"
#include "webui.h"

#include <WiFi.h>
#include <WiFiUdp.h>

static WiFiServer      *gHttp = nullptr;
static WebSocketServer  gWs;
static WiFiUDP          gUdp;
static Receiver        *gSelf = nullptr;

static void onWsText(const char *line) {
  if (gSelf) gSelf->handlePacket(line);
}

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

void Receiver::handlePacket(const char *line) {
  if (line[0] != 'C' || line[1] != ',') return;

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

  // So marca o link como vivo depois de um pacote inteiro e valido: lixo na
  // rede nao pode segurar o failsafe.
  cmd.lastPacketMs = millis();
}

void Receiver::poll() {
  serveHttp();
  gWs.poll();

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

  char buf[320];
  snprintf(buf, sizeof(buf),
    "{\"r\":%.1f,\"p\":%.1f,\"y\":%.0f,\"alt\":%.2f,\"vz\":%.2f,"
    "\"g\":%.2f,\"f\":%.2f,\"il\":%d,\"ir\":%d,\"vb\":%.2f,"
    "\"armed\":%d,\"snr\":%d,\"hz\":%u,\"st\":\"%s\"}",
    t.roll, t.pitch, t.yaw, t.altitude, t.verticalSpeed,
    t.ground, t.front, t.irL ? 1 : 0, t.irR ? 1 : 0, t.vbat,
    t.armed ? 1 : 0, t.usingSonar ? 1 : 0, t.loopHz, t.status);

  gWs.broadcast(buf);
}
