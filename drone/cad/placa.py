#!/usr/bin/env python3
"""
Monta todas as pecas numa unica placa de impressao.

    python3 placa.py                    # tudo: placa_impressao.stl
    python3 placa.py --essencial        # so o que vale o peso (ver suportes.py)
    python3 placa.py --helices          # inclui 2 CCW + 2 CW (so bancada!)
    python3 placa.py --mesa 180 180     # confere contra outra mesa

Cada peca ja sai apoiada em z = 0, na orientacao certa, separada das outras.
Abra no fatiador e mande imprimir: **nao precisa de suporte em nenhuma delas**.

Foi para isso que os pes de pouso sairam de dentro do frame. Integrados, eles
apontam para baixo e poriam o frame 20 mm no ar, exigindo suporte sob a base e
os bracos inteiros -- muito material e uma face inferior arruinada. Soltos,
imprimem em pe e colam depois.
"""

import argparse
import math

import frame
import helice
import suportes
from frame import volume, write_stl


def bbox(tris):
    xs = [v[0] for t in tris for v in t]
    ys = [v[1] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def move(tris, dx, dy, dz):
    return [[(v[0] + dx, v[1] + dy, v[2] + dz) for v in t] for t in tris]


def arrange(pecas, bed_x, bed_y, gap=6.0):
    """Empacotamento por prateleiras: ordena pela profundidade e vai enfileirando,
    quebrando linha quando nao cabe mais. Simples e suficiente para 8 pecas."""
    itens = []
    for nome, tris in pecas:
        lo, hi = bbox(tris)
        itens.append([nome, tris, hi[0] - lo[0], hi[1] - lo[1], lo])
    itens.sort(key=lambda i: -i[3])           # mais fundo primeiro

    out, x, y, linha = [], gap, gap, 0.0
    for nome, tris, w, d, lo in itens:
        if x + w + gap > bed_x:               # quebra a linha
            x, y, linha = gap, y + linha + gap, 0.0
        if y + d + gap > bed_y:
            raise SystemExit(f"nao cabe na mesa: {nome} nao entra em "
                             f"{bed_x:.0f} x {bed_y:.0f} mm")
        out.append((nome, move(tris, x - lo[0], y - lo[1], -lo[2])))
        x += w + gap
        linha = max(linha, d)
    return out, y + linha + gap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--essencial', action='store_true',
                    help='so frame, sonar de baixo e os 4 pes')
    ap.add_argument('--helices', action='store_true',
                    help='inclui 2 CCW + 2 CW -- helice impressa NAO voa, '
                         'e so para conferir folga e sentido de giro na bancada')
    ap.add_argument('--mesa', type=float, nargs=2, default=[220.0, 220.0],
                    metavar=('X', 'Y'))
    ap.add_argument('-o', '--saida', default='placa_impressao.stl')
    args = ap.parse_args()

    fp = dict(frame.P)
    sp = dict(suportes.P)

    pecas = [('frame', frame.build(fp)[0])]
    pecas += [(f'pe {i + 1}', suportes.pe(sp)) for i in range(4)]
    pecas += [('sonar_baixo', suportes.sonar_baixo(sp))]
    if not args.essencial:
        pecas += [('sonar_frente', suportes.sonar_frente(sp))]
        pecas += [(f'suporte_ir {i + 1}', suportes.suporte_ir(sp)) for i in range(2)]
    if args.helices:
        hp = dict(helice.P)
        hp['diam'] = fp['prop_d']            # acompanha o frame
        for i in range(2):
            pecas += [(f'helice_ccw {i + 1}', helice.build(hp, True))]
            pecas += [(f'helice_cw {i + 1}', helice.build(hp, False))]

    postas, usado_y = arrange(pecas, args.mesa[0], args.mesa[1])

    tris, total = [], 0.0
    print(f"  {'peca':<18}{'g (PLA)':>9}")
    for nome, t in postas:
        g = volume(t) / 1000.0 * 1.24
        total += g
        tris += t
        print(f"  {nome:<18}{g:9.1f}")
    write_stl(tris, args.saida)

    lo, hi = bbox(tris)
    print(f"  {'-' * 27}\n  {'TOTAL':<18}{total:9.1f}")
    print(f"\n  {args.saida}: {len(tris)} triangulos")
    print(f"  ocupa {hi[0] - lo[0]:.0f} x {hi[1] - lo[1]:.0f} mm "
          f"numa mesa de {args.mesa[0]:.0f} x {args.mesa[1]:.0f}")
    print(f"  altura maxima {hi[2]:.0f} mm")
    print("\n  PLA ou PETG, camada 0,2 mm, 4 perimetros, 40 % de preenchimento.")
    if args.helices:
        print("\n  SUPORTE: so nas helices, e PINTADO -- nao global.")
        print("  A pa flutua ~2,5 mm no ar (a raiz torce 58 graus), entao sem")
        print("  suporte ela vira macarrao. Mas suporte GLOBAL enche a fresta")
        print("  de 1,9 mm do sonar_baixo, e dali nao sai mais. Usar 'pintar")
        print("  suporte' nas 4 helices resolve os dois de uma vez -- Orca,")
        print("  Bambu, PrusaSlicer e Cura tem essa ferramenta.")
        print("  (Sem paciencia para isso: rode sem --helices e imprima as")
        print("   helices num job separado, com suporte ligado a vontade.)")
        print("\n  AS HELICES IMPRESSAS NAO SAO PARA VOAR. Saem desbalanceadas e")
        print("  a camada delamina sob forca centrifuga. Bancada e conferencia")
        print("  de folga apenas -- e de oculos. Ver o cabecalho de helice.py.")
    else:
        print("  SEM SUPORTE -- todas as pecas foram orientadas para dispensar.")


if __name__ == '__main__':
    main()
