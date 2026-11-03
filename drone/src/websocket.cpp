#include "websocket.h"
#include "sha1.h"
#include <string.h>

namespace ws {

static const char GUID[] = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

void acceptKey(const char *clientKey, char *out, size_t outSize) {
  char joined[128];
  const size_t kn = strlen(clientKey);
  if (kn + sizeof(GUID) > sizeof(joined)) { if (outSize) out[0] = '\0'; return; }

  memcpy(joined, clientKey, kn);
  memcpy(joined + kn, GUID, sizeof(GUID) - 1);

  uint8_t digest[20];
  sha1((const uint8_t *)joined, kn + sizeof(GUID) - 1, digest);
  base64Encode(digest, 20, out, outSize);
}

DecodeResult decode(uint8_t *buf, size_t len, Frame &out, size_t &consumed) {
  consumed = 0;
  if (len < 2) return DEC_INCOMPLETE;

  const uint8_t b0 = buf[0], b1 = buf[1];
  out.fin    = (b0 & 0x80) != 0;
  out.opcode = b0 & 0x0F;

  const bool masked = (b1 & 0x80) != 0;
  uint64_t plen = b1 & 0x7F;
  size_t pos = 2;

  if (plen == 126) {
    if (len < 4) return DEC_INCOMPLETE;
    plen = ((uint64_t)buf[2] << 8) | buf[3];
    pos = 4;
  } else if (plen == 127) {
    // Comandos de pilotagem tem dezenas de bytes. Um frame de 64 bits aqui so
    // pode ser erro ou ataque, e nao cabe no buffer de qualquer forma.
    return DEC_ERROR;
  }

  // O RFC exige que todo frame vindo do cliente venha mascarado.
  if (!masked) return DEC_ERROR;

  if (plen > WS_RX_BUFFER) return DEC_ERROR;
  if (len < pos + 4 + plen) return DEC_INCOMPLETE;

  const uint8_t *mask = buf + pos;
  pos += 4;

  uint8_t *p = buf + pos;
  for (uint64_t i = 0; i < plen; i++) p[i] ^= mask[i & 3];

  out.payload = p;
  out.len = (size_t)plen;
  consumed = pos + (size_t)plen;
  return DEC_OK;
}

size_t encodeHeader(uint8_t *hdr, uint8_t opcode, size_t payloadLen) {
  hdr[0] = 0x80 | (opcode & 0x0F);   // FIN + opcode
  if (payloadLen < 126) {
    hdr[1] = (uint8_t)payloadLen;    // servidor nunca mascara
    return 2;
  }
  hdr[1] = 126;
  hdr[2] = (uint8_t)(payloadLen >> 8);
  hdr[3] = (uint8_t)(payloadLen);
  return 4;
}

}  // namespace ws

// ===========================================================================
#if !PLATFORM_HOST

void WebSocketServer::begin(uint16_t port) {
  _server = new WiFiServer(port);
  _server->begin();
}

void WebSocketServer::drop(Session &s) {
  s.sock.stop();
  s.open = false;
  s.ready = false;
  s.len = 0;
}

