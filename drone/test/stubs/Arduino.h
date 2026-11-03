// Stub minimo de Arduino apenas para os testes de logica no PC.
// Nao pretende emular hardware: registra o que o firmware escreveu nos pinos
// para que os testes possam conferir a fiacao.
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <strings.h>
#include <algorithm>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define CHANGE 3

typedef uint8_t byte;

template <typename T, typename A, typename B>
static inline T constrain(T x, A lo, B hi) {
  return x < (T)lo ? (T)lo : (x > (T)hi ? (T)hi : x);
}

unsigned long millis();
unsigned long micros();
void delay(unsigned long);
void delayMicroseconds(unsigned int);
void pinMode(uint8_t, uint8_t);
void digitalWrite(uint8_t, uint8_t);
int  digitalRead(uint8_t);
int  analogRead(uint8_t);
void analogReadResolution(uint8_t);
void attachInterrupt(int, void (*)(), int);
int  digitalPinToInterrupt(uint8_t);

// ---- espionagem para os testes -------------------------------------------
#define STUB_PINS 64
extern int      stubMode[STUB_PINS];    // -1 = nunca configurado
extern int      stubLevel[STUB_PINS];   // -1 = nunca escrito
extern long     stubSeq[STUB_PINS];     // ordem da ultima escrita
extern long     stubClock;
extern unsigned long stubMillis;        // relogio controlado pelo teste
void stubReset();

struct SerialStub {
  void begin(unsigned long) {}
  void println(const char *) {}
  void println() {}
  void print(const char *) {}
  int  printf(const char *f, ...) { (void)f; return 0; }
};
extern SerialStub Serial;

// String suficiente para o pouco que a camada de plataforma usa.
class String {
public:
  String() { _b[0] = '\0'; }
  String(const char *s) { snprintf(_b, sizeof(_b), "%s", s ? s : ""); }
  const char *c_str() const { return _b; }
private:
  char _b[64];
};
