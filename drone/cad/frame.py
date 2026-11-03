#!/usr/bin/env python3
"""
Gerador parametrico do frame do drone.

    python3 frame.py                 # gera frame.stl
    python3 frame.py --guardas       # com protecao de helice
    python3 frame.py --diagonal 170  # muda o tamanho

Parte da base de 130 x 30 mm, que e a placa perfurada de fenolite inteira --
ela e quem manda no resto das dimensoes. Tudo o mais e derivado dela e das
helices.

Duas escolhas de projeto que explicam a diferenca de peso para o modelo antigo:

1. A base nao e uma chapa macica, e um quadro perimetral. A placa perfurada ja
   e rigida; o frame so precisa segura-la pelas bordas. Chapa macica de
   130x30x3 mm pesaria 14,5 g sozinha, contra 8 g do quadro.

2. Os anéis de protecao sao opcionais e vem desligados. Eles custam ~11 g e nao
   dao ganho aerodinamico nenhum na folga em que trabalham: sao protecao de
   helice, e essa e uma decisao de quem voa, nao do projeto.

O STL sai como varios solidos fechados que se sobrepoem. Todo fatiador
(Cura, PrusaSlicer, Orca, Bambu) faz a uniao na hora de fatiar -- e o jeito
mais robusto de montar geometria assim sem um kernel CAD.
"""

import argparse
import math
import struct

# ---------------------------------------------------------------- parametros

P = dict(
    # --- base: e a placa perfurada que define isto ---
    # Placa de fenolite inteira, 130 x 30 mm. So a LARGURA entra na geometria:
    # a posicao do motor sai de largura/2 + raio da helice + folga, entao
    # estreitar encurta a diagonal e encurtar nao mexe em nada. Os 130 mm de
    # comprimento so custam peso (placa + trilhos), e sao a area que sobra para
    # os MOSFET, os terminais e os conectores ao lado do Pico W (51 x 21 mm).
    base_l      = 130.0,   # comprimento da placa perfurada
    base_w      = 30.0,    # largura da placa perfurada
    rail_w      = 5.0,     # largura do trilho do quadro
    plate_t     = 3.0,     # espessura da base e dos bracos

    # --- helice e motor ---
    prop_d      = 75.0,    # diametro da helice
    prop_gap    = 5.0,     # folga minima entre helice e base
    # Coreless 1020: cilindro de 10 mm de diametro por 20 mm, eixo de 1 mm.
    # (Para o 716/720 que veio do E88: --motor 7 --helice 55. Aquele motor da
    # ~12 g de empuxo, 48 g nos quatro, e nao levanta este drone.)
    #
    # Nenhum suporte plastico e usado: o tubo abaixo segura o motor direto,
    # com menos peca e junta mais rigida.
    motor_d     = 10.0,
    motor_len   = 20.0,
    motor_fit   = 0.1,     # folga de encaixe (interferencia leve segura sozinho)
    motor_wall  = 2.0,
    motor_h     = 10.0,    # altura do tubo (deixa o eixo e a helice livres)

    # --- bracos ---
    arm_w_root  = 12.0,
    arm_w_tip   = 9.0,
    brace_w     = 5.0,     # contraventamento diagonal ate o canto da base

    # --- protecao de helice (opcional) ---
    guard       = False,
    guard_wall  = 1.6,
    guard_h     = 6.0,
    guard_gap   = 3.0,     # folga entre a ponta da helice e o anel

    # --- pes de pouso ---
    # DESLIGADOS por padrao, e nao por serem opcionais: eles apontam para BAIXO,
    # entao integra-los deixaria o frame inteiro 20 mm no ar, exigindo suporte
    # sob a base e os bracos todos. Imprima `pe.stl` (suportes.py) separado e
    # cole -- imprime em pe, sem suporte nenhum, e sai melhor.
    # `--pes` liga assim mesmo, se voce quiser encarar o suporte.
    feet        = False,
    foot_h      = 20.0,
    foot_r      = 2.0,

    # --- amarracao ---
    tie_slot    = 4.0,     # vao para abracadeira
    diagonal    = None,    # se None, calcula o minimo que da folga a helice
)

# ---------------------------------------------------------------- primitivas

