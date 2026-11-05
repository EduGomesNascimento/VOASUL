#!/usr/bin/env python3
"""
Gera o esquema (drone.kicad_sch, KiCad 7) a partir de projeto.py.

Cada peca vira um bloco com os pinos nomeados; cada pino ligado recebe uma
ETIQUETA com o nome da rede (mesmo nome = mesma ligacao, como no Proteus).
Pino sem ligacao recebe o X de "nao conectado". Assim o esquema e a placa
saem da MESMA lista e nao tem como divergirem.
"""
import os
import uuid

import projeto as P

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, 'drone.kicad_sch')
G = 2.54
NS = uuid.UUID('6c1f0b1e-2a43-4d55-9a7e-0d0b0e5a1c01')


def uid(*partes):
    return str(uuid.uuid5(NS, '/'.join(map(str, partes))))


RAIZ = uid('raiz')

# nomes dos pinos por tipo de peca
NOMES = {
    'R_PE': {'1': '1', '2': '2'},
    'C_DISC': {'1': '1', '2': '2'},
    'C_0805': {'1': '1', '2': '2'},
    'CP_D8': {'1': '+', '2': '-'},
    'CP_D6': {'1': '+', '2': '-'},
    'SMA': {'1': 'K', '2': 'A'},
    'SOT23': {'1': 'G', '2': 'S', '3': 'D'},
    'MOTOR': {'1': '+', '2': '-'},
    'BATERIA': {'1': '+', '2': '-'},
    'MT3608': {'1': 'IN+', '2': 'IN-', '3': 'OUT+', '4': 'OUT-'},
    'GY_BMI160': dict(zip('1234567', ['VIN', '3V3', 'GND', 'SCL', 'SDA', 'CS', 'SAO'])),
    'GY_BMP280': dict(zip('123456', ['VCC', 'GND', 'SCL', 'SDA', 'CSB', 'SDO'])),
    'CONN4': dict(zip('1234', ['VCC', 'OUT_E', 'OUT_D', 'GND'])),
    'CONN6': dict(zip('123456', ['GND', 'ECHO_B', 'TRIG_B', 'ECHO_F', 'TRIG_F', 'VCC'])),
    'CONN2x3': dict(zip('123456', ['VCC', 'MISO', 'GND', 'SCK', 'CS', 'MOSI'])),
}
FOOTPRINT = {
    'R_PE': 'Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical',
    'C_DISC': 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    'C_0805': 'Capacitor_SMD:C_0805_2012Metric',
    'CP_D8': 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
    'CP_D6': 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',
    'SMA': 'Diode_SMD:D_SMA', 'SOT23': 'Package_TO_SOT_SMD:SOT-23',
    'MOTOR': 'drone:Ilhas_motor', 'BATERIA': 'drone:Ilhas_bateria',
    'MT3608': 'drone:MT3608_modulo', 'GY_BMI160': 'drone:GY_BMI160', 'GY_BMP280': 'drone:GY_BMP280',
    'CONN4': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
    'CONN6': 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
    'CONN2x3': 'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical',
    'ESP32_DEVKIT': 'drone:ESP32_DevKitC_38p',
}


def pinos_da_peca(pc):
    """lista (numero, nome, lado) -- lado 'E' esquerda / 'D' direita"""
    t = pc['tipo']
    if t == 'ESP32_DEVKIT':
        out = []
        for i, n in enumerate(P.ESP_J2):
            out.append((str(i + 1), n, 'E'))
        for i, n in enumerate(P.ESP_J3):
            out.append((str(i + 20), n, 'D'))
        return out
    nomes = NOMES[t]
    nums = sorted(nomes, key=int)
    if len(nums) <= 2:
        return [(nums[0], nomes[nums[0]], 'E'), (nums[1], nomes[nums[1]], 'D')]
    if t == 'MT3608':
        return [('1', 'IN+', 'E'), ('2', 'IN-', 'E'), ('3', 'OUT+', 'D'), ('4', 'OUT-', 'D')]
    if t == 'SOT23':
        return [('1', 'G', 'E'), ('3', 'D', 'D'), ('2', 'S', 'D')]
    return [(n, nomes[n], 'E') for n in nums]


