# Conferência completa: esquema e placa

## 1. A placa do Proteus (a sua, `pcb/proteus/`)

| Item | Resultado |
|---|---|
| Ligações (netlist) | ✅ estavam certas para a pinagem **antiga** (conferido na sessão anterior). |
| **Pegada do ESP32** | ❌ **espelhada.** Lendo o PDF de componentes: com a antena para a direita, a fileira `3V3 EN SP SN 34 … 5V` está **embaixo** (y = 62 mm) e a `GND 23 22 TX RX … CLK` está **em cima** (y = 42 mm). No DevKitC de verdade, visto de cima (componentes para cima) e com a antena para a direita, a fileira do 3V3 fica **em cima**. Montado do jeito normal, cada pino cairia na trilha errada: 5V no CLK, 3V3 no GND, e o ESP32 queimaria no primeiro liga. O defeito é da biblioteca `ESP32_38P`, não do seu desenho. |
| Como conferir com o ESP32 na mão | Antena para a direita, chip para cima: a fileira de cima começa (da direita para a esquerda) com **3V3, EN, VP, VN**. |
| Pinagem | ⚠ desatualizada: a placa nova usa outros GPIOs (tabela abaixo). |

**Conclusão:** não fabrique a placa do Proteus. A placa do KiCad substitui ela.

---

## 2. Esquema × placa do KiCad

| Verificação | Resultado |
|---|---|
| Esquema e placa vêm da mesma lista (`projeto.py`) | ✅ |
| Netlist exportada pelo KiCad do esquema × redes da placa | ✅ **33 redes, 126 pinos, 0 diferenças** (conferido sozinho em `gerar.py saidas`) |
| DRC da placa caseira (`drc.txt`) | ✅ **0 erros, 0 pinos desligados** |
| DRC da placa profissional (`pro/drc_pro.txt`) | ✅ **0 erros, 0 pinos desligados** |
| GND | fecha todo pelo cobre e pelos jumpers. Ele atravessa as ilhas dos pinos GND 14, 20 e 26 do ESP32 (cobre da placa, não o módulo): o teste de continuidade funciona sem o ESP32 encaixado. |
| Folga mínima entre cobres | 0,8 mm (pino, trilha, ilha) |
| Trilha mais fina | 0,8 mm, só nos 3 últimos mm antes de um pino de passo 2,54 |

---

## 3. Revisão elétrica

| Bloco | Verificação | Resultado |
|---|---|---|
| MOSFET AO3400A | porta a 3,3 V: Vgs(th) 0,65–1,45 V; Rds(on) ≈ 50 mΩ a 2,5 V | ✅ liga cheio com 3,3 V |
| | 100 Ω na porta (limita pico de corrente do GPIO) e 10k porta→GND (motor parado enquanto o ESP32 dá boot) | ✅ |
| Diodo SS34 | catodo no VBAT, anodo no dreno: segura o pico do motor ao desligar | ✅ |
| 100 nF 0805 por motor | no dreno↔VBAT, perto das ilhas | ✅ (melhor ainda: um 100 nF soldado direto nos terminais de cada motor) |
| Bateria | 1000 µF no VBAT, junto do J1 | ✅ |
| 5 V | MT3608 → pino 5V do ESP32 (o regulador do DevKit faz o 3V3) + 470 µF + sonares | ✅ ajuste 5,0 V antes de encaixar o ESP32 |
| Divisor da bateria | 10k/10k → IO35 (ADC1, funciona com Wi-Fi): 4,2 V → 2,1 V | ✅ |
| ECHO dos sonares | 1k série + 2k ao GND: 5 V → 3,33 V | ✅ |
| 2k do ECHO da frente | vai ao GND pela ilha do pino 14 do ESP32 | ✅ |
| Fluxo óptico J4 (PMW3901, opcional) | SPI em IO32 (MISO), IO33 (SCK), IO25 (MOSI), IO26 (CS); 3V3 e GND no conector. Nenhum é pino de strap | ✅ |
| J4 vazio | o firmware lê o ID do chip (0x49) **e** o inverso (0xB6): com o MISO flutuando nunca batem os dois, então "ausente" é certo | ✅ testado com sensor simulado |
| IR FC-51 | alimentado em 3,3 V, saída com pull-up do próprio módulo, entra no IO36/IO39 (só entrada) | ✅ |
| I²C | **dois barramentos**: BMP280 em IO21/22, BMI160 em IO16/18 (assim nada cruza embaixo do ESP32) | ✅ firmware atualizado |
| Endereços | BMI160 0x69 (SAO no 3V3), BMP280 0x76 (SDO no GND) | ✅ batem com o firmware |
| Pinos de boot | só o 12 é usado (ECHO da frente, preso em 0 pelo 2k, ver abaixo); 0, 2, 5 e 15 livres | ✅ |
| IO14 (TRIG baixo) | solta PWM no boot: o sonar de baixo dispara uma vez, inofensivo | ✅ |
| IO12 (ECHO frente) | pino de strap: tem de estar em 0 no boot. O 2k do divisor o prende ao GND, e o ECHO do sonar parado é 0 V | ✅ |
| IO16/IO17 | livres no **WROOM-32/32U**. No WROVER (com PSRAM) eles são da memória e **não servem** | ⚠ confirme que é WROOM |
| Antena | área sem cobre embaixo da antena do WROOM | ✅ |

