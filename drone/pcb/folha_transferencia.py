#!/usr/bin/env python3
"""
Monta a folha de transferencia termica (toner) a partir dos PDFs que o Proteus
exporta da placa -- em escala 1:1, pronta para imprimir em A4.

    pip install pymupdf
    python3 folha_transferencia.py TOP.PDF BOTTOM.PDF MONTAGEM.PDF -o folha.pdf

Os tres PDFs de entrada sao exportados do PCB Layout VISTOS DE CIMA (o padrao
do Proteus). O script confere isso pelos furos: se as duas faces nao baterem
sem espelhar, ele para e avisa.

Por que uma face vai espelhada e a outra nao:

  - O papel vai DE CARA PARA BAIXO sobre o cobre, entao o que sai no cobre e o
    espelho do que esta no papel.
  - Face de CIMA: queremos no cobre a vista de cima. Logo o papel leva o
    espelho dela.
  - Face de BAIXO: olhando a placa por baixo, o cobre e o espelho da vista de
    cima; o papel (espelhado de novo ao transferir) leva a vista de cima como
    esta. Logo, sem espelhar.

Regra pratica que nao depende de lembrar disso: NO PAPEL, TODO TEXTO DE COBRE
TEM DE APARECER AO CONTRARIO.
"""

import argparse
import re

import pymupdf

MM = 72 / 25.4                      # pontos por mm
A4 = (210 * MM, 297 * MM)


def furos(pg):
    """Centros dos furos (circulos brancos pequenos), em pontos."""
    out = []
    for p in pg.get_drawings():
        if p.get('fill') == (1.0, 1.0, 1.0) and p['rect'].width < 10:
            r = p['rect']
            out.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    return out


def confere_vista(top, bot):
    """As duas faces exportadas na mesma vista (de cima) tem os furos no mesmo
    lugar. Se so baterem espelhando, a de baixo veio vista por baixo."""
    a, b = furos(top), furos(bot)
    W = bot.rect.width
    def casa(pa, pb):
        return sum(1 for (x, y) in pa if any(abs(x - u) < 0.5 and abs(y - v) < 0.5
                                             for (u, v) in pb))
    direto = casa(a, b)
    espelho = casa(a, [(W - x, y) for (x, y) in b])
    if not a:
        return 'sem furos para conferir'
    if direto >= 0.9 * len(a):
        return f'{direto}/{len(a)} furos batem: as duas faces estão vistas de cima'
    if espelho >= 0.9 * len(a):
        raise SystemExit('A face de BAIXO foi exportada vista por baixo (espelhada). '
                         'Exporte de novo vista de cima, ou troque a regra de espelhamento.')
    raise SystemExit(f'Os furos não batem ({direto}/{len(a)}): confira se são da mesma placa.')


def cola(pagina, src, x_mm, y_mm, espelhar=False):
    """Cola a pagina `src` em 1:1 com o canto superior esquerdo em (x_mm, y_mm).
    Espelhar e feito trocando a matriz do XObject no fluxo de conteudo: o
    pymupdf nao espelha direto, e assim continua tudo vetorial."""
    w, h = src.rect.width, src.rect.height
    r = pymupdf.Rect(x_mm * MM, y_mm * MM, x_mm * MM + w, y_mm * MM + h)
    pagina.show_pdf_page(r, src.parent, src.number)
    if not espelhar:
        return r
    # O pymupdf grava so "q /fzFrmN Do Q": a escala fica no proprio XObject.
    # Espelhar = inserir antes do Do uma matriz que reflete em torno do eixo
    # vertical que passa pelo centro do quadro (x' = 2*cx - x).
    xref = pagina.get_contents()[-1]
    doc = pagina.parent
    s = doc.xref_stream(xref).decode('latin-1')
    m = list(re.finditer(r'/(\w+) Do', s))
    if not m:
        raise SystemExit('não achei o XObject colado para espelhar')
    g = m[-1]
    cx = (r.x0 + r.x1) / 2
    s = s[:g.start()] + f'-1 0 0 1 {2 * cx:.4f} 0 cm ' + s[g.start():]
    doc.update_stream(xref, s.encode('latin-1'))
    return r


def cruzes(pagina, r, braco=3):
    """Cruzes de registro nos 4 cantos -- simetricas, entao continuam no lugar
    com ou sem espelhamento. Servem para alinhar as duas folhas."""
    for x, y in ((r.x0, r.y0), (r.x1, r.y0), (r.x0, r.y1), (r.x1, r.y1)):
        pagina.draw_line((x - braco * MM, y), (x + braco * MM, y), width=0.2 * MM)
        pagina.draw_line((x, y - braco * MM), (x, y + braco * MM), width=0.2 * MM)


