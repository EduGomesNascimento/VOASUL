# Placa do drone no KiCad (face única, trilhas grossas)

Projeto KiCad 7 da placa redonda (Ø97 mm) do drone. Abre no KiCad 7, 8 ou 9.

| Arquivo | O que é |
|---|---|
| `drone.kicad_pro` / `.kicad_sch` / `.kicad_pcb` | o projeto: esquema e placa |
| `drone.kicad_dru` | regras extras (sensores e resistores embaixo do ESP32 de propósito) |
| `projeto.py` | **a fonte de tudo**: peças, redes, posições, larguras e pinos do ESP32 |
| `gerar.py`, `etapas.py` | montam a placa a partir do `projeto.py` (Python do KiCad) |
| `rotear.py` | roteador próprio para face única (só numpy) |
| `gerar_esquema.py` | gera o esquema a partir do `projeto.py` |
| `modelos3d.py` + `3d/` | modelos 3D (ESP32 DevKit, MT3608, GY-BMI160, GY-BMP280 feitos aqui; o resto da biblioteca do KiCad) |
| `saidas/` | PDFs de transferência, imagens 3D, lista de redes, relatório de DRC |

## Regras da placa

- **Face única:** todo o cobre fica embaixo (B.Cu). Onde duas trilhas teriam de se cruzar
  entra um **jumper**: fio rígido por cima, do lado dos componentes (aparece como trilha fina em F.Cu
  entre duas vias, e desenhado na folha de montagem).
- **Trilhas grossas:** 2,5 mm (VBAT, drenos dos motores) · 1,5 mm (GND, 5 V, 3V3) · 1,2 mm (sinais).
  Só afinam para 0,8 mm nos últimos 3 mm antes de um pino de passo 2,54.
- **Folga de 0,8 mm** entre cobres de redes diferentes, inclusive entre ilhas de pinos (ilhas
  ovais de 1,7 × 3,0 mm), para o toner amassado não encostar.
- **Anel de VBAT** de 2,5 mm por dentro da borda, e **plano de GND** no resto.
- Peças SMD (MOSFET SOT-23, diodo SS34, capacitor 0805) ficam **embaixo, no lado do cobre**,
  fora dos raios do frame (que passam a 2 mm da placa nas diagonais).
- **BMI160 e BMP280 ficam embaixo do ESP32**, entre as barras fêmea (8,5 mm de vão), soldados
  direto com barra macho. O giroscópio fica perto do centro do drone.

## Pinos do ESP32 (mudaram!)

Para não cruzar trilha, os pinos seguem a ordem física dos braços. O `include/board_esp32.h`
já está atualizado:

| Função | GPIO | | Função | GPIO |
|---|---|---|---|---|
| Motor FR | 17 | | Sonar baixo TRIG / ECHO | 14 / 27 |
| Motor RR | 4 | | Sonar frente TRIG / ECHO | 13 / 12 |
| Motor RL | 23 | | IR esquerdo / direito | 36 / 39 |
| Motor FL | 19 | | Bateria (ADC1) | 35 |
| I²C 1 (BMP280) SDA / SCL | 21 / 22 | | LED | 2 |
| I²C 2 (BMI160) SDA / SCL | 16 / 18 | | Fluxo óptico MISO / SCK / MOSI / CS | 32 / 33 / 25 / 26 |

## Fluxo óptico (J4): opcional

O **J4** é o conector do sensor de fluxo óptico **PMW3901** (SPI). A placa e o firmware
funcionam **com e sem** o módulo:

- sem o módulo, o J4 fica vazio e o drone voa como sempre;
- com o módulo, o firmware o encontra sozinho no boot (lê o ID do chip) e passa a frear a
  deriva quando o manche está solto. A página do celular mostra o estado no quadro **Fluxo**;
- se o módulo parar de responder em voo (fio solto), o firmware percebe em menos de 1 s e
  segue sem ele.

Pinos do J4 (da esquerda para a direita, visto de cima): **3V3, MISO, SCK, MOSI, CS, GND**.
O módulo vai embaixo do drone, com a lente para baixo. Ligue e desligue só com o drone
**desligado**. Teste e ajuste: `docs/PLANO_DE_MONTAGEM.md`, fase 12.

## Arquivos para usar já

| Para | Arquivo |
|---|---|
| Transferência térmica (imprimir 1:1, laser) | `saidas/transferencia_B_Cu.pdf` |
| Montagem por cima / por baixo | `saidas/montagem_cima.pdf`, `saidas/montagem_baixo_vista_por_baixo.pdf` |
| Lista de jumpers | `saidas/jumpers.txt` (14: 10 de GND, 4 de sinal) |
| Teste de continuidade | `saidas/redes.txt` |
| Esquema | `saidas/esquema.pdf` |
| Mandar fazer na fábrica | `pro/drone_pro_gerber.zip` (+ `pro/drone_pro.kicad_pcb`) |
| Ver em 3D | `saidas/drone3d_*.png`; interativo: `python3 -m http.server` nesta pasta e abrir `saidas/visualizador3d.html` |

## Regerar tudo

Tudo de uma vez: `./gerar_tudo.sh` (leva uns 15 minutos por causa do roteador). Passo a passo:

```bash
python3 gerar.py placa        # peças e redes (Python do KiCad: /usr/bin/python3)
python3 gerar.py exportar     # geometria.json para o roteador
python3 rotear.py geometria.json rotas.json   # qualquer Python com numpy
python3 gerar.py aplicar      # trilhas, jumpers, plano de GND
python3 gerar.py drc          # verificação de regras -> drc.txt
python3 gerar_esquema.py      # esquema
python3 gerar.py saidas       # PDFs de transferência e 3D
```