### Pinagem nova do ESP32 (já no `include/board_esp32.h`)

| Função | GPIO | Função | GPIO |
|---|---|---|---|
| Motor FR | 17 | Sonar baixo TRIG / ECHO | 14 / 27 |
| Motor RR | 4 | Sonar frente TRIG / ECHO | 13 / 12 |
| Motor RL | 23 | IR esquerdo / direito | 36 / 39 |
| Motor FL | 19 | Bateria | 35 |
| I²C 1 (BMP280) SDA / SCL | 21 / 22 | I²C 2 (BMI160) SDA / SCL | 16 / 18 |
| Fluxo óptico MISO / SCK | 32 / 33 | Fluxo óptico MOSI / CS | 25 / 26 |

---

## 4. Revisão mecânica

| Item | Resultado |
|---|---|
| Diâmetro | Ø97,0 mm (o disco medido tem 97,08; o rebaixo do frame tem 97,9) ✅ |
| Peças embaixo × raios do frame (2 mm de vão nas diagonais) | MOSFET SOT-23 (1,1 mm) pode ficar sobre o raio; diodo SS34 (2,3 mm) e capacitor 0805 ficam **fora** da faixa de 8 mm do raio ✅ |
| Rabichos dos pinos embaixo | corte rente (≤ 1,5 mm) sobre as diagonais ⚠ |
| Anel de VBAT sobre o degrau do frame | o cobre encosta na fita de espuma, que isola ✅ |
| BMI160/BMP280 embaixo do ESP32 | barra macho (2,5 mm) + placa (1,6) + chip ≈ 5 mm < 11 mm de vão ✅ |
| Resistores em pé junto do ESP32 e do MT3608 | passam por baixo da borda dos módulos elevados ✅ |
| Cabo USB do ESP32 | sai pela direita, por cima do C2 (470 µF): encaixa, mas é justo ⚠ |

---

## 5. Jumpers (fios por cima): 11 no total

6 de GND, 1 de 3V3 (para o J4) e 4 de sinal de motor (FR, RR e 2 no RL). Três deles (GND do pino 14 ao
centro de trás, GND do centro ao canto do motor RL, e o 3V3 do J4) foram posicionados à mão em
`projeto.JUMPERS_FIXOS`. Lista com coordenadas: `saidas/jumpers.txt`;
desenho: `saidas/montagem_cima.pdf` (linhas finas entre dois furos).

A placa é de face única. Onde duas trilhas precisariam se cruzar, um fio rígido passa por cima,
do lado dos componentes, entre dois furos marcados na folha de montagem.

- **Jumpers de GND** que levam a corrente de volta dos motores: use fio **grosso** (20–22 AWG).
- **Jumpers de sinal** (porta de motor): qualquer fio rígido fino serve.
- Solde **todos os jumpers antes** dos módulos (ESP32, BMI160, BMP280).
