#pragma once
#include <Arduino.h>

// Mixer quad X + saida PWM (LEDC). Compativel com Arduino-ESP32 core 2.x e 3.x.

class Motors {
public:
  void begin();

  // Entradas normalizadas 0..1 (throttle) e correcoes do PID em fracao de throttle.
  // roll  > 0 -> inclina para a direita
  // pitch > 0 -> nariz para cima
  // yaw   > 0 -> gira para a direita
  void mix(float throttle, float roll, float pitch, float yaw, float dt);

  void stop();                       // corta tudo, motores em 0
  void setEnabled(bool en);          // desarmado -> saida sempre 0

  // Partida suave. `armStart()` no instante de armar; enquanto `spooling()` for
  // verdadeiro os quatro motores estao subindo de 0 ate MOTOR_IDLE, defasados
  // entre si, e o controle de voo deve ficar fora do caminho (ver runControl).
  void armStart();
  bool spooling() const;

  float out[4] = {0, 0, 0, 0};       // FR, RR, RL, FL depois do mixer (0..1)

private:
  bool _enabled = false;
  bool _spoolOn = false;             // rampa de partida em andamento
  uint32_t _spoolMs = 0;             // instante em que ela comecou
  float _thrPrev = 0.0f;             // throttle comum do ciclo anterior
  float spoolCeil(uint8_t idx) const;
  void write(uint8_t idx, float value);
};
