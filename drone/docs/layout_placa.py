#!/usr/bin/env python3
"""
Distribuicao dos componentes na placa perfurada de 130 x 30 mm, em escala.

    pip install matplotlib
    python3 layout_placa.py         # layout_placa.png e layout_placa.svg

E uma SUGESTAO que prova que tudo cabe -- nao uma obrigacao. As medidas dos
modulos variam de fabricante para fabricante: confira as suas com paquimetro e
corrija o dicionario PECAS antes de levar para o CAD.

Coordenadas em mm. x ao longo da placa (0 = traseira, 130 = nariz), y na
largura (0 = lado direito, 30 = lado esquerdo, olhando de cima com o nariz para
a frente).
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrow

L, W = 130.0, 30.0
PASSO = 2.54

# nome: (x, y, comprimento, largura, cor, rotulo)
TOPO = {
    'esp32':  (0.0,   1.0, 55.0, 28.0, '#9ecae1',
               'U1  ESP32 DevKit 38 pinos\n55 × 28 mm  ·  ~9 g\n← antena nesta ponta, na borda'),
    'bmi':    (58.5,  5.0, 13.0, 18.0, '#fdae6b', '\n\n\n\nU3 BMI160\n13 × 18'),
    'bmp':    (73.5,  4.0, 11.5, 15.0, '#fdd0a2', 'U4\nBMP280\n11,5 × 15'),
    'stepup': (87.0,  1.0, 36.0, 17.0, '#c7e9c0', 'U2  step-up MT3608\n36 × 17 mm'),
    'fets':   (73.5, 20.5, 49.5,  8.5, '#d9d9d9',
               'Q1–Q4 + D1–D4 + R1–R8   (4 canais × ~12 mm)'),
    'div':    (56.5, 24.0, 15.0,  5.0, '#e5e5e5', 'R9–R14'),
}
C1 = (126.0, 9.5, 4.0)        # x, y, raio -- 1000 uF em pe (diametro 8)
J1 = (126.0, 22.0)            # rabicho do conector da bateria (Molex)

BAIXO = {
    'sonar':  (4.0,   5.0, 45.0, 20.0, '#bcbddc',
               'U5  HC-SR04 de baixo\n45 × 20 mm, transdutores para o chão'),
    'bat':    (75.0,  2.5, 40.0, 25.0, '#fc9272',
               'J1  bateria Leão LB530LP1\n1S 530 mAh 30C\n40 × 25 × 8 mm  ·  14 g\n(velcro: desliza p/ o CG)'),
}


def placa(ax, titulo):
    ax.add_patch(Rectangle((0, 0), L, W, fc='#f3ead2', ec='#7a6a3a', lw=1.4))
    xs = [PASSO * i + 1.27 for i in range(int(L / PASSO))]
    ys = [PASSO * j + 1.27 for j in range(int(W / PASSO))]
    ax.scatter([x for x in xs for _ in ys], [y for _ in xs for y in ys],
               s=1.2, c='#b9a77a', zorder=1)
    ax.set_xlim(-14, L + 14)
    ax.set_ylim(-9, W + 9)
    ax.set_aspect('equal')
    ax.set_title(titulo, loc='left', fontsize=11)
    ax.set_xticks(range(0, 131, 10))
    ax.set_yticks([0, 15, 30])
    ax.tick_params(labelsize=8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    # centro geometrico = onde o CG tem de ficar
    ax.plot([L / 2 - 3, L / 2 + 3], [W / 2, W / 2], c='k', lw=1, zorder=5)
    ax.plot([L / 2, L / 2], [W / 2 - 3, W / 2 + 3], c='k', lw=1, zorder=5)
    ax.annotate('CG', (L / 2, W / 2), (L / 2 + 1.5, W / 2 + 3.2), fontsize=8, zorder=5)
    ax.add_patch(FancyArrow(L + 2, W / 2, 8, 0, width=1.2, head_length=3,
                            color='k', zorder=5))
    ax.text(L + 2, W / 2 + 2.5, 'nariz', fontsize=8)


def pecas(ax, d, alpha=0.85):
    for x, y, l, w, cor, rot in d.values():
        ax.add_patch(Rectangle((x, y), l, w, fc=cor, ec='#333', lw=0.9, alpha=alpha,
                               zorder=3))
        ax.text(x + l / 2, y + w / 2, rot, ha='center', va='center', fontsize=7,
                zorder=4)


def main():
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.4))

    placa(a1, 'Placa perfurada 130 × 30 mm — VISTA DE CIMA (sugestão; medidas em mm)')
    pecas(a1, TOPO)
    x, y, r = C1
    a1.add_patch(Circle((x, y), r, fc='#a1d99b', ec='#333', lw=0.9, zorder=3))
    a1.text(x, y, 'C1', ha='center', va='center', fontsize=7, zorder=4)
    a1.text(L + 1.5, 1.0, 'C1  1000 µF\nØ8 × 12, em pé', fontsize=6.5, zorder=4)
    a1.plot(*J1, marker='s', ms=6, c='#e6550d', zorder=4)
    a1.text(L + 1.5, 24.0, 'J1: fio da\nbateria (Molex)', fontsize=6.5, zorder=4)
    # zona da antena: nada de fio ou metal perto
    a1.add_patch(Rectangle((-8, 1.0), 8, 28, fc='none', ec='#d62728', ls='--', lw=1,
                           zorder=4))
    a1.text(-13.5, -6.5, 'antena: área livre\n(nada de fio/metal)', fontsize=7,
            color='#d62728')
    a1.text(0, -8.3, 'BMI160 com a seta Y apontando para o nariz e Z para cima '
            '(ver include/ahrs.h).  Placa por cima do frame; a nervura do frame '
            'cruza em x = 36 e x = 94.', fontsize=7)

    placa(a2, 'VISTA DE BAIXO (vista através da placa, mesma orientação da de cima)')
    pecas(a2, BAIXO)
    a2.text(0, -8.3, 'Embaixo ficam só a bateria e o sonar. Pés de pouso (19,5 mm) '
            'são mais altos que o sonar (~15 mm) e a bateria (8 mm): nada encosta '
            'no chão.', fontsize=7)

    fig.tight_layout()
    import os
    aqui = os.path.dirname(os.path.abspath(__file__))
    fig.savefig(os.path.join(aqui, 'layout_placa.png'), dpi=150)
    fig.savefig(os.path.join(aqui, 'layout_placa.svg'))
    print('layout_placa.png e layout_placa.svg gerados')


if __name__ == '__main__':
    main()
