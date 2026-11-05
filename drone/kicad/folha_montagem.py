#!/usr/bin/env python3
"""
Folha de MONTAGEM do drone (A4, 3 paginas), a partir de saidas/montagem.json
(gerado por extrair_montagem.py com o Python do KiCad).

  pag. 1  EM CIMA: pecas, valores, pino 1, polaridade, jumpers numerados
  pag. 2  EMBAIXO (vista por baixo): MOSFETs, diodos e capacitores SMD
  pag. 3  lista de pecas e ordem de montagem
"""
import json
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyBboxPatch, Polygon

AQUI = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(AQUI, 'saidas', 'montagem.json')))
NJ = len(D['jumpers'])
NJ_GND = sum(1 for j in D['jumpers'] if j['rede'] == 'GND')
_c = os.path.join(AQUI, 'saidas', 'conferencia.txt')     # escrito pela etapa 'saidas'
CONF = open(_c).read().strip() if os.path.exists(_c) else 'ver CONFERENCIA.md'
A4 = (210, 297)
MM = 1 / 25.4
VERDE, LARANJA, CINZA, TINTA, AZUL = '#0f6b4f', '#c4501a', '#9aa39d', '#17201b', '#1d5fa8'

PINOS = {  # nome de cada pino nos conectores e modulos (para escrever na folha)
    'J2': ['GND', 'ECHO B', 'TRIG B', 'ECHO F', 'TRIG F', '5V'],
    'J3': ['3V3', 'IR E', 'IR D', 'GND'],
    'J4': ['3V3', 'MISO', 'SCK', 'MOSI', 'CS', 'GND'],
    'U2': {'1': 'IN+', '2': 'IN-', '3': 'OUT+', '4': 'OUT-'},
    'U3': ['VIN', '3V3', 'GND', 'SCL', 'SDA', 'CS', 'SAO'],
    'U4': ['VCC', 'GND', 'SCL', 'SDA', 'CSB', 'SDO'],
}


def pagina(titulo, sub):
    fig = plt.figure(figsize=(A4[0] * MM, A4[1] * MM))
    fig.text(0.07, 0.955, titulo, fontsize=17, weight='bold', color=TINTA, family='DejaVu Sans')
    fig.text(0.07, 0.935, sub, fontsize=8, color='#5d6a62', family='DejaVu Sans')
    return fig


def eixo_placa(fig, espelhar=False):
    # 180 x 180 mm de desenho para +-56 mm de placa -> ampliado 1,6x
    ax = fig.add_axes([15 / 210, 80 / 297, 180 / 210, 180 / 297])
    ax.set_xlim(56, -56) if espelhar else ax.set_xlim(-56, 56)
    ax.set_ylim(-56, 56)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.add_patch(Circle((0, 0), D['raio'], fill=False, lw=1.4, ec=TINTA))
    return ax


def pad(ax, p, cor, cheio=False, lw=0.6, alpha=1.0):
    c, s = math.cos(math.radians(p['rot'])), math.sin(math.radians(p['rot']))
    w, h = p['w'], p['h']
    if p['forma'] == 'c':
        ax.add_patch(Circle((p['x'], p['y']), w / 2, fc=cor if cheio else 'white', ec=cor, lw=lw, alpha=alpha))
    else:
        pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
        pts = [(p['x'] + x * c - y * s, p['y'] + x * s + y * c) for x, y in pts]
        ax.add_patch(Polygon(pts, closed=True, fc=cor if cheio else 'white', ec=cor, lw=lw, alpha=alpha))
    if p['furo'] > 0:
        ax.add_patch(Circle((p['x'], p['y']), p['furo'] / 2, fc='white', ec=cor, lw=0.3, alpha=alpha))


def contorno(ax, pc, cor, lw=0.8, ls='-', alpha=1.0):
    for f in pc['fab']:
        if f['c'] != 'fab':
            continue
        if f['t'] == 'seg':
            xs, ys = zip(*f['p'])
            ax.plot(xs, ys, color=cor, lw=lw, ls=ls, alpha=alpha, solid_capstyle='round')
        elif f['t'] == 'circ':
            ax.add_patch(Circle(f['p'][0], f['r'], fill=False, ec=cor, lw=lw, ls=ls, alpha=alpha))
        elif f['t'] == 'poly':
            ax.add_patch(Polygon(f['p'], closed=True, fill=False, ec=cor, lw=lw, ls=ls, alpha=alpha))


