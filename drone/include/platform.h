#pragma once
#include <Arduino.h>

// ============================================================================
//  Camada fina de plataforma.  Tudo que difere entre ESP32 e Raspberry Pi
//  Pico W mora aqui -- o resto do firmware nao sabe em qual placa esta rodando.
// ============================================================================

#if defined(ARDUINO_ARCH_RP2040)
  #define PLATFORM_PICO 1
#elif defined(ARDUINO_ARCH_ESP32) || defined(ESP32)
  #define PLATFORM_ESP32 1
#else
  #define PLATFORM_HOST 1     // testes de logica no PC
#endif

#ifndef IRAM_ATTR
  #define IRAM_ATTR
#endif

// ---------------------------------------------------------------------------
#if PLATFORM_PICO
  #include <pico/mutex.h>
  #include <hardware/gpio.h>

  typedef mutex_t plat_lock_t;
  static inline void platLockInit(plat_lock_t &m) { mutex_init(&m); }
  static inline void platLock(plat_lock_t &m)     { mutex_enter_blocking(&m); }
  static inline void platUnlock(plat_lock_t &m)   { mutex_exit(&m); }

  static inline bool platFastRead(uint8_t pin) { return gpio_get(pin); }

#elif PLATFORM_ESP32
  #include <freertos/FreeRTOS.h>
  #include <freertos/task.h>
  #include <soc/gpio_struct.h>

  typedef portMUX_TYPE plat_lock_t;
  static inline void platLockInit(plat_lock_t &m) { m = (plat_lock_t)portMUX_INITIALIZER_UNLOCKED; }
  static inline void platLock(plat_lock_t &m)     { portENTER_CRITICAL(&m); }
  static inline void platUnlock(plat_lock_t &m)   { portEXIT_CRITICAL(&m); }

  static inline bool platFastRead(uint8_t pin) {
  #if defined(CONFIG_IDF_TARGET_ESP32)
    if (pin < 32) return (GPIO.in >> pin) & 0x1;
    return (GPIO.in1.val >> (pin - 32)) & 0x1;
  #else
    return digitalRead(pin);      // C3/S3/C6 (estacao terra): registradores diferentes
  #endif
  }

#else   // host
  typedef int plat_lock_t;
  static inline void platLockInit(plat_lock_t &) {}
  static inline void platLock(plat_lock_t &) {}
  static inline void platUnlock(plat_lock_t &) {}
  static inline bool platFastRead(uint8_t pin) { return digitalRead(pin); }
#endif

// --------------------------------------------------------------- PWM
// O ESP32 configura frequencia e resolucao por pino (LEDC); o RP2040 usa
// ajustes globais do analogWrite. A interface aqui esconde os dois.

void platPwmBegin(uint32_t freqHz, uint8_t bits);
void platPwmAttach(uint8_t pin);
void platPwmWrite(uint8_t pin, uint16_t duty);

// --------------------------------------------------------------- I2C
void platI2CBegin(uint8_t sda, uint8_t scl, uint32_t clockHz);
// Segundo barramento I2C (so no ESP32: Wire1). Devolve o barramento para o
// driver usar; nas outras plataformas devolve o barramento principal.
class TwoWire;
TwoWire *platI2C2Begin(uint8_t sda, uint8_t scl, uint32_t clockHz);

// --------------------------------------------------------------- ADC
void platAdcBegin(uint8_t pin);

// --------------------------------------------------------------- LED
// No Pico W o LED da placa fica pendurado no chip de WiFi: so pode ser
// acionado pelo core que cuida da rede, nunca pelo loop de voo.
void platLedBegin();
void platLedWrite(bool on);

// --------------------------------------------------------------- WiFi
void platStartAP(const char *ssid, const char *pass);
String platApIP();

// --------------------------------------------------------------- tempo
static inline void platYieldFor(uint32_t us) {
#if PLATFORM_ESP32
  if (us > 1500) vTaskDelay(pdMS_TO_TICKS((us - 500) / 1000));
#elif PLATFORM_PICO
  if (us > 1500) delayMicroseconds(us - 500);
#else
  (void)us;
#endif
}
