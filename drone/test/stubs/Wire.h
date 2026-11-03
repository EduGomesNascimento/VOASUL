#pragma once
#include <Arduino.h>

class TwoWire {
public:
  void    begin(int sda, int scl, uint32_t freq);
  void    begin();
  void    setSDA(uint8_t);
  void    setSCL(uint8_t);
  void    setClock(uint32_t);
  void    setTimeOut(uint16_t ms);
  void    beginTransmission(uint8_t addr);
  size_t  write(uint8_t v);
  uint8_t endTransmission();
  uint8_t endTransmission(bool stop);
  int     requestFrom(int addr, int len);
  int     read();
};
extern TwoWire Wire;
