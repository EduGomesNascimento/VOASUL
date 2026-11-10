#include "platform.h"
#include "config.h"
#include <Wire.h>

#if !PLATFORM_HOST
  #include <WiFi.h>
#endif
#if PLATFORM_ESP32
  #include <esp_wifi.h>
#endif

// ---------------------------------------------------------------- PWM

static uint8_t  gPwmBits = 10;

#if PLATFORM_ESP32
static uint32_t gPwmFreq = 20000;
#endif

void platPwmBegin(uint32_t freqHz, uint8_t bits) {
  gPwmBits = bits;
#if PLATFORM_PICO
  // No RP2040 a frequencia e a escala do analogWrite sao globais, definidas
  // uma vez antes de anexar os pinos.
  analogWriteFreq(freqHz);
  analogWriteRange((1u << bits) - 1);
#elif PLATFORM_ESP32
  gPwmFreq = freqHz;
#else
  (void)freqHz;
#endif
}

void platPwmAttach(uint8_t pin) {
#if PLATFORM_PICO
  pinMode(pin, OUTPUT);
  // O GPIO do RP2040 sai de fabrica com 4 mA de capacidade. A porta do MOSFET
  // e um capacitor de ~6,5 nC: com 4 mA ela leva ~1,6 us para carregar, o que
  // a 20 kHz deixa o transistor em transicao 3% do tempo. Nessa faixa ele nao
  // esta nem ligado nem desligado, e dissipa mais do que conduzindo.
  // Com 12 mA a transicao cai para ~540 ns e a perda de chaveamento vai a um
  // terco. Se ainda assim o MOSFET esquentar, baixe MOTOR_PWM_FREQ para 12000.
  gpio_set_drive_strength(pin, GPIO_DRIVE_STRENGTH_12MA);
  gpio_set_slew_rate(pin, GPIO_SLEW_RATE_FAST);
  analogWrite(pin, 0);
#elif PLATFORM_ESP32
  #if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcAttach(pin, gPwmFreq, gPwmBits);
  #else
    static uint8_t ch = 0;
    ledcSetup(ch, gPwmFreq, gPwmBits);
    ledcAttachPin(pin, ch);
    ch++;
  #endif
#else
  pinMode(pin, OUTPUT);
#endif
}

void platPwmWrite(uint8_t pin, uint16_t duty) {
#if PLATFORM_PICO
  analogWrite(pin, duty);
#elif PLATFORM_ESP32
  ledcWrite(pin, duty);
#else
  (void)pin; (void)duty;
#endif
}

// ---------------------------------------------------------------- I2C

void platI2CBegin(uint8_t sda, uint8_t scl, uint32_t clockHz) {
#if PLATFORM_PICO
  Wire.setSDA(sda);
  Wire.setSCL(scl);
  Wire.begin();
  Wire.setClock(clockHz);
#elif PLATFORM_ESP32
  Wire.begin(sda, scl, clockHz);
#else
  (void)sda; (void)scl; (void)clockHz;
#endif
}

TwoWire *platI2C2Begin(uint8_t sda, uint8_t scl, uint32_t clockHz) {
#if PLATFORM_ESP32
  Wire1.begin(sda, scl, clockHz);
  return &Wire1;
#else
  (void)sda; (void)scl; (void)clockHz;
  return &Wire;
#endif
}

// ---------------------------------------------------------------- ADC

void platAdcBegin(uint8_t pin) {
#if PLATFORM_PICO
  // O ADC do RP2040 e sempre de 12 bits e le 0..3,3 V; nao ha atenuacao.
  analogReadResolution(12);
  (void)pin;
#elif PLATFORM_ESP32
  pinMode(pin, INPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(pin, ADC_11db);   // fundo de escala ~3,3 V
#else
  (void)pin;
#endif
}

// ---------------------------------------------------------------- LED

void platLedBegin() {
#if !PLATFORM_HOST
  pinMode(PIN_STATUS_LED, OUTPUT);
#endif
}

void platLedWrite(bool on) {
#if !PLATFORM_HOST
  digitalWrite(PIN_STATUS_LED, on ? HIGH : LOW);
#else
  (void)on;
#endif
}

// ---------------------------------------------------------------- WiFi

void platStartAP(const char *ssid, const char *pass) {
#if PLATFORM_PICO
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, pass);
#elif PLATFORM_ESP32
  WiFi.mode(WIFI_AP);
#if WIFI_ONLY_11B
  // Antes do softAP, para o AP ja nascer anunciando so as taxas do 11b.
  esp_wifi_set_protocol(WIFI_IF_AP, WIFI_PROTOCOL_11B);
#endif
  WiFi.softAP(ssid, pass, WIFI_CHANNEL);
  // Potencia maxima. Isto ficava em 11 dBm "para reduzir ruido na
  // alimentacao", e eram 8,5 dB de enlace jogados fora -- no ar livre, 2,7x
  // menos alcance. O ruido se resolve com capacitor perto do ESP32 (ver
  // docs/HARDWARE.md), nao cortando a potencia do radio.
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  WiFi.setSleep(false);   // o sleep de WiFi adiciona dezenas de ms de latencia
#else
  (void)ssid; (void)pass;
#endif
}

String platApIP() {
#if !PLATFORM_HOST
  return WiFi.softAPIP().toString();
#else
  return String("0.0.0.0");
#endif
}
