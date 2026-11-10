// Testes da luva no PC:  cd luva/test && make
#include <cstdio>
#include <cmath>
#include "gestos.h"
using namespace gestos;

static int falhas = 0;
static void ok(const char *nome, bool v) { printf("%s %s\n", v ? "[ok]   " : "[FALHA]", nome); if (!v) falhas++; }

static Comando cmd(float roll, float pitch, float giro = 0, uint32_t t = 1000) {
  static Estado e; e = Estado();
  Mao m; m.roll = roll; m.pitch = pitch; m.giro = giro;
  return interpretar(m, t, e);
}

int main() {
  printf("\n--- gestos da luva ---\n");
  Comando c = cmd(0, 0);
  ok("mao reta: parado, mantem a altura", c.modo == PARADO && c.roll == 0 && c.pitch == 0 && c.throttle == 0.5f);
  c = cmd(3, -5, 10);
  ok("tremidinha da mao (zona morta): parado", c.modo == PARADO && c.yaw == 0);
  c = cmd(0, 25);
  ok("dedos para baixo 25 graus: anda para a FRENTE (pitch do drone negativo)", c.pitch < -0.3f && c.roll == 0);
  c = cmd(0, -25);
  ok("dedos para cima 25 graus: anda para TRAS", c.pitch > 0.3f);
  c = cmd(25, 0);
  ok("inclinar para a direita: anda para a DIREITA (roll +)", c.roll > 0.3f);
  c = cmd(0, 40);
  ok("inclinacao inteira: no maximo GANHO_INCL", fabsf(c.pitch) <= GANHO_INCL + 1e-6f);
  c = cmd(0, 0, 100);
  ok("girar a mao para a esquerda: drone gira para a ESQUERDA (yaw -)", c.yaw < -0.3f);
  c = cmd(0, -60);
  ok("dedos para cima (mao em pe): SOBE", c.modo == SUBINDO && c.throttle > 0.7f && c.pitch == 0);
  c = cmd(0, 60);
  ok("dedos para baixo (mao em pe): DESCE", c.modo == DESCENDO && c.throttle < 0.3f);
  c = cmd(0, 45);
  ok("faixa de transicao (45 graus): parado, sem andar nem descer", c.modo == PARADO && c.pitch == 0 && c.throttle == 0.5f);

  // histerese: subindo, continua subindo ate voltar abaixo de 50
  {
    Estado e; Mao m;
    m.pitch = -60; interpretar(m, 0, e);
    m.pitch = -52; Comando k = interpretar(m, 20, e);
    ok("histerese: em 52 graus continua subindo", k.modo == SUBINDO);
    m.pitch = -45; k = interpretar(m, 40, e);
    ok("histerese: em 45 graus para de subir", k.modo != SUBINDO);
  }
  // palma para cima: so pousa depois de segurar
  {
    Estado e; Mao m; m.roll = 170;
    Comando k = interpretar(m, 1000, e);
    ok("palma para cima por um instante: ainda nao pousa", !k.pousar);
    k = interpretar(m, 1500, e);
    ok("palma para cima segurada 0,5 s: POUSA", k.pousar && k.modo == POUSANDO);
    m.roll = 0; k = interpretar(m, 1600, e);
    ok("voltou a mao: para de pedir pouso", !k.pousar);
  }
  // filtro: mao parada inclinada -> angulos certos
  {
    Filtro f;
    const float th = 20 * 3.14159265f / 180;
    for (int i = 0; i < 500; i++) f.atualizar(-sinf(th), 0, cosf(th), 0, 0, 0.02f);
    ok("filtro: dedos para baixo 20 graus -> pitch +20", fabsf(f.pitch - 20) < 0.5f);
    Filtro g;
    for (int i = 0; i < 500; i++) g.atualizar(0, sinf(th), cosf(th), 0, 0, 0.02f);
    ok("filtro: direita para baixo 20 graus -> roll +20", fabsf(g.roll - 20) < 0.5f);
    Filtro h;
    for (int i = 0; i < 50; i++) h.atualizar(0, 0.05f, -1, 0, 0, 0.02f);
    ok("filtro: palma para cima -> |roll| > 150", fabsf(h.roll) > 150);
  }
  printf("\n%s (%d falha(s))\n", falhas ? "FALHOU" : "TUDO OK", falhas);
  return falhas ? 1 : 0;
}
