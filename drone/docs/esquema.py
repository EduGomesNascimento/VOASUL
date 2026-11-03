#!/usr/bin/env python3
"""
Esquema eletrico do drone -- ESP32 DevKit de 38 pinos.

    pip install schemdraw matplotlib
    python3 esquema.py              # esquema.pdf (3 folhas A3), .svg e .png

Os GPIO saem de include/board_esp32.h. Mudou um pino la, mude aqui tambem: nem
o teste de sinais nem o mixer conferem a fiacao por voce.

As ligacoes entre blocos sao por ETIQUETA DE REDE: dois pontos com o mesmo nome
(M_FR, SDA, +5V...) estao ligados, mesmo sem fio desenhado entre eles. E o jeito
padrao de desenhar esquema com muitos blocos sem virar macarrao.

Nota de schemdraw, para quem for mexer: em elemento VERTICAL, label 'bottom'
cai a direita e 'top' a esquerda. E caixa de CI (elm.Ic) herda a rotacao do
elemento anterior -- por isso todas levam .theta(0).
"""

import schemdraw
import schemdraw.elements as elm

FS_BASE, FS_T_BASE, LW_BASE = 10, 12, 1.2
FS, FS_T, LW = FS_BASE, FS_T_BASE, LW_BASE   # ajustados por escala() nas folhas A3


def escala(s):
    """Fonte e traco acompanham a reducao da folha, senao o texto (em pontos)
    fica grande demais para o desenho (em unidades) e encavala."""
    global FS, FS_T, LW
    FS, FS_T, LW = FS_BASE * s, FS_T_BASE * s, LW_BASE * s

# canal, GPIO, sentido de giro visto de cima -- igual a src/motors.cpp
CANAIS = [
    ('FR', 25, 'anti-horário'),
    ('RR', 26, 'horário'),
    ('RL', 27, 'anti-horário'),
    ('FL', 4,  'horário'),
]

REV = 'rev. A · 2026-10-06'


# ---------------------------------------------------------------- utilitarios

def tag(at, nome, lado='left', comp=0.6):
    """Fio curto saindo de `at` e terminando numa etiqueta de rede."""
    ln = getattr(elm.Line().at(at), lado)(comp)
    getattr(elm.Tag().at(ln.end), lado)().label(nome, fontsize=FS - 1)


def terra(at, lado='left', comp=0.6):
    """Fio curto saindo de `at` e terminando no simbolo de GND."""
    ln = getattr(elm.Line().at(at), lado)(comp)
    elm.Ground().at(ln.end)


def texto(x, y, s, fs=FS, **kw):
    elm.Label().at((x, y)).label(s, fontsize=fs, halign='left', **kw)


def titulo(x, y, s):
    texto(x, y, s, fs=FS_T)


def caixa(nome, pinos, at, pinspacing=0.9, w=None):
    """Modulo como caixa de CI. pinos = [(nome, lado), ...], lado 'L' ou 'R'.
    Devolve o elemento; os pinos ficam como atributos p0, p1, ..."""
    ps = [elm.IcPin(name=n, side=s, anchorname=f'p{i}') for i, (n, s) in enumerate(pinos)]
    kw = dict(pins=ps, pinspacing=pinspacing, edgepadH=0.5, edgepadW=0.6, lsize=FS)
    if w:
        kw['size'] = (w, None)
    return elm.Ic(**{k: v for k, v in kw.items() if v is not None}).theta(0).at(at) \
              .label(nome, 'top', fontsize=FS)


# ---------------------------------------------------------------- potencia

