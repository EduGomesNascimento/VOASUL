#!/usr/bin/env python3
"""
Gera a placa do drone no KiCad 7 a partir de projeto.py.

    python3 gerar.py placa      # monta a placa (pecas, redes, contorno) -> drone.kicad_pcb
    python3 gerar.py rotear     # autoroteia com o Freerouting (precisa de java + freerouting.jar)
    python3 gerar.py acabar     # planos de GND, textos, DRC e saidas (PDF de transferencia, 3D)

Regras de placa caseira (transferencia termica, dupla face SEM furo metalizado):
  * pecas que cobrem o furo por cima (barras femea/macho, eletroliticos) tem ilha
    SO EMBAIXO (B.Cu): por cima nao da para soldar.
  * resistores, capacitor ceramico e ilhas de fio (motor, bateria) tem ilha nos dois lados.
  * MOSFET e diodo SMD ficam EMBAIXO, no lado do cobre, fora dos raios do frame.
  * via = pedaco de fio soldado nos dois lados: furo 0,8 / ilha 1,8.
"""
import json
import math
import os
import sys

import pcbnew

import projeto as P

AQUI = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(AQUI, 'drone.kicad_pcb')
PRO = os.path.join(AQUI, 'drone.kicad_pro')
LIB = '/usr/share/kicad/footprints'
MM = pcbnew.FromMM
CX, CY = 100.0, 100.0           # centro do disco na folha do KiCad


def kpt(x, y):
    """mm locais (Y p/ frente) -> ponto do KiCad (Y p/ baixo)"""
    return pcbnew.VECTOR2I(MM(CX + x), MM(CY - y))


def modelo3d(fp, arquivo, off=(0, 0, 0), rot=(0, 0, 0)):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = '${KIPRJMOD}/3d/' + arquivo
    m.m_Offset = pcbnew.VECTOR3D(*off)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
    fp.Add3DModel(m)


def trocar_modelos(fp):
    """troca o caminho da biblioteca do KiCad pela copia em 3d/ (projeto portatil)"""
    ms = list(fp.Models())
    fp.Models().clear()
    for m in ms:
        nome = os.path.basename(m.m_Filename).replace('.step', '.wrl')
        modelo3d(fp, nome, (m.m_Offset.x, m.m_Offset.y, m.m_Offset.z),
                 (m.m_Rotation.x, m.m_Rotation.y, m.m_Rotation.z))


def so_embaixo(pad):
    """ilha so em B.Cu: furo sem cobre por cima"""
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.B_Cu)
    ls.AddLayer(pcbnew.B_Mask)
    pad.SetLayerSet(ls)


def novo_pad(fp, num, x, y, d=1.8, furo=1.0, forma='circ', w=None, h=None, embaixo=True):
    """pad em coordenadas locais da pegada (Y para cima)"""
    p = pcbnew.PAD(fp)
    p.SetNumber(str(num))
    p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    p.SetLayerSet(pcbnew.PAD.PTHMask())
    if forma == 'ret':
        p.SetShape(pcbnew.PAD_SHAPE_RECT)
    elif forma == 'oval':
        p.SetShape(pcbnew.PAD_SHAPE_OVAL)
    else:
        p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(pcbnew.VECTOR2I(MM(w or d), MM(h or d)))
    p.SetDrillSize(pcbnew.VECTOR2I(MM(furo), MM(furo)))
    p.SetPos0(pcbnew.VECTOR2I(MM(x), MM(-y)))
    p.SetPosition(pcbnew.VECTOR2I(MM(x), MM(-y)))
    if embaixo:
        so_embaixo(p)
    fp.Add(p)
    return p


def retangulo(fp, x0, y0, x1, y1, camada, larg=0.12):
    for (a, b, c, d) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        s = pcbnew.FP_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart0(pcbnew.VECTOR2I(MM(a), MM(-b)))
        s.SetEnd0(pcbnew.VECTOR2I(MM(c), MM(-d)))
        s.SetStart(pcbnew.VECTOR2I(MM(a), MM(-b)))
        s.SetEnd(pcbnew.VECTOR2I(MM(c), MM(-d)))
        s.SetLayer(camada)
        s.SetWidth(MM(larg))
        fp.Add(s)


def caixa_peca(fp, x0, y0, x1, y1):
    """contorno no silk, fab e courtyard"""
    retangulo(fp, x0, y0, x1, y1, pcbnew.F_SilkS, 0.15)
    retangulo(fp, x0, y0, x1, y1, pcbnew.F_Fab, 0.1)
    retangulo(fp, x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3, pcbnew.F_CrtYd, 0.05)


