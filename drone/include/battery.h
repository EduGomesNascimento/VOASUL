#pragma once
#include <Arduino.h>

// Monitor da celula 3,7 V. Filtro lento porque a tensao afunda muito com o
// pico de corrente dos motores: sem filtro o alarme dispararia a cada rajada.

class Battery {
public:
  void  begin();
  void  update();

  float voltage = 4.2f;
  bool  warning  = false;   // abaixo de VBAT_WARN_V
  bool  critical = false;   // abaixo de VBAT_CRITICAL_V -> pouso automatico

private:
  bool     _init = false;
  uint32_t _lastMs = 0;
  uint32_t _lowSinceMs = 0;
};
