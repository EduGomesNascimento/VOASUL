#include "altitude.h"
#include "config.h"
#include <math.h>

void AltitudeEstimator::reset() {
  altitude = 0;
  velocity = 0;
  _baroBias = 0;
  _init = false;
  usingSonar = false;
}

void AltitudeEstimator::update(float sonarM, bool sonarValid,
                               float baroM, float earthAccZ, float dt) {
  if (!_init) {
    altitude = sonarValid ? sonarM : baroM;
    _baroBias = baroM - altitude;
    velocity = 0;
    _init = true;
    return;
  }

  // Predicao por aceleracao vertical: da a resposta rapida que barometro e
  // ultrassom (20-26 Hz, com atraso) nao conseguem entregar sozinhos.
  velocity += earthAccZ * dt;
  altitude += velocity * dt;

  float measurement;
  float kAlt, kVel;

  if (sonarValid && sonarM < SONAR_MAX_M * 0.85f) {
    // Sonar manda: e o unico que sabe onde esta o chao de verdade.
    measurement = sonarM;
    kAlt = 3.0f;
    kVel = 2.0f;
    usingSonar = true;
    // Mantem o barometro calibrado contra o sonar enquanto ele e confiavel,
    // para que a troca de fonte na subida nao produza um degrau de altitude.
    _baroBias += (baroM - sonarM - _baroBias) * 0.5f * dt;
  } else {
    measurement = baroM - _baroBias;
    kAlt = 0.6f;      // barometro e ruidoso, entra com peso baixo
    kVel = 0.3f;
    usingSonar = false;
  }

  // Correcao complementar de 2 estados: o residuo empurra altitude e velocidade.
  const float residual = measurement - altitude;
  altitude += kAlt * residual * dt;
  velocity += kVel * residual * dt;

  velocity = constrain(velocity, -6.0f, 6.0f);
}
