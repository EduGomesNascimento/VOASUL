#!/usr/bin/env python3
"""
Frame para a placa de circuito REDONDA (Ø 97,1 mm) -- a versao corrigida do
modelo do Inventor (DRONE.stl).

    python3 frame_redondo.py                  # frame_redondo.stl
    python3 frame_redondo.py --raio 94        # motores mais perto do centro
    python3 frame_redondo.py --placa 97.3 --folga 0.3   # com a SUA placa medida

Mantem a ideia do modelo original -- disco com rebaixo para a placa e quatro
bracos em X com os motores a 100,4 mm do centro -- e corrige o que impedia de
montar e de voar:

  1. Furo do motor: era Ø 8,5 (medida de motor 8520). O 1020 tem Ø 10: aqui e
     um TUBO de Ø 9,9 interno por 10 mm de altura. Furo numa chapa fina so
     daria 3 mm de apoio e o motor sairia com a vibracao.
  2. Peso: o original tinha bracos macicos de 6,7 mm (~87 g de PLA). Aqui os
     bracos tem 3 mm, com uma nervura em cima -- a nervura e o que da rigidez
     a flexao, a uma fracao do peso.
  3. Bracos no ar: no original o fundo dos bracos ficava 2 mm acima da mesa e
     precisava de suporte. Aqui tudo nasce em z = 0. Imprime sem suporte.
  4. Fundo cheio: trocado por quatro raios em X. A placa apoia num degrau na
     borda, 2 mm acima dos raios -- as pontas dos pinos soldados na face de
     baixo ficam livres, e os vaos entre os raios deixam o ultrassonico ver o
     chao e a cinta da bateria passar.

Frente = +Y (a seta na parede). Motores: FR em (+,+), FL em (-,+), RR em (+,-),
RL em (-,-) -- a mesma convencao do mixer em src/motors.cpp.
"""

import argparse
import math

from frame import beam, prism, tube, volume, write_stl

P = dict(
    raio_motor  = 100.4,   # centro ao eixo do motor (o do modelo original)
    placa_d     = 97.1,    # diametro da placa de circuito
    folga       = 0.4,     # folga radial placa-parede (furo impresso sai menor;
                           # placa cortada a mao sai maior -- meca a sua)
    parede      = 2.0,     # espessura da parede do rebaixo
    degrau      = 3.0,     # largura do degrau onde a placa apoia
    raio_t      = 2.0,     # espessura dos raios (fundo)
    vao_pinos   = 2.0,     # folga entre os raios e a face de baixo da placa
    sobra_par   = 2.0,     # quanto a parede passa acima do degrau
    raio_w      = 8.0,     # largura dos raios internos
    braco_t     = 3.0,     # espessura dos bracos
    braco_raiz  = 14.0,
    braco_ponta = 10.0,
    nerv_w      = 1.6,     # nervura em cima do braco
    nerv_h      = 4.0,
    motor_d     = 10.0,    # coreless 1020
    motor_fit   = 0.1,     # interferencia: segura por atrito
    tubo_parede = 2.0,
    tubo_h      = 10.0,
    helice_d    = 75.0,
)