def rotulo(ax, pc, dx=0, dy=0, valor=True, cor=TINTA, tam=6.2):
    txt = pc['ref'] + (f"\n{pc['valor']}" if valor else '')
    ax.text(pc['x'] + dx, pc['y'] + dy, txt, ha='center', va='center', fontsize=tam, weight='bold', color=cor,
            linespacing=0.95, family='DejaVu Sans',
            bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85))


def pagina_cima(pdf):
    fig = pagina('Montagem: lado de CIMA (componentes)',
                 'Ampliado 1,6x (não use para medir). Visto de cima, frente para cima. '
                 'Vermelho = jumper (fio rígido por cima), soldado embaixo.')
    ax = eixo_placa(fig)
    ax.annotate('FRENTE', xy=(0, 55), xytext=(0, 50.5), ha='center', fontsize=7, weight='bold',
                arrowprops=dict(arrowstyle='->', lw=1))
    for pc in D['pecas']:                         # pecas de baixo: so a sombra
        if pc['lado'] == 'B':
            contorno(ax, pc, CINZA, lw=0.5, ls=':')
    for pc in D['pecas']:
        if pc['lado'] != 'F':
            continue
        sob = pc['ref'] in ('U3', 'U4')
        contorno(ax, pc, AZUL if sob else TINTA, lw=0.6 if sob else 0.9, ls='--' if sob else '-')
        for p in pc['pads']:
            pino1 = p['n'] == '1' and pc['ref'][0] in 'JUC' and pc['ref'] not in ('U1',)
            pad(ax, p, VERDE if pino1 else '#55605a', cheio=pino1, lw=0.5)
    # rotulos com ajuste fino
    desl = {'U1': (0, 6.5), 'U2': (0, 0), 'U3': (0, 4.8), 'U4': (0, 4.2), 'J1': (0, -4.2), 'J2': (6, -5.2),
            'J3': (0, 4.2), 'J4': (6, -5.2), 'C1': (0, -6.0), 'C2': (1.5, -6.2)}
    for pc in D['pecas']:
        if pc['lado'] != 'F':
            continue
        dx, dy = desl.get(pc['ref'], (0, 0))
        if pc['ref'][0] == 'R':
            dx, dy = 0, 3.6 if pc['y'] >= 0 else -3.6
            if pc['ref'] in ('R9', 'R10'):
                dx, dy = -5.5, 0
        if pc['ref'][0] == 'M':
            dx, dy = (-5 if pc['x'] > 0 else 5), 0
        if pc['ref'] == 'U1':
            rotulo(ax, pc, 0, 7.5, valor=False, tam=9)
            ax.text(pc['x'], pc['y'] + 3.6, 'ESP32 nas barras fêmea', ha='center', fontsize=5.5, color=TINTA)
            continue
        if pc['ref'] in ('U3', 'U4'):
            rotulo(ax, pc, dx, dy, cor=AZUL, tam=5.6)
            continue
        rotulo(ax, pc, dx, dy, tam=5.6 if pc['ref'][0] in 'RC' else 6.2)
    # nomes de pinos
    for pc in D['pecas']:
        nomes = PINOS.get(pc['ref'])
        if not nomes:
            continue
        for p in pc['pads']:
            n = nomes[p['n']] if isinstance(nomes, dict) else nomes[int(p['n']) - 1]
            off = -2.6 if pc['ref'] in ('J2', 'J4', 'U3', 'U4') else 2.6
            if pc['ref'] == 'U2':
                off = -3.2 if p['y'] > pc['y'] else 3.2
            ax.text(p['x'], p['y'] + off, n, ha='center', va='center', fontsize=3.6, color=VERDE, rotation=0,
                    weight='bold')
    # polaridade
    for pc in D['pecas']:
        if pc['ref'] in ('C1', 'C2', 'J1') or pc['ref'][0] == 'M':
            p1 = next(p for p in pc['pads'] if p['n'] == '1')
            ax.text(p1['x'], p1['y'] + 2.6 if pc['ref'] != 'C1' else p1['y'] - 2.8, '+', ha='center', va='center',
                    fontsize=8, weight='bold', color=LARANJA)
    u1 = next(pc for pc in D['pecas'] if pc['ref'] == 'U1')
    ax.text(u1['x'] - 25.5, u1['y'], '← ANTENA', fontsize=5.5, va='center', ha='left', color=TINTA, weight='bold')
    ax.text(u1['x'] + 25.5, u1['y'], 'USB →', fontsize=5.5, va='center', ha='right', color=TINTA, weight='bold')
    ax.text(u1['x'] - 22.9, u1['y'] - 9.6, 'pino 1\n(3V3)', fontsize=4.2, ha='center', color=VERDE)
    # jumpers
    for k, j in enumerate(D['jumpers'], 1):
        (x1, y1), (x2, y2) = j['a'], j['b']
        cor = '#d62728' if j['rede'] == 'GND' else '#9c27b0'
        ax.plot([x1, x2], [y1, y2], color=cor, lw=2.2, solid_capstyle='round', alpha=0.85)
        for x, y in ((x1, y1), (x2, y2)):
            ax.add_patch(Circle((x, y), 1.0, fc='white', ec=cor, lw=1))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.add_patch(Circle((mx, my), 1.9, fc=cor, ec='white', lw=0.6))
        ax.text(mx, my, str(k), ha='center', va='center', fontsize=5.2, color='white', weight='bold')
    leg = [('pino 1 (quadrado verde)', VERDE), ('+  polaridade', LARANJA), ('jumper de GND (fio 20–22 AWG)', '#d62728'),
           ('jumper de sinal (fio fino)', '#9c27b0'), ('embaixo do ESP32 (BMI160/BMP280)', AZUL),
           ('peça SMD do lado de baixo', CINZA)]
    for k, (t, c) in enumerate(leg):
        fig.text(0.08 + (k % 2) * 0.43, 0.245 - (k // 2) * 0.018, '■ ' + t, color=c, fontsize=7.2,
                 family='DejaVu Sans', weight='bold')
    fig.text(0.08, 0.185,
             'Jumpers (de-para em mm, a partir do centro): ver saidas/jumpers.txt. Numeração igual nos dois.\n'
             'Solde TODOS os jumpers e o BMI160/BMP280 ANTES de colocar as barras fêmea do ESP32.\n'
             'U3/U4 (azul) ficam EMBAIXO do ESP32, soldados com barra macho baixa (pinos cortados rente).',
             fontsize=7.4, family='DejaVu Sans', linespacing=1.5, va='top')
    pdf.savefig(fig)
    plt.close(fig)


def desenho_baixo(ax, zoom=False):
    for ang in (45, 135):                         # raios do frame / bracos de madeira
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        tx, ty = -uy, ux
        pts = [(48 * ux + 4 * tx, 48 * uy + 4 * ty), (-48 * ux + 4 * tx, -48 * uy + 4 * ty),
               (-48 * ux - 4 * tx, -48 * uy - 4 * ty), (48 * ux - 4 * tx, 48 * uy - 4 * ty)]
        ax.add_patch(Polygon(pts, closed=True, fc='#efe6d3', ec='none', zorder=0))
    for pc in D['pecas']:
        for p in pc['pads']:
            if p['furo'] > 0:
                pad(ax, p, CINZA, lw=0.4, alpha=0.6)
        if zoom and pc['lado'] == 'F' and pc['ref'][0] in 'RM':
            ax.text(pc['x'], pc['y'], pc['ref'], ha='center', va='center', fontsize=6, color=CINZA, weight='bold')
    t_pad = 7 if zoom else 4.2
    for pc in D['pecas']:
        if pc['lado'] != 'B':
            continue
        contorno(ax, pc, TINTA, lw=1.2 if zoom else 0.9)
        for p in pc['pads']:
            pad(ax, p, VERDE, cheio=True, lw=0.4)
        if pc['ref'][0] == 'Q':
            for p in pc['pads']:
                ax.text(p['x'], p['y'], {'1': 'G', '2': 'S', '3': 'D'}[p['n']], ha='center', va='center',
                        fontsize=t_pad, color='white', weight='bold')
        if pc['ref'][0] == 'D':
            k = next(p for p in pc['pads'] if p['n'] == '1')
            ax.add_patch(Circle((k['x'], k['y']), 0.9, fc=LARANJA, ec='none'))
            ax.text(k['x'], k['y'], 'K', ha='center', va='center', fontsize=t_pad, color='white', weight='bold')
        if pc['ref'][0] == 'C' and zoom:
            for p in pc['pads']:
                ax.text(p['x'], p['y'], {'1': 'VBAT', '2': 'dreno'}[p['n']], ha='center', va='center',
                        fontsize=4.5, color='white', weight='bold')
        r = math.hypot(pc['x'], pc['y'])
        ux, uy = pc['x'] / r, pc['y'] / r
        if zoom:
            rotulo(ax, pc, -ux * 3.2, -uy * 3.2, tam=7)
        else:
            rotulo(ax, pc, -ux * 4.5, -uy * 4.5, tam=5.8)


def pagina_baixo(pdf):
    fig = pagina('Montagem: lado de BAIXO (cobre, SMD)',
                 'Visto POR BAIXO (placa virada): é como você vai olhar ao soldar. Ampliado 1,6x. '
                 'Faixa bege = braço do frame (2 mm de vão).')
    ax = eixo_placa(fig, espelhar=True)
    desenho_baixo(ax)
    # detalhe ampliado de um canto (os 4 sao iguais, so giram)
    q1 = next(pc for pc in D['pecas'] if pc['ref'] == 'Q1')
    cx, cy = q1['x'] * 1.13, q1['y'] * 1.13
    axz = fig.add_axes([0.50, 0.03, 0.45, 0.235])
    axz.set_xlim(cx + 12.5, cx - 12.5)
    axz.set_ylim(cy - 8.5, cy + 8.5)
    axz.set_aspect('equal')
    axz.set_xticks([]); axz.set_yticks([])
    for sp in axz.spines.values():
        sp.set_color(TINTA); sp.set_linewidth(1)
    desenho_baixo(axz, zoom=True)
    axz.set_title('Detalhe do canto FR (ampliado ~5x, visto por baixo)', fontsize=7.5, weight='bold')
    ax.add_patch(Circle((cx, cy), 10, fill=False, ec=TINTA, lw=0.8, ls='--'))
    fig.text(0.07, 0.255,
             'Q1–Q4  AO3400A (SOT-23): G = porta, S = fonte (GND),\n'
             '            D = dreno (motor). Marcação A09T para cima.\n'
             'D1–D4  SS34: a FAIXA do diodo (catodo, K) vai na ilha K,\n'
             '            a de FORA (anel de VBAT).\n'
             'C3–C6  100 nF 0805: sem polaridade.\n\n'
             'Como soldar SMD: fluxo na ilha, estanhe UMA ilha,\n'
             'posicione com a pinça, solde esse pino, alinhe,\n'
             'solde o resto. Depois: bip entre os pinos do\n'
             'SOT-23 (não pode ter ponte).\n\n'
             'Pontas dos pinos sobre a faixa do braço:\n'
             'corte rente (até 1,5 mm).',
             fontsize=7.4, family='DejaVu Sans', linespacing=1.45, va='top')
    pdf.savefig(fig)
    plt.close(fig)


def pagina_lista(pdf):
    fig = pagina('Lista de peças e ordem de montagem', 'Confira cada valor com o multímetro antes de soldar.')
    linhas = [
        ('Ordem', 'Ref.', 'Peça', 'Cuidado'),
        ('1', 'Q1–Q4', 'MOSFET AO3400A (SOT-23)', 'embaixo; G-S-D como na pág. 2'),
        ('2', 'D1–D4', 'Diodo SS34', 'embaixo; faixa (K) para fora'),
        ('3', 'C3–C6', '100 nF 0805', 'embaixo; sem polaridade'),
        ('4', f'1–{NJ}', 'Jumpers (fio rígido)', f'{NJ_GND} de GND (fio grosso), {NJ - NJ_GND} de sinal'),
        ('5', 'U4', 'GY-BMP280-3.3', 'barra macho baixa, embaixo do ESP32'),
        ('6', 'U3', 'GY-BMI160', 'barra macho baixa, embaixo do ESP32; VIN solto'),
        ('7', 'R1–R4', '100 Ω (porta)', 'em pé; 100–220 Ω servem'),
        ('7', 'R5–R10', '10 kΩ (pull-down e divisor)', 'em pé; R9/R10 = divisor da bateria'),
        ('7', 'R11, R12', '1 kΩ (ECHO)', 'em pé'),
        ('7', 'R13, R14', '2 kΩ (ECHO)', 'em pé; 1k8 ou 2k2 também servem'),
        ('8', 'U1', 'Barras fêmea 2×19 do ESP32', 'solde com o ESP32 encaixado, para alinhar'),
        ('9', 'J2, J3, J4', 'Barra macho 1×6, 1×4 e 1×6', 'sonar (J2), IR (J3), fluxo óptico (J4, opcional)'),
        ('10', 'C1', '1000 µF 10–16 V', 'POLARIDADE: listra = negativo, + na ilha marcada'),
        ('10', 'C2', '470 µF 10–16 V', 'POLARIDADE'),
        ('11', 'U2', 'MT3608 em 4 pernas de fio', 'confira IN+/IN-/OUT+/OUT-; 5,0 V antes do ESP32'),
        ('12', 'J1', 'Rabicho Molex da bateria', '+ (vermelho) na ilha quadrada, a de fora'),
        ('13', 'M1–M4', 'Fios dos motores', '+ na ilha quadrada; por último'),
    ]
    y = 0.885
    for k, (o, r, p, c) in enumerate(linhas):
        peso = 'bold' if k == 0 else 'normal'
        cor = '#5d6a62' if k == 0 else TINTA
        for x, t in ((0.08, o), (0.15, r), (0.29, p), (0.60, c)):
            fig.text(x, y, t, fontsize=8.2, weight=peso if x != 0.15 else 'bold', color=cor, family='DejaVu Sans')
        y -= 0.026
        fig.add_artist(plt.Line2D([0.08, 0.93], [y + 0.016, y + 0.016], color='#d7ded8', lw=0.6))
    fig.text(0.08, y - 0.02, 'O que NÃO está na folha de cobre (e você precisa fazer):', fontsize=10, weight='bold',
             color=LARANJA, family='DejaVu Sans')
    extra = [
        f'{NJ} jumpers por cima: sem eles a placa NÃO funciona (pág. 1 e jumpers.txt).',
        'Fios para fora da placa: bateria (J1), 4 motores (M1–M4), cabos do sonar (J2) e do IR (J3).',
        'J4 (fluxo óptico PMW3901) é OPCIONAL: solde a barra mesmo sem o módulo; o drone voa igual.',
        '   Ligue/desligue o módulo só com o drone DESLIGADO. O firmware descobre sozinho no boot.',
        'Os módulos (ESP32, MT3608, BMI160, BMP280) fazem parte do circuito: o GND do pino 26 do ESP32',
        '   chega pelo próprio ESP32. Teste de continuidade do GND dos sensores: só com o ESP32 encaixado.',
        f'Conferido no KiCad: esquema × placa sem diferenças ({CONF}) e DRC sem erros.',
    ]
    for k, t in enumerate(extra):
        fig.text(0.08, y - 0.05 - 0.024 * k, ('• ' if not t.startswith('   ') else '  ') + t.strip(), fontsize=8.2,
                 family='DejaVu Sans')
    pdf.savefig(fig)
    plt.close(fig)


if __name__ == '__main__':
    saida = os.path.join(AQUI, 'saidas', 'folha_montagem.pdf')
    with PdfPages(saida) as pdf:
        pagina_cima(pdf)
        pagina_baixo(pdf)
        pagina_lista(pdf)
    print('salvo:', saida)
