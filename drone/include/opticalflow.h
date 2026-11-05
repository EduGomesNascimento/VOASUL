#pragma once
#include <Arduino.h>

// ============================================================================
//  Fluxo optico PMW3901: OPCIONAL.
//
//  O sensor olha para o chao e mede quanto a imagem andou. Com a altura do
//  sonar isso vira velocidade horizontal, e com ela o drone freia a deriva
//  sozinho quando o manche esta solto.
//
//  O mesmo firmware voa com e sem o modulo:
//   - no boot, PMW3901::begin() le o ID do chip (0x49) e o ID invertido (0xB6).
//     Sem modulo a leitura nao bate e o drone voa como sempre voou;
//   - em voo, o ID e conferido a cada 0,5 s. Se o modulo parar de responder
//     (fio solto), a correcao some suavemente e o drone segue sem ele;
//   - a telemetria diz se o modulo esta ausente, presente ou segurando.
//
//  Este arquivo tem tres partes:
//   PMW3901       driver SPI (so existe na placa que define PIN_FLOW_CS)
//   FlowEstimator contagens -> velocidade em m/s (pura conta, testada no PC)
//   FlowHold      velocidade -> inclinacao de freio (pura conta, testada no PC)
// ============================================================================

// Um quadro lido do sensor (registrador de rajada 0x16).
struct FlowFrame {
  int16_t  dx = 0, dy = 0;   // contagens desde a leitura anterior, eixos do sensor
  uint8_t  motion = 0;       // bit 7 = houve movimento desde a leitura anterior
  uint8_t  squal = 0;        // qualidade da superficie (0 = sem textura)
  uint16_t shutter = 0;
};

// Estado para a telemetria.
enum FlowStatus : uint8_t {
  FLOW_ABSENT  = 0,   // modulo nao ligado (ou parou de responder)
  FLOW_IDLE    = 1,   // ligado, mas sem leitura confiavel (alto/baixo demais, sem textura)
  FLOW_READING = 2,   // lendo velocidade
  FLOW_HOLDING = 3,   // lendo e freando a deriva
};

// ---------------------------------------------------------------- driver
class PMW3901 {
public:
  // Procura o modulo. true = encontrado e configurado.
  bool begin();
  // Le um quadro. false = o modulo parou de responder (present vira false).
  bool read(FlowFrame &f);

  bool    present = false;
  uint8_t chipId = 0, chipIdInv = 0;   // o que foi lido no boot (diagnostico)

private:
  uint8_t  regRead(uint8_t reg);
  void     regWrite(uint8_t reg, uint8_t val);
  void     initRegisters();
  uint16_t _reads = 0;
  uint8_t  _idFails = 0;
};

// ---------------------------------------------------------------- estimador
class FlowEstimator {
public:
  // f      : quadro novo
  // dt     : s desde o quadro anterior
  // rates  : graus/s, na convencao do ahrs.h (roll > 0 = direita, pitch > 0 = nariz p/ cima)
  // height : m ate o chao (sonar, ja corrigido pela inclinacao)
  void update(const FlowFrame &f, float dt, float rollRateDps, float pitchRateDps,
              float heightM, bool heightOk);
  void reset();

  bool  valid = false;   // velocidade confiavel agora
  float vFwd = 0;        // m/s, + = indo para a FRENTE
  float vRight = 0;      // m/s, + = indo para a DIREITA
  uint8_t squal = 0;

private:
  bool _primed = false;  // o filtro ja tem um valor de partida
};

// ---------------------------------------------------------------- freio
class FlowHold {
public:
  // engage: o piloto soltou o manche (ou pouso automatico) e nada mais esta
  // empurrando o drone. Fora disso a correcao volta a zero aos poucos.
  void update(const FlowEstimator &e, bool engage, float dt);
  void reset();

  float pitchBias = 0;   // graus somados ao setpoint de pitch
  float rollBias  = 0;   // graus somados ao setpoint de roll
  bool  holding = false;

private:
  float _iFwd = 0, _iRight = 0;
};
