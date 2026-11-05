# Plano de montagem do drone VoaSul (placa de face única)

Cada fase tem quatro partes:

- **Para começar:** o que precisa estar pronto antes. Não pule.
- **Material à mão:** o que deixar na bancada.
- **Como fazer:** os passos, na ordem.
- **Para passar de fase:** o teste que tem de dar certo. Se não passar, **pare e conserte**.
  Problema numa fase vira um problema três vezes maior na seguinte.

Lista de compras com marcação (já tenho / comprei / falta / repensar):
<https://claude.ai/artifact/JfMoUsfyh2TjpAySVM2ZgH>

---

## Regras de segurança (valem em todas as fases)

| Risco | Regra |
|---|---|
| LiPo pegar fogo | Carregar só **com você olhando**, longe de coisa inflamável, de preferência dentro de pote de vidro ou de cerâmica. Bateria estufada vai para o descarte, não para o drone. |
| LiPo morrer | Nunca abaixo de **3,3 V** em repouso. O firmware pousa em 3,4 V: respeite. |
| Hélice cortar | **Sem hélice** em toda a bancada até a fase 8. Hélice só no teste de empuxo e no voo. |
| Curto na placa | O primeiro liga de toda placa nova passa por um **fusível de 3 A** em série. |
| Percloreto | Luva, óculos e janela aberta. Mancha roupa e pia para sempre. Não jogue no ralo: neutralize com bicarbonato e leve a um ponto de descarte. |
| Ferro de solda | Suporte firme e esponja úmida. Nunca apoie o ferro na bancada. |

---

## Fase 0: decisões que travam o resto

**Para começar:** nada.

**Como fazer:**
1. **Veja qual é o seu ESP32.** Olhe o módulo metálico: se tiver um conectorzinho dourado
   redondo (U.FL) no canto, é **WROOM-32U** e precisa da antena externa. Se tiver uma trilha em
   zigue-zague desenhada na placa, é **WROOM-32** comum e a antena externa não serve.
2. **Meça o ESP32 com régua:** a distância entre as duas fileiras de pinos tem de dar
   **25,4 mm** (centro a centro). A placa foi desenhada assim. Se der 22,9 mm, me avise antes de imprimir.
3. **Bateria:** LiPo **1S** (3,7 V, uma célula) de 500 a 600 mAh, 25C ou mais, ~15 g, Molex 51005.
   2S (7,4 V) queima os motores 1020.
4. **Disco de fenolite:** confira Ø97 mm e se é **face simples** ou dupla. A placa nova usa
   cobre **só embaixo**: numa dupla face, o cobre de cima é removido todo na corrosão (cubra com fita ou deixe corroer).

**Para passar de fase:** as quatro respostas anotadas na lista de compras.

---

## Fase 1: firmware só no USB

**Para começar:** ESP32 na mão, cabo USB **de dados** (cabo só de carga não grava).

**Material à mão:** PC com VS Code + PlatformIO, o repositório, o cabo.

**Como fazer:**
1. Abra a pasta `drone/` no PlatformIO e grave o ambiente do ESP32.
2. Abra o monitor serial (115200).
3. No celular, conecte na rede **DRONE-PICO** (senha `voar1234`) e abra `192.168.4.1`.

**Para passar de fase:**
- [ ] o monitor serial mostra o boot sem reiniciar sozinho em loop;
- [ ] a rede Wi-Fi aparece e a página abre;
- [ ] a página mostra telemetria mudando (mesmo sem sensor, o tempo de ciclo aparece).

> ⚠ Esta versão do firmware **nunca foi compilada para o ESP32 aqui** (só passou nos testes no PC).
> Se der erro de compilação, mande a mensagem inteira.

---

## Fase 2: sensores na protoboard

**Para começar:** fase 1 ok. BMI160 e BMP280 com a barra macho soldada.

**Material à mão:** protoboard, 8 jumpers macho-macho, multímetro.

**Como fazer:** ligue igual à placa final:

