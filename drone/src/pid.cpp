#include "pid.h"

static constexpr float TWO_PI_F = 6.28318530718f;

void PID::init(float kp, float ki, float kd, float iLimit, float outLimit,
               float dLpfHz) {
  _kp = kp; _ki = ki; _kd = kd;
  _iLimit = iLimit; _outLimit = outLimit;
  _dLpfRC = (dLpfHz > 0.0f) ? (1.0f / (TWO_PI_F * dLpfHz)) : 0.0f;
  reset();
}

void PID::reset() {
  p = i = d = 0;
  _prevMeas = 0;
  _first = true;
}

float PID::update(float setpoint, float measurement, float dt) {
  if (dt <= 0.0f) return constrain(p + i + d, -_outLimit, _outLimit);

  const float error = setpoint - measurement;

  p = _kp * error;

  i += _ki * error * dt;
  i = constrain(i, -_iLimit, _iLimit);

  // Derivada na medida (com sinal invertido): um degrau no setpoint nao
  // produz o pico que a derivada do erro geraria.
  if (_first) {
    d = 0;
    _first = false;
  } else {
    const float raw = -_kd * (measurement - _prevMeas) / dt;
    if (_dLpfRC > 0.0f) {
      // Passa-baixa de primeira ordem, com alfa recalculado a cada passo:
      // o dt do loop varia um pouco, e usar um alfa fixo mudaria a frequencia
      // de corte junto com ele.
      const float alpha = dt / (dt + _dLpfRC);
      d += alpha * (raw - d);
    } else {
      d = raw;
    }
  }
  _prevMeas = measurement;

  return constrain(p + i + d, -_outLimit, _outLimit);
}
