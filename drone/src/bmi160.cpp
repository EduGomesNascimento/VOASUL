#include "bmi160.h"
#include <Wire.h>

namespace {
  constexpr uint8_t REG_CHIP_ID   = 0x00;
  constexpr uint8_t REG_PMU_STAT  = 0x03;
  constexpr uint8_t REG_DATA_GYR  = 0x0C;   // GYR_X_L .. ACC_Z_H em sequencia (12 bytes)
  constexpr uint8_t REG_ACC_CONF  = 0x40;
  constexpr uint8_t REG_ACC_RANGE = 0x41;
  constexpr uint8_t REG_GYR_CONF  = 0x42;
  constexpr uint8_t REG_GYR_RANGE = 0x43;
  constexpr uint8_t REG_CMD       = 0x7E;

  constexpr uint8_t CHIP_ID_BMI160 = 0xD1;
}

bool BMI160::write8(uint8_t reg, uint8_t val) {
  _w->beginTransmission(_addr);
  _w->write(reg);
  _w->write(val);
  return _w->endTransmission() == 0;
}

bool BMI160::readBytes(uint8_t reg, uint8_t *buf, uint8_t len) {
  _w->beginTransmission(_addr);
  _w->write(reg);
  if (_w->endTransmission(false) != 0) return false;
  if (_w->requestFrom((int)_addr, (int)len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = _w->read();
  return true;
}

int16_t BMI160::read16(const uint8_t *p) {
  return (int16_t)((uint16_t)p[1] << 8 | p[0]);   // little endian
}

bool BMI160::begin(uint8_t addr) {
  _addr = addr;

  uint8_t id = 0;
  if (!readBytes(REG_CHIP_ID, &id, 1)) return false;
  if (id != CHIP_ID_BMI160) {
    Serial.printf("[BMI160] chip id inesperado: 0x%02X (esperado 0xD1)\n", id);
    return false;
  }

  write8(REG_CMD, 0xB6);   // soft reset
  delay(100);

  write8(REG_CMD, 0x11);   // acelerometro em modo normal
  delay(50);
  write8(REG_CMD, 0x15);   // giroscopio em modo normal
  delay(100);              // o giro leva ~80 ms para estabilizar

  // ODR 400 Hz nos dois: acima do loop de 400 Hz nao adianta, abaixo cria atraso.
  write8(REG_ACC_CONF,  0x2A);   // bwp=normal(avg4), odr=400 Hz
  write8(REG_ACC_RANGE, 0x08);   // +-8 g  -> 4096 LSB/g
  write8(REG_GYR_CONF,  0x2A);   // bwp=normal, odr=400 Hz
  write8(REG_GYR_RANGE, 0x01);   // +-1000 dps -> 32.8 LSB/dps
  delay(20);

  uint8_t pmu = 0;
  readBytes(REG_PMU_STAT, &pmu, 1);
  // bits 5:4 = acc_pmu, 3:2 = gyr_pmu; 01 = normal nos dois
  if (((pmu >> 4) & 0x03) != 0x01 || ((pmu >> 2) & 0x03) != 0x01) {
    Serial.printf("[BMI160] PMU nao entrou em normal: 0x%02X\n", pmu);
    return false;
  }

  Serial.println("[BMI160] ok");
  return true;
}

bool BMI160::read() {
  uint8_t b[12];
  if (!readBytes(REG_DATA_GYR, b, 12)) return false;

  const float rgx = read16(&b[0]) / GYR_LSB_PER_DPS;
  const float rgy = read16(&b[2]) / GYR_LSB_PER_DPS;
  const float rgz = read16(&b[4]) / GYR_LSB_PER_DPS;

  const float rax = read16(&b[6])  / ACC_LSB_PER_G;
  const float ray = read16(&b[8])  / ACC_LSB_PER_G;
  const float raz = read16(&b[10]) / ACC_LSB_PER_G;

  gx = rgx - gxOff;
  gy = rgy - gyOff;
  gz = rgz - gzOff;

  ax = rax - axOff;
  ay = ray - ayOff;
  az = raz - azOff;
  return true;
}

bool BMI160::calibrate(uint16_t samples) {
  double sgx = 0, sgy = 0, sgz = 0, sax = 0, say = 0, saz = 0;
  uint16_t got = 0;

  gxOff = gyOff = gzOff = 0;
  axOff = ayOff = azOff = 0;

  for (uint16_t i = 0; i < samples; i++) {
    if (read()) {
      sgx += gx; sgy += gy; sgz += gz;
      sax += ax; say += ay; saz += az;
      got++;
    }
    delay(3);
  }
  if (got < samples / 2) return false;

  gxOff = sgx / got;
  gyOff = sgy / got;
  gzOff = sgz / got;

  // No acelerometro so tiramos o desvio horizontal. O eixo Z tem de continuar
  // marcando 1 g, senao o AHRS perde a referencia de gravidade.
  axOff = sax / got;
  ayOff = say / got;
  azOff = (saz / got) - 1.0f;

  Serial.printf("[BMI160] offsets giro: %.2f %.2f %.2f dps | acel: %.3f %.3f %.3f g\n",
                gxOff, gyOff, gzOff, axOff, ayOff, azOff);
  return true;
}