| Sensor | Pino | Vai em |
|---|---|---|
| BMI160 | 3V3, CS, SAO | 3V3 do ESP32 |
| BMI160 | GND | GND |
| BMI160 | SCL / SDA | **GPIO 18 / GPIO 16** (barramento próprio, Wire1) |
| BMI160 | VIN | **solto** |
| BMP280 | VCC, CSB | 3V3 |
| BMP280 | GND, SDO | GND |
| BMP280 | SCL / SDA | GPIO 22 / GPIO 21 |

**Para passar de fase:**
- [ ] a varredura I²C acha **0x76** (BMP280) no barramento 1 (21/22) e **0x69** (BMI160) no barramento 2 (16/18);
- [ ] parado na mesa, roll e pitch ficam em ±1° e não "andam" mais que 1° por minuto;
- [ ] inclinar para a frente aumenta o pitch e para a direita aumenta o roll (anote o sinal: se estiver ao contrário, me avise);
- [ ] a altitude do BMP280 oscila menos de ±0,3 m parada.

---

## Fase 3: fabricar a placa (transferência térmica, face única)

**Para começar:** fases 0 e 2 ok (a pinagem foi confirmada). Acesso a uma impressora **laser**.

**Material à mão:** disco de fenolite, palha de aço, detergente, álcool isopropílico, papel
glossy, ferro de passar roupa (sem vapor), bacia com água, caneta de retoque, percloreto,
pote plástico com tampa, luvas, régua, furadeira/micro retífica, brocas 0,9 / 1,0 / 1,3 mm.

**Como fazer:**
1. **Imprima o PDF de transferência** (`kicad/saidas/transferencia_B_Cu.pdf`) em **100%**, sem
   "ajustar à página". **Meça a régua de 100 mm impressa:** tem de dar 100 mm. Se der 98 ou 102, a escala está errada.
2. **Prepare o cobre:** palha de aço com detergente, em círculos, até ficar rosa-brilhante por
   igual. Depois álcool. **Não encoste o dedo** no cobre daí em diante (gordura da pele = falha).
3. **Transfira:** toner virado para o cobre, prenda com fita. Ferro no máximo do algodão,
   **3 a 5 minutos** apertando e girando, insistindo nas bordas. Deixe esfriar 1 minuto.
4. **Tire o papel:** de molho na água por 10 minutos, depois esfregue com o dedão até sair todo o papel branco.
5. **Confira com lupa, trilha por trilha.** Falha pequena: retoque com a caneta. Falha grande
   ou trilha borrada encostando em outra: **lixe e repita** (é por isso que tem placa reserva).
   A folga é de 0,8 mm justamente para o toner amassado não encostar.
6. **Corroa:** percloreto **morno** (40–50 °C em banho-maria), placa boiando com o cobre para
   baixo, ou mexendo o pote a cada minuto. Leva de 10 a 25 minutos. Tire quando todo o cobre
   fora do toner sumir. Lave bem.
7. **Tire o toner** com palha de aço ou acetona.
8. **Fure** de baixo para cima (lado do cobre), broca reta, devagar:
   **0,9 mm** pinos e resistores; **1,0 mm** motor, MT3608, conectores e eletrolíticos; **1,3 mm** bateria.
9. **Estanhe** as trilhas com o ferro (opcional, mas evita oxidar).

**Para passar de fase (antes de soldar qualquer peça):**
- [ ] **sem curto**: medindo resistência, VBAT↔GND, +5V↔GND e +3V3↔GND dão **circuito aberto** (OL);
- [ ] **continuidade** de cada rede, pela tabela de redes (`kicad/saidas/redes.txt`): bip de ponta a ponta;
- [ ] encaixe as **barras fêmea com o ESP32 encaixado nelas** sobre os furos: entram sem forçar;
- [ ] nenhuma trilha mais fina que ~1 mm em nenhum ponto (exceto os "pescoços" nos pinos).

---

## Fase 4: soldar, em ordem

A ordem importa: **baixo antes de alto**, e o que fica embaixo de outra peça antes dela.

**Para começar:** fase 3 ok.

**Material à mão:** ferro 30–60 W (ponta fina), estanho com fluxo, fluxo em pasta, malha
dessoldadora, pinça, alicate de corte, lupa, multímetro, fio rígido (jumper).

