#include "opticalflow.h"
#include "config.h"
#include <math.h>

// FLOW_HW_TEST: teste no PC com um PMW3901 simulado (test/flowhw.cpp)
#if defined(PIN_FLOW_CS) && (PLATFORM_ESP32 || defined(FLOW_HW_TEST))
  #include <SPI.h>
  #define FLOW_HW 1
  static SPIClass flowSpi(HSPI);
  static const SPISettings FLOW_SPI(2000000, MSBFIRST, SPI_MODE3);
#else
  #define FLOW_HW 0
#endif

// ============================================================================
//  Driver
//  Tempos e sequencia de registradores iguais aos do driver da Bitcraze
//  (crazyflie-firmware, src/drivers/src/pmw3901.c), que segue a folha de dados.
// ============================================================================

uint8_t PMW3901::regRead(uint8_t reg) {
#if FLOW_HW
  flowSpi.beginTransaction(FLOW_SPI);
  digitalWrite(PIN_FLOW_CS, LOW);
  delayMicroseconds(50);
  flowSpi.transfer(reg & 0x7F);
  delayMicroseconds(100);
  const uint8_t v = flowSpi.transfer(0);
  delayMicroseconds(50);
  digitalWrite(PIN_FLOW_CS, HIGH);
  flowSpi.endTransaction();
  delayMicroseconds(200);
  return v;
#else
  (void)reg;
  return 0;
#endif
}

void PMW3901::regWrite(uint8_t reg, uint8_t val) {
#if FLOW_HW
  flowSpi.beginTransaction(FLOW_SPI);
  digitalWrite(PIN_FLOW_CS, LOW);
  delayMicroseconds(50);
  flowSpi.transfer(reg | 0x80);
  delayMicroseconds(50);
  flowSpi.transfer(val);
  delayMicroseconds(50);
  digitalWrite(PIN_FLOW_CS, HIGH);
  flowSpi.endTransaction();
  delayMicroseconds(200);
#else
  (void)reg; (void)val;
#endif
}

bool PMW3901::begin() {
  present = false;
#if FLOW_HW
  pinMode(PIN_FLOW_CS, OUTPUT);
  digitalWrite(PIN_FLOW_CS, HIGH);
  flowSpi.begin(PIN_FLOW_SCK, PIN_FLOW_MISO, PIN_FLOW_MOSI, -1);
  delay(40);
  // Um pulso no CS zera a interface serial do sensor.
  digitalWrite(PIN_FLOW_CS, LOW);
  delay(2);
  digitalWrite(PIN_FLOW_CS, HIGH);
  delay(2);

  // Os DOIS IDs tem de bater: com o J4 vazio o MISO flutua e pode ler qualquer
  // coisa, mas nunca 0x49 e o inverso dele ao mesmo tempo.
  chipId = regRead(0x00);
  chipIdInv = regRead(0x5F);
  if (chipId != 0x49 || chipIdInv != 0xB6) return false;

  regWrite(0x3A, 0x5A);           // reset de power-on
  delay(5);
  for (uint8_t r = 0x02; r <= 0x06; r++) regRead(r);
  delay(1);
  initRegisters();

  _reads = 0;
  _idFails = 0;
  present = true;
#endif
  return present;
}

bool PMW3901::read(FlowFrame &f) {
  if (!present) return false;
#if FLOW_HW
  uint8_t b[12];
  flowSpi.beginTransaction(FLOW_SPI);
  digitalWrite(PIN_FLOW_CS, LOW);
  delayMicroseconds(50);
  flowSpi.transfer(0x16);         // leitura em rajada: 12 bytes de uma vez
  delayMicroseconds(50);
  for (uint8_t i = 0; i < sizeof(b); i++) b[i] = flowSpi.transfer(0);
  digitalWrite(PIN_FLOW_CS, HIGH);
  flowSpi.endTransaction();

  f.motion  = b[0];
  f.dx      = (int16_t)(b[2] | (b[3] << 8));
  f.dy      = (int16_t)(b[4] | (b[5] << 8));
  f.squal   = b[6];
  f.shutter = (uint16_t)((b[10] << 8) | b[11]);

  // Tudo 0x00 ou tudo 0xFF = fio solto. Confere o ID ja, sem esperar a vez.
  bool flat = true;
  for (uint8_t i = 1; i < sizeof(b); i++) flat &= (b[i] == b[0]);

  // Confere o ID a cada 50 leituras (0,5 s a 100 Hz).
  if (flat || ++_reads >= 50) {
    _reads = 0;
    if (regRead(0x00) == 0x49) {
      _idFails = 0;
    } else if (++_idFails >= 3) {
      present = false;            // parou de responder: segue sem ele
      return false;
    }
  }
  if (flat) f.squal = 0;          // quadro sem valor
  return true;
#else
  (void)f;
  return false;
#endif
}