def pegada_vazia(nome):
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID('drone', nome))
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    return fp


# ---------------------------------------------------------------- pegadas
OVAL_254 = (1.7, 3.0)      # ilha de pino 2,54: oval, larga p/ o lado de fora -> folga 0,84


def fp_esp32():
    fp = pegada_vazia('ESP32_DevKitC_38p')
    w, h = OVAL_254
    for i in range(19):                                  # J2: pino 1 (3V3) na ponta da antena
        novo_pad(fp, i + 1, 22.86 - i * 2.54, 12.7, forma='oval', w=w, h=h)
    for i in range(19):                                  # J3: pino 20 (GND) na ponta da antena
        novo_pad(fp, 20 + i, 22.86 - i * 2.54, -12.7, forma='oval', w=w, h=h)
    caixa_peca(fp, -26.5, -14.0, 28.5, 14.0)
    retangulo(fp, 22.0, -9.0, 28.5, 9.0, pcbnew.F_SilkS, 0.15)   # antena
    for y in (12.7, -12.7):                              # barras femea 1x19
        modelo3d(fp, 'PinSocket_1x19_P2.54mm_Vertical.wrl', (22.86, y, 0), (0, 0, -90))
    modelo3d(fp, 'ESP32_DevKitC_38p.wrl')
    return fp


def fp_gy(nome, n, larg, alt, modelo):
    fp = pegada_vazia(nome)
    w, h = OVAL_254
    for i in range(n):
        novo_pad(fp, i + 1, (i - (n - 1) / 2) * 2.54, 0, forma='oval', w=w, h=h)
    caixa_peca(fp, -larg / 2, -1.5, larg / 2, alt - 1.5)
    modelo3d(fp, modelo)
    return fp


def fp_mt3608():
    fp = pegada_vazia('MT3608_modulo')
    # IN+ IN- OUT+ OUT- nos cantos; pernas de fio rigido (ilha oval = tolerancia)
    for num, x, y in ((1, -16.5, 6.5), (2, -16.5, -6.5), (3, 16.5, 6.5), (4, 16.5, -6.5)):
        novo_pad(fp, num, x, y, furo=1.0, forma='oval', w=2.6, h=3.4)
    caixa_peca(fp, -18.0, -8.5, 18.0, 8.5)
    modelo3d(fp, 'MT3608.wrl')
    return fp


def fp_ilhas(nome, passo, d, furo):
    """ilhas de fio (motor/bateria)"""
    fp = pegada_vazia(nome)
    novo_pad(fp, 1, -passo / 2, 0, d=d, furo=furo, forma='ret')
    novo_pad(fp, 2, passo / 2, 0, d=d, furo=furo)
    t = pcbnew.FP_TEXT(fp)
    t.SetText('+')
    t.SetPos0(pcbnew.VECTOR2I(MM(-passo / 2), MM(-d / 2 - 1.2)))
    t.SetPosition(pcbnew.VECTOR2I(MM(-passo / 2), MM(-d / 2 - 1.2)))
    t.SetLayer(pcbnew.F_SilkS)
    fp.Add(t)
    caixa_peca(fp, -passo / 2 - d / 2 - 0.4, -d / 2 - 0.4, passo / 2 + d / 2 + 0.4, d / 2 + 0.4)
    return fp


