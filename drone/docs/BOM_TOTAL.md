# BOM total do drone VoaSul (versão mínima)

Drone com BMI160 + BMP280 (sem sonar, IR e fluxo óptico), pilotado pelo celular através da estação terra (ESP32-C3 na capinha, ESP-NOW até o drone; ver TERRA.md). "tem" vem das suas marcações na lista de compras. Preço da AliExpress de 10/11/2026 ("a partir de", sem frete e imposto); "~" é estimativa. Planilha: `BOM_TOTAL.csv`.

## Quanto falta gastar

| | R$ |
|---|---|
| Drone + estação terra (comum às duas energias) | R$ 100,60 |
| + Energia A: bateria | R$ 90,91 |
| + Energia B: cabo do chão | R$ 9,00 |
| **Total com bateria** | **R$ 191,51** |
| **Total com cabo** | **R$ 109,60** |

Imposto da AliExpress (compra abaixo de US$ 50): o carrinho mostra; conte uns 20 a 45 % a mais sobre a parte da AliExpress. Chega em 2 a 5 semanas. Se não der para esperar, o BMI160 sai ~R$ 26 mais caro na MB3.


## Drone: placa

| Qtd | Item | Onde vai | Situação | Comprar em | R$ |
|---|---|---|---|---|---|
| 1 | ESP32 DevKitC 38 pinos (WROOM-32) | U1 | ✅ tem |  | — |
| 1 | Giroscopio GY-BMI160 (placa roxa, 7 pinos) (MB3 R$ 31,90 se precisar ja; vale comprar 2 (1 reserva)) | U3 | 🛒 comprar | AliExpress | R$ 5,99 |
| 1 | Barometro GY-BMP280-3.3 (placa roxa, 6 pinos) (confirme que tem 6 pinos) | U4 | ✅ tem |  | — |
| 1 | Step-up MT3608 (ajuste 5,0 V antes do ESP32) | U2 | ✅ tem |  | — |
| 4 | MOSFET AO3400A (SOT-23) | Q1-Q4 | ✅ tem |  | — |
| 4 | Diodo SS34 (SMA) | D1-D4 | ✅ tem |  | — |
| 4 | Capacitor 100 nF 0805 | C3-C6 | ✅ tem |  | — |
| 1 | Eletrolitico 1000 uF 10-16 V (D8) | C1 | ✅ tem |  | — |
| 1 | Eletrolitico 470 uF 10-16 V (D6,3) | C2 | ✅ tem |  | — |
| 4 | Resistor 100 ohm (100-220 ohm servem) | R1-R4 | ✅ tem |  | — |
| 6 | Resistor 10 k (8k2 + 2k em serie servem) | R5-R10 | ✅ tem |  | — |
| 2 | Resistor 1 k (so com o sonar) | R11, R12 | opcional |  | — |
| 2 | Resistor 2 k (so com o sonar) | R13, R14 | opcional |  | — |
| 1 | Barra femea 1x40 (corta 2 x 19) | U1 | ✅ tem |  | — |
| 1 | Barra macho 1x40 (J2/J3/J4 opcionais na versao minima) | U3, U4, J2-J4 | ✅ tem |  | — |
| 1 | Fenolite 15x20 face simples (da 2 discos) (fresada na CNC do amigo) | placa | 🛒 comprar | MB3 | R$ 19,00 |
| 1 | Fio rigido para os 11 jumpers (de cabo de rede) | jumpers | ✅ tem |  | — |

## Drone: voo

| Qtd | Item | Onde vai | Situação | Comprar em | R$ |
|---|---|---|---|---|---|
| 4 | Motor coreless 1020 (2 CW + 2 CCW) | M1-M4 | ✅ tem |  | — |
| 2 | Helice 75 mm furo 1 mm (2 CW + 2 CCW por jogo) (Gemfan; ML 3 x R$ 19) | motores | 🛒 comprar | AliExpress | R$ 18,28 |
| 1 | Conector Molex 51005 macho + femea com fio (10 pares; serve para bateria e cabo) | J1 | 🛒 comprar | AliExpress | R$ 11,60 |
| 1 | Fio de silicone 24 AWG vermelho e preto, 2 m (ML R$ 19) | motores, J1 | 🛒 comprar | AliExpress | R$ 7,22 |
| 1 | Fita dupla face de espuma (MB3 R$ 15,90) | placa no frame | 🛒 comprar | AliExpress | R$ 9,61 |
| 1 | Frame: compensado 3 mm (molde 1:1 pronto) (~R$ 10; PLA a escola cobra por grama) | frame | 🛒 comprar | madeireira | R$ 10,00 |

## Energia A: bateria

| Qtd | Item | Onde vai | Situação | Comprar em | R$ |
|---|---|---|---|---|---|
| 1 | LiPo 1S 530 mAh 30C Molex (Leao LB530LP1) (LiPo nao vale importar) | J1 | 🛒 comprar | Mercado Livre | R$ 58,00 |
| 1 | Carregador USB LiPo 1S saida Molex 51005 (ML R$ 35) |  | 🛒 comprar | AliExpress | R$ 10,90 |
| 1 | Velcro para a bateria (MB3 R$ 17,90) | frame | 🛒 comprar | AliExpress | R$ 11,26 |
| 1 | Saco anti-chamas para LiPo (ou carregar num pote de vidro, sempre olhando) |  | 🛒 comprar | AliExpress | R$ 10,75 |

## Energia B: cabo

| Qtd | Item | Onde vai | Situação | Comprar em | R$ |
|---|---|---|---|---|---|
| 1 | Fio paralelo 2 x 0,5 mm2 (~20 AWG), 3 m (~R$ 3/m; queda de ~0,9 V a 7 A em 2 m) | J1 | 🛒 comprar | loja de material eletrico | R$ 9,00 |
| 1 | Fonte de bancada ajustavel (~4,9 V, 8 A) (a da escola) |  | ✅ tem |  | — |

## Estacao terra

| Qtd | Item | Onde vai | Situação | Comprar em | R$ |
|---|---|---|---|---|---|
| 1 | ESP32-C3 Super Mini (de preferencia a Plus, com antena externa) (ver docs/TERRA.md) | capinha do celular | 🛒 comprar | AliExpress | R$ 10,90 |
| 1 | Cabo USB-C <-> USB-C curto (OTG) (~R$ 8; o C3 e alimentado pelo celular) | celular -> C3 | 🛒 comprar | AliExpress | R$ 8,00 |
| 1 | Fita dupla face ou velcro (sobra da do frame) | C3 na capinha | ✅ tem |  | — |

## Bancada

| Qtd | Item | Onde vai | Situação | Comprar em | R$ |
|---|---|---|---|---|---|
| 1 | Multimetro, ferro, estanho, fluxo, malha, pinca, lupa (robotica / escola) |  | ✅ tem |  | — |
| 1 | Fusivel 4 A + porta-fusivel (do DAMP) | primeiro liga | ✅ tem |  | — |
| 1 | Alcool isopropilico | limpar o fluxo | opcional | MB3 | — |

## Depois (opcional)

| Qtd | Item | Onde vai | Situação | Comprar em | R$ |
|---|---|---|---|---|---|
| 1 | Fluxo optico PMW3901 (segura o drone parado) | J4 | opcional | AliExpress | — |
| 2 | Sonar HC-SR04 / IR FC-51 (ja tem; fora da versao minima) | J2 / J3 | ✅ tem |  | — |