void PMW3901::initRegisters() {
  static const uint8_t A[][2] = {
    {0x7F, 0x00}, {0x61, 0xAD}, {0x7F, 0x03}, {0x40, 0x00}, {0x7F, 0x05},
    {0x41, 0xB3}, {0x43, 0xF1}, {0x45, 0x14}, {0x5B, 0x32}, {0x5F, 0x34},
    {0x7B, 0x08}, {0x7F, 0x06}, {0x44, 0x1B}, {0x40, 0xBF}, {0x4E, 0x3F},
    {0x7F, 0x08}, {0x65, 0x20}, {0x6A, 0x18}, {0x7F, 0x09}, {0x4F, 0xAF},
    {0x5F, 0x40}, {0x48, 0x80}, {0x49, 0x80}, {0x57, 0x77}, {0x60, 0x78},
    {0x61, 0x78}, {0x62, 0x08}, {0x63, 0x50}, {0x7F, 0x0A}, {0x45, 0x60},
    {0x7F, 0x00}, {0x4D, 0x11}, {0x55, 0x80}, {0x74, 0x1F}, {0x75, 0x1F},
    {0x4A, 0x78}, {0x4B, 0x78}, {0x44, 0x08}, {0x45, 0x50}, {0x64, 0xFF},
    {0x65, 0x1F}, {0x7F, 0x14}, {0x65, 0x67}, {0x66, 0x08}, {0x63, 0x70},
    {0x7F, 0x15}, {0x48, 0x48}, {0x7F, 0x07}, {0x41, 0x0D}, {0x43, 0x14},
    {0x4B, 0x0E}, {0x45, 0x0F}, {0x44, 0x42}, {0x4C, 0x80}, {0x7F, 0x10},
    {0x5B, 0x02}, {0x7F, 0x07}, {0x40, 0x41}, {0x70, 0x00},
  };
  static const uint8_t B[][2] = {
    {0x32, 0x44}, {0x7F, 0x07}, {0x40, 0x40}, {0x7F, 0x06}, {0x62, 0xF0},
    {0x63, 0x00}, {0x7F, 0x0D}, {0x48, 0xC0}, {0x6F, 0xD5}, {0x7F, 0x00},
    {0x5B, 0xA0}, {0x4E, 0xA8}, {0x5A, 0x50}, {0x40, 0x80}, {0x7F, 0x00},
    {0x5A, 0x10}, {0x54, 0x00},
  };
  for (auto &r : A) regWrite(r[0], r[1]);
  delay(10);
  for (auto &r : B) regWrite(r[0], r[1]);
}

// ============================================================================
//  Estimador: contagens -> m/s
//
//  O sensor ve dois movimentos misturados:
//   - translacao: andando para a frente a v m/s, a h m do chao, a imagem corre
//     v/h rad/s;
//   - rotacao: inclinar o drone tambem faz a imagem correr, mesmo parado.
//     Nariz para cima parece andar para a frente; rolar para a direita parece
//     andar para a esquerda.
//  Tirando a rotacao (giroscopio) sobra a translacao:
//     vFrente  = h * (fluxoFrente  - taxaPitch)
//     vDireita = h * (fluxoDireita + taxaRoll)
//  (mesmo modelo do filtro de Kalman do Crazyflie, ja na convencao do ahrs.h)
// ============================================================================

