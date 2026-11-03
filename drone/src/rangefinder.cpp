#include "rangefinder.h"
#include "config.h"
#include "platform.h"
#include <math.h>

// ---------------------------------------------------------------- Sonar

void Sonar::begin(uint8_t trigPin, uint8_t echoPin, void (*isr)()) {
  _trig = trigPin;
  _echo = echoPin;
  pinMode(_trig, OUTPUT);
  digitalWrite(_trig, LOW);
  pinMode(_echo, INPUT);
  attachInterrupt(digitalPinToInterrupt(_echo), isr, CHANGE);
}

void Sonar::onEcho() {
  // platFastRead le o registrador de GPIO direto: digitalRead() nao tem
  // garantia de estar em RAM em todas as versoes de core, e chamar codigo em
  // flash de dentro de uma ISR trava a placa quando a SPI de flash esta ocupada.
  if (platFastRead(_echo)) {
    _riseUs = micros();
  } else {
    _pulseUs = micros() - _riseUs;
    _pending = true;
  }
}

void Sonar::trigger() {
  _pending = false;
  digitalWrite(_trig, LOW);
  delayMicroseconds(3);
  digitalWrite(_trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(_trig, LOW);
  _trigMs = millis();
}

bool Sonar::poll(float speedOfSound) {
  if (!_pending) {
    // Sem eco dentro da janela: fora de alcance ou superficie que nao reflete
    // (grama, tecido, agua). Trata como leitura invalida em vez de manter a antiga.
    if (_trigMs && (millis() - _trigMs) > (SONAR_TIMEOUT_US / 1000 + 10)) {
      _trigMs = 0;
      distance = -1.0f;
    }
    return false;
  }

  _pending = false;
  const uint32_t pulse = _pulseUs;
  _trigMs = 0;

  if (pulse == 0 || pulse > SONAR_TIMEOUT_US) { distance = -1.0f; return false; }

  // ida e volta -> divide por 2
  const float d = (pulse * 1e-6f * speedOfSound) * 0.5f;
  if (d < SONAR_MIN_M || d > SONAR_MAX_M) { distance = -1.0f; return false; }

  // Mediana de 3: o HC-SR04 solta leituras absurdas isoladas quando pega
  // um eco de segunda ordem. A media deixaria passar; a mediana descarta.
  _med[_medIdx] = d;
  _medIdx = (_medIdx + 1) % 3;

  float a = _med[0], b = _med[1], c = _med[2];
  if (a < 0 || b < 0 || c < 0) {
    distance = d;   // ainda enchendo a janela
  } else {
    float mx = fmaxf(a, fmaxf(b, c));
    float mn = fminf(a, fminf(b, c));
    distance = a + b + c - mx - mn;
  }

  lastValidMs = millis();
  return true;
}

bool Sonar::isValid(uint32_t maxAgeMs) const {
  return distance > 0 && lastValidMs && (millis() - lastValidMs) < maxAgeMs;
}

// ---------------------------------------------------------------- IR

void IRSensor::begin(uint8_t pin) {
  _pin = pin;
  // GPIO 34..39 nao tem pull-up interno; o FC-51 tem saida push-pull,
  // entao INPUT puro basta nesses pinos.
  if (pin >= 34) pinMode(pin, INPUT);
  else           pinMode(pin, INPUT_PULLUP);
}

void IRSensor::poll() {
  bool raw = digitalRead(_pin);
#if IR_ACTIVE_LOW
  raw = !raw;
#endif
  if (raw != _last) {
    _last = raw;
    _changeMs = millis();
  } else if (_stable != raw && (millis() - _changeMs) > 20) {
    _stable = raw;   // 20 ms estavel para valer
  }
}

// ---------------------------------------------------------------- Conjunto

static Sonar sDown;
static Sonar sFront;

static void IRAM_ATTR isrDown()  { sDown.onEcho(); }
static void IRAM_ATTR isrFront() { sFront.onEcho(); }

static IRSensor irL, irR;

void Rangefinders::begin() {
  sDown.begin(PIN_SONAR_DOWN_TRIG,  PIN_SONAR_DOWN_ECHO,  isrDown);
  sFront.begin(PIN_SONAR_FRONT_TRIG, PIN_SONAR_FRONT_ECHO, isrFront);
  irL.begin(PIN_IR_LEFT);
  irR.begin(PIN_IR_RIGHT);
  Serial.println("[RANGE] 2x HC-SR04 + 2x IR prontos");
}

void Rangefinders::update(float temperatureC, float tiltCos, float tiltDeg) {
  // Velocidade do som corrigida pela temperatura do BMP280.
  // De 0 a 40 graus a diferenca chega a 7%: a 2 m sao 14 cm de erro,
  // o suficiente para o alt-hold oscilar entre um voo frio e um quente.
  const float c = 331.3f + 0.606f * temperatureC;

  sDown.poll(c);
  sFront.poll(c);
  irL.poll();
  irR.poll();

  // Disparo alternado: dois HC-SR04 juntos ouvem o eco um do outro.
  const uint32_t now = millis();
  if (now - _lastTrigMs >= SONAR_PERIOD_MS) {
    _lastTrigMs = now;
    if (_turn == 0) sDown.trigger();
    else            sFront.trigger();
    _turn ^= 1;
  }

  // Sonar de solo: mede a distancia ao longo do eixo do drone, nao a vertical.
  // Inclinado 20 graus, a leitura fica 6% maior que a altura real.
  groundValid = sDown.isValid() && fabsf(tiltDeg) < SONAR_MAX_TILT_DEG;
  groundDistance = groundValid ? sDown.distance * tiltCos : -1.0f;

  frontValid = sFront.isValid();
  frontDistance = frontValid ? sFront.distance : -1.0f;

  irLeft  = irL.detected();
  irRight = irR.detected();
}
