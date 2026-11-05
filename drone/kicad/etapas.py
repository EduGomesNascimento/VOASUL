"""
Etapas depois de montar a placa (rodam no Python do KiCad, chamadas por gerar.py):

  exportar  -> geometria.json   (pinos, redes, larguras, areas proibidas, anel de VBAT)
  aplicar   <- rotas.json       (trilhas + jumpers) -> plano de GND, textos, DRC
"""
import json
import math
import os
import sys

import pcbnew

import projeto as P

AQUI = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(AQUI, 'drone.kicad_pcb')
GEO = os.path.join(AQUI, 'geometria.json')
ROTAS = os.path.join(AQUI, 'rotas.json')
MM = pcbnew.FromMM
CX, CY = 100.0, 100.0

ORDEM = (['VBAT', '+3V3', '+5V'] +
         ['DRENO_' + m for m in ('FR', 'RR', 'RL', 'FL')] +
         ['PORTA_' + m for m in ('FR', 'RR', 'RL', 'FL')] +
         # o sinal do motor RR desce pelo lado direito, onde tambem passa o sonar: vai antes
         ['M_RR'] +
         # sonar numa ordem em que um nao fecha o caminho do outro
         ['ECHO_F', 'TRIG_B', 'ECHO_B', 'TRIG_F', 'ECHO_B5', 'ECHO_F5', '+5V:adiado'] +
         ['M_FR', 'M_RL', 'M_FL'] +
         ['SDA', 'SCL', 'IR_E', 'IR_D', 'VBAT_ADC', 'FLOW_MISO', 'FLOW_SCK', 'FLOW_MOSI', 'FLOW_CS',
          'SDA2', 'SCL2',
          # GND antes do 3V3 do J4: o 3V3 cortaria o canto de tras-esquerda (Q3, R7, J3, R10) ao meio
          'GND', '+3V3:adiado'])

TEXTO_Y = 40.0    # texto no cobre, na frente, entre as ilhas do MT3608

# corpo encostado na placa: jumper nao passa por cima nem fura embaixo
SEM_JUMPER_TIPOS = ('C', 'R', 'J2', 'J3', 'J4')   # U3/U4: jumper soldado ANTES do modulo pode passar embaixo


def loc(v):
    return pcbnew.ToMM(v.x) - CX, CY - pcbnew.ToMM(v.y)


def kpt(x, y):
    return pcbnew.VECTOR2I(MM(CX + x), MM(CY - y))


def anel():
    """anel de VBAT: poligono de 72 lados no raio R_ANEL"""
    n = 72
    pts = [(P.R_ANEL * math.cos(2 * math.pi * i / n), P.R_ANEL * math.sin(2 * math.pi * i / n))
           for i in range(n + 1)]
    w = P.CLASSES['POTENCIA'][0]
    return [dict(rede='VBAT', x1=a[0], y1=a[1], x2=b[0], y2=b[1], w=w) for a, b in zip(pts, pts[1:])]