| # | Peça | Cuidado | Teste logo depois |
|---|---|---|---|
| 1 | **MOSFETs Q1–Q4** (SOT-23, lado do cobre) | Fluxo na ilha, prenda um pino, alinhe, solde os outros. Pino 1 = porta. | Sem ponte entre os 3 pinos (bip). |
| 2 | **Diodos D1–D4** (SS34, lado do cobre) | **Faixa (catodo) para o lado de fora**, no anel de VBAT. | Diodo do multímetro: ~0,2 V num sentido, OL no outro. |
| 3 | **Jumpers** (fio rígido por cima) | Só os que o desenho mostra, retos e encostados na placa. | Bip de ponta a ponta. |
| 4 | **BMI160 e BMP280**, embaixo do ESP32 | Barra macho com o **plástico na placa**; corte a sobra dos pinos rente. Altura total < 7 mm. | Nada encosta no ESP32 encaixado. |
| 5 | **Resistores em pé** | Confira o valor com o multímetro **antes** de soldar. | Medir na placa: 100 Ω, 10k, 1k, 2k nos lugares certos. |
| 6 | **Capacitores 100 nF** | Sem polaridade. | — |
| 7 | **Barras fêmea do ESP32** | Solde com o **ESP32 encaixado**, para alinhar. Um pino de cada ponta primeiro, confira se ficou reto e só depois o resto. | ESP32 entra e sai sem forçar. |
| 8 | **Conectores J2 (sonar), J3 (IR) e J4 (fluxo óptico)** | Solde o J4 mesmo sem ter o módulo: ele é opcional e o drone voa sem. | — |
| 9 | **Eletrolíticos C1 e C2** | **Polaridade!** Listra = negativo, vai na ilha de GND. Ao contrário, ele estoura. | — |
| 10 | **MT3608** em 4 pernas de fio rígido (~5 mm de altura) | Confira IN+/IN−/OUT+/OUT− na serigrafia do módulo **e** na placa. | — |
| 11 | **Rabicho da bateria** (Molex) | **+ (vermelho) na ilha quadrada**, a de fora. | — |
| 12 | **Fios dos motores** | Por último, depois de passar pelo braço do frame. + (vermelho) na ilha quadrada. | — |

**Para passar de fase:**
- [ ] repita os testes de curto da fase 3 (agora com as peças): VBAT↔GND **não** pode dar zero.
  Com C1 soldado o multímetro sobe devagar até OL: isso é normal, é o capacitor carregando;
- [ ] olhe tudo com lupa procurando ponte de solda, principalmente no SOT-23 e nas barras.

---

## Fase 5: primeiro liga, SEM ESP32 e SEM motor

**Para começar:** fase 4 ok, ESP32 **fora** da placa, motores **desligados**.

**Material à mão:** bateria carregada (4,1–4,2 V), fusível 3 A com porta-fusível, multímetro, chave de fenda pequena.

**Como fazer:**
1. Bateria → **fusível** → placa.
2. Meça VBAT (ilha + da bateria): igual à bateria.
3. Meça a saída do MT3608 e **gire o trimpot até 5,0 V** (5,0 a 5,1). O multivoltas precisa de muitas voltas: é normal.
4. Meça os 5 V no pino 5V do soquete do ESP32 e no pino 6 do J2.
5. Meça a porta de cada MOSFET: **0 V** (o pull-down de 10k está segurando).

**Para passar de fase:**
- [ ] 5,0 V estáveis; o MT3608 não esquenta;
- [ ] fusível inteiro;
- [ ] portas em 0 V.

---

## Fase 6: liga COM ESP32, sem hélice

**Para começar:** fase 5 ok. Firmware da fase 1 gravado.

**Material à mão:** o de antes + celular + 4 motores sem hélice + papel e caneta.

**Como fazer e testar:**
1. Encaixe o ESP32 **com a bateria desligada**. Ligue com o fusível.
2. Meça o 3V3 no pino do ESP32: 3,2 a 3,35 V.
3. Abra a página: atitude, altitude e bateria aparecem. **Calibre a bateria**: compare a
   tensão da página com o multímetro e ajuste `VBAT` no firmware se errar mais de 0,05 V.
4. **Teste de canal, um motor por vez** (ainda sem hélice), pela tela de teste de motor:
   gire cada motor a 10 % e anote **qual gira** e **para que lado**.

