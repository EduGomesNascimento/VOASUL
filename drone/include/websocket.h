#pragma once
#include <Arduino.h>
#include "platform.h"

// Servidor WebSocket minimo (RFC 6455), so o que a pilotagem usa:
// aperto de mao, frames de texto, ping/pong e fechamento.
//
// Escrito a mao de proposito: as bibliotecas prontas divergem entre ESP32 e
// RP2040, e assim as duas placas rodam exatamente o mesmo codigo -- que ainda
// por cima da para testar no PC.

namespace ws {

enum Opcode : uint8_t {
  OP_CONT = 0x0, OP_TEXT = 0x1, OP_BIN = 0x2,
  OP_CLOSE = 0x8, OP_PING = 0x9, OP_PONG = 0xA
};

struct Frame {
  uint8_t  opcode = 0;
  bool     fin = false;
  uint8_t *payload = nullptr;   // aponta para dentro do buffer, ja desmascarado
  size_t   len = 0;
};

enum DecodeResult { DEC_INCOMPLETE = 0, DEC_OK = 1, DEC_ERROR = 2 };

// Maior payload aceito. Os comandos de pilotagem tem algumas dezenas de bytes;
// qualquer coisa maior e erro ou abuso, e nao caberia no buffer de recepcao.
#define WS_RX_BUFFER    320

// Calcula o valor do cabecalho Sec-WebSocket-Accept a partir do
// Sec-WebSocket-Key enviado pelo navegador. Precisa de 30 bytes em out.
void acceptKey(const char *clientKey, char *out, size_t outSize);

// Tenta extrair um frame do inicio de buf, desmascarando no proprio buffer.
// consumed recebe quantos bytes o frame ocupou.
DecodeResult decode(uint8_t *buf, size_t len, Frame &out, size_t &consumed);

// Monta o cabecalho de um frame do servidor (nunca mascarado).
// Precisa de 4 bytes em hdr; devolve o tamanho do cabecalho.
size_t encodeHeader(uint8_t *hdr, uint8_t opcode, size_t payloadLen);

}  // namespace ws

#if !PLATFORM_HOST
#include <WiFi.h>

// O core 2.x do ESP32 chama isto de available(); o 3.x e o arduino-pico usam
// accept(). available() no 3.x significa outra coisa, entao nao da para so
// escolher um dos nomes.
static inline WiFiClient serverAccept(WiFiServer &s) {
#if PLATFORM_ESP32 && ESP_ARDUINO_VERSION_MAJOR < 3
  return s.available();
#else
  return s.accept();
#endif
}

#define WS_MAX_CLIENTS  2
#define WS_HS_BUFFER    640

class WebSocketServer {
public:
  void begin(uint16_t port);
  void poll();
  void broadcast(const char *text);
  uint8_t clientCount() const;

  // Chamado para cada frame de texto recebido, ja terminado em '\0'.
  void onText(void (*cb)(const char *)) { _cb = cb; }

private:
  struct Session {
    WiFiClient sock;
    bool     open = false;
    bool     ready = false;        // aperto de mao concluido
    size_t   len = 0;
    // Dimensionado pelo aperto de mao, que e o maior dos dois usos: o cabecalho
    // HTTP do navegador passa de 400 bytes, enquanto os frames de comando tem
    // algumas dezenas. O mesmo buffer serve as duas fases.
    uint8_t  buf[WS_HS_BUFFER];
  };

  WiFiServer *_server = nullptr;
  Session     _cli[WS_MAX_CLIENTS];
  void      (*_cb)(const char *) = nullptr;

  void handshake(Session &s);
  void pump(Session &s);
  void drop(Session &s);
};
#endif  // !PLATFORM_HOST