def exportar():
    b = pcbnew.LoadBoard(PCB)
    pads = []
    forma = {pcbnew.PAD_SHAPE_CIRCLE: 'circ', pcbnew.PAD_SHAPE_OVAL: 'oval'}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if not p.IsOnLayer(pcbnew.B_Cu):
                continue
            x, y = loc(p.GetPosition())
            s = p.GetSize()
            pads.append(dict(ref=fp.GetReference(), num=p.GetNumber(),
                             rede=p.GetNetname() or None, x=x, y=y,
                             w=pcbnew.ToMM(s.x), h=pcbnew.ToMM(s.y),
                             rot=p.GetOrientationDegrees(), tipo=forma.get(p.GetShape(), 'ret')))
    sem_cobre = []
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
            bb = z.GetBoundingBox()
            x0, y1 = loc(bb.GetOrigin())
            x1, y0 = loc(bb.GetEnd())
            sem_cobre.append(dict(x=(x0 + x1) / 2, y=(y0 + y1) / 2, w=x1 - x0, h=y1 - y0))
    # texto 'VoaSul | Drones' no cobre de baixo: area reservada
    sem_cobre.append(dict(x=0.0, y=TEXTO_Y, w=20.0, h=2.8))
    sem_jumper = []
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if fp.GetLayer() != pcbnew.F_Cu:
            continue
        if not (ref.startswith(('C', 'R')) or ref in SEM_JUMPER_TIPOS):
            continue
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
        x0, y1 = loc(bb.GetOrigin())
        x1, y0 = loc(bb.GetEnd())
        sem_jumper.append(dict(x=(x0 + x1) / 2, y=(y0 + y1) / 2, w=x1 - x0, h=y1 - y0))
    # barras femea do ESP32: encostadas na placa, o fio do jumper nao atravessa a
    # faixa dos pinos (pode passar embaixo do modulo, entre as barras, e dobrar na ponta)
    u1 = [loc(p.GetPosition()) for p in b.FindFootprintByReference('U1').Pads()]
    for yb in sorted({round(y, 2) for _, y in u1}):
        xs = [x for x, y in u1 if abs(y - yb) < 0.1]
        sem_jumper.append(dict(x=(min(xs) + max(xs)) / 2, y=yb, w=max(xs) - min(xs), h=2.54))
    larg = {}
    for nome, (w, redes) in P.CLASSES.items():
        for r in redes:
            larg[r] = w
    redes = sorted({p['rede'] for p in pads if p['rede']})
    ordem = [r for r in ORDEM if r.split(':')[0] in redes] + [r for r in redes if r not in ORDEM]
    geo = dict(raio=P.DISCO_D / 2, folga=P.FOLGA, folga_borda=P.FOLGA_BORDA,
               pescoco=P.LARG_PESCOCO, larguras=larg, larg_padrao=P.CLASSES['Default'][0],
               jumper_ilha=P.JUMPER_ILHA, pads=pads, sem_cobre=sem_cobre,
               sem_jumper=sem_jumper, fixas=anel(), ordem=ordem,
               # GND por onde passa a corrente dos motores: so cobre da placa
               gnd_potencia=['J1.2', 'C1.2', 'U2.2', 'U1.20'] + [f'Q{n}.2' for n in range(1, 5)],
               # pinos ligados por dentro do proprio modulo
               grupos_internos=[['U1.14', 'U1.20', 'U1.26'], ['U2.2', 'U2.4']],
               # pinos ligados so DEPOIS dos sinais (rede:adiado): o 3V3 do J4 nao pode
               # dar a volta no ESP32 e fechar o caminho de todo mundo; entra por jumper
               # e o 5V do J2 entra depois do sonar (senao desce em diagonal no corredor dele)
               adiar={'+3V3': ['J4.1'], '+5V': ['J2.6']})
    json.dump(geo, open(GEO, 'w'), indent=1)
    print('geometria:', len(pads), 'pinos,', len(redes), 'redes ->', GEO)


def trilha(b, rede, x1, y1, x2, y2, w, camada):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(kpt(x1, y1))
    t.SetEnd(kpt(x2, y2))
    t.SetWidth(MM(w))
    t.SetLayer(camada)
    t.SetNet(b.FindNet(rede))
    b.Add(t)


