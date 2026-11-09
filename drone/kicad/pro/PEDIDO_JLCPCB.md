# Pedido da placa na JLCPCB

Arquivo para subir: **`drone_VoaSul_JLCPCB.zip`** (nesta pasta). Para o Claude do navegador montar o
carrinho sozinho, use **`PROMPT_CARRINHO_JLCPCB.md`**. É a versão profissional da mesma
placa, conferida: DRC com 0 erros e 0 pinos desligados, esquema × placa com 0 diferenças.

- Furo metalizado e cobre nas duas faces.
- Os 11 jumpers da placa caseira viraram trilhas na face de cima, com via. **Não há fio para soldar.**
- Plano de GND nas duas faces, máscara de solda e serigrafia com o nome de cada peça.

## Como pedir

1. Entre em jlcpcb.com e clique em **Order now → Add gerber file**. Suba o zip.
2. Confira a pré-visualização:
   - disco de **97 mm**;
   - face de cima com o plano de GND e o texto "VoaSul Drones rev C 2026";
   - face de baixo com as trilhas grossas.
3. Preencha conforme a tabela abaixo. O que não estiver na tabela, deixe no padrão.
4. **PCB Assembly: não.** As peças são soldadas por você. **Stencil: não.**
5. Escolha o frete e confira o total, com o imposto, antes de pagar.

## Especificações

| Campo no site | Escolha | Por quê |
|---|---|---|
| Base Material | **FR-4** | padrão |
| Layers | **2** | cobre nas duas faces |
| Dimensions | **97,1 × 97,1 mm** (preenche sozinho) | cabe na faixa mais barata (até 100 × 100 mm) |
| PCB Qty | **5** | é o mínimo e custa o mesmo que 2 |
| Product Type | Industrial/Consumer electronics | — |
| Different Design | **1** | — |
| Delivery Format | **Single PCB** | — |
| PCB Thickness | **1,6 mm** | é a espessura que o rebaixo do frame espera |
| PCB Color | **Green** | mais barata e mais rápida |
| Silkscreen | White | — |
| Surface Finish | **HASL (with lead)** | mais barata e fácil de soldar (LeadFree também serve) |
| Outer Copper Weight | **1 oz** | as trilhas de 2,5 mm aguentam a corrente dos motores |
| Via Covering | Tented | — |
| Min via hole size | 0,3 mm (padrão) | as vias da placa têm 0,5 mm |
| Board Outline Tolerance | ±0,2 mm (Regular) | o rebaixo do frame tem 97,9 mm |
| Mark on PCB | padrão | o número do pedido vai na serigrafia, sem problema |
| Electrical Test | Flying Probe (padrão) | grátis nesse tamanho |
| Gold Fingers / Castellated / Edge plating | **No** | — |

Números da placa, para conferir:
- trilha mais fina: 0,8 mm (o mínimo da JLCPCB é 0,1 mm);
- folga mínima entre cobres: 0,75 mm;
- furos: 30 de 0,9 mm, 81 de 1,0 mm e 2 de 1,3 mm;
- 22 vias de 0,5 mm (ilha de 1,0 mm).

## Custo e prazo (estimativa, confira no carrinho)

| | |
|---|---|
| Placas (5 un.) | a partir de US$ 2 (~R$ 11) |
| Frete econômico (Global Standard Direct) | 2 a 4 semanas |
| Frete DHL Express | ~1 semana, mais caro |
| Imposto | Pelas regras de 2026, o frete entra na base do imposto. Até US$ 50 em loja certificada no Remessa Conforme: ICMS de 17–20%. Fora disso: imposto de importação + ICMS. Com DHL, a DHL cobra o imposto na entrega. |

Não achei dados oficiais da JLCPCB sobre o Brasil (frete, prazo, se o imposto já vem pago), por
isso use o valor que aparece no checkout com o seu endereço. Produção de 1 a 2 dias + DHL de 3 a 5
dias úteis: pedindo hoje (09/11), chega por volta de 14 a 18/11. **Para 13/11 não dá mais tempo.**