def simbolo_lib(nome, pinos, larg=10.16):
    esq = [p for p in pinos if p[2] == 'E']
    dir_ = [p for p in pinos if p[2] == 'D']
    n = max(len(esq), len(dir_), 1)
    alt = n * G
    y0 = alt / 2
    s = [f'    (symbol "drone:{nome}" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)',
         f'      (property "Reference" "U" (at 0 {y0 + 2.54:.2f} 0) (effects (font (size 1.27 1.27))))',
         f'      (property "Value" "{nome}" (at 0 {-y0 - 2.54:.2f} 0) (effects (font (size 1.27 1.27))))',
         '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         '      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         f'      (symbol "{nome}_0_1" (rectangle (start {-larg / 2:.2f} {y0:.2f}) (end {larg / 2:.2f} {-y0:.2f})'
         ' (stroke (width 0.254) (type default)) (fill (type background))))',
         f'      (symbol "{nome}_1_1"']
    pos = {}
    for k, p in enumerate(esq):
        y = y0 - G / 2 - k * G
        x = -larg / 2 - G
        pos[p[0]] = (x, y)
        s.append(f'        (pin passive line (at {x:.2f} {y:.2f} 0) (length 2.54) '
                 f'(name "{p[1]}" (effects (font (size 1.0 1.0)))) (number "{p[0]}" (effects (font (size 1.0 1.0)))))')
    for k, p in enumerate(dir_):
        y = y0 - G / 2 - k * G
        x = larg / 2 + G
        pos[p[0]] = (x, y)
        s.append(f'        (pin passive line (at {x:.2f} {y:.2f} 180) (length 2.54) '
                 f'(name "{p[1]}" (effects (font (size 1.0 1.0)))) (number "{p[0]}" (effects (font (size 1.0 1.0)))))')
    s.append('      )')
    s.append('    )')
    return '\n'.join(s), pos, alt


# blocos do esquema: titulo, refs (na ordem), coluna, linha (mm na folha A3)
BLOCOS = [
    ('ALIMENTACAO', ['J1', 'C1', 'U2', 'C2', 'R9', 'R10'], 25, 40),
    ('CONTROLE (ESP32) E SENSORES DE BORDO', ['U1', 'U3', 'U4'], 140, 40),
    ('SONAR, IR E FLUXO OPTICO', ['J2', 'R11', 'R13', 'R12', 'R14', 'J3', 'J4'], 300, 40),
    ('MOTOR FR', ['M1', 'C3', 'D1', 'Q1', 'R1', 'R5'], 25, 175),
    ('MOTOR RR', ['M2', 'C4', 'D2', 'Q2', 'R2', 'R6'], 120, 175),
    ('MOTOR RL', ['M3', 'C5', 'D3', 'Q3', 'R3', 'R7'], 215, 175),
    ('MOTOR FL', ['M4', 'C6', 'D4', 'Q4', 'R4', 'R8'], 310, 175),
]


