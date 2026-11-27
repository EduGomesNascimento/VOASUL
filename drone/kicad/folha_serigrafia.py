"""Folha A4 para transferir a SERIGRAFIA no lado de CIMA da placa (lado dos componentes):
contornos e nomes das pecas, valor dos resistores, nome dos pinos dos conectores, os jumpers
numerados e um anel em cada furo (para alinhar com os furos ja feitos).

  Pagina 1: ESPELHADA, para a transferencia termica (papel virado para a placa).
  Pagina 2: normal, para ler e conferir.

Saida: saidas/folha_serigrafia_A4.pdf.  Roda com o Python do KiCad:  /usr/bin/python3 folha_serigrafia.py
"""
import io
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pcbnew
import pymupdf
from PIL import Image

import projeto as P

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, 'saidas')
PCB = os.path.join(AQUI, 'drone.kicad_pcb')
LADO = 104.0          # mm: quadrado em volta do disco de 97 mm
DPI = 1200
M = pcbnew.ToMM

PINOS = {  # nome dos pinos escrito ao lado de cada ilha
    'J1': {'1': '+', '2': '-'},
    'J2': {'1': 'GND', '2': 'ECHO B', '3': 'TRIG B', '4': 'ECHO F', '5': 'TRIG F', '6': '5V'},
    'J3': {'1': '3V3', '2': 'IR E', '3': 'IR D', '4': 'GND'},
    'J4': {'1': '3V3', '2': 'MISO', '3': 'GND', '4': 'SCK', '5': 'CS', '6': 'MOSI'},
    'U2': {'1': 'IN+', '2': 'IN-', '3': 'OUT+', '4': 'OUT-'},
}
NOME_MOTOR = {'M1': 'FR', 'M2': 'RR', 'M3': 'RL', 'M4': 'FL'}


def loc(v):
    return M(v.x) - 100.0, 100.0 - M(v.y)