def via(b, rede, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(kpt(x, y))
    v.SetDrill(MM(P.JUMPER_FURO))
    v.SetWidth(MM(P.JUMPER_ILHA))
    v.SetNet(b.FindNet(rede))
    b.Add(v)


def texto(b, s, x, y, alt, camada, espelhar=False, ang=0):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(s)
    t.SetPosition(kpt(x, y))
    t.SetLayer(camada)
    t.SetTextSize(pcbnew.VECTOR2I(MM(alt), MM(alt)))
    t.SetTextThickness(MM(alt * 0.18))
    t.SetMirrored(espelhar)
    t.SetTextAngleDegrees(ang)
    b.Add(t)


def aplicar():
    # parte sempre da placa recem-montada (gerar.py placa), sem trilhas
    b = pcbnew.LoadBoard(PCB)
    if len(b.GetTracks()):
        raise SystemExit('rode antes: python3 gerar.py placa (a placa ja tem trilhas)')
    r = json.load(open(ROTAS))
    for t in anel() + r['trilhas']:
        trilha(b, t['rede'], t['x1'], t['y1'], t['x2'], t['y2'], t['w'], pcbnew.B_Cu)
    # jumpers em sequencia (um termina onde o outro comeca) dividem o MESMO furo
    furos = []                                   # (rede, x, y)

    def furo(rede, x, y):
        for (rr, fx, fy) in furos:
            if rr == rede and math.hypot(fx - x, fy - y) < 1.6:
                return fx, fy
        furos.append((rede, x, y))
        via(b, rede, x, y)
        return x, y
    for j in r['jumpers']:
        x1, y1 = furo(j['rede'], j['x1'], j['y1'])
        x2, y2 = furo(j['rede'], j['x2'], j['y2'])
        trilha(b, j['rede'], x1, y1, x2, y2, 0.8, pcbnew.F_Cu)

    # plano de GND embaixo: menos cobre para corroer, retorno largo dos motores
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNet(b.FindNet('GND'))
    z.SetLocalClearance(MM(P.FOLGA))
    z.SetMinThickness(MM(1.0))
    z.SetThermalReliefGap(MM(P.FOLGA))
    z.SetThermalReliefSpokeWidth(MM(1.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    for i in range(120):
        a = 2 * math.pi * i / 120
        rr = P.DISCO_D / 2 - 0.2
        o.Append(MM(CX + rr * math.cos(a)), MM(CY - rr * math.sin(a)))
    b.Add(z)

    # textos no cobre (embaixo = espelhado, para ler pelo lado do cobre)
    texto(b, 'VoaSul | Drones', 0, TEXTO_Y, 1.3, pcbnew.B_Cu, espelhar=True)
    for d in list(b.GetDrawings()):
        if d.GetLayer() == pcbnew.Dwgs_User:
            b.Remove(d)
    regua(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    print('aplicado:', len(r['trilhas']), 'trilhas,', len(r['jumpers']), 'jumpers;',
          'falhas:', r['falhas'])


def drc():
    b = pcbnew.LoadBoard(PCB)
    rel = os.path.join(AQUI, 'drc.txt')
    pcbnew.WriteDRCReport(b, rel, pcbnew.EDA_UNITS_MILLIMETRES, True)
    cont = {}
    for linha in open(rel):
        if linha.startswith('['):
            k = linha.split(']')[0][1:]
            cont[k] = cont.get(k, 0) + 1
    print('DRC:', cont)


def redes_txt(b, caminho):
    redes = {}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname():
                redes.setdefault(p.GetNetname(), []).append(f'{fp.GetReference()}.{p.GetNumber()}')
    with open(caminho, 'w') as f:
        f.write('# Redes da placa (use para o teste de continuidade: bip de ponta a ponta)\n')
        for n in sorted(redes):
            f.write(f'{n:10s} {" ".join(sorted(redes[n]))}\n')


def saidas():
    import subprocess
    out = os.path.join(AQUI, 'saidas')
    os.makedirs(out, exist_ok=True)
    b = pcbnew.LoadBoard(PCB)
    redes_txt(b, os.path.join(out, 'redes.txt'))
    # lista de jumpers (fio por cima): de onde, para onde, rede e bitola
    js = [t for t in b.GetTracks() if t.GetClass() != 'PCB_VIA' and t.GetLayer() == pcbnew.F_Cu]
    with open(os.path.join(out, 'jumpers.txt'), 'w') as f:
        f.write('# Jumpers: fio rigido por CIMA da placa (lado dos componentes), soldado embaixo.\n'
                '# Coordenadas em mm a partir do CENTRO do disco; X para a direita, Y para a FRENTE.\n'
                '# Solde todos ANTES dos modulos (ESP32, BMI160, BMP280).\n\n')
        f.write(f'{"n":>2}  {"rede":8s} {"de (x, y)":>16s}   {"para (x, y)":>16s}  {"compr.":>6s}  fio\n')
        for k, t in enumerate(sorted(js, key=lambda t: t.GetNetname()), 1):
            x1, y1 = loc(t.GetStart())
            x2, y2 = loc(t.GetEnd())
            fio = '20-22 AWG (GND: pode levar corrente de motor)' if t.GetNetname() == 'GND' else 'qualquer fio rigido fino'
            f.write(f'{k:2d}  {t.GetNetname():8s} ({x1:6.1f}, {y1:6.1f})   ({x2:6.1f}, {y2:6.1f})  '
                    f'{math.hypot(x2 - x1, y2 - y1):5.1f}   {fio}\n')

    def cli(*a):
        subprocess.run(['kicad-cli', 'pcb', 'export', *a, PCB], check=True, capture_output=True)
    # transferencia: so o cobre de baixo, preto, 1:1, SEM espelhar (vista de cima)
    cli('pdf', '--layers', 'B.Cu,Edge.Cuts,Dwgs.User', '--black-and-white', '--ibt',
        '--drill-shape-opt', '2', '-o', os.path.join(out, 'transferencia_B_Cu.pdf'))
    # montagem por cima (pecas THT, jumpers) e por baixo (SMD, vista por baixo)
    cli('pdf', '--layers', 'F.SilkS,F.Fab,F.Cu,Edge.Cuts,Dwgs.User', '--ibt', '--ev',
        '-o', os.path.join(out, 'montagem_cima.pdf'))
    cli('pdf', '--layers', 'B.SilkS,B.Fab,B.Cu,Edge.Cuts', '--mirror', '--ibt', '--ev',
        '-o', os.path.join(out, 'montagem_baixo_vista_por_baixo.pdf'))
    cli('svg', '--layers', 'B.Cu,F.Cu,F.SilkS,Edge.Cuts', '--page-size-mode', '2',
        '--exclude-drawing-sheet', '-o', os.path.join(out, 'placa.svg'))
    # 3D: ver gerar.py cena3d + saidas/visualizador3d.html
    print(conferir_esquema(b, out))
    print('saidas em', out)


def conferir_esquema(b, out):
    """netlist exportada pelo KiCad do ESQUEMA x redes da PLACA. Escreve
    saidas/conferencia.txt (usado na folha de montagem) e para tudo se houver diferenca."""
    import re
    import subprocess
    sch = os.path.join(AQUI, 'drone.kicad_sch')
    net = os.path.join(out, 'esquema.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '-o', net, sch], check=True, capture_output=True)
    txt = open(net).read()
    esq = {}
    for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)', txt, re.S):
        nome = m.group(1).lstrip('/')
        nos = set(re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
        if nome.startswith('unconnected') or len(nos) < 1:
            continue
        esq[nome] = nos
    placa = {}
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            if pd.GetNetname():
                placa.setdefault(pd.GetNetname(), set()).add((fp.GetReference(), pd.GetNumber()))
    dif = []
    for n in sorted(set(esq) | set(placa)):
        if esq.get(n, set()) != placa.get(n, set()):
            dif.append(f'{n}: esquema {sorted(esq.get(n, set()) - placa.get(n, set()))} '
                       f'placa {sorted(placa.get(n, set()) - esq.get(n, set()))}')
    npin = sum(len(v) for v in placa.values())
    if dif:
        raise SystemExit('ESQUEMA x PLACA DIFEREM:\n  ' + '\n  '.join(dif))
    res = f'{len(placa)} redes, {npin} pinos'
    open(os.path.join(out, 'conferencia.txt'), 'w').write(res + '\n')
    return 'esquema x placa: 0 diferencas (' + res + ')'


def regua(b):
    """regua de 100 mm na folha (fora da placa) para conferir a escala impressa"""
    y = -56.0
    def seg(x1, y1, x2, y2):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(kpt(x1, y1))
        s.SetEnd(kpt(x2, y2))
        s.SetLayer(pcbnew.Dwgs_User)
        s.SetWidth(MM(0.25))
        b.Add(s)
    seg(-50, y, 50, y)
    for k in range(11):
        h = 3 if k % 5 == 0 else 1.5
        seg(-50 + 10 * k, y, -50 + 10 * k, y - h)
    texto(b, 'REGUA 100 mm: confira com uma regua antes de passar o ferro', 0, y + 2.5, 1.8, pcbnew.Dwgs_User)
    texto(b, 'DRONE VoaSul  face unica  cobre (B.Cu) vista de cima  NAO espelhar', 0, 54.5, 1.8, pcbnew.Dwgs_User)


# ------------------------------------------------------------------ PROFISSIONAL
def profissional():
    """Versao para fabrica de PCB (JLCPCB, PCBWay...): mesma placa, mesmas trilhas,
    mas com furo metalizado e ilhas nas DUAS faces, os jumpers viram trilhas de
    cima com via, plano de GND nas duas faces, mascara e serigrafia.
    Saida: pro/drone_pro.kicad_pcb + pro/gerber/*.gbr + pro/drone_pro_gerber.zip"""
    import shutil
    import subprocess
    import zipfile
    pasta = os.path.join(AQUI, 'pro')
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, 'drone_pro.kicad_pcb')
    b = pcbnew.LoadBoard(PCB)
    # ilhas nas duas faces (furo metalizado)
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                p.SetLayerSet(pcbnew.PAD.PTHMask())
    # jumpers: via menor e trilha de cima de 0,8 mm (ja saem do roteador assim)
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            t.SetDrill(MM(0.5))
            t.SetWidth(MM(1.0))
    # plano de GND em cima tambem (o de baixo ja existe)
    for z in list(b.Zones()):
        if not z.GetIsRuleArea() and z.GetLayer() == pcbnew.B_Cu:
            z2 = z.Duplicate()
            z2.SetLayer(pcbnew.F_Cu)
            b.Add(z2)
    texto(b, 'VoaSul Drones  rev C  2026', 0, -40.5, 1.4, pcbnew.F_SilkS)
    for d in list(b.GetDrawings()):
        if d.GetLayer() == pcbnew.Dwgs_User:
            b.Remove(d)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(destino, b)
    for ext in ('.kicad_pro', '.kicad_dru'):
        shutil.copy(PCB.replace('.kicad_pcb', ext), destino.replace('.kicad_pcb', ext))
    # regras de fabrica (JLCPCB/PCBWay, 2 camadas): furo e via bem menores que na caseira.
    # As trilhas continuam grossas e com 0,8 mm de folga: so os limites minimos mudam.
    pro_json = destino.replace('.kicad_pcb', '.kicad_pro')
    with open(pro_json) as f:
        pj = json.load(f)
    pj['board']['design_settings']['rules'].update(
        min_via_diameter=0.6, min_via_annular_width=0.13, min_through_hole_diameter=0.3,
        min_hole_to_hole=0.25, min_hole_clearance=0.25)
    sev = pj['board']['design_settings'].setdefault('rule_severities', {})
    sev.update(silk_over_copper='ignore', silk_overlap='ignore', lib_footprint_issues='ignore',
               lib_footprint_mismatch='ignore')
    with open(pro_json, 'w') as f:
        json.dump(pj, f, indent=2)
    # DRC da versao profissional
    # (processo separado: o KiCad guarda o projeto antigo em cache neste processo)
    subprocess.run([sys.executable, '-c',
                    'import pcbnew; pcbnew.WriteDRCReport(pcbnew.LoadBoard(%r), %r, '
                    'pcbnew.EDA_UNITS_MILLIMETRES, True)' % (destino, os.path.join(pasta, 'drc_pro.txt'))],
                   check=True, capture_output=True)
    # gerbers + furacao
    gdir = os.path.join(pasta, 'gerber')
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)
    camadas = 'F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'
    subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers', '--layers', camadas,
                    '--no-x2', '--subtract-soldermask', '-o', gdir + '/', destino],
                   check=True, capture_output=True)
    subprocess.run(['kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon',
                    '--excellon-separate-th', '--generate-map', '--map-format', 'gerberx2',
                    '-o', gdir + '/', destino], check=True, capture_output=True)
    z = os.path.join(pasta, 'drone_pro_gerber.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(gdir)):
            zf.write(os.path.join(gdir, f), f)
    print('profissional:', destino, '|', z, '|', sorted(os.listdir(gdir)))


def cena3d():
    """cena3d.json: pecas (posicao, giro, lado, modelos) + cobre, para o visualizador 3D"""
    b = pcbnew.LoadBoard(PCB)
    pecas = []
    for fp in b.GetFootprints():
        x, y = loc(fp.GetPosition())
        mods = []
        for m in fp.Models():
            nome = os.path.basename(m.m_Filename)
            mods.append(dict(arq=nome, off=[m.m_Offset.x, m.m_Offset.y, m.m_Offset.z],
                             rot=[m.m_Rotation.x, m.m_Rotation.y, m.m_Rotation.z],
                             esc=[m.m_Scale.x, m.m_Scale.y, m.m_Scale.z]))
        pecas.append(dict(ref=fp.GetReference(), valor=fp.GetValue(), x=x, y=y,
                          rot=fp.GetOrientationDegrees(),
                          lado='B' if fp.GetLayer() == pcbnew.B_Cu else 'F', modelos=mods))
    trilhas, vias, pads = [], [], []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            x, y = loc(t.GetPosition())
            vias.append(dict(x=x, y=y, d=pcbnew.ToMM(t.GetWidth())))
        else:
            x1, y1 = loc(t.GetStart())
            x2, y2 = loc(t.GetEnd())
            trilhas.append(dict(x1=x1, y1=y1, x2=x2, y2=y2, w=pcbnew.ToMM(t.GetWidth()),
                                lado='B' if t.GetLayer() == pcbnew.B_Cu else 'F', rede=t.GetNetname()))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            x, y = loc(p.GetPosition())
            s = p.GetSize()
            pads.append(dict(x=x, y=y, w=pcbnew.ToMM(s.x), h=pcbnew.ToMM(s.y), rot=p.GetOrientationDegrees(),
                             furo=pcbnew.ToMM(p.GetDrillSize().x), circ=p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE,
                             oval=p.GetShape() == pcbnew.PAD_SHAPE_OVAL))
    zona = []
    for z in b.Zones():
        if not z.GetIsRuleArea() and z.GetLayer() == pcbnew.B_Cu:
            fl = z.GetFilledPolysList(pcbnew.B_Cu)
            for i in range(fl.OutlineCount()):
                o = fl.Outline(i)
                zona.append([list(loc(o.CPoint(k))) for k in range(o.PointCount())])
                for h in range(fl.HoleCount(i)):
                    pass
    out = os.path.join(AQUI, 'saidas', 'cena3d.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(dict(raio=P.DISCO_D / 2, pecas=pecas, trilhas=trilhas, vias=vias, pads=pads),
              open(out, 'w'))
    print('cena 3D:', len(pecas), 'pecas,', len(trilhas), 'trilhas ->', out)