## Lista de materiais (BOM)

A BOM completa está em **`../saidas/BOM.csv`** (gerada da placa por `bom.py`): quantidade,
referências, valor, descrição, pegada, se é SMD ou de furo, lado e observação. Abre no Excel ou no
Google Planilhas. Resumo:

| Qtd | Peça | Ref. | Observação |
|---|---|---|---|
| 1 | ESP32 DevKitC 38 pinos (WROOM-32) | U1 | vai em **2 barras fêmea 1×19** |
| 1 | GY-BMI160 | U3 | embaixo do ESP32, com barra macho baixa |
| 1 | GY-BMP280-3.3 (6 pinos) | U4 | embaixo do ESP32, com barra macho baixa |
| 1 | MT3608 (step-up) | U2 | ajuste 5,0 V antes de encaixar o ESP32 |
| 4 | MOSFET AO3400A (SOT-23) | Q1–Q4 | face de baixo |
| 4 | Diodo SS34 (SMA) | D1–D4 | face de baixo, faixa para fora |
| 4 | Capacitor 100 nF 0805 | C3–C6 | face de baixo |
| 1 | Eletrolítico 1000 µF 10–16 V (Ø8) | C1 | polaridade |
| 1 | Eletrolítico 470 µF 10–16 V (Ø6,3) | C2 | polaridade |
| 4 | Resistor 100 Ω | R1–R4 | em pé |
| 6 | Resistor 10 kΩ | R5–R10 | em pé |
| 2 | Resistor 1 kΩ | R11, R12 | em pé |
| 2 | Resistor 2 kΩ | R13, R14 | em pé (1k8 ou 2k2 servem) |
| 1 | Barra macho 1×6 | J2 | sonar |
| 1 | Barra macho 1×4 | J3 | IR |
| 1 | Barra macho 2×3 | J4 | fluxo óptico (dá para usar dois pedaços de 1×3 lado a lado) |
| 2 | Barra fêmea 1×19 | — | para o ESP32 (corte de barras 1×40) |
| 1 | Rabicho Molex 51005 macho com fio 24 AWG | J1 | + na ilha quadrada |
| 4 | Motor coreless 1020 (2 CW + 2 CCW), com fio | M1–M4 | + na ilha quadrada |

## Montagem das peças SMD pela JLCPCB (opcional)

As 12 peças SMD (4 AO3400A, 4 SS34 e 4 capacitores 0805) ficam na **face de baixo**, e a JLCPCB
pode soldá-las. São peças *Basic*, sem taxa de peça extra. Os arquivos estão em `montagem_jlc/`:

| Arquivo | O que é |
|---|---|
| `BOM_JLCPCB.csv` | as 3 peças com o código LCSC: C20917 (AO3400A), C8678 (SS34), C49678 (100 nF 0805) |
| `CPL_JLCPCB.csv` | posição e giro de cada uma (face de baixo) |

Configuração: *Economic*, *Bottom Side*, 2 placas montadas. **Confira a tela de posicionamento**:
giro de peça na face de baixo é o erro mais comum. A versão B do prompt faz isso e para para você
olhar. Vale a pena se você não quiser soldar SOT-23 à mão. Custa uma taxa fixa a mais e deixa o
pedido alguns dias mais lento.

## O que deixou de ser necessário com a placa da JLCPCB

| Item | Onde estava | Economia |
|---|---|---|
| Papel de transferência | carrinho do Mercado Livre | R$ 28,54 |
| Fenolite 15×20 | orçamento da MB3 | R$ 19,00 |
| Palha de aço | mercado | ~R$ 5 |
| Percloreto, microbrocas, fio rígido dos jumpers, ferro de passar | bancada | — |

O **álcool isopropílico continua** na lista: ele serve para limpar o fluxo depois da solda.
