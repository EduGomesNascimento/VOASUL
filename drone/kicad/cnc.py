"""G-code para fresar a placa de FACE UNICA (versao de usinagem) numa CNC de PCB (GRBL: CNC 3018 e parecidas).

Saidas em cnc/:
  1_isolamento_vbit.nc       isolamento das trilhas (fresa em V)
  2_furos_0.9mm.nc           furos de 0,9 mm (pinos e jumpers)
  3_furos_1.0mm.nc           furos de 1,0 mm (motores, modulos, barras)
  4_furos_1.3mm.nc           furos de 1,3 mm (bateria)
  2a_furos_todos_1.0mm.nc    alternativa: todos os furos com broca de 1,0 mm
  5_contorno_fresa1mm.nc     recorte do disco de 97 mm, com 4 pontes
  6_limpar_antena_vbit.nc    (opcional) tira o cobre embaixo da antena do ESP32
  previa_cnc.png             desenho dos percursos

COORDENADAS: a placa e fresada com o COBRE PARA CIMA, entao tudo sai espelhado (visto por
baixo). Origem X0 Y0 = CENTRO do disco. Z0 = superficie do cobre.
Roda no Python do KiCad (/usr/bin/python3) com shapely e matplotlib.
"""
import math
import os

import pcbnew
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.ops import linemerge, unary_union

AQUI = os.path.dirname(os.path.abspath(__file__))
# placa de usinagem (gerar.py usinagem): ilhas maiores e sem texto no cobre; se nao existir, a caseira
PCB = os.path.join(AQUI, 'usinagem', 'drone_usinagem.kicad_pcb')
if not os.path.exists(PCB):
    PCB = os.path.join(AQUI, 'drone.kicad_pcb')
OUT = os.path.join(AQUI, 'cnc')
CX, CY = 100.0, 100.0                 # centro do disco na folha do KiCad

# ---------------------------------------------------------------- ajuste aqui
V_PONTA, V_ANGULO = 0.10, 30.0        # fresa em V: ponta (mm) e angulo
ISO_PROF = 0.08                       # profundidade do isolamento (mm)
ISO_PASSES = 2                        # passadas em volta de cada trilha
ISO_PASSO = 0.10                      # distancia entre passadas (mm)
ISO_AVANCO, ISO_MERGULHO = 150, 50    # mm/min
RPM = 10000

FURO_PROF = 1.9                       # placa de 1,6 mm + folga
FURO_MERGULHO = 50

CONT_FRESA = 1.0                      # fresa de topo (mm)
CONT_PROF, CONT_PASSO = 1.8, 0.3      # profundidade total e por passada
CONT_AVANCO = 100
PONTE_LARG, PONTE_ALT = 3.0, 0.5      # 4 pontes (largura, espessura que fica)

Z_SEGURO = 2.0
# ----------------------------------------------------------------------------

ISO_LARG = V_PONTA + 2 * ISO_PROF * math.tan(math.radians(V_ANGULO / 2))   # largura do corte


def mm(v):
    return pcbnew.ToMM(v)


def maquina(x, y):
    """folha do KiCad -> maquina (vista por baixo, origem no centro)"""
    return (CX - x, CY - y)


def geo_maquina(g):
    """aplica a mesma transformacao a uma geometria shapely (espelho + y para cima)"""
    from shapely.affinity import affine_transform
    return affine_transform(g, [-1, 0, 0, -1, CX, CY])


