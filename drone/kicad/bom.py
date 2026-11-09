"""BOM (lista de materiais) e arquivos de montagem da JLCPCB, tirados da placa profissional.

Saidas:
  saidas/BOM.csv                    lista completa, agrupada por valor (para comprar e conferir)
  pro/montagem_jlc/BOM_JLCPCB.csv   so as pecas SMD (formato do site: Comment, Designator, Footprint, LCSC)
  pro/montagem_jlc/CPL_JLCPCB.csv   posicao das pecas SMD (Designator, Mid X, Mid Y, Layer, Rotation)

A montagem pela JLCPCB e OPCIONAL: as pecas SMD ficam na face de BAIXO (MOSFET, diodo,
capacitor 0805) e o resto e furo passante, soldado a mao.
Roda no Python do KiCad (/usr/bin/python3), depois de 'gerar.py profissional'.
"""
import csv
import os
import subprocess
from collections import OrderedDict

import pcbnew

AQUI = os.path.dirname(os.path.abspath(__file__))
PRO = os.path.join(AQUI, 'pro', 'drone_pro.kicad_pcb')

# descricao, observacao de compra e codigo LCSC (so para o que a JLCPCB pode montar)
INFO = {
    'ESP32 DevKitC 38p': ('Placa ESP32 DevKitC V4, 38 pinos, WROOM-32', 'em 2 barras femea 1x19', ''),
    'GY-BMI160': ('Modulo giroscopio/acelerometro GY-BMI160', 'barra macho baixa, embaixo do ESP32', ''),
    'GY-BMP280': ('Modulo barometro GY-BMP280-3.3 (6 pinos)', 'barra macho baixa, embaixo do ESP32', ''),
    'MT3608 5,0V': ('Modulo step-up MT3608', 'em 4 pernas de fio; ajuste 5,0 V antes do ESP32', ''),
    '1000uF 10V': ('Capacitor eletrolitico 1000 uF 10-16 V, D8 mm, passo 3,5 mm', 'polaridade', ''),
    '470uF 10V': ('Capacitor eletrolitico 470 uF 10-16 V, D6,3 mm, passo 2,5 mm', 'polaridade', ''),
    '100nF 0805': ('Capacitor ceramico 100 nF 50 V X7R, 0805', 'face de baixo', 'C49678'),
    'SS34': ('Diodo Schottky SS34 40 V 3 A, SMA', 'face de baixo, faixa para fora', 'C8678'),
    'AO3400A': ('MOSFET canal N AO3400A 30 V 5,7 A, SOT-23', 'face de baixo', 'C20917'),
    '100': ('Resistor 100 ohm 1/4 W', 'em pe; 100-220 ohm servem', ''),
    '10k': ('Resistor 10 kohm 1/4 W', 'em pe', ''),
    '1k': ('Resistor 1 kohm 1/4 W', 'em pe', ''),
    '2k': ('Resistor 2 kohm 1/4 W', 'em pe; 1k8 ou 2k2 servem', ''),
    'IR (FC-51 x2)': ('Barra de pinos macho 1x4, 2,54 mm', 'conector dos IR', ''),
    'SONAR (HC-SR04 x2)': ('Barra de pinos macho 1x6, 2,54 mm', 'conector dos sonares', ''),
    'FLUXO (PMW3901)': ('Barra de pinos macho 2x3, 2,54 mm', 'fluxo optico (opcional); ou 2 pedacos de 1x3', ''),
    'LiPo 1S': ('Rabicho Molex 51005 macho com fio 24 AWG', '+ (vermelho) na ilha quadrada', ''),
}
MOTOR = ('Ilhas para o motor coreless 1020', 'fios do motor; + na ilha quadrada', '')
# pecas que nao estao na placa, mas o circuito precisa
EXTRAS = [
    (2, '', 'Barra de pinos femea 1x19, 2,54 mm', 'U1 (ESP32)', 'corte de 2 barras 1x40'),
    (4, '', 'Motor coreless 1020 (2 CW + 2 CCW)', 'M1-M4', 'ja comprado'),
    (1, '', 'Bateria LiPo 1S 500-600 mAh 25C+ com Molex 51005', 'J1', 'ex.: Leao LB530LP1'),
]


def pecas():
    b = pcbnew.LoadBoard(PRO)
    out = []
    for fp in b.GetFootprints():
        smd = bool(fp.GetAttributes() & pcbnew.FP_SMD)
        out.append(dict(ref=fp.GetReference(), valor=fp.GetValue(),
                        pegada=str(fp.GetFPID().GetLibItemName()),
                        lado='baixo' if fp.GetLayer() == pcbnew.B_Cu else 'cima', smd=smd))
    return out


def ordem_ref(r):
    letras = ''.join(c for c in r if c.isalpha())
    num = ''.join(c for c in r if c.isdigit())
    return (letras, int(num or 0))


def main():
    ps = pecas()
    grupos = OrderedDict()
    for p in sorted(ps, key=lambda p: ordem_ref(p['ref'])):
        grupos.setdefault((p['valor'], p['pegada'], p['lado'], p['smd']), []).append(p['ref'])

    # ---- BOM completa
    saida = os.path.join(AQUI, 'saidas', 'BOM.csv')
    with open(saida, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Qtd', 'Referencias', 'Valor', 'Descricao', 'Pegada', 'Montagem', 'Lado', 'LCSC', 'Observacao'])
        linhas = []
        for (valor, peg, lado, smd), refs in grupos.items():
            desc, obs, lcsc = MOTOR if refs[0].startswith('M') else INFO.get(valor, (valor, '', ''))
            linhas.append([len(refs), ' '.join(refs), valor, desc, peg, 'SMD' if smd else 'THT', lado, lcsc, obs])
        for qtd, valor, desc, refs, obs in EXTRAS:
            linhas.append([qtd, refs, valor, desc, '', 'fora da placa', '', '', obs])
        w.writerows(linhas)
    print('BOM:', saida, '|', len(linhas), 'linhas,', len(ps), 'pecas na placa')

    # ---- JLCPCB: BOM e posicao das pecas SMD
    pasta = os.path.join(AQUI, 'pro', 'montagem_jlc')
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, 'BOM_JLCPCB.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (valor, peg, lado, smd), refs in grupos.items():
            if smd:
                w.writerow([valor, ','.join(refs), peg, INFO[valor][2]])
    pos = os.path.join(pasta, '_pos_kicad.csv')
    subprocess.run(['kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm',
                    '--side', 'both', '--smd-only', '-o', pos, PRO], check=True, capture_output=True)
    with open(pos, encoding='utf-8') as f:
        rs = list(csv.DictReader(f))
    os.remove(pos)
    with open(os.path.join(pasta, 'CPL_JLCPCB.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in sorted(rs, key=lambda r: ordem_ref(r['Ref'])):
            lado = 'Bottom' if r['Side'].lower().startswith('b') else 'Top'
            w.writerow([r['Ref'], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm", lado,
                        f"{float(r['Rot']) % 360:.1f}"])
    print('JLCPCB:', pasta, '|', len(rs), 'pecas SMD')


if __name__ == '__main__':
    main()
