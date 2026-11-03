#include "battery.h"
#include "config.h"
#include "platform.h"

void Battery::begin() {
  platAdcBegin(PIN_VBAT);
  _init = false;
  update();
}

void Battery::update() {
  const uint32_t now = millis();
  if (_init && (now - _lastMs) < 50) return;
  _lastMs = now;

  uint32_t acc = 0;
  for (uint8_t i = 0; i < 8; i++) acc += analogRead(PIN_VBAT);
  const float mv = (acc / 8.0f) * (VBAT_ADC_FULLSCALE_MV / VBAT_ADC_MAX);

  const float divider = (VBAT_DIV_R1 + VBAT_DIV_R2) / VBAT_DIV_R2;
  const float v = (mv / 1000.0f) * divider * VBAT_ADC_SCALE;

  if (!_init) { voltage = v; _init = true; }
  else        { voltage += (v - voltage) * 0.05f; }   // filtro lento

  warning = voltage < VBAT_WARN_V;

  // O critico so vale se persistir por 2 s. Um pico de corrente derruba a
  // tensao instantaneamente; cortar o voo por causa de uma rajada de throttle
  // seria pior do que a bateria fraca.
  if (voltage < VBAT_CRITICAL_V) {
    if (_lowSinceMs == 0) _lowSinceMs = now;
    critical = (now - _lowSinceMs) > 2000;
  } else {
    _lowSinceMs = 0;
    critical = false;
  }
}