def fp_lib(lib, nome, tam=None, furo=None, oval_perp=False):
    """pegada da biblioteca do KiCad; ilhas THT viram ilhas SO EMBAIXO (face unica).
    oval_perp: ilha oval com o lado comprido perpendicular a fileira (passo 2,54)."""
    fp = pcbnew.FootprintLoad(os.path.join(LIB, lib + '.pretty'), nome)
    trocar_modelos(fp)
    pads = list(fp.Pads())
    tht = [p for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
    vertical = len(tht) > 1 and abs(tht[0].GetPos0().x - tht[1].GetPos0().x) < 10
    for p in tht:
        if oval_perp:
            w, h = OVAL_254
            p.SetShape(pcbnew.PAD_SHAPE_OVAL)
            p.SetSize(pcbnew.VECTOR2I(MM(h), MM(w)) if vertical else pcbnew.VECTOR2I(MM(w), MM(h)))
        elif tam:
            p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            p.SetSize(pcbnew.VECTOR2I(MM(tam), MM(tam)))
        if furo:
            p.SetDrillSize(pcbnew.VECTOR2I(MM(furo), MM(furo)))
        so_embaixo(p)
    if not tht:                       # SMD: fica embaixo, no lado do cobre
        pass
    return fp


def pegada(tipo):
    if tipo == 'ESP32_DEVKIT':
        return fp_esp32()
    if tipo == 'GY_BMI160':
        return fp_gy('GY_BMI160', 7, 20.0, 13.5, 'GY_BMI160.wrl')
    if tipo == 'GY_BMP280':
        return fp_gy('GY_BMP280', 6, 15.0, 11.5, 'GY_BMP280.wrl')
    if tipo == 'MT3608':
        return fp_mt3608()
    if tipo == 'BATERIA':
        return fp_ilhas('Ilhas_bateria', 6.0, 3.6, 1.3)
    if tipo == 'MOTOR':
        return fp_ilhas('Ilhas_motor', 5.0, 3.0, 1.0)
    if tipo == 'R_PE':
        return fp_lib('Resistor_THT', 'R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical', furo=0.9, oval_perp=True)
    if tipo == 'C_0805':
        return fp_lib('Capacitor_SMD', 'C_0805_2012Metric')
    if tipo == 'C_DISC':
        return fp_lib('Capacitor_THT', 'C_Disc_D5.0mm_W2.5mm_P5.00mm', 2.4, 0.9)
    if tipo == 'CP_D8':
        return fp_lib('Capacitor_THT', 'CP_Radial_D8.0mm_P3.50mm', 2.4, 1.0)
    if tipo == 'CP_D6':
        return fp_lib('Capacitor_THT', 'CP_Radial_D6.3mm_P2.50mm', furo=0.9, oval_perp=True)
    if tipo == 'SOT23':
        fp = fp_lib('Package_TO_SOT_SMD', 'SOT-23')
        for p in fp.Pads():             # ilha mais curta: folga de 0,8 entre o pino 3 e os pinos 1/2
            p.SetShape(pcbnew.PAD_SHAPE_RECT)
            p.SetSize(pcbnew.VECTOR2I(MM(1.05), MM(0.7)))
        return fp
    if tipo == 'SMA':
        return fp_lib('Diode_SMD', 'D_SMA')
    if tipo == 'CONN4':
        return fp_lib('Connector_PinHeader_2.54mm', 'PinHeader_1x04_P2.54mm_Vertical', furo=1.0, oval_perp=True)
    if tipo == 'CONN6':
        return fp_lib('Connector_PinHeader_2.54mm', 'PinHeader_1x06_P2.54mm_Vertical', furo=1.0, oval_perp=True)
    raise ValueError(tipo)


# ---------------------------------------------------------------- placa
def area_regra(board, pontos, camadas, sem_cobre=True, sem_via=True, sem_trilha=True, nome=''):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowCopperPour(sem_cobre)
    z.SetDoNotAllowVias(sem_via)
    z.SetDoNotAllowTracks(sem_trilha)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for c in camadas:
        ls.AddLayer(c)
    z.SetLayerSet(ls)
    if nome:
        z.SetZoneName(nome)
    o = z.Outline()
    o.NewOutline()
    for x, y in pontos:
        o.Append(MM(CX + x), MM(CY - y))
    board.Add(z)
    return z


def circulo_pts(r, n=72):
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def girar_para_fora(fp, num):
    """gira de 15 em 15 graus e fica com o angulo em que o pino 'num' aponta
    exatamente para fora (radial)"""
    def nota(a):
        fp.SetOrientationDegrees(a)
        c = fp.GetPosition()
        p = fp.FindPadByNumber(num).GetPosition()
        vx, vy = pcbnew.ToMM(p.x - c.x), pcbnew.ToMM(p.y - c.y)
        rx, ry = pcbnew.ToMM(c.x) - CX, pcbnew.ToMM(c.y) - CY
        return (vx * rx + vy * ry) / (math.hypot(vx, vy) * math.hypot(rx, ry) + 1e-9)
    melhor = max(range(0, 360, 15), key=nota)
    fp.SetOrientationDegrees(melhor)


def montar():
    import modelos3d
    modelos3d.gerar_todos(os.path.join(AQUI, '3d'))

    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(2)

    # contorno: disco
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(kpt(0, 0))
    s.SetEnd(kpt(P.DISCO_D / 2, 0))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    board.Add(s)

    # redes
    redes = {}
    for pc in P.PECAS:
        for rede in pc['pinos'].values():
            if rede and rede not in redes:
                n = pcbnew.NETINFO_ITEM(board, rede)
                board.Add(n)
                redes[rede] = n

    for pc in P.PECAS:
        fp = pegada(pc['tipo'])
        fp.SetReference(pc['ref'])
        fp.SetValue(pc['valor'])
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
        fp.Reference().SetTextThickness(MM(0.15))
        board.Add(fp)
        fp.SetPosition(kpt(pc['x'], pc['y']))
        fp.SetOrientationDegrees(pc['rot'])
        if pc['lado'] == 'B':
            fp.Flip(fp.GetPosition(), False)
        if pc.get('pino_fora'):
            girar_para_fora(fp, pc['pino_fora'])
        for p in fp.Pads():
            rede = pc['pinos'].get(p.GetNumber())
            if rede:
                p.SetNet(redes[rede])

    # antena do WROOM: sem cobre nenhum embaixo (vale se for a antena impressa)
    u1 = board.FindFootprintByReference('U1')
    ux, uy = pcbnew.ToMM(u1.GetPosition().x) - CX, CY - pcbnew.ToMM(u1.GetPosition().y)
    sx = -1 if P.ESP_ROT == 180 else 1
    xa, xb = sorted((ux + sx * 23.0, ux + sx * 29.5))   # antena do WROOM: ultimos ~6 mm do modulo
    area_regra(board, [(xa, uy - 9.5), (xb, uy - 9.5), (xb, uy + 9.5), (xa, uy + 9.5)],
               [pcbnew.F_Cu, pcbnew.B_Cu], nome='ANTENA')

    pcbnew.SaveBoard(PCB, board)
    ajustar_projeto()
    print('placa salva:', PCB, '|', len(P.PECAS), 'pecas,', len(redes), 'redes')


def ajustar_projeto():
    """classes de rede (larguras) e regras minimas no .kicad_pro"""
    with open(PRO) as f:
        pro = json.load(f)
    base = dict(bus_width=12, clearance=0.5, diff_pair_gap=0.25, diff_pair_via_gap=0.25,
                diff_pair_width=0.2, line_style=0, microvia_diameter=0.3, microvia_drill=0.1,
                pcb_color='rgba(0, 0, 0, 0.000)', schematic_color='rgba(0, 0, 0, 0.000)',
                via_diameter=P.JUMPER_ILHA, via_drill=P.JUMPER_FURO, wire_width=6)
    classes, padroes = [], []
    for nome, (larg, redes) in P.CLASSES.items():
        c = dict(base, name=nome, track_width=larg, clearance=P.FOLGA)
        classes.append(c)
        for r in redes:
            padroes.append({'netclass': nome, 'pattern': r})
    ns = pro.setdefault('net_settings', {})
    ns['classes'] = classes
    ns['meta'] = {'version': 3}
    ns['netclass_patterns'] = padroes
    ds = pro.setdefault('board', {}).setdefault('design_settings', {})
    regras = ds.setdefault('rules', {})
    regras.update(min_clearance=P.FOLGA - 0.05, min_track_width=P.LARG_PESCOCO - 0.05, min_via_diameter=1.6,
                  min_via_annular_width=0.3, min_through_hole_diameter=0.7,
                  min_copper_edge_clearance=P.FOLGA_BORDA - 0.05, min_hole_clearance=0.4, min_hole_to_hole=0.5,
                  min_silk_clearance=0.0, min_text_height=0.8, min_text_thickness=0.12)
    # pegadas foram alteradas de proposito (ilhas so embaixo, ovais): nao e erro
    ds.setdefault('rule_severities', {}).update(
        lib_footprint_issues='ignore', lib_footprint_mismatch='ignore',
        silk_overlap='ignore', silk_over_copper='ignore')
    ds['track_widths'] = [0.0, 0.8, 1.2, 1.5, 2.0, 2.5, 3.0]
    ds['rules']['min_resolved_spokes'] = 1
    ds['via_dimensions'] = [{'diameter': 0.0, 'drill': 0.0},
                            {'diameter': P.JUMPER_ILHA, 'drill': P.JUMPER_FURO}]
    with open(PRO, 'w') as f:
        json.dump(pro, f, indent=2)


if __name__ == '__main__':
    etapa = sys.argv[1] if len(sys.argv) > 1 else 'placa'
    if etapa == 'placa':
        montar()
    else:
        import etapas
        getattr(etapas, etapa)()
