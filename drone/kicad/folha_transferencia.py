"""Folha A4 de transferencia termica: duas copias 1:1 do cobre (saidas/transferencia_B_Cu.pdf),
cruzes de corte, regua de 100 mm e instrucoes. Saida: saidas/folha_transferencia_A4.pdf
Roda depois de 'gerar.py saidas'. Precisa de pymupdf."""
import os

import pymupdf

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, 'saidas')
MM = 72 / 25.4

src = pymupdf.open(os.path.join(OUT, 'transferencia_B_Cu.pdf'))
# a placa esta centrada em (100, 100) mm na folha do KiCad; disco de 97 mm
clip = pymupdf.Rect(48 * MM, 48 * MM, 152 * MM, 152 * MM)       # 104 x 104 mm em volta do disco
out = pymupdf.open()
p = out.new_page(width=210 * MM, height=297 * MM)
for i, y0 in enumerate((22, 136)):
    dst = pymupdf.Rect(53 * MM, y0 * MM, 157 * MM, (y0 + 104) * MM)   # mesmo tamanho = 1:1
    p.show_pdf_page(dst, src, 0, clip=clip)
    p.insert_text((14 * MM, (y0 + 52) * MM), f'COPIA {i + 1}', fontsize=9, fontname='hebo', rotate=90)
# cruzes de corte nos cantos de cada copia
for y0 in (22, 136):
    for x, y in ((53, y0), (157, y0), (53, y0 + 104), (157, y0 + 104)):
        p.draw_line(((x - 3) * MM, y * MM), ((x + 3) * MM, y * MM), width=0.3)
        p.draw_line((x * MM, (y - 3) * MM), (x * MM, (y + 3) * MM), width=0.3)
# regua de 100 mm
y = 252
p.draw_line((55 * MM, y * MM), (155 * MM, y * MM), width=0.8)
for k in range(11):
    h = 3 if k % 5 == 0 else 1.6
    p.draw_line(((55 + 10 * k) * MM, y * MM), ((55 + 10 * k) * MM, (y - h) * MM), width=0.6)
p.insert_text((55 * MM, (y + 4) * MM), 'REGUA 100 mm - meca antes de passar o ferro (tem que dar 100 mm exatos)', fontsize=7.5)
txt = ['DRONE VoaSul - folha de transferencia termica - cobre de baixo (face unica), 1:1',
       '1) Impressora LASER, papel glossy/transferencia, escala 100% (desligue "ajustar a pagina").',
       '2) NAO espelhe: o texto "VoaSul | Drones" da placa aparece AO CONTRARIO no papel - esta certo.',
       '3) Toner virado para o cobre; ferro no algodao, 3-5 min apertando; agua 10 min; tire o papel.',
       '4) Duas copias: use a 2a se a 1a falhar. Furos: 0,9 pinos | 1,0 motor/modulos | 1,3 bateria.']
for k, t in enumerate(txt):
    p.insert_text((14 * MM, (264 + 5.2 * k) * MM), t, fontsize=8.2 if k else 9, fontname='hebo' if k == 0 else 'helv')
saida = os.path.join(OUT, 'folha_transferencia_A4.pdf')
out.save(saida)
print('salvo:', saida)
