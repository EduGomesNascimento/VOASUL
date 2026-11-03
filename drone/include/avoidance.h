#pragma once
#include <Arduino.h>
#include "rangefinder.h"

// Desvio de obstaculos: soma uma inclinacao de fuga aos setpoints de angulo.
//
// - Ultrassom frontal: recuo proporcional entre AVOID_FRONT_SLOW_M e
//   AVOID_FRONT_STOP_M. Tambem limita o avanco pedido pelo piloto, em vez de
//   apenas empurrar para tras: assim o drone nao "briga" com o comando.
// - IR esquerdo/direito: sao digitais (so ligado/desligado), entao geram um
//   degrau lateral fixo para o lado oposto, com rampa para nao ser brusco.

class Avoidance {
public:
  void setEnabled(bool en) { _enabled = en; }
  bool enabled() const { return _enabled; }

  // Recebe os setpoints do piloto (graus) e devolve corrigidos.
  void apply(const Rangefinders &rf, float &rollSp, float &pitchSp, float dt);

  bool  frontBlocked = false;
  float frontBias = 0;   // graus aplicados no pitch
  float sideBias  = 0;   // graus aplicados no roll

private:
  bool  _enabled = true;
  float _frontRamp = 0;
  float _sideRamp  = 0;
};
