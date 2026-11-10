"""BOM TOTAL do projeto (versao minima): drone controlado pelo app no celular, com o que ja tem e o mais barato do que falta.
Gera BOM_TOTAL.csv (planilha) e BOM_TOTAL.md.   python3 bom_total.py
Precos: AliExpress de 10/11/2026 ("a partir de"); Brasil = carrinho do Mercado Livre / orcamento MB3;
"~" = estimativa."""
import csv
import os

AQUI = os.path.dirname(os.path.abspath(__file__))

# grupo, item, qtd, onde vai, situacao, onde comprar (mais barato), preco unit (R$), qtd a comprar, obs
T, C, O = 'tem', 'comprar', 'opcional'
ITENS = [
    # ---------------------------------------------------------------- drone: placa
    ('Drone: placa', 'ESP32 DevKitC 38 pinos (WROOM-32)', 1, 'U1', T, '', 0, 0, ''),
    ('Drone: placa', 'Giroscopio GY-BMI160 (placa roxa, 7 pinos)', 1, 'U3', C,
     'AliExpress', 5.99, 1, 'MB3 R$ 31,90 se precisar ja; vale comprar 2 (1 reserva)'),
    ('Drone: placa', 'Barometro GY-BMP280-3.3 (placa roxa, 6 pinos)', 1, 'U4', T, '', 0, 0, 'confirme que tem 6 pinos'),
    ('Drone: placa', 'Step-up MT3608', 1, 'U2', T, '', 0, 0, 'ajuste 5,0 V antes do ESP32'),
    ('Drone: placa', 'MOSFET AO3400A (SOT-23)', 4, 'Q1-Q4', T, '', 0, 0, ''),
    ('Drone: placa', 'Diodo SS34 (SMA)', 4, 'D1-D4', T, '', 0, 0, ''),
    ('Drone: placa', 'Capacitor 100 nF 0805', 4, 'C3-C6', T, '', 0, 0, ''),
    ('Drone: placa', 'Eletrolitico 1000 uF 10-16 V (D8)', 1, 'C1', T, '', 0, 0, ''),
    ('Drone: placa', 'Eletrolitico 470 uF 10-16 V (D6,3)', 1, 'C2', T, '', 0, 0, ''),
    ('Drone: placa', 'Resistor 100 ohm', 4, 'R1-R4', T, '', 0, 0, '100-220 ohm servem'),
    ('Drone: placa', 'Resistor 10 k', 6, 'R5-R10', T, '', 0, 0, '8k2 + 2k em serie servem'),
    ('Drone: placa', 'Resistor 1 k', 2, 'R11, R12', O, '', 0, 0, 'so com o sonar'),
    ('Drone: placa', 'Resistor 2 k', 2, 'R13, R14', O, '', 0, 0, 'so com o sonar'),
    ('Drone: placa', 'Barra femea 1x40 (corta 2 x 19)', 1, 'U1', T, '', 0, 0, ''),
    ('Drone: placa', 'Barra macho 1x40', 1, 'U3, U4, J2-J4', T, '', 0, 0, 'J2/J3/J4 opcionais na versao minima'),
    ('Drone: placa', 'Fenolite 15x20 face simples (da 2 discos)', 1, 'placa', C,
     'MB3', 19.00, 1, 'fresada na CNC do amigo'),
    ('Drone: placa', 'Fio rigido para os 11 jumpers', 1, 'jumpers', T, '', 0, 0, 'de cabo de rede'),
    # ---------------------------------------------------------------- drone: voo
    ('Drone: voo', 'Motor coreless 1020 (2 CW + 2 CCW)', 4, 'M1-M4', T, '', 0, 0, ''),
    ('Drone: voo', 'Helice 75 mm furo 1 mm (2 CW + 2 CCW por jogo)', 2, 'motores', C,
     'AliExpress', 9.14, 2, 'Gemfan; ML 3 x R$ 19'),
    ('Drone: voo', 'Conector Molex 51005 macho + femea com fio', 1, 'J1', C,
     'AliExpress', 11.60, 1, '10 pares; serve para bateria e cabo'),
    ('Drone: voo', 'Fio de silicone 24 AWG vermelho e preto, 2 m', 1, 'motores, J1', C,
     'AliExpress', 7.22, 1, 'ML R$ 19'),
    ('Drone: voo', 'Fita dupla face de espuma', 1, 'placa no frame', C,
     'AliExpress', 9.61, 1, 'MB3 R$ 15,90'),
    ('Drone: voo', 'Frame: compensado 3 mm (molde 1:1 pronto)', 1, 'frame', C,
     'madeireira', 10.00, 1, '~R$ 10; PLA a escola cobra por grama'),
    # ---------------------------------------------------------------- energia: opcao A
    ('Energia A: bateria', 'LiPo 1S 530 mAh 30C Molex (Leao LB530LP1)', 1, 'J1', C,
     'Mercado Livre', 58.00, 1, 'LiPo nao vale importar'),
    ('Energia A: bateria', 'Carregador USB LiPo 1S saida Molex 51005', 1, '', C,
     'AliExpress', 10.90, 1, 'ML R$ 35'),
    ('Energia A: bateria', 'Velcro para a bateria', 1, 'frame', C, 'AliExpress', 11.26, 1, 'MB3 R$ 17,90'),
    ('Energia A: bateria', 'Saco anti-chamas para LiPo', 1, '', C, 'AliExpress', 10.75, 1,
     'ou carregar num pote de vidro, sempre olhando'),
    # ---------------------------------------------------------------- energia: opcao B
    ('Energia B: cabo', 'Fio paralelo 2 x 0,5 mm2 (~20 AWG), 3 m', 1, 'J1', C,
     'loja de material eletrico', 9.00, 1, '~R$ 3/m; queda de ~0,9 V a 7 A em 2 m'),
    ('Energia B: cabo', 'Fonte de bancada ajustavel (~4,9 V, 8 A)', 1, '', T, '', 0, 0, 'a da escola'),
    # ---------------------------------------------------------------- estacao terra
    ('Estacao terra', 'ESP32-C3 Super Mini (de preferencia a Plus, com antena externa)', 1, 'capinha do celular', C,
     'AliExpress', 10.90, 1, 'ver docs/TERRA.md'),
    ('Estacao terra', 'Cabo USB-C <-> USB-C curto (OTG)', 1, 'celular -> C3', C,
     'AliExpress', 8.00, 1, '~R$ 8; o C3 e alimentado pelo celular'),
    ('Estacao terra', 'Fita dupla face ou velcro', 1, 'C3 na capinha', T, '', 0, 0, 'sobra da do frame'),
    # ---------------------------------------------------------------- bancada
    ('Bancada', 'Multimetro, ferro, estanho, fluxo, malha, pinca, lupa', 1, '', T, '', 0, 0, 'robotica / escola'),
    ('Bancada', 'Fusivel 4 A + porta-fusivel', 1, 'primeiro liga', T, '', 0, 0, 'do DAMP'),
    ('Bancada', 'Alcool isopropilico', 1, 'limpar o fluxo', O, 'MB3', 9.00, 0, ''),
    # ---------------------------------------------------------------- depois
    ('Depois (opcional)', 'Fluxo optico PMW3901', 1, 'J4', O, 'AliExpress', 31.99, 0, 'segura o drone parado'),
    ('Depois (opcional)', 'Sonar HC-SR04 / IR FC-51', 2, 'J2 / J3', T, '', 0, 0, 'ja tem; fora da versao minima'),
]