def bloco_alimentacao(x0, y0):
    titulo(x0 - 1, y0 + 2.2, 'ALIMENTAÇÃO')

    # J1 -- bateria. Barramento VBAT na horizontal, no alto do bloco.
    bat = elm.Battery().up().at((x0, y0 - 4.5)).label(
        'J1  bateria\nLiPo 1S 530 mAh\n30C · 3,3–4,2 V', 'top', fontsize=FS)
    elm.Ground().at(bat.start)
    rail_y = y0
    elm.Line().at(bat.end).toy(rail_y)
    elm.Line().right(15.5)
    tag((x0 + 15.5, rail_y), 'VBAT', 'right')

    # C1 -- reserva para o pico dos motores, colado no conector
    x = x0 + 2.4
    elm.Dot().at((x, rail_y))
    c1 = elm.Capacitor(polar=True).down().at((x, rail_y)) \
            .label('C1\n1000 µF\n10 V', 'bottom', fontsize=FS)
    elm.Ground().at(c1.end)

    # R9/R10 -- VBAT/2 no ADC1 (o ADC2 nao funciona com o WiFi ligado)
    x = x0 + 6.0
    elm.Dot().at((x, rail_y))
    r9 = elm.Resistor().down().at((x, rail_y)).label('R9\n10 kΩ', 'bottom', fontsize=FS)
    elm.Dot().at(r9.end)
    r10 = elm.Resistor().down().at(r9.end).label('R10\n10 kΩ', 'bottom', fontsize=FS)
    elm.Ground().at(r10.end)
    tag(r9.end, 'VBAT_ADC', 'left', comp=0.8)

    # U2 -- step-up para 5 V (ESP32 e ultrassonicos)
    x = x0 + 9.6
    elm.Dot().at((x, rail_y))
    up = caixa('U2  step-up (MT3608)',
               [('IN−', 'L'), ('IN+', 'L'), ('OUT−', 'R'), ('OUT+', 'R')],
               at=(x + 1.0, rail_y - 4.2), pinspacing=1.1)
    elm.Wire('|-').at((x, rail_y)).to(up.p1)
    terra(up.p0, 'left', 0.5)
    terra(up.p2, 'right', 0.5)
    tag(up.p3, '+5V', 'right')
    texto(x - 0.6, rail_y - 5.6, 'Gire o trimpot até medir 5,0 V\nna saída ANTES de ligar o ESP32.',
          fs=FS - 1, color='firebrick')


