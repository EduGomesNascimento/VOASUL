// SPI falso com um PMW3901 simulado, so para test/flowhw.cpp.
#pragma once
#include <cstdint>
#define HSPI 2
#define MSBFIRST 1
#define SPI_MODE3 3

struct SimPMW {
  bool    plugged = true;     // false = J4 vazio / fio solto (MISO flutuando)
  uint8_t floatValue = 0xFF;  // o que o MISO le flutuando
  int16_t dx = 0, dy = 0;
  uint8_t squal = 80;
  int     writes = 0;         // registradores escritos (init)
  // estado de uma transacao
  int     step = 0;
  uint8_t addr = 0;
};
extern SimPMW simPmw;

struct SPISettings { SPISettings(uint32_t, uint8_t, uint8_t) {} };
struct SPIClass {
  explicit SPIClass(uint8_t) {}
  void begin(int8_t, int8_t, int8_t, int8_t) {}
  void beginTransaction(const SPISettings &) { simPmw.step = 0; }
  void endTransaction() {}
  uint8_t transfer(uint8_t b) {
    SimPMW &s = simPmw;
    const int k = s.step++;
    if (k == 0) { s.addr = b; return s.plugged ? 0x00 : s.floatValue; }
    if (!s.plugged) return s.floatValue;
    if (s.addr & 0x80) { s.writes++; return 0; }          // escrita
    if (s.addr == 0x00) return 0x49;                       // ID
    if (s.addr == 0x5F) return 0xB6;                       // ID invertido
    if (s.addr == 0x16) {                                  // rajada de 12 bytes
      const uint8_t m = (s.dx || s.dy) ? 0xB0 : 0x30;
      const uint8_t r[12] = {m, 0, (uint8_t)s.dx, (uint8_t)(s.dx >> 8),
                             (uint8_t)s.dy, (uint8_t)(s.dy >> 8), s.squal, 0x40, 0x80, 0x10, 0x01, 0x00};
      return r[(k - 1) % 12];
    }
    return 0;
  }
};
