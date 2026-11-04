#!/usr/bin/env python3
"""
Molde 1:1 (A4) do frame do drone em COMPENSADO, alternativa ao frame de PLA.

    python3 molde_compensado.py            # -> molde_compensado.pdf
    python3 molde_compensado.py --furo 9.9 # muda o furo do motor (mm)

Pecas (chapa de 3 mm):
  - BRACO A: inteiro, de motor a motor;
  - BRACO B: duas metades que encostam nas laterais do braco A, no centro;
  - 2 PLACAS DO CENTRO (O36 mm): uma em cima e uma embaixo do cruzamento,
    coladas nos dois bracos -> trava a junta e deixa os 4 motores no MESMO plano.

Mesmas medidas do frame de PLA: motores a 100,4 mm do centro (diagonal 200,8 mm),
helice de 75 mm, placa de O97 mm. Pagina 1 = molde 1:1; pagina 2 = montagem (1:2).
"""
import argparse
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Arc, Circle, Rectangle

P = dict(
    raio_motor=100.4,   # centro ao eixo do motor
    larg=12.0,          # largura do braco
    pad_d=17.0,         # ponta redonda em volta do motor
    furo=9.8,           # motor coreless 1020 (O10): entra justo
    placa_c=36.0,       # placas do centro
    chapa=3.0,          # espessura do compensado
    dens=0.6,           # g/cm3 (compensado comum)
    placa_d=97.0,       # placa de circuito
    helice=75.0,
)
A4 = (210.0, 297.0)
MM = 1 / 25.4
LW_CORTE = 0.9
LW_AUX = 0.5


