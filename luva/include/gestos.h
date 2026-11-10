#pragma once
// ============================================================================
//  Luva simples: UM sensor (MPU-6050) nas costas da mao -> comando do drone.
//
//  Montagem do sensor: modulo nas costas da mao, componentes para cima,
//  seta X apontando para os DEDOS. Assim, com a palma para baixo:
//     X -> dedos     Y -> lado do polegar (mao direita)     Z -> cima
//
//  Gestos (sempre a partir da mao reta, palma para baixo, como na calibracao):
//
//    mao reta ............................ fica parado no ar
//    inclinar para frente / para tras ..... anda para frente / para tras
//    inclinar para a direita / esquerda ... anda para o lado
//    girar a mao deitada (como um volante) . gira no lugar
//    dedos para CIMA (mao em pe) .......... sobe
//    dedos para BAIXO ...................... desce
//    palma para CIMA (virar a mao) ........ pousa sozinho
//
//  Este arquivo e so conta (sem hardware): e testado no PC em test/.
// ============================================================================
#include <math.h>
#include <stdint.h>

namespace gestos {

// ---------------------------------------------------------------- ajustes
constexpr float ZONA_MORTA = 8.0f;    // graus: abaixo disto a mao conta como reta
constexpr float INCL_CHEIA = 30.0f;   // graus: inclinacao que da o comando maximo
constexpr float GANHO_INCL = 0.6f;    // fracao do angulo maximo do drone (0,6 x 25 = 15 graus)
constexpr float LIMITE_HORIZ = 35.0f; // ate aqui a inclinacao e "andar"
constexpr float LIMITE_SOBE = 55.0f;  // a partir daqui, dedos para cima/baixo = subir/descer
constexpr float HISTERESE = 5.0f;
constexpr float VEL_VERTICAL = 0.30f; // quanto do manche de altura (0,5 +- isto)
constexpr float GIRO_MORTO = 25.0f;   // graus/s: giro da mao abaixo disto e ignorado
constexpr float GIRO_CHEIO = 150.0f;  // graus/s que dao o giro maximo
constexpr float PALMA_CIMA = 120.0f;  // graus de rolagem: palma virada para cima
constexpr uint32_t POUSO_MS = 400;    // segurar a palma para cima por isto = pousar

// Orientacao da mao, ja descontada a posicao neutra da calibracao.
struct Mao {
  float roll = 0;    // graus, + = inclinada para a DIREITA (lado do mindinho para baixo)
  float pitch = 0;   // graus, + = dedos para BAIXO
  float giro = 0;    // graus/s em volta da vertical, + = girando para a ESQUERDA (anti-horario)
};

enum Modo : uint8_t { PARADO, ANDANDO, SUBINDO, DESCENDO, POUSANDO };

struct Comando {
  float roll = 0, pitch = 0, yaw = 0;   // -1..1, convencao do drone (receiver.h)
  float throttle = 0.5f;                // 0..1 com alt-hold: 0,5 = mantem a altura
  bool  pousar = false;
  Modo  modo = PARADO;
};

inline float limitar(float x, float a, float b) { return x < a ? a : (x > b ? b : x); }

// 0 dentro da zona morta, sobe linear ate 1 em 'cheio', com o sinal de x
inline float curva(float x, float morto, float cheio) {
  const float a = fabsf(x);
  if (a <= morto) return 0.0f;
  return copysignf(limitar((a - morto) / (cheio - morto), 0.0f, 1.0f), x);
}

// Guarda o que precisa de memoria entre leituras (histerese e tempo da palma para cima).
struct Estado {
  Modo vertical = PARADO;       // SUBINDO / DESCENDO / PARADO (com histerese)
  uint32_t palmaDesde = 0;      // 0 = palma nao esta para cima
};

inline Comando interpretar(const Mao &m, uint32_t agoraMs, Estado &e) {
  Comando c;

  // ---- palma para cima: pousar (precisa segurar um instante) ----
  if (fabsf(m.roll) > PALMA_CIMA) {
    if (e.palmaDesde == 0) e.palmaDesde = agoraMs ? agoraMs : 1;
    if (agoraMs - e.palmaDesde >= POUSO_MS) {
      c.pousar = true;
      c.modo = POUSANDO;
    }
    e.vertical = PARADO;
    return c;                     // enquanto vira a mao, fica parado
  }
  e.palmaDesde = 0;

  // ---- dedos para cima / para baixo: subir / descer (com histerese) ----
  const float limSobe = LIMITE_SOBE - (e.vertical != PARADO ? HISTERESE : 0.0f);
  if (m.pitch <= -limSobe)      e.vertical = SUBINDO;
  else if (m.pitch >= limSobe)  e.vertical = DESCENDO;
  else                          e.vertical = PARADO;

  if (e.vertical == SUBINDO)  { c.throttle = 0.5f + VEL_VERTICAL; c.modo = SUBINDO;  return c; }
  if (e.vertical == DESCENDO) { c.throttle = 0.5f - VEL_VERTICAL; c.modo = DESCENDO; return c; }

  // ---- faixa de transicao (entre andar e subir/descer): parado, sem surpresa ----
  if (fabsf(m.pitch) > LIMITE_HORIZ || fabsf(m.roll) > 45.0f) return c;

  // ---- andar: a inclinacao da mao vira inclinacao do drone ----
  // dedos para baixo (pitch da mao +) = frente = pitch do drone NEGATIVO (nariz para baixo)
  c.pitch = -GANHO_INCL * curva(m.pitch, ZONA_MORTA, INCL_CHEIA);
  c.roll  =  GANHO_INCL * curva(m.roll,  ZONA_MORTA, INCL_CHEIA);
  // girar a mao para a esquerda = drone gira para a esquerda (yaw do drone + = direita)
  c.yaw   = -curva(m.giro, GIRO_MORTO, GIRO_CHEIO);
  c.modo  = (c.roll != 0 || c.pitch != 0 || c.yaw != 0) ? ANDANDO : PARADO;
  return c;
}

// Filtro complementar: giroscopio no curto prazo, acelerometro no longo.
// ax..az em g, gx/gy em graus/s, eixos do sensor (X dedos, Y polegar, Z cima).
struct Filtro {
  float roll = 0, pitch = 0;
  bool iniciado = false;
  void atualizar(float ax, float ay, float az, float gx, float gy, float dt) {
    const float R2D = 57.29578f;
    const float rA = atan2f(ay, az) * R2D;                       // + = direita para baixo
    const float pA = atan2f(-ax, sqrtf(ay * ay + az * az)) * R2D; // + = dedos para baixo
    if (!iniciado) { roll = rA; pitch = pA; iniciado = true; return; }
    const float a = 0.98f;
    roll  = a * (roll + gx * dt) + (1 - a) * rA;
    pitch = a * (pitch + gy * dt) + (1 - a) * pA;
    // perto de virar de cabeca para baixo o filtro se perde no +-180: segue o acelerometro
    if (fabsf(rA) > 150.0f) roll = rA;
  }
};

}  // namespace gestos