def bloco_motores(x0, y0, colunas=4):
    titulo(x0 - 3, y0 + 2.2, 'DRIVER DOS MOTORES · 4 canais iguais, MOSFET no lado de baixo')
    linhas = (len(CANAIS) + colunas - 1) // colunas
    for i, (nome, gpio, sentido) in enumerate(CANAIS):
        n = i + 1
        cx = x0 + (i % colunas) * 7.6
        cy = y0 - (i // colunas) * 9.6
        texto(cx - 2.4, cy + 1.1, f'{nome} · GPIO {gpio} · {sentido}')

        # VBAT -> motor -> dreno
        tag((cx, cy), 'VBAT', 'left', comp=0.5)
        mot = elm.Motor().down().at((cx, cy)).label(f'M{n}\n1020', 'top', fontsize=FS)
        dreno = mot.end
        elm.Dot().at((cx, cy))
        elm.Dot().at(dreno)

        # D -- roda livre: anodo no dreno, catodo no VBAT
        elm.Line().at((cx, cy)).right(1.5)
        elm.Schottky().down().reverse().label(f'D{n}\nSS34', 'bottom', fontsize=FS)
        elm.Line().left(1.5)

        # C -- 100 nF soldado nos terminais do motor
        elm.Line().at((cx + 1.5, cy)).right(1.9)
        elm.Capacitor().down().label(f'C{n + 2}\n100 nF', 'bottom', fontsize=FS)
        elm.Line().left(1.9)

        # Q -- dreno no motor, fonte no GND, porta pela esquerda
        elm.Line().at(dreno).down(0.5)
        q = elm.NFet().right().reverse().anchor('drain') \
               .label(f'Q{n}\nAO3400A', 'right', ofst=(0.2, 0.3), fontsize=FS)
        elm.Ground().at(q.source)

        # porta: 100 ohm em serie, 10 k para o GND (porta em LOW no boot)
        elm.Line().at(q.gate).left(0.4)
        g = elm.Dot()
        rs = elm.Resistor().left(2.0).label(f'R{n}\n100 Ω', 'top', fontsize=FS)
        tag(rs.end, f'M_{nome}', 'left', comp=0.3)
        rg = elm.Resistor().down(2.0).at(g.center).label(f'R{n + 4}\n10 kΩ', 'bottom',
                                                         fontsize=FS)
        elm.Ground().at(rg.end)

    notas = ['AO3400A (SOT-23): pino 1 = porta (G), 2 = fonte (S), 3 = dreno (D).',
             'SS34: a faixa no corpo é o catodo, vai no VBAT.',
             'Caminho de potência (VBAT → motor → MOSFET → GND, até 12 A no total):',
             'fio de silicone 20 AWG. O resto é sinal: qualquer fio fino serve.']
    sep = '\n' if colunas < 4 else '   '
    texto(x0 - 3, y0 - 6.4 - (linhas - 1) * 9.6,
          (notas[0] + sep + notas[1] + '\n' + notas[2] + sep + notas[3]),
          fs=FS - 1)


# ---------------------------------------------------------------- controle

ESP_L = [('5V (VIN)', '+5V'), ('3V3', '3V3'), ('GND', None),
         ('IO36 (VP)', 'VBAT_ADC'), ('IO39 (VN)', 'IR_E'), ('IO34', 'ECHO_B'),
         ('IO35', 'ECHO_F'), ('IO32', 'IR_D'), ('IO33', 'TRIG_F')]
ESP_R = [('IO25', 'M_FR'), ('IO26', 'M_RR'), ('IO27', 'M_RL'), ('IO4', 'M_FL'),
         ('IO13', 'TRIG_B'), ('IO21', 'SDA'), ('IO22', 'SCL'), ('IO2', '·LED'),
         ('GND', None)]


def bloco_controle(x0, y0):
    titulo(x0 - 1, y0 + 2.2, 'CONTROLE E RÁDIO')

    # Ic desenha os pinos de cada lado de baixo para cima; invertemos para a
    # lista acima ler de cima para baixo.
    pinos = [(n, 'L') for n, _ in reversed(ESP_L)] + [(n, 'R') for n, _ in reversed(ESP_R)]
    esp = caixa('U1  ESP32 DevKit 38 pinos (WROOM-32)', pinos,
                at=(x0 + 4, y0 - 9.5), pinspacing=0.95)

    nl = len(ESP_L)
    for i, (_, net) in enumerate(reversed(ESP_L)):
        p = getattr(esp, f'p{i}')
        if net is None:
            terra(p, 'left', 0.6)
        else:
            tag(p, net, 'left', comp=0.6)
    for j, (_, net) in enumerate(reversed(ESP_R)):
        p = getattr(esp, f'p{nl + j}')
        if net is None:
            terra(p, 'right', 0.6)
        elif net.startswith('·'):
            elm.Line().at(p).right(0.6).label('LED da placa', 'right', fontsize=FS - 1)
        else:
            tag(p, net, 'right', comp=0.6)

    gnd_d = getattr(esp, f'p{nl}')
    texto(gnd_d[0] + 3.4, gnd_d[1] + 0.2,
          'Rádio: WiFi 2,4 GHz, 19,5 dBm, só 802.11b.\n'
          'Antena (ponta do módulo) para FORA da placa\n'
          'perfurada: nada de cobre, bateria ou fio\na menos de 15 mm dela.', fs=FS - 1)

    # C2 -- reserva para as rajadas do radio, colada no pino 5V do ESP32
    cx, cy = x0 + 1.0, y0 - 11.6
    tag((cx, cy), '+5V', 'left', comp=0.4)
    elm.Dot().at((cx, cy))
    c2 = elm.Capacitor(polar=True).down().at((cx, cy)).label(
        'C2  470 µF 10 V\ncolado no pino 5V\ndo ESP32', 'bottom', fontsize=FS)
    elm.Ground().at(c2.end)


# ---------------------------------------------------------------- sensores

def i2c(nome, pinos, at, nota):
    """Modulo I2C: todos os pinos a esquerda, cada um para a sua rede."""
    pins = [(n, 'L') for n, _ in reversed(pinos)]
    u = caixa(nome, pins, at=at, pinspacing=1.05)
    for i, (_, net) in enumerate(reversed(pinos)):
        p = getattr(u, f'p{i}')
        if net == 'GND':
            terra(p, 'left', 0.6)
        elif net == 'NC':
            elm.Line().at(p).left(0.6).label('sem ligação', 'left', fontsize=FS - 2)
        else:
            tag(p, net, 'left', comp=0.6)
    texto(at[0] + 3.0, at[1] + 1.2, nota, fs=FS - 1)
    return u


def bloco_sensores(x0, y0, ir=True):
    titulo(x0 - 3, y0 + 2.2, 'SENSORES')

    # --- IMU e barometro: mesmo barramento I2C (400 kHz) ---
    # GY-BMI160: 12 pinos. Esta e a fileira de 7; a outra (SDX, SCX, INT1,
    # INT2, OCS) e a interface auxiliar e as interrupcoes -- nao usadas.
    i2c('U3  BMI160 (GY-BMI160)', [('VIN', 'NC'), ('3V3', '3V3'), ('GND', 'GND'),
                                   ('SCL', 'SCL'), ('SDA', 'SDA'), ('CS', '3V3'),
                                   ('SAO', '3V3')],
        at=(x0, y0 - 5.6),
        nota='I2C 0x69\nCS no 3V3 = modo I2C\nseta Y → nariz, Z → cima\n'
             'outra fileira (SDX, SCX,\nINT1, INT2, OCS):\nsem ligação')
    i2c('U4  BMP280', [('VCC', '3V3'), ('GND', 'GND'), ('SCL', 'SCL'),
                       ('SDA', 'SDA'), ('CSB', '3V3'), ('SDO', 'GND')],
        at=(x0, y0 - 14.2),
        nota='I2C 0x76\nmódulo de 3,3 V\nespuma por cima\n(vento da hélice)')

    # --- ultrassonicos: 5 V, ECHO por divisor 1 k / 2 k (5 V -> 3,3 V) ---
    for k, (lado, trig, echo, ra, rb) in enumerate([
            ('baixo (altura)', 'TRIG_B', 'ECHO_B', 11, 13),
            ('frente (desvio)', 'TRIG_F', 'ECHO_F', 12, 14)]):
        bx, by = x0 + 11.5, y0 - 3.4 - k * 7.6
        u = caixa(f'U{5 + k}  HC-SR04 {lado}',
                  [('GND', 'L'), ('ECHO', 'L'), ('TRIG', 'L'), ('VCC', 'L')],
                  at=(bx, by - 2.4), pinspacing=0.9)
        tag(u.p3, '+5V', 'left', comp=0.6)
        tag(u.p2, trig, 'left', comp=0.6)
        terra(u.p0, 'left', 0.6)
        # ECHO -> 1 k -> no -> ESP32 ; no -> 2 k -> GND
        ra_ = elm.Resistor().left(2.0).at(u.p1).label(f'R{ra}  1 kΩ', 'top', fontsize=FS)
        no = elm.Dot()
        tag(no.center, echo, 'left', comp=0.4)
        rb_ = elm.Resistor().down(1.8).at(no.center).label(f'R{rb}\n2 kΩ', 'top', fontsize=FS)
        elm.Ground().at(rb_.end)
    texto(x0 + 6.6, y0 - 15.8, 'ECHO sai em 5 V; o divisor\nentrega 3,3 V ao ESP32.\n'
          '(2,2 kΩ no lugar de 2 kΩ dá 3,4 V,\nainda dentro do limite de 3,6 V)', fs=FS - 1)

    if ir:
        bloco_ir(x0 + 21.5, y0 - 4.0)


def bloco_ir(bx0, by0, titulo_=None):
    """FC-51 no 3V3, assim a saida ja sai em 3,3 V."""
    if titulo_:
        titulo(bx0 - 5.5, by0 + 1.6, titulo_)
    for k, (lado, net) in enumerate([('esquerdo', 'IR_E'), ('direito', 'IR_D')]):
        bx, by = bx0, by0 - k * 6.0
        u = caixa(f'U{7 + k}  FC-51 {lado}', [('GND', 'L'), ('OUT', 'L'), ('VCC', 'L')],
                  at=(bx, by - 1.6), pinspacing=0.9)
        tag(u.p2, '3V3', 'left', comp=0.6)
        tag(u.p1, net, 'left', comp=0.6)
        terra(u.p0, 'left', 0.6)
    texto(bx0 - 3, by0 - 9.6, 'FC-51 no 3V3, NÃO no 5V:\na saída sai no nível do VCC.', fs=FS - 1)


# ---------------------------------------------------------------- montagem

def visao_geral():
    """Tudo numa imagem so (PNG/SVG): bom para tela, ruim para imprimir."""
    bloco_alimentacao(0, 0)
    bloco_motores(25, 0)
    bloco_controle(0, -10.5)
    bloco_sensores(23, -10.5)
    texto(0, -29.0, 'Drone — esquema elétrico · ESP32 DevKit 38 pinos · ' + REV +
          '   ·   pinos conforme include/board_esp32.h', fs=FS)
    texto(0, -30.1, 'Ligações por etiqueta de rede: pontos com o mesmo nome '
          'estão ligados.   Terra em estrela: o GND dos MOSFETs volta ao negativo '
          'da bateria por fio próprio, separado do GND do ESP32 e dos sensores.',
          fs=FS - 1)


def desenhar(arquivo_svg, arquivo_png):
    escala(1.0)
    for backend, arq in (('svg', arquivo_svg), ('matplotlib', arquivo_png)):
        schemdraw.use(backend)
        with schemdraw.Drawing(show=False) as d:
            d.config(fontsize=FS, unit=2.0, lw=LW, font='DejaVu Sans')
            visao_geral()
        if backend == 'svg':
            d.save(arq)
        else:
            d.save(arq, dpi=110)


# ---------------------------------------------------------------- folhas A3

MM = 1 / 25.4
A3 = (420, 297)
# area util: margem esquerda de 25 mm e 10 nas outras (ABNT NBR 10068);
# o desenho fica acima do carimbo
AREA = (32, 50, 403, 280)          # x0, y0, x1, y1 em mm

FOLHAS = [
    ('Potência — alimentação e driver dos motores',
     lambda: (bloco_alimentacao(0, 0), bloco_motores(25, 0, colunas=2))),
    ('Controle, rádio e sensores',
     lambda: (bloco_controle(0, 0), bloco_sensores(23, 0, ir=False),
              bloco_ir(15.0, -15.2, 'SENSORES IR (desvio lateral)'))),
]

# ref, peca, valor, o que procurar no Proteus (Pick Devices), observacao
BOM = [
    ('J1', 'Bateria LiPo 1S', '530 mAh 30C', 'BATTERY', 'Voltage = 3.7V'),
    ('C1', 'Capacitor eletrolítico', '1000 µF 10 V', 'CAP-ELEC', ''),
    ('C2', 'Capacitor eletrolítico', '470 µF 10 V', 'CAP-ELEC', ''),
    ('C3–C6', 'Capacitor cerâmico', '100 nF', 'CAP', 'nos terminais do motor'),
    ('R1–R4', 'Resistor', '100 Ω', 'RES', ''),
    ('R5–R10', 'Resistor', '10 kΩ', 'RES', ''),
    ('R11, R12', 'Resistor', '1 kΩ', 'RES', ''),
    ('R13, R14', 'Resistor', '2 kΩ', 'RES', ''),
    ('D1–D4', 'Diodo Schottky', 'SS34', '1N5822', 'troque o valor p/ SS34'),
    ('Q1–Q4', 'MOSFET canal N', 'AO3400A', 'IRLZ44N', 'troque o valor p/ AO3400A'),
    ('M1–M4', 'Motor coreless', '1020', 'MOTOR', ''),
    ('U1', 'ESP32 DevKit 38 pinos', 'WROOM-32', 'ESP32 DEVKIT V4', 'biblioteca ESP32_38P (nota 2)'),
    ('U2', 'Step-up', 'MT3608 → 5,0 V', 'CONN-SIL4', 'IN+ IN− OUT+ OUT−'),
    ('U3', 'IMU', 'GY-BMI160 (12 pinos)', 'CONN-SIL7', 'VIN 3V3 GND SCL SDA CS SAO'),
    ('U4', 'Barômetro', 'BMP280', 'CONN-SIL6', ''),
    ('U5, U6', 'Ultrassom', 'HC-SR04', 'CONN-SIL4', 'VCC TRIG ECHO GND'),
    ('U7, U8', 'Sensor IR', 'FC-51', 'CONN-SIL3', 'VCC GND OUT'),
]

# rede, pinos ligados
NETLIST = [
    ('VBAT', 'J1 +, C1 +, R9, U2 IN+, M1–M4 (+), D1–D4 catodo, C3–C6'),
    ('GND', 'J1 −, C1 −, C2 −, R10, R5–R8, R13, R14, U2 IN− e OUT−,\n'
            'Q1–Q4 fonte, U1 GND, U3–U8 GND, U4 SDO'),
    ('+5V', 'U2 OUT+, U1 5V, C2 +, U5 VCC, U6 VCC'),
    ('3V3', 'U1 3V3, U3 3V3/CS/SAO, U4 VCC/CSB, U7 VCC, U8 VCC'),
    ('VBAT_ADC', 'R9–R10 (meio), U1 IO36'),
    ('M_FR', 'U1 IO25 → R1'),
    ('M_RR', 'U1 IO26 → R2'),
    ('M_RL', 'U1 IO27 → R3'),
    ('M_FL', 'U1 IO4 → R4'),
    ('porta n', 'Rn, R(n+4), Qn porta          (n = 1 a 4)'),
    ('dreno n', 'Mn (−), Dn anodo, C(n+2), Qn dreno'),
    ('SDA', 'U1 IO21, U3 SDA, U4 SDA'),
    ('SCL', 'U1 IO22, U3 SCL, U4 SCL'),
    ('TRIG_B', 'U1 IO13 → U5 TRIG'),
    ('TRIG_F', 'U1 IO33 → U6 TRIG'),
    ('ECHO_B', 'U1 IO34, R11, R13      (U5 ECHO → R11)'),
    ('ECHO_F', 'U1 IO35, R12, R14      (U6 ECHO → R12)'),
    ('IR_E', 'U1 IO39 → U7 OUT'),
    ('IR_D', 'U1 IO32 → U8 OUT'),
]

NOTAS_PROTEUS = [
    '1.  Módulos (step-up, sensores) entram como CONECTOR com os pinos do módulo. O Proteus '
    'não tem esses módulos — e conector é o que de fato vai na placa: no ARES vira barra de pinos de 2,54 mm.',
    '2.  ESP32: copie ESP32_38PDVC.LIB/.IDX e ESP32_38PPKG.LIB/.IDX para a pasta LIBRARY do Proteus, '
    'reabra o Proteus e busque "ESP32 DEVKIT V4" (fica em Microprocessor ICs → AVR Family). Nela os '
    'pinos têm outro nome: IO25 → G25, IO4 → G04, IO2 → G02, IO36 → SP, IO39 → SN, 5V → V5; '
    'os demais seguem o número (IO13 → G13, IO21 → G21...).',
    '3.  Ligue os blocos por ETIQUETA DE FIO (Wire Label) com o nome da rede: mesmo nome = mesma ligação, '
    'igual a este esquema.',
    '4.  VBAT, +5V e 3V3: terminal POWER com o nome da rede. GND: terminal GROUND.',
    '5.  O nome das peças muda entre versões do Proteus. Não achou? Busque pela palavra: "schottky", '
    '"mosfet", "motor", "electrolytic".',
    '6.  O Proteus não simula o ESP32 nem os módulos. Mas simula UM canal de motor — gerador de pulso + '
    'MOSFET + MOTOR, com e sem o diodo — e mostra o pico de tensão que o diodo corta. Ótimo para o relatório de Potência.',
]


def moldura(fig, folha, total, conteudo):
    """Moldura e carimbo, em mm, numa camada que cobre a folha inteira."""
    import matplotlib.patches as mp
    pg = fig.add_axes([0, 0, 1, 1])
    pg.set_xlim(0, A3[0]); pg.set_ylim(0, A3[1]); pg.axis('off')
    pg.add_patch(mp.Rectangle((25, 10), 385, 277, fill=False, lw=1.0))
    # carimbo: 180 x 32 mm no canto inferior direito
    cx, cy, cw, ch = 230, 10, 180, 32
    pg.add_patch(mp.Rectangle((cx, cy), cw, ch, fill=False, lw=1.0))
    for y in (cy + 21, cy + 11):
        pg.plot([cx, cx + cw], [y, y], c='k', lw=0.6)
    pg.plot([cx + 130, cx + 130], [cy, cy + 21], c='k', lw=0.6)
    t = dict(fontsize=7, va='center', family='DejaVu Sans')
    pg.text(cx + 3, cy + 26.5, 'DRONE QUADRICÓPTERO — ESQUEMA ELÉTRICO',
            fontsize=11, weight='bold', va='center', family='DejaVu Sans')
    pg.text(cx + 3, cy + 16, conteudo, fontsize=8.5, va='center', family='DejaVu Sans')
    pg.text(cx + 3, cy + 5.5, 'Trabalho: Comunicações + Potência        Autor: ____________________', **t)
    pg.text(cx + 133, cy + 16, f'FOLHA {folha}/{total}', fontsize=10, weight='bold',
            va='center', family='DejaVu Sans')
    pg.text(cx + 133, cy + 5.5, f'{REV}\nA3 · sem escala', **t)
    pg.text(30, 13, 'Pinos conforme include/board_esp32.h. Ligações por etiqueta de rede: '
            'pontos com o mesmo nome estão ligados.\nTerra em estrela: o GND dos MOSFETs volta '
            'ao negativo da bateria por fio próprio, separado do GND do ESP32 e dos sensores.',
            fontsize=6.5, va='bottom', family='DejaVu Sans')
    return pg


def folha_esquema(fig, desenho):
    """Desenha um conjunto de blocos ajustado na AREA da folha."""
    import matplotlib
    # 1) mede em tamanho natural (0,5 pol por unidade, o padrao do schemdraw)
    escala(1.0)
    schemdraw.use('svg')
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=FS, unit=2.0, lw=LW)
        desenho()
    bb = d.get_bbox()
    w_in = (AREA[2] - AREA[0]) * MM
    h_in = (AREA[3] - AREA[1]) * MM
    s = min(w_in / ((bb.xmax - bb.xmin) * 0.5), h_in / ((bb.ymax - bb.ymin) * 0.5))
    # 2) desenha de verdade, com fonte e traco na mesma reducao
    escala(s)
    schemdraw.use('matplotlib')
    ax = fig.add_axes([AREA[0] / A3[0], AREA[1] / A3[1],
                       (AREA[2] - AREA[0]) / A3[0], (AREA[3] - AREA[1]) / A3[1]])
    ax.axis('off')
    with schemdraw.Drawing(canvas=ax, show=False) as d:
        d.config(fontsize=FS, unit=2.0, lw=LW, font='DejaVu Sans')
        desenho()
    d.draw(show=False, canvas=ax)    # com show=False, sair do `with` nao desenha
    bb = d.get_bbox()
    ax.set_xlim(bb.xmin, bb.xmax)
    ax.set_ylim(bb.ymin, bb.ymax)
    ax.set_aspect('equal', adjustable='datalim', anchor='C')
    return s