def desenhar(ax, b):
    lw = lambda w: max(w, 0.15) * 72 / 25.4          # largura em mm -> pontos
    ax.add_patch(plt.Circle((0, 0), P.DISCO_D / 2, fill=False, lw=lw(0.2), color='k'))
    # contornos da serigrafia de cima (das pegadas e da placa)
    itens = [g for fp in b.GetFootprints() for g in fp.GraphicalItems()] + list(b.GetDrawings())
    for g in itens:
        if g.GetLayer() != pcbnew.F_SilkS or not isinstance(g, pcbnew.PCB_SHAPE):
            continue
        w = M(g.GetWidth())
        forma = g.GetShape()
        if forma == pcbnew.SHAPE_T_SEGMENT:
            (x1, y1), (x2, y2) = loc(g.GetStart()), loc(g.GetEnd())
            ax.plot([x1, x2], [y1, y2], 'k-', lw=lw(w), solid_capstyle='round')
        elif forma == pcbnew.SHAPE_T_CIRCLE:
            cx, cy = loc(g.GetCenter())
            ax.add_patch(plt.Circle((cx, cy), M(g.GetRadius()), fill=g.IsFilled(), lw=lw(w), color='k'))
        elif forma == pcbnew.SHAPE_T_ARC:
            cx, cy = loc(g.GetCenter())
            r = M(g.GetRadius())
            a0 = math.atan2(loc(g.GetStart())[1] - cy, loc(g.GetStart())[0] - cx)
            am = math.atan2(loc(g.GetArcMid())[1] - cy, loc(g.GetArcMid())[0] - cx)
            a1 = math.atan2(loc(g.GetEnd())[1] - cy, loc(g.GetEnd())[0] - cx)
            # vai de a0 a a1 passando por am
            d1 = (a1 - a0) % (2 * math.pi)
            if (am - a0) % (2 * math.pi) > d1:
                d1 -= 2 * math.pi
            t = np.linspace(a0, a0 + d1, 40)
            ax.plot(cx + r * np.cos(t), cy + r * np.sin(t), 'k-', lw=lw(w))
        elif forma in (pcbnew.SHAPE_T_RECT, pcbnew.SHAPE_T_POLY):
            pts = [loc(c) for c in (g.GetRectCorners() if forma == pcbnew.SHAPE_T_RECT else
                                    [g.GetPolyShape().CVertex(i) for i in range(g.GetPolyShape().TotalVertices())])]
            pts.append(pts[0])
            xs, ys = zip(*pts)
            if g.IsFilled():
                ax.fill(xs, ys, 'k')
            else:
                ax.plot(xs, ys, 'k-', lw=lw(w))
    # referencia (+ valor) de cada peca
    valor = {pc['ref']: pc['valor'] for pc in P.PECAS}
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        t = fp.Reference()
        if t.GetLayer() != pcbnew.F_SilkS:
            continue
        x, y = loc(t.GetPosition())
        h = max(M(t.GetTextHeight()), 1.1)
        ang = t.GetTextAngle().AsDegrees()
        if ang > 90.5 or ang < -90.5:
            ang -= 180
        txt = ref
        if ref[0] == 'R':
            txt = f'{ref} {valor[ref].replace("100", "100Ω")}'
        elif ref in NOME_MOTOR:
            txt = f'{ref} {NOME_MOTOR[ref]}'
        ax.text(x, y, txt, fontsize=h * 1.8, rotation=ang, ha='center', va='center',
                family='DejaVu Sans', weight='bold')
    # nome dos pinos dos conectores e do MT3608
    for fp in b.GetFootprints():
        nomes = PINOS.get(fp.GetReference())
        if not nomes:
            continue
        centro = [loc(p.GetPosition()) for p in fp.Pads()]      # origem da pegada pode ser o pino 1
        cx, cy = sum(c[0] for c in centro) / len(centro), sum(c[1] for c in centro) / len(centro)
        for p in fp.Pads():
            n = nomes.get(p.GetNumber())
            if not n:
                continue
            x, y = loc(p.GetPosition())
            dx, dy = x - cx, y - cy                         # afasta para fora da peca
            d = math.hypot(dx, dy) or 1.0
            if fp.GetReference() in ('J2', 'J3'):          # fileira: nome em pe, embaixo
                ax.text(x, y - 1.7, n, fontsize=1.8, rotation=90, ha='center', va='top', family='DejaVu Sans')
            elif fp.GetReference() == 'J4':                # 2x3: fileira de cima em cima, de baixo embaixo
                ax.text(x, y + (1.7 if dy > 0 else -1.7), n, fontsize=1.7, ha='center',
                        va='bottom' if dy > 0 else 'top', family='DejaVu Sans')
            else:
                ax.text(x + dx / d * 2.4, y + dy / d * 2.4, n, fontsize=1.9, ha='center', va='center',
                        family='DejaVu Sans')
    # anel em cada furo (pinos e jumpers): alinha a folha com os furos contra a luz
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and M(p.GetDrillSize().x) > 0:
                x, y = loc(p.GetPosition())
                ax.add_patch(plt.Circle((x, y), M(p.GetDrillSize().x) / 2 + 0.3, fill=False, lw=lw(0.15), color='k'))
    # jumpers: linha fina numerada (mesma ordem de saidas/jumpers.txt)
    js = sorted([t for t in b.GetTracks() if t.GetClass() != 'PCB_VIA' and t.GetLayer() == pcbnew.F_Cu],
                key=lambda t: t.GetNetname())
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            x, y = loc(t.GetPosition())
            ax.add_patch(plt.Circle((x, y), 0.75, fill=False, lw=lw(0.15), color='k'))
    for k, t in enumerate(js, 1):
        (x1, y1), (x2, y2) = loc(t.GetStart()), loc(t.GetEnd())
        ax.plot([x1, x2], [y1, y2], 'k-', lw=lw(0.35))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.add_patch(plt.Circle((mx, my), 1.15, color='w', zorder=3))
        ax.add_patch(plt.Circle((mx, my), 1.15, fill=False, lw=lw(0.2), color='k', zorder=4))
        ax.text(mx, my, str(k), fontsize=3.4, ha='center', va='center', weight='bold', zorder=5,
                family='DejaVu Sans')
    # frente
    ax.annotate('', xy=(0, 46.2), xytext=(0, 43.6), arrowprops=dict(arrowstyle='-|>', lw=0.6, color='k'))
    ax.text(3.2, 44.8, 'FRENTE', fontsize=3.2, ha='left', va='center', weight='bold', family='DejaVu Sans')


