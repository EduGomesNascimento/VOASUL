#pragma once
#include <Arduino.h>

// Comandos vindos do celular/PC.
//
// Dois caminhos, ambos ativos ao mesmo tempo:
//   - WebSocket (porta 81): usado pela pagina HTML embarcada, funciona em
//     qualquer navegador de celular.
//   - UDP (porta 4210): para um transmissor dedicado no futuro; tem menos
//     latencia, mas o navegador nao consegue falar UDP.
//
// Protocolo de texto, um pacote por linha:
//   C,<roll>,<pitch>,<yaw>,<throttle>,<flags>
//     roll/pitch/yaw : -1.0 .. 1.0
//     throttle       :  0.0 .. 1.0
//     flags (bitmask): 1=armar  2=alt-hold  4=desvio de obstaculos

struct ControlInput {
  float roll = 0, pitch = 0, yaw = 0, throttle = 0;
  bool  arm = false;
  bool  altHold = false;
  bool  avoid = true;
  uint32_t lastPacketMs = 0;
};

struct Telemetry {
  float roll, pitch, yaw;
  float altitude, verticalSpeed;
  float ground, front;
  bool  irL, irR;
  float vbat;
  bool  armed, altHold, avoid, usingSonar;
  float m[4];
  uint16_t loopHz;
  const char *status;
};

class Receiver {
public:
  void begin();
  void poll();
  void sendTelemetry(const Telemetry &t);
  bool linkAlive() const;

  // Publico porque o callback do WebSocket e uma funcao livre, fora da classe.
  void handlePacket(const char *line);

  ControlInput cmd;

private:
  uint32_t _lastTeleMs = 0;
  void serveHttp();
};
