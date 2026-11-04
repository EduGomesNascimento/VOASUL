"""Extrai da placa (pcbnew) o que a folha de montagem precisa -> saidas/montagem.json"""
import json, math, os, pcbnew
AQUI = os.path.dirname(os.path.abspath(__file__))
CX, CY = 100.0, 100.0
def loc(v): return pcbnew.ToMM(v.x) - CX, CY - pcbnew.ToMM(v.y)
b = pcbnew.LoadBoard(os.path.join(AQUI, 'drone.kicad_pcb'))
pecas = []
for fp in b.GetFootprints():
    lado = 'B' if fp.GetLayer() == pcbnew.B_Cu else 'F'
    fab = []
    for g in fp.GraphicalItems():
        if g.GetClass() != 'MGRAPHIC' and not hasattr(g, 'GetShape'):
            continue
        if g.GetLayer() not in (pcbnew.F_Fab, pcbnew.B_Fab, pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            continue
        cam = 'fab' if g.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab) else 'crt'
        try:
            sh = g.GetShape()
        except Exception:
            continue
        if sh == pcbnew.SHAPE_T_SEGMENT:
            fab.append(dict(c=cam, t='seg', p=[loc(g.GetStart()), loc(g.GetEnd())]))
        elif sh == pcbnew.SHAPE_T_CIRCLE:
            fab.append(dict(c=cam, t='circ', p=[loc(g.GetCenter())], r=pcbnew.ToMM(g.GetRadius())))
        elif sh == pcbnew.SHAPE_T_RECT:
            fab.append(dict(c=cam, t='poly', p=[loc(pt) for pt in g.GetRectCorners()]))
        elif sh == pcbnew.SHAPE_T_POLY:
            ps = g.GetPolyShape()
            if ps.OutlineCount():
                o = ps.Outline(0)
                fab.append(dict(c=cam, t='poly', p=[loc(o.CPoint(k)) for k in range(o.PointCount())]))
        elif sh == pcbnew.SHAPE_T_ARC:
            fab.append(dict(c=cam, t='seg', p=[loc(g.GetStart()), loc(g.GetArcMid()), loc(g.GetEnd())]))
    pads = []
    for p in fp.Pads():
        s = p.GetSize()
        pads.append(dict(n=p.GetNumber(), x=loc(p.GetPosition())[0], y=loc(p.GetPosition())[1],
                         w=pcbnew.ToMM(s.x), h=pcbnew.ToMM(s.y), rot=p.GetOrientationDegrees(),
                         forma={pcbnew.PAD_SHAPE_CIRCLE: 'c', pcbnew.PAD_SHAPE_OVAL: 'o'}.get(p.GetShape(), 'r'),
                         furo=pcbnew.ToMM(p.GetDrillSize().x), rede=p.GetNetname()))
    x, y = loc(fp.GetPosition())
    pecas.append(dict(ref=fp.GetReference(), valor=fp.GetValue(), x=x, y=y, rot=fp.GetOrientationDegrees(),
                      lado=lado, fab=fab, pads=pads))
jump = []
for t in b.GetTracks():
    if t.GetClass() != 'PCB_VIA' and t.GetLayer() == pcbnew.F_Cu:
        jump.append(dict(rede=t.GetNetname(), a=loc(t.GetStart()), b=loc(t.GetEnd())))
jump.sort(key=lambda j: j['rede'])      # mesma ordem do jumpers.txt
json.dump(dict(raio=48.5, pecas=pecas, jumpers=jump), open(os.path.join(AQUI, 'saidas', 'montagem.json'), 'w'))
print(len(pecas), 'pecas,', len(jump), 'jumpers')
