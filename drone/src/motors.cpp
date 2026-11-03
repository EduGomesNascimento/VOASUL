#include "motors.h"
#include "config.h"
#include "platform.h"

static const uint8_t kPwmPins[4] = {
  PIN_MOTOR_FR, PIN_MOTOR_RR, PIN_MOTOR_RL, PIN_MOTOR_FL
};

#if MOTOR_DRIVER_L298N
// Entrada complementar da ponte (IN2/IN4). Um drone nunca inverte o giro das
// helices, entao ela e fixada uma vez no boot e nunca mais muda. Ainda assim e
// acionada por software, e nao amarrada no fio: assim o firmware garante que a
// ponte comece em estado conhecido, em vez de depender de como o pino ficou
// flutuando durante o reset.
static const uint8_t kInB[4] = {
  PIN_MOTOR_FR_B, PIN_MOTOR_RR_B, PIN_MOTOR_RL_B, PIN_MOTOR_FL_B
};
#if L298N_HAS_ENABLE
static const uint8_t kInA[4] = {
  PIN_MOTOR_FR_A, PIN_MOTOR_RR_A, PIN_MOTOR_RL_A, PIN_MOTOR_FL_A
};
#endif
#endif

static constexpr uint16_t kMaxDuty = (1 << MOTOR_PWM_BITS) - 1;

void Motors::begin() {
#if MOTOR_DRIVER_L298N
  // A entrada complementar vai a LOW ANTES do PWM ser anexado. Com as duas
  // entradas em LOW a ponte deixa as saidas em curto, que e justamente o estado
  // de motor parado -- nao ha tranco nenhum ao ligar.
  for (uint8_t i = 0; i < 4; i++) {
    pinMode(kInB[i], OUTPUT);
    digitalWrite(kInB[i], LOW);
  }
  #if L298N_HAS_ENABLE
  // Modulo com ENA/ENB: o PWM vai no enable, e o par IN1/IN2 fixa o sentido.
  for (uint8_t i = 0; i < 4; i++) {
    pinMode(kInA[i], OUTPUT);
    digitalWrite(kInA[i], HIGH);
  }
  #endif
#endif

  platPwmBegin(MOTOR_PWM_FREQ, MOTOR_PWM_BITS);
  for (uint8_t i = 0; i < 4; i++) platPwmAttach(kPwmPins[i]);

  stop();
}

void Motors::write(uint8_t idx, float value) {
  value = constrain(value, 0.0f, 1.0f);
  platPwmWrite(kPwmPins[idx], (uint16_t)(value * kMaxDuty + 0.5f));
}

void Motors::setEnabled(bool en) {
  _enabled = en;
  if (!en) stop();
}

void Motors::stop() {
  for (uint8_t i = 0; i < 4; i++) {
    out[i] = 0;
    write(i, 0);
  }
  _thrPrev = 0.0f;   // rearmar depois disto comeca do zero, nao de onde parou
}

void Motors::armStart() {
  _spoolOn = true;
  _spoolMs = millis();
  _thrPrev = 0.0f;
}

// Teto da rampa de partida para um motor, 0..1. Cada motor entra
// MOTOR_SPOOL_STAGGER ms depois do anterior: quatro rotores travados largando
// no mesmo instante somam os quatro picos de corrente, que e exatamente o que
// faz o VSYS afundar e o Pico reiniciar.
float Motors::spoolCeil(uint8_t idx) const {
  if (!_spoolOn) return 1.0f;
  const int32_t t = (int32_t)(millis() - _spoolMs)
                  - (int32_t)idx * MOTOR_SPOOL_STAGGER;
  if (t <= 0) return 0.0f;
  if (t >= MOTOR_SPOOL_MS) return 1.0f;
  return (float)t / (float)MOTOR_SPOOL_MS;
}

bool Motors::spooling() const {
  if (!_spoolOn) return false;
  return (millis() - _spoolMs) < (uint32_t)(MOTOR_SPOOL_MS
                                            + 3 * MOTOR_SPOOL_STAGGER);
}

void Motors::mix(float throttle, float roll, float pitch, float yaw, float dt) {
  if (!_enabled) { stop(); _spoolOn = false; return; }

  throttle = constrain(throttle, 0.0f, MOTOR_MAX);

  // Partida suave, parte 1: limita a subida do throttle COMUM. So o valor
  // medio dos quatro motores passa por aqui -- as correcoes do PID entram
  // depois, no mixer, e nao sao tocadas. E por isso que este limite nao
  // atrasa a malha de atitude: ele nao consegue, nao enxerga o diferencial.
  if (dt > 0.0f) {
    const float maxUp = MOTOR_SLEW_UP * dt;
    if (throttle > _thrPrev + maxUp) throttle = _thrPrev + maxUp;
  }
  _thrPrev = throttle;

  float m[4];
  m[0] = throttle - roll - pitch + yaw;   // FR, anti-horario
  m[1] = throttle - roll + pitch - yaw;   // RR, horario
  m[2] = throttle + roll + pitch + yaw;   // RL, anti-horario
  m[3] = throttle + roll - pitch - yaw;   // FL, horario

  // Dessaturacao: se algum motor estourou o teto, baixa os quatro pelo mesmo
  // tanto. Preserva a diferenca entre eles, que e o que de fato controla a
  // atitude -- simplesmente cortar no limite faria o drone tombar para o lado
  // do motor saturado.
  float hi = m[0], lo = m[0];
  for (uint8_t i = 1; i < 4; i++) {
    if (m[i] > hi) hi = m[i];
    if (m[i] < lo) lo = m[i];
  }
  if (hi > MOTOR_MAX) {
    const float excess = hi - MOTOR_MAX;
    for (uint8_t i = 0; i < 4; i++) m[i] -= excess;
    lo -= excess;
  }
  if (lo < MOTOR_IDLE) {
    const float deficit = MOTOR_IDLE - lo;
    for (uint8_t i = 0; i < 4; i++) m[i] += deficit;
  }

  for (uint8_t i = 0; i < 4; i++) {
    out[i] = constrain(m[i], MOTOR_IDLE, MOTOR_MAX);
    // Partida suave, parte 2: o teto da rampa. Ele vem DEPOIS do piso de
    // MOTOR_IDLE -- e a unica coisa neste arquivo autorizada a mandar um motor
    // abaixo do idle, porque no instante de armar o idle e justamente o degrau
    // que se quer evitar.
    const float c = spoolCeil(i);
    if (c < 1.0f) {
      const float lim = c * MOTOR_IDLE;
      if (out[i] > lim) out[i] = lim;
    }
    write(i, out[i]);
  }
  if (_spoolOn && !spooling()) _spoolOn = false;
}