def nova_pagina():
    fig = plt.figure(figsize=(A4[0] * MM, A4[1] * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4[0])
    ax.set_ylim(0, A4[1])
    ax.set_aspect('equal')
    ax.axis('off')
    return fig, ax


def furo_motor(ax, x, y, d):
    ax.add_patch(Circle((x, y), d / 2, fill=False, lw=LW_CORTE))
    for dx, dy in ((1, 0), (0, 1)):
        ax.plot([x - dx * (d / 2 + 2), x + dx * (d / 2 + 2)], [y - dy * (d / 2 + 2), y + dy * (d / 2 + 2)],
                lw=0.3, color='k')
    ax.text(x, y - d / 2 - 1.2, f'furo O{d:.1f}'.replace('.', ','), ha='center', va='top', fontsize=5.5)


def ponta(ax, x, y, ang_braco):
    """ponta redonda do braco; ang_braco = direcao em que o braco SAI da ponta (graus)"""
    r, w = P['pad_d'] / 2, P['larg'] / 2
    a = math.degrees(math.asin(w / r))          # meio angulo ocupado pelo braco
    ax.add_patch(Arc((x, y), 2 * r, 2 * r, theta1=ang_braco + a, theta2=ang_braco - a + 360,
                     lw=LW_CORTE))
    return math.sqrt(r * r - w * w)             # distancia do centro ate onde as laterais encostam


def braco(ax, x, y_ini, comprimento, duas_pontas, nome, sub):
    """braco vertical: ponta (motor) em y_ini; se duas_pontas, outra ponta em y_ini+comprimento"""
    w = P['larg'] / 2
    d0 = ponta(ax, x, y_ini, 90)
    furo_motor(ax, x, y_ini, P['furo'])
    if duas_pontas:
        y_fim = y_ini + comprimento
        d1 = ponta(ax, x, y_fim, -90)
        furo_motor(ax, x, y_fim, P['furo'])
        for s in (-1, 1):
            ax.plot([x + s * w, x + s * w], [y_ini + d0, y_fim - d1], lw=LW_CORTE, color='k')
        meio = (y_ini + y_fim) / 2
        # area do cruzamento (onde as metades do braco B encostam) e centro
        ax.add_patch(Rectangle((x - w, meio - w), 2 * w, 2 * w, fill=False, lw=LW_AUX, ls='--'))
        ax.plot([x - w - 3, x + w + 3], [meio, meio], lw=0.3, color='k')
        ax.text(x + w + 1.5, meio, 'centro\n(cola aqui as\nmetades do B)', fontsize=5, va='center')
    else:
        y_fim = y_ini + comprimento
        for s in (-1, 1):
            ax.plot([x + s * w, x + s * w], [y_ini + d0, y_fim], lw=LW_CORTE, color='k')
        ax.plot([x - w, x + w], [y_fim, y_fim], lw=LW_CORTE, color='k')
        ax.text(x, y_fim + 1.2, 'ponta reta: encosta\nna lateral do braco A', fontsize=5, ha='center', va='bottom')
    ax.text(x - w - 1.5, y_ini + comprimento * 0.45, f'{nome}\n{sub}', fontsize=7, rotation=90,
            ha='right', va='center', weight='bold')


def placa_centro(ax, x, y, nome):
    r = P['placa_c'] / 2
    ax.add_patch(Circle((x, y), r, fill=False, lw=LW_CORTE))
    w = P['larg'] / 2
    for ang in (45, 135):           # onde passam os bracos (em X)
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        tx, ty = -uy, ux
        for s in (-1, 1):
            x0, y0 = x + s * w * tx - r * ux * 0.98, y + s * w * ty - r * uy * 0.98
            x1, y1 = x + s * w * tx + r * ux * 0.98, y + s * w * ty + r * uy * 0.98
            ax.plot([x0, x1], [y0, y1], lw=LW_AUX, ls='--', color='k')
    ax.plot([x, x], [y + r - 4, y + r + 3], lw=0.8, color='k')
    ax.text(x, y + r + 3.5, 'FRENTE', fontsize=5.5, ha='center', va='bottom')
    ax.text(x, y - r - 1.5, nome, fontsize=6.5, ha='center', va='top', weight='bold')


def regua(ax, x, y):
    ax.plot([x, x + 100], [y, y], lw=0.8, color='k')
    for k in range(11):
        h = 3 if k % 5 == 0 else 1.6
        ax.plot([x + 10 * k, x + 10 * k], [y, y + h], lw=0.6, color='k')
        if k % 5 == 0:
            ax.text(x + 10 * k, y + 3.5, f'{10 * k}', fontsize=5.5, ha='center')
    ax.text(x + 50, y - 2.2, 'REGUA 100 mm: confira com uma regua antes de cortar (impressao em 100%, sem "ajustar")',
            fontsize=5.5, ha='center', va='top')


def pagina_molde(pdf):
    fig, ax = nova_pagina()
    R = P['raio_motor']
    ax.text(105, 288, 'Frame do drone VoaSul em compensado 3 mm: MOLDE 1:1', fontsize=10, ha='center',
            weight='bold')
    ax.text(105, 283, 'Linha cheia = corte | tracejado = referencia de colagem | cruz = centro do furo',
            fontsize=6.5, ha='center')
    regua(ax, 55, 14)
    # braco A (inteiro): motores em y0 e y0 + 2R
    y0 = 35.0
    braco(ax, 32, y0, 2 * R, True, 'BRACO A', '(1 peca)')
    # metades do braco B: do motor ate a lateral do braco A (R - larg/2)
    meio_b = R - P['larg'] / 2
    braco(ax, 68, y0, meio_b, False, 'BRACO B', '(metade 1)')
    braco(ax, 68, y0 + meio_b + 22, meio_b, False, 'BRACO B', '(metade 2)')
    # placas do centro
    placa_centro(ax, 130, 230, 'PLACA DO CENTRO (cima)')
    placa_centro(ax, 130, 175, 'PLACA DO CENTRO (baixo)')
    # resumo
    vol = ((2 * R + P['pad_d']) * P['larg'] + 2 * meio_b * P['larg'] + 2 * math.pi * (P['placa_c'] / 2) ** 2) \
        * P['chapa'] / 1000
    massa = vol * P['dens']
    txt = (f'Chapa: compensado {P["chapa"]:.0f} mm\n'
           f'Peso estimado: ~{massa:.0f} g (+~1 g de cola)\n'
           f'PLA atual: ~28 g\n\n'
           f'Motores a {R:.1f} mm do centro\n'
           f'(diagonal motor-motor {2 * R:.1f} mm)\n'
           f'Furo do motor O{P["furo"]:.1f}: broca de 10 mm e\n'
           f'teste; folgado -> volta de fita\n\n'
           f'Cortar: 1 braco A, 2 metades B,\n2 placas do centro\n'
           f'Montagem na pagina 2').replace('.', ',')
    ax.text(100, 140, txt, fontsize=7, va='top', family='DejaVu Sans',
            bbox=dict(boxstyle='square,pad=0.6', fc='none', ec='k', lw=0.5))
    pdf.savefig(fig)
    plt.close(fig)


def pagina_montagem(pdf):
    fig, ax = nova_pagina()
    ax.text(105, 288, 'Montagem do frame de compensado', fontsize=12, ha='center', weight='bold')
    ax.text(105, 282, 'Desenho em ESCALA 1:2 (metade do tamanho real): use as medidas escritas, nao a regua',
            fontsize=7, ha='center')
    s = 0.5
    cx, cy = 105, 190
    R = P['raio_motor'] * s
    w = P['larg'] / 2 * s
    # bracos em X
    for ang in (45, 135):
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        tx, ty = -uy, ux
        pts = [(cx + R * ux + w * tx, cy + R * uy + w * ty), (cx - R * ux + w * tx, cy - R * uy + w * ty),
               (cx - R * ux - w * tx, cy - R * uy - w * ty), (cx + R * ux - w * tx, cy + R * uy - w * ty)]
        ax.add_patch(plt.Polygon(pts, closed=True, fc='#e8d2a6', ec='k', lw=0.6))
    nomes = {(1, 1): ('FR', 'anti-horario'), (1, -1): ('RR', 'horario'), (-1, -1): ('RL', 'anti-horario'),
             (-1, 1): ('FL', 'horario')}
    for (sx, sy), (n, giro) in nomes.items():
        mx, my = cx + sx * R / math.sqrt(2), cy + sy * R / math.sqrt(2)
        ax.add_patch(Circle((mx, my), P['pad_d'] / 2 * s, fc='#e8d2a6', ec='k', lw=0.6))
        ax.add_patch(Circle((mx, my), 5 * s, fc='#777777', ec='k', lw=0.6))
        ax.add_patch(Circle((mx, my), P['helice'] / 2 * s, fill=False, ec='#3a6fc4', lw=0.6, ls=':'))
        ax.text(mx + sx * 4, my + sy * 13, f'{n}\n{giro}', fontsize=6.5, ha='center', va='center', weight='bold')
    ax.add_patch(Circle((cx, cy), P['placa_c'] / 2 * s, fc='#d9bf8c', ec='k', lw=0.6))
    ax.add_patch(Circle((cx, cy), P['placa_d'] / 2 * s, fill=False, ec='#0f6b4f', lw=1.0, ls='--'))
    ax.text(cx, cy + P['placa_d'] / 2 * s + 2, 'placa de circuito O97 (por cima)', fontsize=6, ha='center',
            color='#0f6b4f')
    ax.annotate('', xy=(cx, cy + 68), xytext=(cx, cy + 56), arrowprops=dict(arrowstyle='->', lw=1))
    ax.text(cx, cy + 69, 'FRENTE (lado do MT3608 da placa)', fontsize=7, ha='center', va='bottom', weight='bold')
    ax.text(cx + 52, cy - 46, f'{P["raio_motor"]:.1f} mm do centro\nao eixo do motor'.replace('.', ','),
            fontsize=6, ha='left')

    passos = [
        ('Antes', 'Imprima a pagina 1 em 100% (A4, sem "ajustar a pagina") e confira a regua de 100 mm. '
                  'Meca a chapa: o molde e para 3 mm; 4 mm tambem serve, so pesa mais.'),
        ('1. Molde', 'Cole o papel na chapa com cola bastao. Fure ANTES de cortar (a peca ainda firme): '
                     'broca fina de guia na cruz, depois a de 10 mm. Teste o motor: tem que entrar justo.'),
        ('2. Corte', 'Serrinha tico-tico ou estilete forte, varias passadas. Corte por FORA da linha e lixe ate ela. '
                     'As metades do braco B tem a ponta reta em esquadro: ela encosta na lateral do braco A.'),
        ('3. Colagem', 'Mesa plana com papel-manteiga. Braco A no meio, as metades do B encostadas nele formando '
                       'um X a 90 graus (use um esquadro). Cola de madeira ou epoxi na junta e nas duas placas do '
                       'centro (em cima e embaixo, seguindo o tracejado). Peso em cima ate secar.'),
        ('4. Conferir', 'Os 4 motores na MESMA altura e a mesma distancia do centro (diagonais iguais). '
                        'Frame torto faz o drone girar sozinho.'),
        ('5. Acabamento', 'Uma demao fina de verniz ou cola branca diluida: a madeira nao empena com umidade.'),
        ('6. Motores', 'Encaixe nos furos (FR e RL anti-horario, RR e FL horario, vistos de cima). Fios por cima '
                       'do braco com pontos de cola quente.'),
        ('7. Placa', 'Sobre a placa do centro de cima, 2 camadas de fita espuma (~3 mm). A placa de circuito fica '
                     'presa so no centro e SEM encostar nos bracos: embaixo dela, nas diagonais, ha soldas e os '
                     'MOSFETs. Corte rente as pontas dos pinos embaixo da placa.'),
        ('8. Bateria e pes', 'Bateria embaixo do cruzamento, com o velcro em volta do braco A. Pes: 4 pedacos de '
                             'EVA ou espuma embaixo dos bracos, ~15 mm antes de cada motor.'),
    ]
    y = 118
    for titulo, texto in passos:
        ax.text(14, y, titulo, fontsize=7.5, weight='bold', va='top')
        import textwrap
        linhas = textwrap.wrap(texto, 105)
        ax.text(42, y, '\n'.join(linhas), fontsize=6.8, va='top', linespacing=1.35)
        y -= 4.2 + 3.3 * len(linhas)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--furo', type=float, help='diametro do furo do motor, mm (padrao 9,8)')
    ap.add_argument('--chapa', type=float, help='espessura do compensado, mm (padrao 3)')
    ap.add_argument('-o', '--saida', default='molde_compensado.pdf')
    a = ap.parse_args()
    if a.furo:
        P['furo'] = a.furo
    if a.chapa:
        P['chapa'] = a.chapa
    with PdfPages(a.saida) as pdf:
        pagina_molde(pdf)
        pagina_montagem(pdf)
    print('molde salvo:', a.saida)


if __name__ == '__main__':
    main()
