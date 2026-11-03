#pragma once
#include <Arduino.h>
#include <Wire.h>

// Driver direto por registradores do BMI160 (giroscopio + acelerometro).
// Sem bibliotecas externas: o BMI160 nao tem lib estavel no ecossistema Arduino.

class BMI160 {
public:
  // Barramento I2C do sensor (padrao: Wire). Chame antes de begin().
  void setBus(TwoWire *bus) { _w = bus; }
  bool begin(uint8_t addr);

  // Le acelerometro (g) e giroscopio (graus/s) ja convertidos e com offset aplicado.
  bool read();

  // Media de N amostras com o drone parado e nivelado.
  // Zera o giroscopio e mede o vetor gravidade do acelerometro.
  bool calibrate(uint16_t samples = 1000);

  float ax = 0, ay = 0, az = 0;    // g
  float gx = 0, gy = 0, gz = 0;    // graus/s

  float gxOff = 0, gyOff = 0, gzOff = 0;
  float axOff = 0, ayOff = 0, azOff = 0;

private:
  uint8_t  _addr = 0x69;
  TwoWire *_w = &Wire;
  bool    write8(uint8_t reg, uint8_t val);
  bool    readBytes(uint8_t reg, uint8_t *buf, uint8_t len);
  int16_t read16(const uint8_t *p);

  static constexpr float ACC_LSB_PER_G   = 4096.0f;  // faixa +-8 g
  static constexpr float GYR_LSB_PER_DPS = 32.8f;    // faixa +-1000 dps
};
