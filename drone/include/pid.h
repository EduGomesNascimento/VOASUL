#pragma once
#include <Arduino.h>

// PID com derivada na medida (evita chute na saida quando o setpoint muda),
// anti-windup por clamp no integrador e filtro passa-baixa no termo D.
//
// Por que so o D e filtrado: derivar amplifica ruido na proporcao da
// frequencia. A vibracao das helices chega ao giroscopio como algumas centenas
// de Hz, e sem filtro o termo D transforma isso em comando de motor -- o drone
// esquenta os motores tentando corrigir tremor que nao existe como movimento.
// O termo P fica sem filtro de proposito: e ele que da a resposta rapida, e
// filtrar tudo so adicionaria atraso na malha.

class PID {
public:
  // dLpfHz = 0 desliga o filtro do termo D.
  void  init(float kp, float ki, float kd, float iLimit, float outLimit,
             float dLpfHz = 0.0f);
  float update(float setpoint, float measurement, float dt);
  void  reset();
  void  setGains(float kp, float ki, float kd) { _kp = kp; _ki = ki; _kd = kd; }

  float p = 0, i = 0, d = 0;   // termos expostos para telemetria/ajuste

private:
  float _kp = 0, _ki = 0, _kd = 0;
  float _iLimit = 0, _outLimit = 0;
  float _dLpfRC = 0;           // constante de tempo do filtro, 0 = sem filtro
  float _prevMeas = 0;
  bool  _first = true;
};