def tabela(ax, x, y, colunas, linhas, titulo_, fs=8.0, alt=5.4):
    """Tabela simples em mm. colunas = [(cabecalho, largura), ...]."""
    ax.text(x, y + 3, titulo_, fontsize=9.5, weight='bold', family='DejaVu Sans')
    larg = sum(w for _, w in colunas)
    def linha_h(yy, lw=0.5):
        ax.plot([x, x + larg], [yy, yy], c='k', lw=lw)
    linha_h(y, 0.9)
    xx = x
    for cab, w in colunas:
        ax.text(xx + 1.2, y - alt / 2, cab, fontsize=fs, weight='bold', va='center',
                family='DejaVu Sans')
        xx += w
    y -= alt
    linha_h(y, 0.9)
    for row in linhas:
        n = max(str(c).count('\n') + 1 for c in row)
        h = alt * n - (n - 1) * 1.2
        xx = x
        for (cab, w), c in zip(colunas, row):
            ax.text(xx + 1.2, y - h / 2, c, fontsize=fs, va='center', family='DejaVu Sans',
                    linespacing=1.25)
            xx += w
        y -= h
        linha_h(y)
    return y


def folha_proteus(fig, pg):
    tabela(pg, 32, 274,
           [('Ref.', 18), ('Peça', 40), ('Valor', 27), ('Procurar no Proteus', 40),
            ('Obs.', 45)],
           BOM, 'LISTA DE MATERIAIS — e o que digitar em "Pick Devices" (tecla P)')
    tabela(pg, 230, 274, [('Rede', 24), ('Pinos ligados', 150)],
                  NETLIST, 'LIGAÇÕES (netlist) — para conferir o seu desenho')
    pg.text(32, 140, 'COMO MONTAR NO PROTEUS', fontsize=10, weight='bold',
            family='DejaVu Sans')
    import textwrap
    y = 132
    for nota in NOTAS_PROTEUS:
        for i, ln in enumerate(textwrap.wrap(nota, 100)):
            pg.text(32 + (0 if i == 0 else 5), y, ln, fontsize=8.2, family='DejaVu Sans')
            y -= 4.4
        y -= 2.0