def cobre():
    """todo o cobre de baixo (B.Cu), como poligonos shapely na folha do KiCad"""
    b = pcbnew.LoadBoard(PCB)
    L = pcbnew.B_Cu
    gs = []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            if t.IsOnLayer(L):
                p = t.GetPosition()
                gs.append(Point(mm(p.x), mm(p.y)).buffer(mm(t.GetWidth()) / 2, 32))
            continue
        if not t.IsOnLayer(L):
            continue
        a, c = t.GetStart(), t.GetEnd()
        ln = LineString([(mm(a.x), mm(a.y)), (mm(c.x), mm(c.y))])
        gs.append(ln.buffer(mm(t.GetWidth()) / 2, 16) if ln.length else Point(ln.coords[0]).buffer(mm(t.GetWidth()) / 2, 16))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if not p.IsOnLayer(L):
                continue
            pos = p.GetPosition()
            x, y = mm(pos.x), mm(pos.y)
            w, h = mm(p.GetSize().x), mm(p.GetSize().y)
            forma = p.GetShape()
            if forma == pcbnew.PAD_SHAPE_CIRCLE:
                g = Point(0, 0).buffer(w / 2, 32)
            elif forma == pcbnew.PAD_SHAPE_OVAL:
                r = min(w, h) / 2
                d = (max(w, h) - min(w, h)) / 2
                seg = LineString([(-d, 0), (d, 0)] if w >= h else [(0, -d), (0, d)])
                g = seg.buffer(r, 16) if d > 0 else Point(0, 0).buffer(r, 32)
            elif forma == pcbnew.PAD_SHAPE_ROUNDRECT:
                r = p.GetRoundRectCornerRadius() / 1e6
                g = box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, 8)
            else:                                   # RECT e o resto
                g = box(-w / 2, -h / 2, w / 2, h / 2)
            # o KiCad gira no sentido anti-horario na tela (y para baixo)
            g = rotate(g, -p.GetOrientationDegrees(), origin=(0, 0))
            gs.append(translate(g, x, y))
    for z in b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(L):
            continue
        f = z.GetFilledPolysList(L)
        for i in range(f.OutlineCount()):
            o = f.Outline(i)
            pts = [(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())]
            holes = []
            for hh in range(f.HoleCount(i)):
                h = f.Hole(i, hh)
                holes.append([(mm(h.CPoint(k).x), mm(h.CPoint(k).y)) for k in range(h.PointCount())])
            gs.append(Polygon(pts, holes).buffer(0))
    furos = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetDrillSize().x > 0:
                pos = p.GetPosition()
                furos.append((round(mm(p.GetDrillSize().x), 2), mm(pos.x), mm(pos.y)))
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            pos = t.GetPosition()
            furos.append((round(mm(t.GetDrillValue()), 2), mm(pos.x), mm(pos.y)))
    return unary_union(gs), furos


def partes(g):
    return list(getattr(g, 'geoms', [g]))


def ordenar(caminhos, inicio=(0.0, 0.0)):
    """vizinho mais proximo, para encurtar os deslocamentos no ar"""
    restam = list(caminhos)
    out, atual = [], inicio
    while restam:
        k = min(range(len(restam)), key=lambda i: math.dist(atual, restam[i][0]))
        c = restam.pop(k)
        out.append(c)
        atual = c[-1]
    return out


def isolamento(cu):
    """aneis de corte em volta de cada ilha de cobre, sem entrar no cobre vizinho"""
    ilhas = partes(cu)
    r = ISO_LARG / 2
    caminhos = []
    for k, ilha in enumerate(ilhas):
        outras = unary_union(ilhas[:k] + ilhas[k + 1:])
        proibido = outras.buffer(r + 0.01, 16)       # a borda da fresa nao encosta no vizinho
        for n in range(ISO_PASSES):
            off = ilha.buffer(r + n * ISO_PASSO, 16)
            for pol in partes(off):
                for anel in [pol.exterior] + list(pol.interiors):
                    resto = LineString(anel.coords).difference(proibido)
                    for ln in partes(resto):
                        if ln.length > 0.05:
                            ln = ln.simplify(0.01)          # menos linhas, mesma forma (0,01 mm)
                            caminhos.append(list(geo_maquina(ln).coords))
    return caminhos


def cabecalho(nome, ferramenta):
    return [f'( {nome} )', f'( ferramenta: {ferramenta} )',
            '( origem X0 Y0 = centro do disco; Z0 = superficie do cobre; placa com o cobre para cima )',
            'G21 G90 G94', f'G0 Z{Z_SEGURO:.2f}', f'M3 S{RPM}', 'G4 P3']


def rodape():
    return [f'G0 Z{Z_SEGURO:.2f}', 'M5', 'G0 Z15', 'G0 X0 Y0', 'M30']