def regua(pagina, x_mm, y_mm, comp=100):
    """Regua de conferencia de escala, com marcas a cada 10 mm."""
    pagina.draw_line((x_mm * MM, y_mm * MM), ((x_mm + comp) * MM, y_mm * MM), width=0.3 * MM)
    for k in range(0, comp + 1, 10):
        alt = 3 if k % 50 == 0 else 1.8
        pagina.draw_line(((x_mm + k) * MM, y_mm * MM), ((x_mm + k) * MM, (y_mm - alt) * MM),
                         width=0.25 * MM)
    txt(pagina, x_mm, y_mm + 4.2, f'{comp} mm — meça com régua. Se não der {comp} mm exatos, '
        'a impressora escalou: reimprima em "Tamanho real".', 7.5)


def txt(pagina, x_mm, y_mm, s, fs=8, negrito=False):
    # a Helvetica embutida no PDF nao tem travessao nem marcador
    s = s.replace('—', '-').replace('–', '-').replace('•', '-')
    pagina.insert_text((x_mm * MM, y_mm * MM), s, fontsize=fs,
                       fontname='hebo' if negrito else 'helv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('top')
    ap.add_argument('bottom')
    ap.add_argument('montagem', nargs='?')
    ap.add_argument('-o', '--saida', default='folha_transferencia.pdf')
    args = ap.parse_args()

    top = pymupdf.open(args.top)[0]
    bot = pymupdf.open(args.bottom)[0]
    print('  ' + confere_vista(top, bot))

    w_mm = top.rect.width / MM
    x0 = (210 - w_mm) / 2
    out = pymupdf.open()

    # ---------- folha 1: as duas faces de cobre ----------
    p = out.new_page(width=A4[0], height=A4[1])
    txt(p, 12, 12, 'DRONE — FOLHA DE TRANSFERÊNCIA TÉRMICA (cobre, dupla face, 1:1)', 11, True)
    txt(p, 12, 17.5, 'Imprima em 100% / "Tamanho real" — NUNCA "ajustar à página". '
        'Impressora a LASER, papel glossy ou fotográfico, preto puro.', 8)

    txt(p, x0 + 5, 26, '1) FACE DE CIMA (TOP) — ESPELHADA', 9, True)
    txt(p, x0 + 5, 30, 'Confira: no papel, todo texto de cobre tem que sair AO CONTRÁRIO.', 7.5)
    r1 = cola(p, top, x0, 32, espelhar=True)
    cruzes(p, r1)

    y2 = 32 + w_mm + 9
    txt(p, x0 + 5, y2 - 5, '2) FACE DE BAIXO (BOTTOM) — NORMAL, sem espelhar', 9, True)
    txt(p, x0 + 5, y2 - 1.2, 'Vista de cima, como o Proteus exportou. O texto também sai AO CONTRÁRIO no papel.', 7.5)
    r2 = cola(p, bot, x0, y2, espelhar=False)
    cruzes(p, r2)

    regua(p, (210 - 100) / 2, y2 + w_mm + 9)
    txt(p, 12, 287, 'Alinhar as faces: ponha as duas folhas toner contra toner, contra a luz, até os furos '
        'e as cruzes coincidirem; prenda com fita e enfie a placa no meio.', 7)

    # ---------- folha 2: montagem ----------
    if args.montagem:
        mont = pymupdf.open(args.montagem)[0]
        p = out.new_page(width=A4[0], height=A4[1])
        txt(p, 12, 12, 'DRONE — GUIA DE MONTAGEM (vista de cima, 1:1, NÃO espelhado)', 11, True)
        txt(p, 12, 17.5, 'Para conferir a posição de cada peça na hora de soldar. '
            'Não é para transferir.', 8)
        r3 = cola(p, mont, x0, 26, espelhar=False)
        cruzes(p, r3)
        notas = [
            'Polaridade — confira antes de soldar:',
            '  • C1 (1000 µF) e C6 (470 µF): perna + no lado marcado "+". Invertido, esquenta e estoura.',
            '  • D1–D4 (SS34): a faixa no corpo é o catodo, vai no VBAT.',
            '  • U2–U5 (AO3400A, marca A09T): perna sozinha = dreno; das duas, porta e fonte.',
            '  • ESP32: confira de que lado ficam o 3V3 e o 5V antes de soldar a barra — virado, o 5V cai num GPIO.',
            'Antes de ligar o ESP32: step-up (U1) ajustado em 5,0 V no multímetro.',
        ]
        y = 26 + w_mm + 10
        for i, n in enumerate(notas):
            txt(p, x0 - 20, y + i * 5, n, 8.5, i == 0)
        regua(p, (210 - 100) / 2, y + len(notas) * 5 + 8)

    out.save(args.saida, garbage=3, deflate=True)
    print(f'  {args.saida}: {len(out)} folha(s) A4')


if __name__ == '__main__':
    main()