def gerar():
    pecas = {p['ref']: p for p in P.PECAS}
    libs, insts, textos = {}, [], []
    for titulo, refs, x0, y0 in BLOCOS:
        textos.append(f'  (text "{titulo}" (at {x0} {y0 - 8} 0) (effects (font (size 2.2 2.2) bold) (justify left bottom)) (uuid {uid("t", titulo)}))')
        y = y0
        col = 0
        for ref in refs:
            pc = pecas[ref]
            pins = pinos_da_peca(pc)
            nome = pc['tipo'] if pc['tipo'] != 'ESP32_DEVKIT' else 'ESP32_DEVKIT_38P'
            larg = 22.86 if pc['tipo'] == 'ESP32_DEVKIT' else 10.16
            if nome not in libs:
                libs[nome] = simbolo_lib(nome, pins, larg)
            _, pos, alt = libs[nome]
            sx = x0 + 18 + col * 46 if pc['tipo'] != 'ESP32_DEVKIT' else x0 + 40
            sy = y + alt / 2 + 4
            sy = round(sy / G) * G
            sx = round(sx / G) * G
            u = uid('s', ref)
            fp = FOOTPRINT[pc['tipo']]
            pin_uuids = '\n'.join(f'    (pin "{n}" (uuid {uid("p", ref, n)}))' for n, _, _ in pins)
            insts.append(
                f'  (symbol (lib_id "drone:{nome}") (at {sx:.2f} {sy:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no)\n'
                f'    (uuid {u})\n'
                f'    (property "Reference" "{ref}" (at {sx:.2f} {sy - alt / 2 - 2.54:.2f} 0) (effects (font (size 1.4 1.4) bold)))\n'
                f'    (property "Value" "{pc["valor"]}" (at {sx:.2f} {sy + alt / 2 + 2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
                f'    (property "Footprint" "{fp}" (at {sx:.2f} {sy:.2f} 0) (effects (font (size 1.27 1.27)) hide))\n'
                f'    (property "Datasheet" "" (at {sx:.2f} {sy:.2f} 0) (effects (font (size 1.27 1.27)) hide))\n'
                f'{pin_uuids}\n'
                f'    (instances (project "drone" (path "/{RAIZ}" (reference "{ref}") (unit 1))))\n'
                f'  )')
            for n, nm, lado in pins:
                px, py = pos[n]
                ax, ay = sx + px, sy - py
                rede = pc['pinos'].get(n)
                if rede:
                    just = 'right' if lado == 'E' else 'left'
                    insts.append(f'  (label "{rede}" (at {ax:.2f} {ay:.2f} {180 if lado == "E" else 0}) '
                                 f'(effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {uid("l", ref, n)}))')
                else:
                    insts.append(f'  (no_connect (at {ax:.2f} {ay:.2f}) (uuid {uid("nc", ref, n)}))')
            if pc['nota']:
                textos.append(f'  (text "{pc["nota"]}" (at {sx - 20:.2f} {sy + alt / 2 + 6:.2f} 0) '
                              f'(effects (font (size 1.0 1.0)) (justify left bottom)) (uuid {uid("n", ref)}))')
            if pc['tipo'] == 'ESP32_DEVKIT':
                y = sy + alt / 2 + 14
            else:
                col += 1
                if col == 2 or x0 + 18 + col * 46 > x0 + 95:
                    col = 0
                    y = sy + alt / 2 + 17
    notas = [
        'Placa de FACE UNICA: cobre so embaixo. Jumpers = fio por cima.',
        'Mesmo nome de etiqueta = mesma ligacao. Pinos conforme include/board_esp32.h.',
        'Trilhas: 2,5 mm (VBAT, drenos) / 1,5 mm (GND, 5V, 3V3) / 1,2 mm (sinais). Folga 0,8 mm.',
    ]
    for k, t in enumerate(notas):
        textos.append(f'  (text "{t}" (at 25 {270 + k * 5} 0) (effects (font (size 1.6 1.6)) (justify left bottom)) (uuid {uid("nota", k)}))')
    out = ['(kicad_sch (version 20230121) (generator eeschema)',
           f'  (uuid {RAIZ})',
           '  (paper "A3")',
           '  (title_block (title "Drone VoaSul - quadricoptero ESP32") (date "2026-11-03") (rev "C - face unica")'
           ' (company "Comunicacoes + Potencia") (comment 1 "gerado por kicad/gerar_esquema.py a partir de projeto.py"))',
           '  (lib_symbols']
    out += [v[0] for v in libs.values()]
    out.append('  )')
    out += insts + textos
    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append(')')
    with open(SAIDA, 'w') as f:
        f.write('\n'.join(out) + '\n')
    print('esquema salvo:', SAIDA, '|', len(P.PECAS), 'pecas')


if __name__ == '__main__':
    gerar()