def prism(poly, z0, z1):
    """Poligono convexo (sentido anti-horario visto de +Z) extrudado em Z."""
    t = []
    n = len(poly)
    for i in range(1, n - 1):                       # tampa de cima
        t.append([(poly[0][0], poly[0][1], z1),
                  (poly[i][0], poly[i][1], z1),
                  (poly[i + 1][0], poly[i + 1][1], z1)])
    for i in range(1, n - 1):                       # tampa de baixo (invertida)
        t.append([(poly[0][0], poly[0][1], z0),
                  (poly[i + 1][0], poly[i + 1][1], z0),
                  (poly[i][0], poly[i][1], z0)])
    for i in range(n):                              # paredes
        a, b = poly[i], poly[(i + 1) % n]
        t.append([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1)])
        t.append([(a[0], a[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)])
    return t


def box(x0, y0, x1, y1, z0, z1):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def tube(cx, cy, ri, ro, z0, z1, seg=64):
    """Cilindro anelar. ri=0 gera um cilindro macico."""
    t = []
    for i in range(seg):
        a0 = 2 * math.pi * i / seg
        a1 = 2 * math.pi * (i + 1) / seg
        co0, si0 = math.cos(a0), math.sin(a0)
        co1, si1 = math.cos(a1), math.sin(a1)

        xo0, yo0 = cx + ro * co0, cy + ro * si0
        xo1, yo1 = cx + ro * co1, cy + ro * si1
        xi0, yi0 = cx + ri * co0, cy + ri * si0
        xi1, yi1 = cx + ri * co1, cy + ri * si1

        # parede externa (normal para fora)
        t.append([(xo0, yo0, z0), (xo1, yo1, z0), (xo1, yo1, z1)])
        t.append([(xo0, yo0, z0), (xo1, yo1, z1), (xo0, yo0, z1)])
        if ri > 0:   # parede interna (normal para dentro)
            t.append([(xi0, yi0, z0), (xi1, yi1, z1), (xi1, yi1, z0)])
            t.append([(xi0, yi0, z0), (xi0, yi0, z1), (xi1, yi1, z1)])
        # tampas
        t.append([(xi0, yi0, z1), (xo0, yo0, z1), (xo1, yo1, z1)])
        t.append([(xi0, yi0, z1), (xo1, yo1, z1), (xi1, yi1, z1)])
        t.append([(xi0, yi0, z0), (xo1, yo1, z0), (xo0, yo0, z0)])
        t.append([(xi0, yi0, z0), (xi1, yi1, z0), (xo1, yo1, z0)])
    return t


def beam(x0, y0, w0, x1, y1, w1, z0, z1):
    """Viga afilada de (x0,y0) a (x1,y1), largura w0 na raiz e w1 na ponta."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    px, py = -dy / L, dx / L          # perpendicular unitaria
    poly = [(x0 + px * w0 / 2, y0 + py * w0 / 2),
            (x0 - px * w0 / 2, y0 - py * w0 / 2),
            (x1 - px * w1 / 2, y1 - py * w1 / 2),
            (x1 + px * w1 / 2, y1 + py * w1 / 2)]
    # garante sentido anti-horario
    area = sum(poly[i][0] * poly[(i + 1) % 4][1] - poly[(i + 1) % 4][0] * poly[i][1]
               for i in range(4))
    if area < 0:
        poly.reverse()
    return prism(poly, z0, z1)

# ---------------------------------------------------------------- montagem

def build(p):
    t = []
    hl, hw = p['base_l'] / 2, p['base_w'] / 2
    rw, tt = p['rail_w'], p['plate_t']
    prop_r = p['prop_d'] / 2

    # Posicao do motor. Layout X QUADRADO: braco de rolagem = braco de arfagem,
    # senao roll e pitch precisariam de ganhos de PID diferentes.
    # O minimo e o que faz a helice livrar a base com folga.
    a_min = hw + prop_r + p['prop_gap']
    a = a_min if p['diagonal'] is None else p['diagonal'] / (2 * math.sqrt(2))
    if a < a_min:
        raise SystemExit(
            f"diagonal pequena demais: a helice de {p['prop_d']:.0f} mm bateria na "
            f"base. Minimo = {a_min * 2 * math.sqrt(2):.0f} mm")

    # --- quadro perimetral da base ---
    # Trilhos longos partidos, com vaos que servem de passagem de abracadeira.
    slots = [-0.62, -0.28, 0.28, 0.62]
    for sy in (+1, -1):
        y1, y0 = sy * hw, sy * (hw - rw)
        cuts = sorted([-hl] + [s * hl for s in slots] + [hl])
        seg = [(-hl, cuts[1] - p['tie_slot'] / 2)]
        for i in range(1, len(cuts) - 1):
            seg.append((cuts[i] + p['tie_slot'] / 2,
                        (cuts[i + 1] - p['tie_slot'] / 2) if i + 1 < len(cuts) - 1 else hl))
        for x0, x1 in seg:
            if x1 > x0:
                t += box(x0, min(y0, y1), x1, max(y0, y1), 0, tt)
    for sx in (+1, -1):                                  # trilhos curtos
        x1, x0 = sx * hl, sx * (hl - rw)
        t += box(min(x0, x1), -hw, max(x0, x1), hw, 0, tt)
    for cx in (-p['base_l'] * 0.22, p['base_l'] * 0.22):  # nervuras de reforco
        t += box(cx - 2, -hw, cx + 2, hw, 0, tt)

    # --- bracos, tubos de motor e guardas ---
    r_in = (p['motor_d'] - p['motor_fit']) / 2
    r_out = r_in + p['motor_wall']

    # Ancoragem do contraventamento, sobre o trilho longo. Ele so triangula se
    # ficar bem afastado do braco em X -- e onde fica depende do comprimento da
    # base: com a placa de 130 mm o motor cai DENTRO do comprimento dela (58 de
    # 65), entao o canto fica quase debaixo do motor e ancorar la nao serve de
    # nada. Escolhe-se entao, entre o canto e um ponto para dentro, o que der o
    # maior afastamento -- com alcance limitado ao proprio comprimento do braco,
    # que e o que da ~45 graus.
    arm_len = a - (hw - rw)
    bx = max((min(a + arm_len, hl - rw), max(a - arm_len, rw)),
             key=lambda v: abs(v - a))

    for sx in (+1, -1):
        for sy in (+1, -1):
            mx, my = sx * a, sy * a
            # A raiz entra no trilho para que a uniao no fatiador seja solida.
            t += beam(mx, sy * (hw - rw), p['arm_w_root'],
                      mx, my, p['arm_w_tip'], 0, tt)
            # Contraventamento. Sem ele o braco fica preso so no trilho de 5 mm
            # e o conjunto motor+helice trabalha como uma alavanca sobre essa
            # unica secao -- e onde frame impresso quebra. A triangulacao custa
            # ~4 g e muda a rigidez da junta por completo.
            t += beam(sx * bx, sy * (hw - rw), p['brace_w'],
                      mx, my, p['brace_w'], 0, tt)
            t += tube(mx, my, r_in, r_out, 0, p['motor_h'])
            # Reforco na junta: o tubo sai de uma chapa de 3 mm, entao a base
            # dele e engrossada para o motor nao arrancar o braco na primeira
            # pancada.
            t += tube(mx, my, r_in, r_out + 2.5, 0, tt + 1.5)
            if p['feet']:
                # Perna sob o motor: e o ponto mais estavel (base de 116 mm de
                # lado) e o tubo de 4 mm bloqueia 0,09 % do disco da helice.
                t += tube(mx, my, 0, p['foot_r'], -p['foot_h'], tt)
                t += tube(mx, my, 0, p['foot_r'] + 1.6,
                          -p['foot_h'], -p['foot_h'] + 1.5)   # sapata
            if p['guard']:
                gi = prop_r + p['guard_gap']
                t += tube(mx, my, gi, gi + p['guard_wall'], 0, p['guard_h'])
                t += beam(mx, my, p['arm_w_tip'],
                          mx, my + sy * (gi + p['guard_wall']), 4.0, 0, tt)
                t += beam(mx, my, p['arm_w_tip'],
                          mx + sx * (gi + p['guard_wall']), my, 4.0, 0, tt)
    return t, a

# ---------------------------------------------------------------- saida

def volume(tris):
    v = 0.0
    for a, b, c in tris:
        v += (a[0] * (b[1] * c[2] - b[2] * c[1])
              - a[1] * (b[0] * c[2] - b[2] * c[0])
              + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return v / 6.0


def write_stl(tris, path):
    with open(path, 'wb') as f:
        f.write(b'frame drone - gerado por cad/frame.py'.ljust(80, b' '))
        f.write(struct.pack('<I', len(tris)))
        for a, b, c in tris:
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f.write(struct.pack('<3f', nx / L, ny / L, nz / L))
            for v in (a, b, c):
                f.write(struct.pack('<3f', *v))
            f.write(b'\0\0')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--guardas', action='store_true', help='inclui protecao de helice')
    ap.add_argument('--diagonal', type=float, help='diagonal motor a motor, mm')
    ap.add_argument('--helice', type=float, help='diametro da helice, mm')
    ap.add_argument('--motor', type=float, help='diametro do motor, mm')
    ap.add_argument('--base', type=float, nargs=2, metavar=('COMPR', 'LARG'),
                    help='tamanho da base, mm (padrao: a placa perfurada, 130 30)')
    ap.add_argument('--espessura', type=float, help='espessura da base e dos bracos, mm')
    ap.add_argument('--trilho', type=float, help='largura do trilho do quadro, mm')
    ap.add_argument('--sem-pes', action='store_true', help='nao gera pes de pouso')
    ap.add_argument('--minimo', action='store_true',
                    help='perfil enxuto: tudo no limite fino, para o drone de '
                         'prova de voo com os motores 716')
    ap.add_argument('-o', '--saida', default='frame.stl')
    args = ap.parse_args()

    p = dict(P)
    if args.minimo:
        # Com 716 o empuxo total e ~48 g, entao o drone inteiro tem de caber em
        # ~30 g. Sobra pouquissimo para o frame, e todas as secoes vao para o
        # minimo que ainda imprime com 3 perimetros de bico 0,4.
        p.update(plate_t=1.6, rail_w=3.5, arm_w_root=8.0, arm_w_tip=5.5,
                 brace_w=3.0, motor_wall=1.4, motor_h=8.0, prop_gap=4.0)
    if args.sem_pes:   p['feet'] = False
    if args.guardas:   p['guard'] = True
    if args.diagonal:  p['diagonal'] = args.diagonal
    if args.helice:    p['prop_d'] = args.helice
    if args.motor:     p['motor_d'] = args.motor
    if args.espessura: p['plate_t'] = args.espessura
    if args.trilho:    p['rail_w'] = args.trilho
    if args.base:      p['base_l'], p['base_w'] = args.base

    tris, a = build(p)
    vol = volume(tris) / 1000.0        # cm3 (aproximado: solidos se sobrepoem)
    write_stl(tris, args.saida)

    diag = a * 2 * math.sqrt(2)
    print(f"{args.saida}: {len(tris)} triangulos")
    print(f"  base                {p['base_l']:.0f} x {p['base_w']:.0f} mm (placa perfurada)")
    print(f"  motores em          (+-{a:.0f}, +-{a:.0f}) mm  [X quadrado]")
    print(f"  diagonal            {diag:.0f} mm")
    print(f"  entre adjacentes    {2 * a:.0f} mm")
    print(f"  helice              {p['prop_d']:.0f} mm  (folga ate a base: "
          f"{a - p['base_w'] / 2 - p['prop_d'] / 2:.1f} mm)")
    print(f"  encaixe do motor    {p['motor_d'] - p['motor_fit']:.1f} mm de diametro interno")
    print(f"  pes de pouso        {'sim, ' + str(int(p['foot_h'])) + ' mm' if p['feet'] else 'nao'}")
    print(f"  guardas             {'sim' if p['guard'] else 'nao'}")
    print(f"\n  volume ~{vol:.1f} cm3  ->  PLA {vol * 1.24:.0f} g | PETG {vol * 1.27:.0f} g")
    print("  (soma dos solidos; o fatiador une as sobreposicoes, entao o peso real fica um pouco menor)")


if __name__ == '__main__':
    main()
