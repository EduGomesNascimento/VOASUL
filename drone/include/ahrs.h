#pragma once
#include <Arduino.h>

// Filtro de Mahony (quaternion) fundindo giroscopio + acelerometro.
// Sem magnetometro: roll e pitch sao absolutos, yaw e relativo (deriva lenta).
//
// CONVENCAO DE EIXOS -- ler antes de mexer em qualquer sinal.
//
// Entrada (referencial do modulo BMI160, como esta serigrafado na placa):
//     X -> direita     Y -> nariz     Z -> cima
//
// Internamente isso e remapeado para o referencial de voo destro
//     X -> nariz       Y -> esquerda  Z -> cima
// porque so nesse arranjo "rolagem" e uma rotacao em torno de X, que e o que
// as equacoes do quaternion abaixo calculam.
//
// Saida, ja na convencao que a controladora usa:
//     roll  > 0  ->  inclinado para a DIREITA
//     pitch > 0  ->  nariz para CIMA
//     yaw   > 0  ->  girado para a DIREITA
//
// Se o BMI160 estiver montado em outra orientacao, corrija APENAS o remapeamento
// em ahrs.cpp. Nao espalhe sinais trocados pelo resto do codigo.

class AHRS {
public:
  void update(float gx, float gy, float gz,   // graus/s, referencial do modulo
              float ax, float ay, float az,   // g, referencial do modulo
              float dt);
  void reset();

  float roll  = 0;   // graus
  float pitch = 0;   // graus
  float yaw   = 0;   // graus, relativo

  // Velocidades angulares na mesma convencao dos angulos acima (graus/s).
  // Saem direto do giroscopio, sem filtro: e disto que a malha interna precisa.
  float rollRate  = 0;
  float pitchRate = 0;
  float yawRate   = 0;

  // Componente Z da aceleracao no referencial da Terra, ja sem a gravidade (m/s^2).
  float earthAccZ = 0;

  // cos do angulo entre o eixo Z do drone e a vertical. Usado para corrigir o
  // sonar e para compensar o throttle quando o drone esta inclinado.
  float tiltCos = 1.0f;

private:
  float q0 = 1, q1 = 0, q2 = 0, q3 = 0;
  float eIx = 0, eIy = 0, eIz = 0;
};
