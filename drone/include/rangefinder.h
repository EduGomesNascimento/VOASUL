#pragma once
#include <Arduino.h>
#include "platform.h"

// Ultrassom HC-SR04 sem bloqueio.
//
// pulseIn() trava a CPU por ate 30 ms. Num loop de 400 Hz (2,5 ms) isso
// destruiria a estabilizacao, entao a medida do eco e feita por interrupcao
// e os dois sensores disparam alternados para nao haver diafonia entre eles.

class Sonar {
public:
  void  begin(uint8_t trigPin, uint8_t echoPin, void (*isr)());
  void  trigger();
  void IRAM_ATTR onEcho();           // chamado pela ISR
  bool  poll(float speedOfSound);    // processa eco pendente; true se ha leitura nova
  bool  isValid(uint32_t maxAgeMs = 200) const;

  float distance = -1.0f;            // metros, -1 = sem leitura valida
  uint32_t lastValidMs = 0;

private:
  uint8_t _trig = 255, _echo = 255;
  volatile uint32_t _riseUs = 0;
  volatile uint32_t _pulseUs = 0;
  volatile bool     _pending = false;
  uint32_t _trigMs = 0;
  float    _med[3] = {-1, -1, -1};
  uint8_t  _medIdx = 0;
};

// Modulo IR de obstaculo (FC-51). Saida digital com anti-repique.
class IRSensor {
public:
  void begin(uint8_t pin);
  void poll();
  bool detected() const { return _stable; }

private:
  uint8_t  _pin = 255;
  bool     _stable = false;
  bool     _last = false;
  uint32_t _changeMs = 0;
};

// Agrupa os quatro sensores de proximidade e faz o escalonamento dos disparos.
class Rangefinders {
public:
  void  begin();
  void  update(float temperatureC, float tiltCos, float tiltDeg);

  float groundDistance = -1.0f;   // metros, ja corrigido pela inclinacao
  float frontDistance  = -1.0f;   // metros
  bool  groundValid    = false;
  bool  frontValid     = false;
  bool  irLeft         = false;
  bool  irRight        = false;

private:
  uint32_t _lastTrigMs = 0;
  uint8_t  _turn = 0;
};