void FlowEstimator::reset() {
  valid = false;
  _primed = false;
  vFwd = vRight = 0;
  squal = 0;
}

void FlowEstimator::update(const FlowFrame &f, float dt, float rollRateDps, float pitchRateDps,
                           float heightM, bool heightOk) {
  squal = f.squal;

  // bit 7 = houve movimento. Com movimento, o byte e 0xB0 num quadro bom;
  // qualquer outra coisa com o bit 7 ligado e lixo (ex.: 0xFF de fio solto).
  const bool moved = (f.motion & 0x80) != 0;
  const int16_t dx = moved ? f.dx : 0;
  const int16_t dy = moved ? f.dy : 0;
  const bool frameOk = f.squal >= FLOW_MIN_SQUAL && (!moved || f.motion == 0xB0) &&
                       abs(dx) < FLOW_OUTLIER_COUNTS && abs(dy) < FLOW_OUTLIER_COUNTS;
  const bool hOk = heightOk && heightM >= FLOW_MIN_HEIGHT_M && heightM <= FLOW_MAX_HEIGHT_M;

  if (!frameOk || !hOk || dt <= 0.0f || dt > 0.1f) {
    valid = false;
    _primed = false;
    return;
  }

  const int16_t cf = FLOW_SWAP_XY ? dx : dy;
  const int16_t cr = FLOW_SWAP_XY ? dy : dx;
  const float flowFwd   = FLOW_SIGN_FWD   * cf * FLOW_RAD_PER_COUNT / dt;   // rad/s
  const float flowRight = FLOW_SIGN_RIGHT * cr * FLOW_RAD_PER_COUNT / dt;
  const float D2R = 0.01745329f;
  const float rawF = heightM * (flowFwd   - pitchRateDps * D2R);
  const float rawR = heightM * (flowRight + rollRateDps  * D2R);

  if (!_primed) {
    vFwd = rawF;
    vRight = rawR;
    _primed = true;
  } else {
    const float a = dt / (dt + 1.0f / (6.2831853f * FLOW_LPF_HZ));
    vFwd   += (rawF - vFwd) * a;
    vRight += (rawR - vRight) * a;
  }
  valid = true;
}

// ============================================================================
//  Freio: velocidade -> inclinacao
//  Indo para a frente, o freio e nariz para CIMA (pitch +).
//  Indo para a direita, o freio e inclinar para a ESQUERDA (roll -).
// ============================================================================

void FlowHold::reset() {
  pitchBias = rollBias = 0;
  _iFwd = _iRight = 0;
  holding = false;
}

void FlowHold::update(const FlowEstimator &e, bool engage, float dt) {
  holding = engage && e.valid;

  float wantP = 0, wantR = 0;
  if (holding) {
    const float iLim = FLOW_I_LIMIT_DEG / FLOW_KI_DEG_PER_M;
    _iFwd   = constrain(_iFwd   + e.vFwd   * dt, -iLim, iLim);
    _iRight = constrain(_iRight + e.vRight * dt, -iLim, iLim);
    wantP =  (FLOW_KP_DEG_PER_MPS * e.vFwd   + FLOW_KI_DEG_PER_M * _iFwd);
    wantR = -(FLOW_KP_DEG_PER_MPS * e.vRight + FLOW_KI_DEG_PER_M * _iRight);
    wantP = constrain(wantP, -FLOW_MAX_TILT_DEG, FLOW_MAX_TILT_DEG);
    wantR = constrain(wantR, -FLOW_MAX_TILT_DEG, FLOW_MAX_TILT_DEG);
  } else {
    // Solto ou sem leitura: esquece a deriva acumulada (meia-vida ~0,35 s).
    const float k = constrain(1.0f - 2.0f * dt, 0.0f, 1.0f);
    _iFwd *= k;
    _iRight *= k;
  }

  // Rampa: a correcao entra e sai sem tranco.
  const float step = FLOW_RAMP_DPS * dt;
  pitchBias += constrain(wantP - pitchBias, -step, step);
  rollBias  += constrain(wantR - rollBias,  -step, step);
}