def gcode_caminhos(caminhos, z, avanco, mergulho):
    g = []
    for c in caminhos:
        g.append(f'G0 X{c[0][0]:.3f} Y{c[0][1]:.3f}')
        g.append(f'G1 Z{-z:.3f} F{mergulho}')
        g.append(f'G1 X{c[1][0]:.3f} Y{c[1][1]:.3f} F{avanco}' if len(c) > 1 else '')
        for x, y in c[2:]:
            g.append(f'X{x:.3f} Y{y:.3f}')
        g.append(f'G0 Z{Z_SEGURO:.2f}')
    return [l for l in g if l]


def comprimento(caminhos):
    return sum(math.dist(a, b) for c in caminhos for a, b in zip(c, c[1:]))


def escrever(nome, linhas):
    with open(os.path.join(OUT, nome), 'w') as f:
        f.write('\n'.join(linhas) + '\n')


def contorno():
    """disco de 97 mm (borda da placa) com a fresa por fora; 4 pontes nas posicoes 0/90/180/270"""
    raio = 97.0 / 2 + CONT_FRESA / 2
    n = 360
    pts = [(raio * math.cos(2 * math.pi * k / n), raio * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
    meia = math.degrees(PONTE_LARG / 2 / raio + CONT_FRESA / 2 / raio)
    def na_ponte(k):
        a = (360.0 * k / n) % 90
        return a < meia or a > 90 - meia
    g, z = [], 0.0
    g.append(f'G0 X{pts[0][0]:.3f} Y{pts[0][1]:.3f}')
    z_ponte = -(CONT_PROF - PONTE_ALT - 0.2)    # a ponte fica com PONTE_ALT mm de material
    while z > -CONT_PROF + 1e-9:
        z = max(z - CONT_PASSO, -CONT_PROF)
        g.append(f'G1 Z{z:.3f} F{FURO_MERGULHO}')
        for k, (x, y) in enumerate(pts[1:], start=1):
            zz = max(z, z_ponte) if na_ponte(k) else z
            g.append(f'G1 X{x:.3f} Y{y:.3f} Z{zz:.3f} F{CONT_AVANCO}')
    g.append(f'G0 Z{Z_SEGURO:.2f}')
    voltas = math.ceil(CONT_PROF / CONT_PASSO)
    return g, 2 * math.pi * raio * voltas


def areas_sem_cobre():
    """retangulos 'sem cobre' (antena do ESP32), na folha do KiCad"""
    b = pcbnew.LoadBoard(PCB)
    out = []
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowCopperPour() and z.IsOnLayer(pcbnew.B_Cu):
            o = z.Outline().Outline(0)
            out.append(Polygon([(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())]))
    return out


def limpar(areas):
    """raspa o cobre de dentro das areas, em linhas paralelas (zigue-zague)"""
    r = ISO_LARG / 2
    cam = []
    for a in areas:
        dentro = a.buffer(-r)
        if dentro.is_empty:
            continue
        x0, y0, x1, y1 = dentro.bounds
        vertical = (y1 - y0) > (x1 - x0)
        n = int(((x1 - x0) if vertical else (y1 - y0)) / (ISO_LARG * 0.8)) + 1
        for k in range(n + 1):
            t = k / n
            if vertical:
                x = x0 + (x1 - x0) * t
                ln = LineString([(x, y0 - 1), (x, y1 + 1)])
            else:
                y = y0 + (y1 - y0) * t
                ln = LineString([(x0 - 1, y), (x1 + 1, y)])
            for parte in partes(ln.intersection(dentro)):
                c = list(geo_maquina(parte).coords)
                cam.append(c if k % 2 == 0 else c[::-1])
        cam.append(list(geo_maquina(dentro.exterior).coords))
    return cam


def main():
    os.makedirs(OUT, exist_ok=True)
    cu, furos = cobre()
    print(f'cobre: {len(partes(cu))} ilhas, {cu.area:.0f} mm2 | furos: {len(furos)}')

    # 1) isolamento
    cam = ordenar(isolamento(cu))
    lin = cabecalho('1 - ISOLAMENTO das trilhas', f'fresa em V {V_ANGULO:.0f} graus ponta {V_PONTA} mm, '
                    f'corte {ISO_LARG:.2f} mm a {ISO_PROF} mm de profundidade')
    lin += gcode_caminhos(cam, ISO_PROF, ISO_AVANCO, ISO_MERGULHO) + rodape()
    escrever('1_isolamento_vbit.nc', lin)
    L_iso = comprimento(cam)

    # 2) furos
    def furos_gcode(lista, nome, broca):
        pts = ordenar([[maquina(x, y)] for _, x, y in lista])
        g = cabecalho(nome, f'broca {broca} mm')
        for (p,) in pts:
            g += [f'G0 X{p[0]:.3f} Y{p[1]:.3f}', f'G1 Z{-FURO_PROF:.2f} F{FURO_MERGULHO}', f'G0 Z{Z_SEGURO:.2f}']
        return g + rodape()
    tam = sorted({d for d, _, _ in furos})
    arqs = {0.9: '2_furos_0.9mm.nc', 1.0: '3_furos_1.0mm.nc', 1.3: '4_furos_1.3mm.nc'}
    for d in tam:
        sel = [f for f in furos if f[0] == d]
        nome = arqs.get(d, f'furos_{d:.1f}mm.nc')
        escrever(nome, furos_gcode(sel, f'FUROS de {d} mm ({len(sel)})', d))
        print(f'  furos {d} mm: {len(sel)} -> {nome}')
    escrever('2a_furos_todos_1.0mm.nc',
             furos_gcode([f for f in furos if f[0] <= 1.0], 'FUROS 0,9 e 1,0 mm, todos com broca de 1,0 mm', 1.0))

    # 2b) limpar o cobre embaixo da antena (opcional)
    lc = limpar(areas_sem_cobre())
    escrever('6_limpar_antena_vbit.nc', cabecalho('6 - (OPCIONAL) LIMPAR o cobre embaixo da antena do ESP32',
                                                  'a mesma fresa em V do isolamento') +
             gcode_caminhos(lc, ISO_PROF, ISO_AVANCO, ISO_MERGULHO) + rodape())
    print(f'limpar antena: {len(lc)} percursos, ~{comprimento(lc) / ISO_AVANCO:.0f} min')

    # 3) contorno
    g, L_cont = contorno()
    escrever('5_contorno_fresa1mm.nc', cabecalho('5 - CONTORNO do disco de 97 mm (4 pontes)',
                                                 f'fresa de topo {CONT_FRESA} mm') + g + rodape())

    main.caminhos, main.cobre = cam, cu
    t_iso = L_iso / ISO_AVANCO + len(cam) * (ISO_PROF + Z_SEGURO) * 2 / ISO_MERGULHO
    t_cont = L_cont / CONT_AVANCO
    print(f'isolamento: {len(cam)} percursos, {L_iso / 1000:.1f} m de corte, ~{t_iso:.0f} min')
    print(f'contorno: ~{t_cont:.0f} min | furos: ~{len(furos) * 0.15:.0f} min')

    # previa
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 10))
    for pol in partes(geo_maquina(cu)):
        xs, ys = pol.exterior.xy
        ax.fill(xs, ys, color='#e8c39e', lw=0)
        for h in pol.interiors:
            xs, ys = h.xy
            ax.fill(xs, ys, color='white', lw=0)
    for c in cam:
        xs, ys = zip(*c)
        ax.plot(xs, ys, color='#c0392b', lw=0.35)
    for c in lc:
        xs, ys = zip(*c)
        ax.plot(xs, ys, color='#8e44ad', lw=0.35)
    for d, x, y in furos:
        X, Y = maquina(x, y)
        ax.add_patch(plt.Circle((X, Y), d / 2, color='#1d5fa8'))
    ax.add_patch(plt.Circle((0, 0), 97 / 2 + CONT_FRESA / 2, fill=False, color='#0f6b4f', lw=1.2))
    ax.plot([0], [0], 'k+', ms=14)
    ax.set_aspect('equal')
    ax.set_xlim(-52, 52)
    ax.set_ylim(-52, 52)
    ax.set_title('Previa CNC (vista com o cobre para cima, origem no centro): '
                 'vermelho = isolamento, roxo = limpar antena, azul = furos, verde = contorno', fontsize=9)
    fig.savefig(os.path.join(OUT, 'previa_cnc.png'), dpi=150)
    print('saidas em', OUT)


if __name__ == '__main__':
    main()