def imagem(b, espelhar):
    fig = plt.figure(figsize=(LADO / 25.4, LADO / 25.4), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-LADO / 2, LADO / 2)
    ax.set_ylim(-LADO / 2, LADO / 2)
    ax.set_aspect('equal')
    ax.axis('off')
    desenhar(ax, b)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=DPI, facecolor='white')
    plt.close(fig)
    im = Image.open(buf).convert('L').point(lambda v: 0 if v < 140 else 255, '1')   # so preto e branco
    if espelhar:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    out = io.BytesIO()
    im.save(out, format='PNG')
    return out.getvalue()


def pagina(doc, png, titulo, linhas):
    MM = 72 / 25.4
    p = doc.new_page(width=210 * MM, height=297 * MM)
    for i, y0 in enumerate((22, 136)):
        p.insert_image(pymupdf.Rect(53 * MM, y0 * MM, (53 + LADO) * MM, (y0 + LADO) * MM), stream=png)
        p.insert_text((14 * MM, (y0 + 52) * MM), f'COPIA {i + 1}', fontsize=9, fontname='hebo', rotate=90)
        for x, y in ((53, y0), (157, y0), (53, y0 + 104), (157, y0 + 104)):
            p.draw_line(((x - 3) * MM, y * MM), ((x + 3) * MM, y * MM), width=0.3)
            p.draw_line((x * MM, (y - 3) * MM), (x * MM, (y + 3) * MM), width=0.3)
    y = 252
    p.draw_line((55 * MM, y * MM), (155 * MM, y * MM), width=0.8)
    for k in range(11):
        h = 3 if k % 5 == 0 else 1.6
        p.draw_line(((55 + 10 * k) * MM, y * MM), ((55 + 10 * k) * MM, (y - h) * MM), width=0.6)
    p.insert_text((55 * MM, (y + 4) * MM), 'REGUA 100 mm - tem que dar 100 mm exatos', fontsize=7.5)
    p.insert_text((14 * MM, 264 * MM), titulo, fontsize=9, fontname='hebo')
    for k, t in enumerate(linhas):
        p.insert_text((14 * MM, (269.2 + 5.2 * k) * MM), t, fontsize=8.2)


def main():
    b = pcbnew.LoadBoard(PCB)
    doc = pymupdf.open()
    pagina(doc, imagem(b, True), 'DRONE VoaSul - SERIGRAFIA do lado de CIMA (componentes), 1:1, JA ESPELHADA',
           ['1) Impressora LASER, escala 100%. NAO espelhe de novo: os nomes aparecem AO CONTRARIO no papel.',
            '2) Passe DEPOIS de corroer e furar. Alinhe os aneis com os furos olhando contra a luz.',
            '3) Toner virado para o lado SEM cobre; ferro um pouco mais frio, 1-2 min, sem arrastar.',
            '4) Opcional: se nao pegar bem, use a pagina 2 impressa normal como guia de montagem.'])
    pagina(doc, imagem(b, False), 'DRONE VoaSul - lado de CIMA visto de cima (para ler e conferir)',
           ['Mesmo desenho da pagina 1, sem espelhar. Numeros nos circulos = jumpers (saidas/jumpers.txt).',
            'Aneis = furos. Resistores com o valor ao lado do nome. Conectores com o nome de cada pino.'])
    saida = os.path.join(OUT, 'folha_serigrafia_A4.pdf')
    doc.save(saida, deflate=True)
    print('salvo:', saida)


if __name__ == '__main__':
    main()