| Motor | Posição | Tem de girar |
|---|---|---|
| M1 FR | frente-direita | anti-horário (CCW), visto de cima |
| M2 RR | trás-direita | horário (CW) |
| M3 RL | trás-esquerda | anti-horário (CCW) |
| M4 FL | frente-esquerda | horário (CW) |

   Girou para o lado errado: troque os **dois fios** daquele motor. Girou o motor errado:
   confira os pinos (`include/board_esp32.h`).
5. **Corrente de partida (para o relatório de Potência):** multímetro em 10 A em série com a
   bateria, motor sem hélice, com e sem o soft starter. Anote o pico.

**Para passar de fase:**
- [ ] cada motor responde ao seu canal e gira para o lado da tabela;
- [ ] desligar o Wi-Fi do celular faz os motores pararem em < 1 s (failsafe);
- [ ] nenhum motor dá tranco quando o ESP32 reinicia.

---

## Fase 7: montagem mecânica e pesagem

**Para começar:** fase 6 ok. Frame `cad/frame_redondo.stl` e pés impressos.

**Material à mão:** balança, fita dupla face de espuma, velcro, abraçadeiras finas, cola quente (pouca), hélices.

**Como fazer:**
1. Motores nos tubos do frame (entram justos; **não cole**): CW e CCW nos lugares da tabela.
2. Fios pelo braço, placa no degrau com 4 quadradinhos de fita espuma. A **seta do frame** é a
   frente: o lado do MT3608 aponta para ela.
3. Bateria embaixo, no centro, com velcro. O centro de gravidade tem de cair **no centro do
   X**: levante o drone pelas pontas de dois braços opostos, e ele não pode tombar para um lado.
4. Pese.

**Para passar de fase:**
- [ ] peso total **≤ 126 g** (sem sonar da frente e sem IR). Acima de 135 g, fale comigo antes de tentar voar;
- [ ] centro de gravidade no meio (± 3 mm).

---

## Fase 8: teste de empuxo na balança

**Para começar:** fase 7 ok. Agora **com hélice**.

**Material à mão:** balança, um peso de ~300 g (ex.: pacote de arroz), fita, óculos.

**Como fazer:** o método completo está em `docs/ORCAMENTO.md`. Resumo: drone preso de cabeça
para baixo em cima do peso, na balança. Hélices empurram o ar para cima, então a balança mostra **mais**
peso. A diferença é o empuxo. Suba o acelerador aos poucos até 100 % por 2 s.

**Para passar de fase:**

| Empuxo / peso | O que fazer |
|---|---|
| ≥ 1,6 | Ótimo: siga. |
| 1,4 – 1,6 | Dá para voar, sem sonar da frente nem IR. |
| 1,3 – 1,4 | Só voo amarrado. Use as alavancas de peso (placa 0,8 mm, tirar barra fêmea). |
| < 1,3 | **Não voe.** Revise hélice, bateria e peso antes. |

---

## Fase 9: voo amarrado

**Para começar:** fase 8 com empuxo/peso ≥ 1,4.

**Material à mão:** linha de pesca (2 pedaços de 50 cm), dois pesos ou o pé de uma mesa, óculos.

**Como fazer:** prenda o drone por **duas pontas opostas** em linhas curtas, presas no chão. Ele
sobe no máximo 30 cm. Suba o acelerador devagar e observe:

- tomba sempre para o mesmo lado → centro de gravidade ou motor fraco;
- oscila rápido (zumbido) → ganho P ou D alto;
- oscila devagar e vai aumentando → ganho P baixo ou I alto;
- gira no próprio eixo (yaw) → algum motor está com hélice ou sentido trocado.

**Para passar de fase:**
- [ ] paira amarrado 30 s sem oscilar, com o acelerador ~70 %;
- [ ] bateria ao final acima de 3,6 V.

---

## Fase 10: primeiro voo livre

**Para começar:** fase 9 ok. Ambiente **fechado e amplo** (quadra, garagem vazia), sem vento, sem pessoas perto.

