#include "avoidance.h"
#include "config.h"
#include <math.h>

void Avoidance::apply(const Rangefinders &rf, float &rollSp, float &pitchSp, float dt) {
  frontBlocked = false;

  if (!_enabled) {
    _frontRamp = 0;
    _sideRamp = 0;
    frontBias = sideBias = 0;
    return;
  }

  // ---- Ultrassom frontal ----
  float wantFront = 0;
  if (rf.frontValid && rf.frontDistance < AVOID_FRONT_SLOW_M) {
    // 0 na distancia "slow", 1 na distancia "stop"
    float t = (AVOID_FRONT_SLOW_M - rf.frontDistance) /
              (AVOID_FRONT_SLOW_M - AVOID_FRONT_STOP_M);
    t = constrain(t, 0.0f, 1.0f);
    wantFront = t * AVOID_MAX_TILT_DEG;
    frontBlocked = t > 0.5f;
  }

  // ---- IR laterais ----
  float wantSide = 0;
  if (rf.irLeft && !rf.irRight)  wantSide =  AVOID_IR_TILT_DEG;   // foge para a direita
  if (rf.irRight && !rf.irLeft)  wantSide = -AVOID_IR_TILT_DEG;   // foge para a esquerda
  // Os dois ao mesmo tempo (corredor estreito): nao ha lado bom, nao desvia.

  // Rampa de 5 graus/s: o IR e digital e liga/desliga de uma vez.
  // Aplicar o degrau direto no setpoint daria um solavanco no drone.
  const float rate = 5.0f * dt * 10.0f;
  _frontRamp += constrain(wantFront - _frontRamp, -rate, rate);
  _sideRamp  += constrain(wantSide  - _sideRamp,  -rate, rate);

  frontBias = _frontRamp;
  sideBias  = _sideRamp;

  // Pitch negativo = nariz para baixo = avanca. Para recuar, pitch positivo.
  // Alem de empurrar para tras, cortamos o avanco pedido pelo piloto: sem isso
  // o piloto com o manche todo a frente venceria o desvio e bateria assim mesmo.
  if (frontBias > 0.0f && pitchSp < 0.0f) {
    const float allowed = 1.0f - (frontBias / AVOID_MAX_TILT_DEG);
    pitchSp *= constrain(allowed, 0.0f, 1.0f);
  }
  pitchSp += frontBias;
  rollSp  += sideBias;

  pitchSp = constrain(pitchSp, -MAX_ANGLE_DEG, MAX_ANGLE_DEG);
  rollSp  = constrain(rollSp,  -MAX_ANGLE_DEG, MAX_ANGLE_DEG);
}