def build(p):
    t = []
    r_bolso = p['placa_d'] / 2 + p['folga']          # parede interna
    r_ext = r_bolso + p['parede']
    z_apoio = p['raio_t'] + p['vao_pinos']            # onde a placa encosta
    z_parede = z_apoio + p['sobra_par']
    seg = 160                                         # circulo liso: a placa e justa

    # --- disco: parede, degrau e raios ---
    t += tube(0, 0, r_bolso, r_ext, 0, z_parede, seg=seg)
    t += tube(0, 0, r_bolso - p['degrau'], r_bolso, 0, z_apoio, seg=seg)
    for ang in (45, 135):
        a = math.radians(ang)
        dx, dy = math.cos(a) * r_bolso, math.sin(a) * r_bolso
        t += beam(-dx, -dy, p['raio_w'], dx, dy, p['raio_w'], 0, p['raio_t'])
    t += tube(0, 0, 0, 7.0, 0, p['raio_t'])           # cubo central

    # seta da frente, por fora da parede, em +Y
    t += prism([(-4, r_ext - 0.5), (4, r_ext - 0.5), (0, r_ext + 5)], 0, 2.0)

    # --- bracos, nervuras e tubos dos motores ---
    r_in = (p['motor_d'] - p['motor_fit']) / 2
    r_out = r_in + p['tubo_parede']
    a = p['raio_motor'] / math.sqrt(2)
    for sx in (1, -1):
        for sy in (1, -1):
            mx, my = sx * a, sy * a
            ux, uy = sx / math.sqrt(2), sy / math.sqrt(2)
            # o braco nasce dentro do degrau (uniao solida no fatiador) e termina
            # no centro do tubo: metade do furo fica fechada e vira o batente do
            # motor -- os quatro na mesma altura. Os fios saem pela metade aberta.
            r0 = r_bolso - p['degrau']
            t += beam(ux * r0, uy * r0, p['braco_raiz'], mx, my, p['braco_ponta'],
                      0, p['braco_t'])
            # nervura: da parede ate o tubo
            t += beam(ux * (r_ext - 1), uy * (r_ext - 1), p['nerv_w'],
                      mx - ux * r_out, my - uy * r_out, p['nerv_w'],
                      p['braco_t'] - 0.01, p['braco_t'] + p['nerv_h'])
            t += tube(mx, my, r_in, r_out, 0, p['tubo_h'])
            t += tube(mx, my, r_in, r_out + 2.5, 0, p['braco_t'] + 1.5)   # reforco
    return t, dict(r_bolso=r_bolso, r_ext=r_ext, z_apoio=z_apoio, z_parede=z_parede)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raio', type=float, help='centro ao eixo do motor, mm (padrão 100,4)')
    ap.add_argument('--placa', type=float, help='diâmetro da placa, mm (padrão 97,1)')
    ap.add_argument('--folga', type=float, help='folga radial da placa, mm (padrão 0,4)')
    ap.add_argument('-o', '--saida', default='frame_redondo.stl')
    args = ap.parse_args()

    p = dict(P)
    if args.raio:  p['raio_motor'] = args.raio
    if args.placa: p['placa_d'] = args.placa
    if args.folga: p['folga'] = args.folga

    tris, g = build(p)
    write_stl(tris, args.saida)
    vol = volume(tris) / 1000.0

    folga_helice = p['raio_motor'] - p['helice_d'] / 2 - g['r_ext']
    if folga_helice < 3:
        raise SystemExit(f'hélice a {folga_helice:.1f} mm do disco: aumente --raio')
    diag = 2 * p['raio_motor']
    print(f"{args.saida}: {len(tris)} triângulos")
    print(f"  rebaixo da placa     Ø {2 * g['r_bolso']:.1f} mm (placa de {p['placa_d']} + "
          f"{p['folga']} de folga em volta)")
    print(f"  placa apoia em       z = {g['z_apoio']:.1f} mm, {p['vao_pinos']:.0f} mm acima dos raios")
    print(f"  motores              a {p['raio_motor']:.1f} mm do centro, diagonal {diag:.0f} mm, "
          f"vizinhos a {diag / math.sqrt(2):.0f} mm")
    print(f"  encaixe do motor     Ø {p['motor_d'] - p['motor_fit']:.1f} mm, tubo de "
          f"{p['tubo_h']:.0f} mm")
    print(f"  hélice até o disco   {folga_helice:.1f} mm de folga")
    print(f"  altura total         {p['tubo_h']:.0f} mm (tubos); disco {g['z_parede']:.0f} mm")
    print(f"\n  volume ~{vol:.1f} cm3  ->  PLA {vol * 1.24:.0f} g (soma dos sólidos; "
          f"o fatiador une as sobreposições)")


if __name__ == '__main__':
    main()
