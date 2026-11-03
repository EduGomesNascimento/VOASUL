#include <Arduino.h>
#include <Wire.h>

SerialStub Serial;
TwoWire    Wire;

int  stubMode[STUB_PINS];
int  stubLevel[STUB_PINS];
long stubSeq[STUB_PINS];
long stubClock = 0;
unsigned long stubMillis = 0;

void stubReset() {
  for (int i = 0; i < STUB_PINS; i++) { stubMode[i] = -1; stubLevel[i] = -1; stubSeq[i] = -1; }
  stubClock = 0;
  stubMillis = 0;
}

unsigned long millis() { return stubMillis; }
unsigned long micros() { return 0; }
void delay(unsigned long) {}
void delayMicroseconds(unsigned int) {}

void pinMode(uint8_t p, uint8_t m) { if (p < STUB_PINS) stubMode[p] = m; }

void digitalWrite(uint8_t p, uint8_t v) {
  if (p < STUB_PINS) { stubLevel[p] = v; stubSeq[p] = ++stubClock; }
}

int  digitalRead(uint8_t) { return 0; }
int  analogRead(uint8_t) { return 0; }
void analogReadResolution(uint8_t) {}
void attachInterrupt(int, void (*)(), int) {}
int  digitalPinToInterrupt(uint8_t p) { return p; }

void TwoWire::begin(int, int, uint32_t) {}
void TwoWire::begin() {}
void TwoWire::setSDA(uint8_t) {}
void TwoWire::setSCL(uint8_t) {}
void TwoWire::setClock(uint32_t) {}
void TwoWire::setTimeOut(uint16_t) {}
void TwoWire::beginTransmission(uint8_t) {}
size_t TwoWire::write(uint8_t) { return 1; }
uint8_t TwoWire::endTransmission() { return 0; }
uint8_t TwoWire::endTransmission(bool) { return 0; }
int TwoWire::requestFrom(int, int len) { return len; }
int TwoWire::read() { return 0; }