void WebSocketServer::handshake(Session &s) {
  // Acumula ate o fim dos cabecalhos HTTP.
  while (s.sock.available() && s.len < WS_HS_BUFFER - 1) {
    s.buf[s.len++] = (uint8_t)s.sock.read();
    if (s.len >= 4 && memcmp(s.buf + s.len - 4, "\r\n\r\n", 4) == 0) break;
  }
  s.buf[s.len] = '\0';

  if (s.len < 4 || memcmp(s.buf + s.len - 4, "\r\n\r\n", 4) != 0) {
    if (s.len >= WS_HS_BUFFER - 1) drop(s);   // cabecalho absurdo, descarta
    return;                                    // ainda chegando
  }

  // Procura o Sec-WebSocket-Key (case-insensitive, como manda o HTTP).
  char *line = nullptr;
  for (char *p = (char *)s.buf; *p; p++) {
    if (strncasecmp(p, "Sec-WebSocket-Key:", 18) == 0) { line = p + 18; break; }
  }
  if (!line) { drop(s); return; }

  while (*line == ' ') line++;
  char key[64];
  size_t n = 0;
  while (line[n] && line[n] != '\r' && line[n] != '\n' && n < sizeof(key) - 1) {
    key[n] = line[n];
    n++;
  }
  key[n] = '\0';

  char accept[40];
  ws::acceptKey(key, accept, sizeof(accept));
  if (accept[0] == '\0') { drop(s); return; }

  char resp[200];
  const int m = snprintf(resp, sizeof(resp),
    "HTTP/1.1 101 Switching Protocols\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    "Sec-WebSocket-Accept: %s\r\n\r\n", accept);
  s.sock.write((const uint8_t *)resp, m);

  s.ready = true;
  s.len = 0;
}

void WebSocketServer::pump(Session &s) {
  while (s.sock.available() && s.len < WS_RX_BUFFER) {
    s.buf[s.len++] = (uint8_t)s.sock.read();
  }

  for (;;) {
    ws::Frame f;
    size_t used = 0;
    const ws::DecodeResult r = ws::decode(s.buf, s.len, f, used);

    if (r == ws::DEC_INCOMPLETE) {
      // Buffer cheio sem frame completo: o fluxo dessincronizou, nao ha como
      // reencontrar o inicio de um frame. Derrubar e deixar o cliente
      // reconectar e mais seguro do que interpretar lixo como comando.
      if (s.len >= WS_RX_BUFFER) drop(s);
      return;
    }
    if (r == ws::DEC_ERROR) { drop(s); return; }

    if (f.opcode == ws::OP_TEXT && _cb) {
      char txt[WS_RX_BUFFER];
      const size_t n = f.len < sizeof(txt) - 1 ? f.len : sizeof(txt) - 1;
      memcpy(txt, f.payload, n);
      txt[n] = '\0';
      _cb(txt);
    } else if (f.opcode == ws::OP_PING) {
      uint8_t hdr[4];
      const size_t hn = ws::encodeHeader(hdr, ws::OP_PONG, f.len);
      s.sock.write(hdr, hn);
      if (f.len) s.sock.write(f.payload, f.len);
    } else if (f.opcode == ws::OP_CLOSE) {
      drop(s);
      return;
    }

    // Consome o frame tratado e desliza o resto para o inicio.
    memmove(s.buf, s.buf + used, s.len - used);
    s.len -= used;
    if (s.len == 0) return;
  }
}

void WebSocketServer::poll() {
  if (!_server) return;

  WiFiClient incoming = serverAccept(*_server);
  if (incoming) {
    bool placed = false;
    for (uint8_t i = 0; i < WS_MAX_CLIENTS && !placed; i++) {
      if (!_cli[i].open) {
        _cli[i].sock = incoming;
        _cli[i].open = true;
        _cli[i].ready = false;
        _cli[i].len = 0;
        placed = true;
      }
    }
    if (!placed) incoming.stop();   // lotado
  }

  for (uint8_t i = 0; i < WS_MAX_CLIENTS; i++) {
    Session &s = _cli[i];
    if (!s.open) continue;
    if (!s.sock.connected()) { drop(s); continue; }
    if (!s.ready) handshake(s);
    else          pump(s);
  }
}

void WebSocketServer::broadcast(const char *text) {
  const size_t n = strlen(text);
  uint8_t hdr[4];
  const size_t hn = ws::encodeHeader(hdr, ws::OP_TEXT, n);

  for (uint8_t i = 0; i < WS_MAX_CLIENTS; i++) {
    Session &s = _cli[i];
    if (!s.open || !s.ready) continue;
    s.sock.write(hdr, hn);
    s.sock.write((const uint8_t *)text, n);
  }
}

uint8_t WebSocketServer::clientCount() const {
  uint8_t n = 0;
  for (uint8_t i = 0; i < WS_MAX_CLIENTS; i++) if (_cli[i].open && _cli[i].ready) n++;
  return n;
}

#endif  // !PLATFORM_HOST
