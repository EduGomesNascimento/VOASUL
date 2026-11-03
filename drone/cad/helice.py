#!/usr/bin/env python3
"""
Gerador de helice para o coreless 1020.

    python3 helice.py                  # helice_ccw.stl e helice_cw.stl
    python3 helice.py --d 65 --p 26    # outro diametro e passo

ANTES DE IMPRIMIR, LEIA:

Helice impressa NAO e para voar. Ela sai desbalanceada -- e desbalanceamento a
30.000 rpm vira vibracao que o BMI160 le como movimento, o termo D do PID
amplifica, e o drone chia parado no ar. Alem disso, camada de FDM delamina sob
forca centrifuga, e o fragmento sai a 100 km/h. **Use oculos de protecao mesmo
para testar.**

Para o que ela serve:
  - conferir a folga da helice no frame antes das de verdade chegarem
  - verificar o encaixe de 1 mm no eixo
  - girar em rotacao baixa na bancada para checar sentido de giro e o mixer

Para voar, compre injetada. A especificacao esta no fim deste arquivo.

--------------------------------------------------------------------------

Geometria: pa torcida de verdade, nao chapa plana. O angulo em cada raio sai do
passo: theta(r) = atan(P / (2*pi*r)). Perto do cubo isso da 44 graus, na ponta
7 graus -- e essa torcao e o que faz a pa inteira trabalhar com o mesmo angulo
de ataque, em vez de so o meio dela empurrar ar.
"""

import argparse
import math
import struct

from frame import tube, volume, write_stl

P = dict(
    diam    = 75.0,   # diametro
    pitch   = 30.0,   # passo: avanco teorico por volta (~0,4 x diametro)
    blades  = 2,      # duas pas: mais eficiente que tres no mesmo diametro
    hub_r   = 4.0,
    hub_h   = 5.0,
    bore    = 1.0,    # eixo do 1020
    root_r  = 3.0,    # a pa comeca dentro do cubo, para soldar as duas pecas
    c_root  = 5.0,    # corda na raiz
    c_max   = 9.0,    # corda maxima (em 0,6 do raio)
    c_tip   = 4.0,    # corda na ponta
    t_root  = 1.1,    # espessura na raiz
    t_tip   = 0.5,
    t_edge  = 0.5,    # espessura minima no bordo (senao nao imprime)
    camber  = 0.04,
    nsta    = 20,     # estacoes ao longo do raio
    npts    = 12,     # pontos por lado do perfil
)

# ---------------------------------------------------------------- perfil

def corda(x, p):
    """Distribuicao de corda: sobe da raiz ate 0,6R e afina ate a ponta."""
    if x < 0.6:
        u = x / 0.6
        return p['c_root'] + (p['c_max'] - p['c_root']) * (1 - (1 - u) ** 2)
    u = (x - 0.6) / 0.4
    return p['c_max'] + (p['c_tip'] - p['c_max']) * u ** 1.5


def secao(c, t, p):
    """Perfil: linha media parabolica com espessura eliptica. Devolve o
    contorno fechado no plano (corda, espessura)."""
    n = p['npts']
    up, lo = [], []
    for i in range(n + 1):
        s = i / n
        yc = 4 * p['camber'] * s * (1 - s) * c
        yt = 0.5 * (t * math.sqrt(max(0.0, 1 - (2 * s - 1) ** 2)) + p['t_edge'])
        u = s * c - c / 2                      # centrado na meia-corda
        up.append((u, yc + yt))
        lo.append((u, yc - yt))
    return up + lo[::-1]


def pa(p, phi):
    """Uma pa, girada de phi ao redor do cubo."""
    R = p['diam'] / 2
    r0 = p['root_r']
    secs = []
    for i in range(p['nsta'] + 1):
        x = i / p['nsta']
        r = r0 + (R - r0) * x
        c = corda(x, p)
        t = p['t_root'] + (p['t_tip'] - p['t_root']) * x
        th = math.atan2(p['pitch'], 2 * math.pi * max(r, 1.0))
        co, si = math.cos(th), math.sin(th)
        cf, sf = math.cos(phi), math.sin(phi)
        pts = []
        for u, v in secao(c, t, p):
            y = u * co - v * si
            z = u * si + v * co
            pts.append((r * cf - y * sf, r * sf + y * cf, z))
        secs.append(pts)

    t = []
    m = len(secs[0])
    for i in range(len(secs) - 1):
        a, b = secs[i], secs[i + 1]
        for j in range(m):
            k = (j + 1) % m
            t.append([a[j], b[j], b[k]])
            t.append([a[j], b[k], a[k]])
    for s, inv in ((secs[0], False), (secs[-1], True)):   # tampa raiz e ponta
        for j in range(1, m - 1):
            tri = [s[0], s[j], s[j + 1]]
            t.append(tri[::-1] if inv else tri)
    return t


def build(p, ccw=True):
    t = tube(0, 0, p['bore'] / 2, p['hub_r'], -p['hub_h'] / 2, p['hub_h'] / 2)
    for k in range(p['blades']):
        t += pa(p, 2 * math.pi * k / p['blades'])
    if not ccw:
        # espelha em Y e reinverte a ordem, senao as normais viram para dentro
        t = [[(v[0], -v[1], v[2]) for v in tri][::-1] for tri in t]
    return t

# ---------------------------------------------------------------- saida

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--d', type=float, help='diametro, mm')
    ap.add_argument('--p', type=float, help='passo, mm')
    ap.add_argument('--pas', type=int, help='numero de pas')
    ap.add_argument('--furo', type=float, help='furo do eixo, mm')
    args = ap.parse_args()

    p = dict(P)
    if args.d:    p['diam'] = args.d
    if args.p:    p['pitch'] = args.p
    if args.pas:  p['blades'] = args.pas
    if args.furo: p['bore'] = args.furo

    for nome, ccw in (('helice_ccw.stl', True), ('helice_cw.stl', False)):
        tris = build(p, ccw)
        write_stl(tris, nome)
        g = abs(volume(tris)) / 1000.0 * 1.24
        print(f"  {nome:<18} {len(tris):5d} triangulos   {g:.2f} g")

    R = p['diam'] / 2
    print(f"\n  diametro {p['diam']:.0f} mm, passo {p['pitch']:.0f} mm, "
          f"{p['blades']} pas, furo {p['bore']:.1f} mm")
    for r in (5, 10, 20, R):
        th = math.degrees(math.atan2(p['pitch'], 2 * math.pi * r))
        print(f"    r = {r:4.1f} mm  ->  {th:4.1f} graus")
    print("\n  Imprima 2 de cada sentido. E hélice de bancada -- para voar,"
          "\n  compre injetada (ver o cabecalho deste arquivo).")


if __name__ == '__main__':
    main()
