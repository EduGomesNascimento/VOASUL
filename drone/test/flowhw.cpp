// Driver do PMW3901 contra um sensor simulado (stubs/SPI.h):
// com modulo, sem modulo, e fio solto no meio do voo.
//   cd drone/test && make flowhw
#include <cstdio>
#include "opticalflow.h"
#include <SPI.h>

SimPMW simPmw;
static int fails = 0;
static void check(const char *name, bool ok) {
  printf("%s %s\n", ok ? "[ok]   " : "[FALHA]", name);
  if (!ok) fails++;
}

int main() {
  printf("\n--- PMW3901: deteccao (sensor simulado) ---\n");
  {
    simPmw = SimPMW(); simPmw.plugged = false; simPmw.floatValue = 0xFF;
    PMW3901 d;
    check("J4 vazio, MISO lendo 0xFF: ausente", !d.begin() && !d.present);
    simPmw.floatValue = 0x00;
    check("J4 vazio, MISO lendo 0x00: ausente", !d.begin() && !d.present);
    FlowFrame f;
    check("ausente: read() nao entrega nada", !d.read(f));
    check("ausente: nenhum registrador escrito", simPmw.writes == 0);
  }
  {
    simPmw = SimPMW();
    PMW3901 d;
    check("modulo ligado: presente", d.begin() && d.present);
    check("modulo ligado: configurado (escreveu os registradores)", simPmw.writes > 70);
    simPmw.dx = 3; simPmw.dy = -2; simPmw.squal = 90;
    FlowFrame f;
    check("le um quadro", d.read(f));
    check("quadro: dx, dy, qualidade e byte de movimento certos",
          f.dx == 3 && f.dy == -2 && f.squal == 90 && f.motion == 0xB0);
    for (int i = 0; i < 200; i++) d.read(f);
    check("200 leituras com o modulo bom: continua presente", d.present);

    // fio solto em voo
    simPmw.plugged = false; simPmw.floatValue = 0xFF;
    int n = 0;
    while (d.read(f) && n < 100) {
      check("fio solto: quadro sai com qualidade 0 (nao usavel)", f.squal == 0);
      n++;
    }
    check("fio solto: vira ausente em ate 3 leituras", !d.present && n <= 3);
    check("depois de perdido, read() nao entrega mais nada", !d.read(f));
  }
  printf("\n%s  (%d falha(s))\n", fails ? "FALHOU" : "TUDO OK", fails);
  return fails ? 1 : 0;
}
