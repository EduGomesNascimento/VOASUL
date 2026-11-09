#!/bin/sh
# Regera a placa inteira a partir do projeto.py (KiCad 7 + numpy).
#   KICAD_PY: o Python que tem o modulo pcbnew (no Ubuntu: /usr/bin/python3)
set -e
cd "$(dirname "$0")"
K=${KICAD_PY:-/usr/bin/python3}
$K gerar.py placa                      # pecas, redes, contorno
$K gerar.py exportar                   # geometria.json
python3 rotear.py geometria.json rotas.json 1   # roteador de face unica (30-40 minutos)
$K gerar.py placa                      # placa limpa de novo...
$K gerar.py aplicar                    # ...com as trilhas, jumpers e o plano de GND
$K gerar.py drc                        # -> drc.txt
python3 gerar_esquema.py               # esquema
$K gerar.py saidas                     # PDFs de transferencia e montagem
$K gerar.py cena3d                     # dados do visualizador 3D
$K gerar.py profissional               # versao para fabrica + gerber
$K extrair_montagem.py                 # dados da folha de montagem
python3 folha_montagem.py              # saidas/folha_montagem.pdf (cima, baixo, lista)
python3 folha_transferencia.py         # saidas/folha_transferencia_A4.pdf (2 copias 1:1)
$K bom.py                              # saidas/BOM.csv + pro/montagem_jlc/ (BOM e CPL da JLCPCB)
$K cnc.py                              # cnc/: G-code para fresar a placa caseira (GRBL)
