#include "ahrs.h"
#include "config.h"
#include <math.h>

static constexpr float DEG2RAD = 0.01745329252f;
static constexpr float RAD2DEG = 57.2957795131f;
static constexpr float G_MS2   = 9.80665f;

void AHRS::reset() {
  q0 = 1; q1 = q2 = q3 = 0;
  eIx = eIy = eIz = 0;
  roll = pitch = yaw = 0;
  rollRate = pitchRate = yawRate = 0;
}

void AHRS::update(float gxs, float gys, float gzs,
                  float axs, float ays, float azs, float dt) {
  // ---- remapeamento modulo -> referencial de voo (X=nariz, Y=esquerda, Z=cima)
  const float bgx =  gys;   // nariz
  const float bgy = -gxs;   // esquerda
  const float bgz =  gzs;   // cima
  const float bax =  ays;
  const float bay = -axs;
  const float baz =  azs;

  float gx = bgx * DEG2RAD;
  float gy = bgy * DEG2RAD;
  float gz = bgz * DEG2RAD;

  const float norm = sqrtf(bax * bax + bay * bay + baz * baz);

  // O acelerometro so serve de referencia quando mede algo proximo de 1 g.
  // Durante uma manobra brusca ele mede a aceleracao do voo, nao a gravidade,
  // e corrigir por ele nessa hora inclina o horizonte artificial.
  if (norm > 0.6f && norm < 1.4f) {
    const float inv = 1.0f / norm;
    const float axn = bax * inv, ayn = bay * inv, azn = baz * inv;

    // Direcao da vertical estimada pelo quaternion atual (3a linha de R)
    const float vx = 2.0f * (q1 * q3 - q0 * q2);
    const float vy = 2.0f * (q0 * q1 + q2 * q3);
    const float vz = q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3;

    // Erro = produto vetorial entre vertical medida e estimada
    const float ex = (ayn * vz - azn * vy);
    const float ey = (azn * vx - axn * vz);
    const float ez = (axn * vy - ayn * vx);

    if (AHRS_MAHONY_KI > 0.0f) {
      eIx += ex * AHRS_MAHONY_KI * dt;
      eIy += ey * AHRS_MAHONY_KI * dt;
      eIz += ez * AHRS_MAHONY_KI * dt;
      gx += eIx; gy += eIy; gz += eIz;
    }
    gx += AHRS_MAHONY_KP * ex;
    gy += AHRS_MAHONY_KP * ey;
    gz += AHRS_MAHONY_KP * ez;
  }

  // ---- integracao do quaternion
  const float hdt = 0.5f * dt;
  const float dq0 = (-q1 * gx - q2 * gy - q3 * gz) * hdt;
  const float dq1 = ( q0 * gx + q2 * gz - q3 * gy) * hdt;
  const float dq2 = ( q0 * gy - q1 * gz + q3 * gx) * hdt;
  const float dq3 = ( q0 * gz + q1 * gy - q2 * gx) * hdt;

  q0 += dq0; q1 += dq1; q2 += dq2; q3 += dq3;

  const float qn = sqrtf(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
  if (qn > 1e-6f) {
    const float inv = 1.0f / qn;
    q0 *= inv; q1 *= inv; q2 *= inv; q3 *= inv;
  }

  // ---- angulos de Euler
  // Rotacao em torno de X (nariz) -> rolagem, ja positiva para a direita.
  roll = atan2f(2.0f * (q0 * q1 + q2 * q3),
                q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3) * RAD2DEG;

  // Rotacao em torno de Y (esquerda): positiva pela regra da mao direita leva
  // o nariz para BAIXO, entao invertemos para "nariz para cima e positivo".
  float sp = 2.0f * (q0 * q2 - q3 * q1);
  sp = constrain(sp, -1.0f, 1.0f);
  pitch = -asinf(sp) * RAD2DEG;

  // Rotacao em torno de Z (cima): positiva e anti-horaria vista de cima,
  // ou seja, para a esquerda. Invertemos para "direita e positivo".
  yaw = -atan2f(2.0f * (q0 * q3 + q1 * q2),
                q0 * q0 + q1 * q1 - q2 * q2 - q3 * q3) * RAD2DEG;

  // ---- velocidades angulares na mesma convencao dos angulos
  rollRate  =  bgx;
  pitchRate = -bgy;
  yawRate   = -bgz;

  // ---- aceleracao vertical no referencial da Terra, sem gravidade
  const float r31 = 2.0f * (q1 * q3 - q0 * q2);
  const float r32 = 2.0f * (q0 * q1 + q2 * q3);
  const float r33 = q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3;
  earthAccZ = (bax * r31 + bay * r32 + baz * r33 - 1.0f) * G_MS2;

  tiltCos = r33;
  if (tiltCos < 0.1f) tiltCos = 0.1f;   // evita divisao explosiva quando capota
}
