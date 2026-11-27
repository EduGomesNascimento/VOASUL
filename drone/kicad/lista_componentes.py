"""PDF 'Componentes' do drone: lista de pecas (com a label de cada uma, valor, onde vai, cuidado e
situacao tem/comprar) + o lado de cima 1:1 com as labels + o lado de baixo (SMD) com as labels.

Precisa de: saidas/BOM.csv (bom.py), saidas/folha_serigrafia_A4.pdf (folha_serigrafia.py) e
saidas/folha_montagem.pdf (folha_montagem.py). Gera saidas/componentes.pdf.
Usa o Chromium do Playwright (node) para transformar a tabela em PDF.
"""
import csv
import html
import os
import subprocess

import pymupdf

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, 'saidas')

# situacao (das marcacoes da lista de compras): T = ja tem, C = comprar
SIT = {'C1': 'T', 'C2': 'T', 'C3 C4 C5 C6': 'T', 'D1 D2 D3 D4': 'T', 'Q1 Q2 Q3 Q4': 'T',
       'R1 R2 R3 R4': 'T', 'R5 R6 R7 R8 R9 R10': 'T', 'R11 R12': 'T', 'R13 R14': 'T',
       'J2': 'T', 'J3': 'T', 'J4': 'T', 'U1': 'T', 'U2': 'T', 'U3': 'C', 'U4': 'T',
       'J1': 'C', 'M1': 'T', 'M2': 'T', 'M3': 'T', 'M4': 'T'}

EXTRAS = [  # (secao, qtd, label, peca, onde/como, cuidado, situacao)
    ('Fora da placa', '2', 'J2', 'Ultrassom HC-SR04 (baixo + frente)', 'cabo de 4 fios no J2',
     'VCC no 5V, GND no GND', 'T'),
    ('Fora da placa', '2', 'J3', 'Sensor de obstaculo IR FC-51 (esquerdo + direito)', 'cabo de 3 fios no J3',
     'o de domo branco (PIR) NAO serve', 'C'),
    ('Fora da placa', '4', 'M1-M4', 'Motor coreless 1020 (2 CW + 2 CCW)', 'fios nas ilhas M1-M4',
     '+ (vermelho) na ilha quadrada', 'T'),
    ('Fora da placa', '2 jogos', '-', 'Helice 75 mm, furo 1,0 mm (2 CW + 2 CCW por jogo)', 'no eixo dos motores',
     'confira o sentido de cada motor', 'C'),
    ('Fora da placa', '1', 'J1', 'Bateria LiPo 1S 530 mAh 30C (Leao LB530LP1) ou cabo do chao', 'no J1',
     'so 1S (3,7 V)', 'C'),
    ('Fora da placa', '1-2 pares', 'J1', 'Conector Molex 51005 (o branquinho da bateria)', 'rabicho no J1',
     'confira o encaixe na bateria', 'C'),
    ('Fora da placa', '-', 'JF/1-14', 'Fio rigido ENCAPADO (cabo de rede) para os 14 jumpers', 'por cima da placa',
     'GND com fio mais grosso (20-22 AWG)', 'T'),
    ('Fora da placa', '2', 'U1', 'Barra de pinos femea 1x19 (corte de 1x40)', 'soquete do ESP32',
     'solde com o ESP32 encaixado', 'T'),
    ('Fora da placa', '-', 'U3/U4/J2-J4', 'Barra de pinos macho 1x40', 'BMI160, BMP280 e conectores', '', 'T'),
    ('Estacao terra', '1', '-', 'ESP32-C3 Super Mini (de preferencia a Plus)', 'capinha do celular',
     'ver docs/TERRA.md', 'C'),
    ('Estacao terra', '1', '-', 'Cabo USB-C <-> USB-C curto (OTG)', 'celular -> C3', '', 'C'),
    ('Fazer a placa', '1', '-', 'Fenolite face simples 15x20 (da 2 discos)', 'placa + reserva', '', 'C'),
    ('Fazer a placa', '2', '-', 'Papel transfer amarelo (A4)', 'cobre + serigrafia', 'impressora laser, 100%', 'C'),
    ('Fazer a placa', '1', '-', 'Percloreto de ferro', 'corrosao', 'luva e oculos', 'T'),
]


