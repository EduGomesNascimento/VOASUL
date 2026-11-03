#!/usr/bin/env python3
"""
Suportes dos sensores de proximidade.

    python3 suportes.py            # gera os quatro STL e informa o peso

Gera:
    sonar_baixo.stl    HC-SR04 apontado para o chao   (alt-hold)
    sonar_frente.stl   HC-SR04 apontado para a frente  (desvio)
    suporte_ir.stl     FC-51 a 90 graus, imprima 2x    (desvio lateral)

NEM TODOS VALEM O PESO. Leia antes de imprimir os quatro:

- O **sonar de baixo** e o unico que precisa mesmo ser impresso. Ele mede a
  altura, e a leitura sai multiplicada pelo cosseno da inclinacao dele: 10 graus
  de folga no suporte viram 1,5 % de erro constante, e o alt-hold fica caçando
  altura a vida toda. Rigidez aqui e funcao, nao acabamento.

- O **sonar da frente** e os **IR** toleram fita dupla-face e abracadeira. Eles
  so precisam apontar aproximadamente na direcao certa: o desvio compara a
  distancia com um limiar, nao integra o valor. Dois graus de erro nao mudam
  nada. Imprimir os tres custa ~6 g, que a esta altura do orcamento e mais do
  que voce quer gastar.

Encaixe por atrito, sem parafuso: a placa desliza na guia em C. Se ficar
folgada, aumente `pcb_t`; se nao entrar, diminua.
"""

import argparse
from frame import box, tube, volume, write_stl

# ---------------------------------------------------------------- medidas

HCSR04 = dict(pcb_l=45.0, pcb_w=20.0)
FC51   = dict(pcb_l=31.0, pcb_w=14.0)

P = dict(
    pcb_t   = 1.9,    # fresta da guia (placa de 1,6 + folga de impressao)
    wall    = 2.0,
    grip    = 2.5,    # quanto a aba avanca sobre a borda da placa
    clear   = 0.4,    # folga lateral
)

# ---------------------------------------------------------------- pecas

def sonar_baixo(p):
    """HC-SR04 deitado, transdutores para baixo. Aparafusa nada: escorrega na
    guia e prende na base por abracadeira, pelos dois vaos do topo."""
    t = []
    L, W = HCSR04['pcb_l'], HCSR04['pcb_w']
    hl, hw = L / 2, W / 2 + p['clear']
    g, wl, pt = p['grip'], p['wall'], p['pcb_t']

    y_in, y_out = hw - g, hw + wl        # aba entra ate y_in, guia vai ate y_out
    for sy in (+1, -1):
        a, b = sy * y_in, sy * y_out
        lo, hi = min(a, b), max(a, b)
        t += box(-hl, lo, hl, hi, -wl, 0)          # aba de baixo: a placa apoia
        t += box(-hl, lo, hl, hi, pt, pt + wl)     # aba de cima: prende
        # alma, so fora da borda da placa, senao fecharia a fresta
        c, d = sy * (hw + 0.3), sy * y_out
        t += box(-hl, min(c, d), hl, max(c, d), 0, pt)

    # batente numa das pontas: a placa entra pela outra e para aqui
    t += box(hl, -y_out, hl + wl, y_out, -wl, pt + wl)

    # duas tiras no topo para a abracadeira passar entre elas
    for x0, x1 in ((-hl, -hl + 8), (hl - 8, hl)):
        t += box(x0, -y_out, x1, y_out, pt + wl, pt + wl + 1.5)
    return t


def sonar_frente(p):
    """HC-SR04 em pe, transdutores para +X. Canaleta que segura a borda de
    baixo, mais dois montantes com lingueta no topo."""
    t = []
    L, W = HCSR04['pcb_l'], HCSR04['pcb_w']
    hl = L / 2
    wl, pt = p['wall'], p['pcb_t']

    # canaleta: piso + parede de tras + labios so nas pontas (o meio tem de
    # ficar livre, e por onde os transdutores olham)
    t += box(-wl, -hl, pt + wl, hl, -wl, 0)                 # piso
    t += box(-wl, -hl, 0, hl, 0, 10)                        # parede de tras
    for y0, y1 in ((-hl, -hl + 5), (hl - 5, hl)):
        t += box(pt, y0, pt + wl, y1, 0, 10)                # labio dianteiro
        t += box(-wl, y0, pt + wl, y1, 10, W)               # montante ate o topo
        t += box(-wl, y0, pt + wl, y1, W, W + 2)            # lingueta de topo

    # pe horizontal que encosta no trilho da base e recebe a abracadeira
    t += box(-wl - 18, -12, -wl, 12, -wl, 0)
    return t


def pe(p):
    """Pe de pouso. Imprima 4x e cole sob o braco, junto ao motor.

    Sai separado do frame por causa da impressao: integrado, ele aponta para
    baixo e poria o frame inteiro 20 mm no ar. Aqui imprime em pe, sem suporte.
    O disco largo vai contra o braco (e a face que assenta na mesa ao imprimir);
    o disco estreito e o que toca o chao."""
    t = []
    t += tube(0, 0, 0, 6.0, 0, 2.0)        # base de colagem
    t += tube(0, 0, 0, 2.5, 0, 18.0)       # perna
    t += tube(0, 0, 0, 4.0, 18.0, 19.5)    # sapata
    return t


def suporte_ir(p):
    """FC-51 de pe, LEDs para fora. Pe horizontal na base, face vertical onde
    a placa e amarrada -- os dois LEDs passam pelo vao central."""
    t = []
    L, W = FC51['pcb_l'], FC51['pcb_w']
    wl = p['wall']
    hw = W / 2 + p['clear']

    t += box(-14, -hw - wl, 0, hw + wl, 0, wl)              # pe
    for z0, z1 in ((wl, wl + 6), (wl + L - 6, wl + L)):     # face partida ao meio
        t += box(-wl, -hw - wl, 0, hw + wl, z0, z1)
    for sy in (+1, -1):                                     # montantes laterais
        a, b = sy * hw, sy * (hw + wl)
        t += box(-wl, min(a, b), 0, max(a, b), wl, wl + L)
    return t

# ---------------------------------------------------------------- saida

PECAS = {
    'sonar_baixo':  (sonar_baixo,  'HC-SR04 para o chao'),
    'sonar_frente': (sonar_frente, 'HC-SR04 para a frente'),
    'suporte_ir':   (suporte_ir,   'FC-51 lateral (imprima 2x)'),
    'pe':           (pe,           'pe de pouso (imprima 4x)'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--folga', type=float, help='fresta da guia, mm (padrao 1,9)')
    ap.add_argument('peca', nargs='?', choices=list(PECAS), help='so uma peca')
    args = ap.parse_args()

    p = dict(P)
    if args.folga:
        p['pcb_t'] = args.folga

    alvo = [args.peca] if args.peca else list(PECAS)
    total = 0.0
    for nome in alvo:
        fn, desc = PECAS[nome]
        tris = fn(p)
        vol = volume(tris) / 1000.0
        write_stl(tris, nome + '.stl')
        n = {'suporte_ir': 2, 'pe': 4}.get(nome, 1)
        total += vol * 1.24 * n
        print(f"  {nome + '.stl':<20} {desc:<30} {vol * 1.24:5.1f} g"
              + (f"  x{n} = {vol * 1.24 * n:.1f} g" if n > 1 else ""))
    print(f"\n  total impresso: {total:.1f} g")
    print("  (imprimir so o sonar_baixo custa "
          f"{volume(sonar_baixo(p)) / 1000 * 1.24:.1f} g -- veja o topo do arquivo)")


if __name__ == '__main__':
    main()