def main():
    linhas = []
    for g, item, q, onde, sit, loja, pu, qc, obs in ITENS:
        linhas.append(dict(grupo=g, item=item, qtd=q, onde=onde, situacao=sit, comprar_em=loja,
                           preco_unit=pu, qtd_comprar=qc, total=round(pu * qc, 2), obs=obs))
    with open(os.path.join(AQUI, 'BOM_TOTAL.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)

    def soma(prefixos):
        return sum(l['total'] for l in linhas if l['grupo'].startswith(prefixos))
    base = soma(('Drone', 'Estacao'))
    bat, cabo = soma(('Energia A',)), soma(('Energia B',))

    def r(v):
        return f'R$ {v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    md = ['# BOM total do drone VoaSul (versão mínima)', '',
          'Drone com BMI160 + BMP280 (sem sonar, IR e fluxo óptico), pilotado pelo celular através da '
          'estação terra (ESP32-C3 na capinha, ESP-NOW até o drone; ver TERRA.md). "tem" vem das suas marcações na lista de compras. Preço da AliExpress de 10/11/2026 '
          '("a partir de", sem frete e imposto); "~" é estimativa. Planilha: `BOM_TOTAL.csv`.', '',
          '## Quanto falta gastar', '',
          '| | R$ |', '|---|---|',
          f'| Drone + estação terra (comum às duas energias) | {r(base)} |',
          f'| + Energia A: bateria | {r(bat)} |',
          f'| + Energia B: cabo do chão | {r(cabo)} |',
          f'| **Total com bateria** | **{r(base + bat)}** |',
          f'| **Total com cabo** | **{r(base + cabo)}** |', '',
          'Imposto da AliExpress (compra abaixo de US$ 50): o carrinho mostra; conte uns 20 a 45 % a mais '
          'sobre a parte da AliExpress. Chega em 2 a 5 semanas. Se não der para esperar, o BMI160 sai '
          '~R$ 26 mais caro na MB3.', '']
    grupo = None
    for l in linhas:
        if l['grupo'] != grupo:
            grupo = l['grupo']
            md += ['', f'## {grupo}', '', '| Qtd | Item | Onde vai | Situação | Comprar em | R$ |',
                   '|---|---|---|---|---|---|']
        preco = r(l['total']) if l['qtd_comprar'] else '—'
        sit = {'tem': '✅ tem', 'comprar': '🛒 comprar', 'opcional': 'opcional'}[l['situacao']]
        obs = f" ({l['obs']})" if l['obs'] else ''
        md.append(f"| {l['qtd']} | {l['item']}{obs} | {l['onde']} | {sit} | {l['comprar_em']} | {preco} |")
    open(os.path.join(AQUI, 'BOM_TOTAL.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print(f'base {base:.2f} | bateria +{bat:.2f} = {base + bat:.2f} | cabo +{cabo:.2f} = {base + cabo:.2f}')


if __name__ == '__main__':
    main()