def linhas_bom():
    secoes = {'cima': 'Na placa - lado de CIMA (pecas com perna, THT)',
              'baixo': 'Na placa - lado de BAIXO, no cobre (SMD)'}
    out = []
    for r in csv.DictReader(open(os.path.join(OUT, 'BOM.csv'), encoding='utf-8')):
        if r['Montagem'] == 'fora da placa':
            continue
        sec = secoes.get(r['Lado'], 'Na placa')
        peca = r['Descricao']
        out.append((sec, r['Qtd'], r['Referencias'], peca, r['Valor'], r['Observacao'],
                    SIT.get(r['Referencias'], 'T')))
    return out


def tabela_html():
    sit = {'T': '<span class="t">tem</span>', 'C': '<span class="c">comprar</span>'}
    grupos = {}
    for sec, q, ref, peca, valor, obs, s in linhas_bom():
        grupos.setdefault(sec, []).append((q, ref, peca, valor, obs, s))
    for sec, q, ref, peca, onde, obs, s in EXTRAS:
        grupos.setdefault(sec, []).append((q, ref, peca, onde, obs, s))
    corpo = []
    for sec, itens in grupos.items():
        col = 'Valor' if sec.startswith('Na placa') else 'Onde / como'
        corpo.append(f'<h2>{html.escape(sec)}</h2><table><tr><th>Qtd</th><th>Label</th><th>Peca</th>'
                     f'<th>{col}</th><th>Cuidado</th><th></th></tr>')
        for q, ref, peca, valor, obs, s in itens:
            corpo.append(f'<tr><td>{html.escape(q)}</td><td class="ref">{html.escape(ref)}</td>'
                         f'<td>{html.escape(peca)}</td><td>{html.escape(valor)}</td>'
                         f'<td>{html.escape(obs)}</td><td>{sit[s]}</td></tr>')
        corpo.append('</table>')
    n_c = sum(1 for g in grupos.values() for i in g if i[-1] == 'C')
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 13mm 12mm; }}
body {{ font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 8.6pt; color: #17201b; }}
h1 {{ font-size: 15pt; margin: 0 0 2px; }} .sub {{ color: #5d6a62; margin: 0 0 8px; }}
h2 {{ font-size: 10.5pt; margin: 12px 0 4px; color: #0f6b4f; }}
table {{ width: 100%; border-collapse: collapse; page-break-inside: auto; }}
tr {{ page-break-inside: avoid; }}
th {{ text-align: left; font-size: 7.6pt; color: #5d6a62; border-bottom: 1.2px solid #17201b; padding: 2px 4px; }}
td {{ border-bottom: 0.6px solid #d7ded8; padding: 3px 4px; vertical-align: top; }}
td.ref {{ font-weight: 700; white-space: nowrap; }}
.t {{ color: #0f6b4f; font-weight: 700; }} .c {{ color: #c4501a; font-weight: 700; }}
</style></head><body>
<h1>Drone VoaSul - componentes</h1>
<p class="sub">Label = o nome que aparece na placa e nas folhas (R5, C1, J3...). "tem"/"comprar" vem das suas
marcacoes na lista de compras ({n_c} itens a comprar). Paginas seguintes: lado de cima 1:1 e lado de baixo, com as labels.</p>
{''.join(corpo)}
</body></html>"""


def main():
    h = os.path.join(OUT, 'componentes_lista.html')
    open(h, 'w', encoding='utf-8').write(tabela_html())
    lista = os.path.join(OUT, 'componentes_lista.pdf')
    js = ("const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();"
          "const p=await b.newPage();await p.goto('file://'+process.argv[1]);"
          "await p.pdf({path:process.argv[2],format:'A4',preferCSSPageSize:true});await b.close();})();")
    subprocess.run(['node', '-e', js, h, lista], check=True)
    doc = pymupdf.open(lista)
    serig = pymupdf.open(os.path.join(OUT, 'folha_serigrafia_A4.pdf'))
    doc.insert_pdf(serig, from_page=1, to_page=1)        # lado de cima, normal, 1:1, com labels
    mont = pymupdf.open(os.path.join(OUT, 'folha_montagem.pdf'))
    doc.insert_pdf(mont, from_page=1, to_page=1)         # lado de baixo (SMD), com labels
    saida = os.path.join(OUT, 'componentes.pdf')
    doc.save(saida, deflate=True)
    os.remove(lista)
    os.remove(h)
    print('salvo:', saida, '|', doc.page_count, 'paginas')


if __name__ == '__main__':
    main()
