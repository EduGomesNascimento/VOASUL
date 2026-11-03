// Verificacao das convencoes de sinal e do comportamento numerico.
#include <cstdio>
#include <cstring>
#include <cmath>
#include "ahrs.h"
#include "pid.h"
#include "motors.h"
#include "altitude.h"
#include "avoidance.h"
#include "sha1.h"
#include "websocket.h"
#include "config.h"

static int fails = 0;
static void check(const char *name, bool ok, const char *detail = "") {
  printf("%s %-52s %s\n", ok ? "[ok]  " : "[FALHA]", name, detail);
  if (!ok) fails++;
}
static void near(const char *name, float got, float want, float tol) {
  char d[128];
  snprintf(d, sizeof(d), "obtido %.3f, esperado %.3f", got, want);
  check(name, fabsf(got - want) <= tol, d);
}

static const float DT = 1.0f / 400.0f;

// Roda o AHRS ate convergir com um vetor de aceleracao fixo (drone parado).
static void settle(AHRS &a, float ax, float ay, float az, int n = 8000) {
  for (int i = 0; i < n; i++) a.update(0, 0, 0, ax, ay, az, DT);
}

int main() {
  printf("\n--- AHRS: angulos ---\n");
  {
    AHRS a; a.reset();
    settle(a, 0, 0, 1.0f);
    near("nivelado -> roll 0", a.roll, 0, 0.5f);
    near("nivelado -> pitch 0", a.pitch, 0, 0.5f);
    near("nivelado -> tiltCos 1", a.tiltCos, 1.0f, 0.01f);
    near("nivelado -> earthAccZ 0", a.earthAccZ, 0, 0.05f);
  }
  {
    // Inclinado 30 graus para a DIREITA: o vetor "para cima" pende para -X
    AHRS a; a.reset();
    const float f = 30 * M_PI / 180;
    settle(a, -sinf(f), 0, cosf(f));
    near("inclinado 30 a direita -> roll +30", a.roll, 30.0f, 1.0f);
    near("inclinado 30 a direita -> pitch 0", a.pitch, 0.0f, 1.0f);
    near("inclinado 30 -> tiltCos cos(30)", a.tiltCos, cosf(f), 0.02f);
  }
  {
    // Nariz 20 graus para CIMA: o vetor "para cima" pende para +Y (nariz)
    AHRS a; a.reset();
    const float t = 20 * M_PI / 180;
    settle(a, 0, sinf(t), cosf(t));
    near("nariz 20 para cima -> pitch +20", a.pitch, 20.0f, 1.0f);
    near("nariz 20 para cima -> roll 0", a.roll, 0.0f, 1.0f);
  }

  printf("\n--- AHRS: taxas do giroscopio ---\n");
  {
    AHRS a; a.reset();
    a.update(0, 50, 0, 0, 0, 1, DT);   // giro no eixo Y do modulo (nariz)
    near("giro +Y modulo -> rollRate +50", a.rollRate, 50.0f, 0.01f);
    a.update(50, 0, 0, 0, 0, 1, DT);   // giro no eixo X do modulo (direita)
    near("giro +X modulo -> pitchRate +50 (nariz sobe)", a.pitchRate, 50.0f, 0.01f);
    a.update(0, 0, 50, 0, 0, 1, DT);   // giro no eixo Z do modulo (cima)
    near("giro +Z modulo -> yawRate -50 (gira a esquerda)", a.yawRate, -50.0f, 0.01f);
  }

  printf("\n--- Mixer ---\n");
  {
    Motors m; m.begin(); m.setEnabled(true);
    const int FR = 0, RR = 1, RL = 2, FL = 3;

    // dt grande de proposito: o limitador de subida do throttle so deixa
    // MOTOR_SLEW_UP*dt por ciclo, e aqui o que se quer testar e o mixer puro.
    // O soft starter tem bloco proprio mais abaixo.
    const float DTBIG = 1.0f;

    m.mix(0.50f, 0.10f, 0, 0, DTBIG);
    check("roll+ acelera os motores da ESQUERDA",
          m.out[RL] > m.out[RR] && m.out[FL] > m.out[FR]);
    near("roll+ diferencial esquerda-direita = 2*u", m.out[FL] - m.out[FR], 0.20f, 1e-3f);

    m.mix(0.50f, 0, 0.10f, 0, DTBIG);
    check("pitch+ (nariz cima) acelera os motores TRASEIROS",
          m.out[RR] > m.out[FR] && m.out[RL] > m.out[FL]);

    m.mix(0.50f, 0, 0, 0.10f, DTBIG);
    check("yaw+ (direita) acelera os motores ANTI-HORARIOS (FR e RL)",
          m.out[FR] > m.out[RR] && m.out[RL] > m.out[FL]);

    // Dessaturacao: mesmo com throttle no teto, o diferencial tem de sobreviver
    m.mix(0.95f, 0.15f, 0, 0, DTBIG);
    near("saturado: diferencial preservado", m.out[FL] - m.out[FR], 0.30f, 1e-3f);
    check("saturado: nenhum motor acima do teto",
          m.out[0] <= MOTOR_MAX + 1e-4f && m.out[1] <= MOTOR_MAX + 1e-4f &&
          m.out[2] <= MOTOR_MAX + 1e-4f && m.out[3] <= MOTOR_MAX + 1e-4f);

    m.setEnabled(false);
    m.mix(0.8f, 0, 0, 0, DTBIG);
    check("desarmado ignora o mixer",
          m.out[0] == 0 && m.out[1] == 0 && m.out[2] == 0 && m.out[3] == 0);
  }

  printf("\n--- Partida suave ---\n");
  {
    // Rampa de partida: o degrau de 0 para MOTOR_IDLE nos quatro motores ao
    // mesmo tempo e o pico de corrente que reinicia o microcontrolador.
    stubReset();
    Motors m; m.begin(); m.setEnabled(true);
    m.armStart();

    check("acabou de armar: ainda esta na rampa", m.spooling());

    m.mix(0.0f, 0, 0, 0, DT);
    check("t=0: os quatro motores em zero, nenhum degrau",
          m.out[0] == 0 && m.out[1] == 0 && m.out[2] == 0 && m.out[3] == 0);

    // No meio da rampa os motores estao defasados: o FR (indice 0) entrou
    // primeiro, o FL (indice 3) por ultimo. E isso que espalha o pico.
    stubMillis = MOTOR_SPOOL_MS / 2;
    m.mix(0.0f, 0, 0, 0, DT);
    check("meio da rampa: escalonado, cada motor entrou num instante",
          m.out[0] > m.out[1] && m.out[1] > m.out[2] && m.out[2] > m.out[3]);
    check("meio da rampa: ninguem passou do idle",
          m.out[0] <= MOTOR_IDLE + 1e-6f);

    stubMillis = MOTOR_SPOOL_MS + 3 * MOTOR_SPOOL_STAGGER + 1;
    check("passado o tempo da rampa, ela terminou", !m.spooling());
    m.mix(0.0f, 0, 0, 0, DT);
    near("terminada a rampa, o piso volta a ser MOTOR_IDLE",
         m.out[3], MOTOR_IDLE, 1e-6f);

    // Limite de subida do throttle COMUM. Repare que abaixo de MOTOR_IDLE ele
    // nao aparece: o piso de idle e maior que o passo da rampa, e piso vence.
    // O limite so passa a morder depois que a saida sobe acima do idle.
    stubReset();
    Motors s; s.begin(); s.setEnabled(true);

    float prev = 0.0f, maiorPasso = 0.0f;
    for (int i = 0; i < 200; i++) {          // 200 ciclos = 0,5 s a 400 Hz
      s.mix(1.0f, 0, 0, 0, DT);
      if (s.out[0] > MOTOR_IDLE + 1e-6f) {
        const float passo = s.out[0] - prev;
        if (passo > maiorPasso) maiorPasso = passo;
      }
      prev = s.out[0];
    }
    check("throttle no talo: nenhum ciclo sobe mais que SLEW_UP*dt",
          maiorPasso <= MOTOR_SLEW_UP * DT + 1e-6f);
    check("mas ele chega la: 0,5 s bastam para o throttle encher",
          s.out[0] >= MOTOR_MAX - 1e-4f);

    s.mix(1.0f, 0.10f, 0, 0, DT);
    near("com o throttle limitado, o diferencial do PID passa intacto",
         s.out[3] - s.out[0], 0.20f, 1e-5f);

    prev = s.out[0];
    s.mix(0.0f, 0, 0, 0, DT);
    check("descida NAO e limitada - cai ao idle num ciclo so",
          prev > 0.5f && s.out[0] <= MOTOR_IDLE + 1e-6f);
  }

  printf("\n--- PID ---\n");
  {
    PID p; p.init(0.002f, 0.0f, 0.0f, 0.2f, 0.4f);
    near("erro +100 com kp=0.002 -> 0.2", p.update(100, 0, DT), 0.2f, 1e-4f);
    near("erro -100 -> -0.2", p.update(-100, 0, DT), -0.2f, 1e-4f);
    check("saida respeita o limite", fabsf(p.update(10000, 0, DT)) <= 0.4f + 1e-6f);

    PID q; q.init(0, 0.5f, 0, 0.1f, 1.0f);
    for (int i = 0; i < 5000; i++) q.update(1, 0, DT);
    check("integrador nao estoura (anti-windup)", fabsf(q.i) <= 0.1f + 1e-6f);

    PID r; r.init(0, 0, 0.001f, 1, 1);
    r.update(0, 0, DT);
    check("derivada na medida: degrau no setpoint nao gera pico",
          fabsf(r.update(100, 0, DT)) < 1e-6f);
  }

  printf("\n--- Filtro do termo D (vibracao das helices) ---\n");
  {
    // Ruido alternando a cada amostra = 200 Hz num loop de 400 Hz. E o que a
    // vibracao da helice parece para o giroscopio.
    auto rms = [](float lpfHz) {
      PID q; q.init(0, 0, 0.0005f, 1, 1, lpfHz);
      double acc = 0; int n = 0;
      for (int k = 0; k < 2000; k++) {
        const float meas = (k % 2) ? 1.0f : -1.0f;
        q.update(0, meas, DT);
        if (k > 200) { acc += (double)q.d * q.d; n++; }   // descarta transitorio
      }
      return (float)sqrt(acc / n);
    };
    const float aberto = rms(0.0f);
    const float f80    = rms(80.0f);
    const float f30    = rms(30.0f);

    char msg[96];
    snprintf(msg, sizeof(msg), "sem filtro %.2f -> 80 Hz %.2f (%.0f%% do ruido)",
             aberto, f80, 100.0f * f80 / aberto);
    check("filtro de 80 Hz atenua o ruido de vibracao", f80 < aberto * 0.55f, msg);
    check("corte mais baixo atenua mais", f30 < f80);

    // O sinal util nao pode sumir junto: uma rampa lenta na medida tem de
    // continuar produzindo termo D com o sinal certo.
    PID s; s.init(0, 0, 0.001f, 1, 1, 80.0f);
    float m = 0;
    for (int k = 0; k < 400; k++) { m += 0.5f; s.update(0, m, DT); }
    check("rampa lenta ainda produz termo D (sinal util preservado)", s.d < -0.05f);

    // Sem o parametro, o comportamento tem de ser identico ao de antes.
    PID a; a.init(0, 0, 0.001f, 1, 1);
    PID b; b.init(0, 0, 0.001f, 1, 1, 0.0f);
    a.update(0, 0, DT); b.update(0, 0, DT);
    check("filtro desligado por padrao (compatibilidade)",
          fabsf(a.update(0, 5, DT) - b.update(0, 5, DT)) < 1e-9f);
  }

  printf("\n--- Estimador de altitude ---\n");
  {
    AltitudeEstimator e; e.reset();
    for (int i = 0; i < 4000; i++) e.update(1.20f, true, 5.0f, 0.0f, DT);
    near("converge para o sonar", e.altitude, 1.20f, 0.05f);
    check("marca que esta usando o sonar", e.usingSonar);
    near("velocidade zero parado", e.velocity, 0.0f, 0.05f);

    // Sem sonar valido acima do alcance, o barometro assume sem dar degrau
    AltitudeEstimator b; b.reset();
    for (int i = 0; i < 4000; i++) b.update(2.0f, true, 12.0f, 0.0f, DT);
    const float before = b.altitude;
    b.update(-1, false, 12.0f, 0.0f, DT);
    check("troca sonar->barometro sem degrau", fabsf(b.altitude - before) < 0.02f);
    check("marca que saiu do sonar", !b.usingSonar);
  }

  printf("\n--- Desvio de obstaculos ---\n");
  {
    Rangefinders rf;
    Avoidance av; av.setEnabled(true);

    rf.frontValid = true; rf.frontDistance = 0.30f;   // colado no obstaculo
    float roll = 0, pitch = -MAX_ANGLE_DEG;           // piloto mandando avancar
    for (int i = 0; i < 400; i++) { pitch = -MAX_ANGLE_DEG; roll = 0;
                                    av.apply(rf, roll, pitch, DT); }
    check("obstaculo a frente vence o comando de avanco", pitch > 0);
    check("sinaliza bloqueio", av.frontBlocked);

    rf.frontValid = false; rf.frontDistance = -1;
    rf.irLeft = true; rf.irRight = false;
    for (int i = 0; i < 400; i++) { roll = 0; pitch = 0;
                                    av.apply(rf, roll, pitch, DT); }
    check("IR esquerdo empurra para a direita", roll > 0);

    rf.irLeft = true; rf.irRight = true;
    for (int i = 0; i < 800; i++) { roll = 0; pitch = 0;
                                    av.apply(rf, roll, pitch, DT); }
    near("IR nos dois lados nao desvia", roll, 0.0f, 0.1f);

    av.setEnabled(false);
    roll = 0; pitch = -10;
    av.apply(rf, roll, pitch, DT);
    near("desligado nao altera o comando", pitch, -10.0f, 1e-4f);
  }

  printf("\n--- Fiacao do driver de motor ---\n");
  {
#if MOTOR_DRIVER_L298N
    stubReset();
    Motors m; m.begin();

    const uint8_t inB[4] = {PIN_MOTOR_FR_B, PIN_MOTOR_RR_B, PIN_MOTOR_RL_B, PIN_MOTOR_FL_B};
    const uint8_t pwm[4] = {PIN_MOTOR_FR, PIN_MOTOR_RR, PIN_MOTOR_RL, PIN_MOTOR_FL};

    bool allLow = true, allOut = true, beforePwm = true;
    for (int i = 0; i < 4; i++) {
      allOut    &= (stubMode[inB[i]] == OUTPUT);
      allLow    &= (stubLevel[inB[i]] == LOW);
      // A entrada complementar tem de ir a LOW antes do pino de PWM ser tocado.
      beforePwm &= (stubSeq[inB[i]] > 0) &&
                   (stubSeq[pwm[i]] < 0 || stubSeq[inB[i]] < stubSeq[pwm[i]]);
    }
    check("IN2/IN4 configurados como saida", allOut);
    check("IN2/IN4 em LOW (ponte em frenagem = motor parado)", allLow);
    check("IN2/IN4 definidos antes do PWM (sem tranco no boot)", beforePwm);
#else
    check("driver sem pinos de ponte (MOSFET)", true);
#endif
  }

  printf("\n--- SHA-1 e base64 ---\n");
  {
    struct { const char *in; const char *hex; } v[] = {
      {"",    "da39a3ee5e6b4b0d3255bfef95601890afd80709"},
      {"abc", "a9993e364706816aba3e25717850c26c9cd0d89d"},
    };
    for (auto &t : v) {
      uint8_t d[20]; char hex[41];
      sha1((const uint8_t *)t.in, strlen(t.in), d);
      for (int i = 0; i < 20; i++) snprintf(hex + i * 2, 3, "%02x", d[i]);
      check(t.in[0] ? "sha1(\"abc\")" : "sha1(\"\")", strcmp(hex, t.hex) == 0, hex);
    }

    // Fronteiras do preenchimento: 55/56 e 119/120 sao onde a implementacao
    // precisa de um bloco extra. E exatamente onde SHA-1 escrito a mao quebra.
    struct { int n; const char *hex; } b[] = {
      { 55, "c1c8bbdc22796e28c0e15163d20899b65621d65a"},
      { 56, "c2db330f6083854c99d4b5bfb6e8f29f201be699"},
      { 63, "03f09f5b158a7a8cdad920bddc29b81c18a551f5"},
      { 64, "0098ba824b5c16427bd7a1122a5a442a25ec644d"},
      {119, "ee971065aaa017e0632a8ca6c77bb3bf8b1dfc56"},
      {120, "f34c1488385346a55709ba056ddd08280dd4c6d6"},
    };
    for (auto &t : b) {
      uint8_t in[130]; memset(in, 'a', t.n);
      uint8_t d[20]; char hex[41], name[48];
      sha1(in, t.n, d);
      for (int i = 0; i < 20; i++) snprintf(hex + i * 2, 3, "%02x", d[i]);
      snprintf(name, sizeof(name), "sha1 de %d bytes (fronteira de bloco)", t.n);
      check(name, strcmp(hex, t.hex) == 0, hex);
    }

    struct { const char *in; const char *out; } b64[] = {
      {"",       ""},        {"f",     "Zg=="},     {"fo",    "Zm8="},
      {"foo",    "Zm9v"},    {"foob",  "Zm9vYg=="}, {"fooba", "Zm9vYmE="},
      {"foobar", "Zm9vYmFy"},
    };
    bool ok = true;
    for (auto &t : b64) {
      char o[32];
      base64Encode((const uint8_t *)t.in, strlen(t.in), o, sizeof(o));
      if (strcmp(o, t.out) != 0) { ok = false; printf("       base64(%s) = %s\n", t.in, o); }
      }
    check("base64 nos 3 restos possiveis", ok);
  }

  printf("\n--- WebSocket ---\n");
  {
    // Exemplo do proprio RFC 6455, secao 1.3
    char acc[40];
    ws::acceptKey("dGhlIHNhbXBsZSBub25jZQ==", acc, sizeof(acc));
    check("Sec-WebSocket-Accept (exemplo do RFC 6455)",
          strcmp(acc, "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=") == 0, acc);

    // Frame de texto mascarado, como todo navegador envia
    const char *msg = "C,0,0,0,0.5,1";
    const uint8_t mask[4] = {0x37, 0xfa, 0x21, 0x3d};
    uint8_t f[64];
    size_t n = strlen(msg);
    f[0] = 0x81; f[1] = 0x80 | (uint8_t)n;
    memcpy(f + 2, mask, 4);
    for (size_t i = 0; i < n; i++) f[6 + i] = (uint8_t)msg[i] ^ mask[i & 3];

    ws::Frame fr; size_t used = 0;
    check("frame incompleto devolve INCOMPLETE",
          ws::decode(f, 4, fr, used) == ws::DEC_INCOMPLETE);

    uint8_t copy[64]; memcpy(copy, f, 6 + n);
    const bool okDec = ws::decode(copy, 6 + n, fr, used) == ws::DEC_OK;
    check("decodifica frame de texto mascarado", okDec);
    check("desmascara o payload corretamente",
          okDec && fr.len == n && memcmp(fr.payload, msg, n) == 0);
    check("consome exatamente o frame", used == 6 + n);
    check("identifica o opcode de texto", fr.opcode == ws::OP_TEXT && fr.fin);

    // Frame sem mascara: o RFC proibe vindo do cliente
    uint8_t bare[8] = {0x81, 0x02, 'o', 'k'};
    check("frame do cliente sem mascara e rejeitado",
          ws::decode(bare, 4, bare[0] ? fr : fr, used) == ws::DEC_ERROR);

    // Payload de 64 bits: nao cabe no buffer, tem de ser recusado
    uint8_t huge[16] = {0x81, 0x80 | 127};
    check("comprimento de 64 bits e recusado",
          ws::decode(huge, 16, fr, used) == ws::DEC_ERROR);

    uint8_t h[4];
    check("cabecalho curto: 2 bytes, sem mascara",
          ws::encodeHeader(h, ws::OP_TEXT, 5) == 2 && h[0] == 0x81 && h[1] == 5);
    check("cabecalho estendido: 2 bytes de comprimento",
          ws::encodeHeader(h, ws::OP_TEXT, 300) == 4 && h[1] == 126 &&
          h[2] == 1 && h[3] == 44);
  }

  printf("\n%s  (%d falha(s))\n", fails ? "FALHOU" : "TUDO OK", fails);
  return fails ? 1 : 0;
}