**Checklist pré-voo (todo voo):**
- [ ] bateria ≥ 4,1 V;
- [ ] hélices firmes e nos motores certos (CW/CCW);
- [ ] nada solto (fio, fita);
- [ ] celular conectado, telemetria chegando;
- [ ] você a 3 m, com o polegar pronto para cortar o acelerador.

**Como fazer:** decole até 0,5–1 m, paire 20 s e pouse. Aumente o tempo aos poucos.

**Para passar de fase:** 5 voos curtos seguidos sem susto.

---

## Fase 11: alcance (para o professor de Comunicações)

**Para começar:** fase 10 ok (ou o drone **no chão**, ligado, sem hélice: o rádio é o mesmo).

**Como fazer:** a página mostra o RSSI. Ande se afastando, anotando **distância × RSSI ×
perda de pacotes** a cada 10 m, em campo aberto, drone a ~1 m do chão. Repita com o celular e com a luva (XIAO, ESP-NOW).

**Para passar de fase:** a tabela pronta e o gráfico RSSI × distância.

---

## Fase 12: extras (sonar da frente, IR, fluxo óptico, luva de gestos)

Um de cada vez, **cada um com o seu teste antes de voar**:

- **Sonar da frente / IR:** peso volta a ser problema. Pese e refaça a conta de empuxo/peso.
- **Fluxo óptico PMW3901 (opcional, no J4):** segura o drone parado quando você solta o
  manche (ou faz "pare" na luva). Sem ele o drone voa igual, só vai à deriva devagar.
  1. **Drone desligado:** ligue o módulo no J4 (3V3, MISO, SCK, MOSI, CS, GND, na ordem da
     serigrafia). Lente **para baixo**, no centro do frame, sem nada na frente. Nunca ligue
     nem desligue o módulo com a bateria conectada.
  2. Ligue o drone e olhe o Serial (ou a página): tem de aparecer
     `[PMW3901] presente`. Sem o módulo aparece `ausente` e o quadro **Fluxo** da página
     mostra "sem módulo". Os dois casos são normais.
  3. **Teste dos sinais, sem hélice, motores desarmados:** segure o drone a ~30 cm de um
     chão com textura (piso, tapete; vidro e piso liso não servem). O quadro **Fluxo** mostra
     duas velocidades: `frente / direita` (m/s).
     - Empurre o drone **para a frente**, sem girar: o primeiro número fica **positivo**.
     - Empurre **para a direita**: o segundo fica **positivo**.
     - Só **incline** o drone no lugar: os dois ficam perto de zero (o firmware desconta a
       inclinação pelo giroscópio).
     Se um sinal estiver trocado, mude `FLOW_SIGN_FWD` / `FLOW_SIGN_RIGHT` em
     `include/config.h`; se frente e direita estiverem trocadas, `FLOW_SWAP_XY 1`.
  4. Abaixo de 8 cm (no chão, decolando) e acima de 2,5 m ele não corrige: o quadro mostra
     "sem leitura". É esperado.
  5. **Voo amarrado:** solte o manche a ~50 cm. O quadro mostra "segura" e o drone deve
     parar de derivar. Se oscilar para frente e para trás, baixe `FLOW_KP_DEG_PER_MPS`
     (8 → 5). Se ainda derivar, suba (8 → 11).
- **Luva:** ver `docs/LUVA_DE_GESTOS.md`. Primeiro com o drone **sem hélice** na bancada,
  conferindo que cada gesto aparece certo na telemetria. Só depois em voo amarrado.

---

## Ferramentas e materiais de teste (resumo)

| Item | Para quê | Fases |
|---|---|---|
| Multímetro com bip | curto, continuidade, tensão, corrente de partida | 3–6, 11 |
| Fusível 3 A + porta-fusível | primeiro liga de placa nova | 5, 6 |
| Lupa com luz | conferir toner e soldas do SOT-23 | 3, 4 |
| Régua de aço | escala da impressão, distância das fileiras do ESP32 | 0, 3 |
| Balança 0,1 g | peso e empuxo | 7, 8 |
| Óculos de proteção | percloreto, hélice | 3, 8–10 |
| Pote de vidro ou cerâmica | carregar LiPo com segurança | todas |
| Linha de pesca | voo amarrado | 9 |
| Trena de 50 m (ou passos contados) | teste de alcance | 11 |
