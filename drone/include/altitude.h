#pragma once
#include <Arduino.h>

// Estimador de altitude por fusao de tres fontes:
//   - ultrassom para baixo : preciso (~1 cm) mas so ate ~3 m e sensivel a inclinacao
//   - barometro BMP280     : funciona em qualquer altura, com ruido de +-0,5 m
//   - aceleracao vertical  : da a velocidade, corrige o atraso dos outros dois
//
// Abaixo de SONAR_MAX_M manda o sonar; acima, o barometro assume, com transicao
// suave para nao dar um degrau no controle de altitude.

class AltitudeEstimator {
public:
  void  reset();
  void  update(float sonarM, bool sonarValid,
               float baroM, float earthAccZ, float dt);

  float altitude = 0;    // metros acima do ponto de decolagem
  float velocity = 0;    // m/s, positivo para cima
  bool  usingSonar = false;

private:
  float _baroBias = 0;   // alinha o barometro com o sonar enquanto o sonar e valido
  bool  _init = false;
};