def folhas_pdf(arquivo_pdf):
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams['pdf.fonttype'] = 42   # texto selecionavel no PDF
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    total = len(FOLHAS) + 1
    escalas = []
    with PdfPages(arquivo_pdf) as pdf:
        for k, (conteudo, desenho) in enumerate(FOLHAS, 1):
            fig = plt.figure(figsize=(A3[0] * MM, A3[1] * MM))
            moldura(fig, k, total, conteudo)
            escalas.append(folha_esquema(fig, desenho))
            pdf.savefig(fig)
            plt.close(fig)
        fig = plt.figure(figsize=(A3[0] * MM, A3[1] * MM))
        pg = moldura(fig, total, total, 'Lista de materiais, ligações e como montar no Proteus')
        folha_proteus(fig, pg)
        pdf.savefig(fig)
        plt.close(fig)
    escala(1.0)
    return escalas


if __name__ == '__main__':
    import os
    aqui = os.path.dirname(os.path.abspath(__file__))
    desenhar(os.path.join(aqui, 'esquema.svg'), os.path.join(aqui, 'esquema.png'))
    esc = folhas_pdf(os.path.join(aqui, 'esquema.pdf'))
    print('esquema.svg e esquema.png (visão geral) e esquema.pdf (3 folhas A3) gerados')
    print('fonte nas folhas: ' + ', '.join(f'{FS_BASE * e:.1f} pt' for e in esc))
