#pragma once
#include <Arduino.h>

// Driver direto por registradores do BMP280 (pressao + temperatura).
// A temperatura tambem alimenta a correcao da velocidade do som no ultrassom.

class BMP280 {
public:
  bool  begin(uint8_t addr);
  bool  read();                 // atualiza pressure/temperature/altitude
  void  setSeaLevel(float hPa) { _seaLevel = hPa; }
  bool  zero();                 // define a altitude atual como zero

  float pressure    = 0;        // Pa
  float temperature = 0;        // graus C
  float altitude    = 0;        // metros, relativo ao ponto zerado

private:
  uint8_t _addr = 0x76;
  float   _seaLevel = 1013.25f;
  float   _altOffset = 0;

  uint16_t T1, P1;
  int16_t  T2, T3, P2, P3, P4, P5, P6, P7, P8, P9;
  int32_t  _tFine = 0;

  bool     write8(uint8_t reg, uint8_t val);
  bool     readBytes(uint8_t reg, uint8_t *buf, uint8_t len);
  bool     readCalibration();
};
