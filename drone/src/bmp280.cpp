#include "bmp280.h"
#include <Wire.h>
#include <math.h>

namespace {
  constexpr uint8_t REG_CALIB     = 0x88;
  constexpr uint8_t REG_ID        = 0xD0;
  constexpr uint8_t REG_RESET     = 0xE0;
  constexpr uint8_t REG_CTRL_MEAS = 0xF4;
  constexpr uint8_t REG_CONFIG    = 0xF5;
  constexpr uint8_t REG_PRESS     = 0xF7;
}

bool BMP280::write8(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(_addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

bool BMP280::readBytes(uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(_addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)_addr, (int)len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

bool BMP280::readCalibration() {
  uint8_t b[24];
  if (!readBytes(REG_CALIB, b, 24)) return false;

  T1 = (uint16_t)(b[1]  << 8 | b[0]);
  T2 = (int16_t) (b[3]  << 8 | b[2]);
  T3 = (int16_t) (b[5]  << 8 | b[4]);
  P1 = (uint16_t)(b[7]  << 8 | b[6]);
  P2 = (int16_t) (b[9]  << 8 | b[8]);
  P3 = (int16_t) (b[11] << 8 | b[10]);
  P4 = (int16_t) (b[13] << 8 | b[12]);
  P5 = (int16_t) (b[15] << 8 | b[14]);
  P6 = (int16_t) (b[17] << 8 | b[16]);
  P7 = (int16_t) (b[19] << 8 | b[18]);
  P8 = (int16_t) (b[21] << 8 | b[20]);
  P9 = (int16_t) (b[23] << 8 | b[22]);
  return true;
}

bool BMP280::begin(uint8_t addr) {
  _addr = addr;

  uint8_t id = 0;
  if (!readBytes(REG_ID, &id, 1)) return false;
  if (id != 0x58) {
    // 0x60 = BME280 (tem umidade). Os registradores usados aqui sao compativeis.
    if (id == 0x60) Serial.println("[BMP280] detectado BME280, seguindo mesmo assim");
    else { Serial.printf("[BMP280] chip id inesperado: 0x%02X\n", id); return false; }
  }

  write8(REG_RESET, 0xB6);
  delay(10);
  if (!readCalibration()) return false;

  // osrs_t x2 (bits 7:5 = 010), osrs_p x16 (bits 4:2 = 101), modo normal (11)
  write8(REG_CTRL_MEAS, (0b010 << 5) | (0b101 << 2) | 0b11);
  // t_standby 0,5 ms (000), filtro IIR x16 (100) -> ~26 Hz de saida bem suave
  write8(REG_CONFIG, (0b000 << 5) | (0b100 << 2));
  delay(50);

  for (int i = 0; i < 20; i++) { read(); delay(20); }   // descarta o transitorio
  zero();

  Serial.println("[BMP280] ok");
  return true;
}

bool BMP280::read() {
  uint8_t b[6];
  if (!readBytes(REG_PRESS, b, 6)) return false;

  int32_t adcP = ((int32_t)b[0] << 12) | ((int32_t)b[1] << 4) | (b[2] >> 4);
  int32_t adcT = ((int32_t)b[3] << 12) | ((int32_t)b[4] << 4) | (b[5] >> 4);

  // Compensacao conforme datasheet Bosch BMP280, secao 3.11.3
  int32_t var1 = ((((adcT >> 3) - ((int32_t)T1 << 1))) * ((int32_t)T2)) >> 11;
  int32_t var2 = (((((adcT >> 4) - ((int32_t)T1)) * ((adcT >> 4) - ((int32_t)T1))) >> 12) *
                  ((int32_t)T3)) >> 14;
  _tFine = var1 + var2;
  temperature = ((_tFine * 5 + 128) >> 8) / 100.0f;

  int64_t v1 = ((int64_t)_tFine) - 128000;
  int64_t v2 = v1 * v1 * (int64_t)P6;
  v2 = v2 + ((v1 * (int64_t)P5) << 17);
  v2 = v2 + (((int64_t)P4) << 35);
  v1 = ((v1 * v1 * (int64_t)P3) >> 8) + ((v1 * (int64_t)P2) << 12);
  v1 = (((((int64_t)1) << 47) + v1)) * ((int64_t)P1) >> 33;
  if (v1 == 0) return false;   // divisao por zero logo apos o reset

  int64_t p = 1048576 - adcP;
  p = (((p << 31) - v2) * 3125) / v1;
  v1 = (((int64_t)P9) * (p >> 13) * (p >> 13)) >> 25;
  v2 = (((int64_t)P8) * p) >> 19;
  p = ((p + v1 + v2) >> 8) + (((int64_t)P7) << 4);

  pressure = (float)p / 256.0f;

  // Formula barometrica internacional
  float raw = 44330.0f * (1.0f - powf(pressure / (_seaLevel * 100.0f), 0.1902949f));
  altitude = raw - _altOffset;
  return true;
}

bool BMP280::zero() {
  if (!read()) return false;
  _altOffset += altitude;
  altitude = 0;
  return true;
}
