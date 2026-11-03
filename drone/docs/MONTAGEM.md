# Roteiro de montagem

A ordem aqui não é arbitrária: cada fase valida uma coisa só, e nenhuma fase
começa antes de a anterior estar funcionando. Assim, quando algo falhar, você
sabe exatamente o que mudou desde a última vez que funcionava.

**Nada de hélice até a Fase 5.**

---

## Lista de compras

Para as fases 0 a 4 (bancada), com o que você já tem:

| Item | Qtd | Para quê |
|---|---|---|
| MOSFET **IRLZ44N** ou **IRLB8721** (TO-220) | 4 | driver de bancada — pernas grossas, fácil de soldar |
| Diodo **1N5822** (DO-201, 3 A) | 4 | roda livre do motor |
| Capacitor cerâmico **100 nF** | 4 | mata o ruído das escovas do motor |
| Resistor 100 Ω | 4 | porta do MOSFET |
| Resistor 10 kΩ | 4 | porta em nível baixo no boot |
| Resistor 1 kΩ e 2 kΩ (ou 2,2 kΩ) | 2+2 | divisor de nível do ECHO |
| Capacitor 470–1000 µF *low ESR* | 1 | segura o pico de corrente |
| Protoboard + jumpers | 1 | fases 1 e 2 |

Para a Fase 5 em diante (o que voa), some:

| Item | Qtd | Para quê |
|---|---|---|
| MOSFET **AO3400A** (SOT-23) | 4 | driver de voo — 3 g contra os 9 g dos TO-220 |
| Diodo **SS34** (SMD, 3 A, 40 V) | 4 | o mesmo papel do 1N5822, ~1 g mais leve cada |
| **Hélice 75 mm, furo 1,0 mm, 2 CW + 2 CCW** | 2 jogos | ver "Hélice" em [`ORCAMENTO.md`](ORCAMENTO.md) |
| **LiPo 1S 530 mAh 30C** (Leão LB530LP1, 14 g, conector Molex) | 1 | ver "Bateria" em [`ORCAMENTO.md`](ORCAMENTO.md) |
| Rabicho Molex fêmea (o lado do drone) | 2 | um soldado no drone, o outro de reserva |
| Carregador USB de LiPo 1S com saída Molex (tipo Syma), ~500 mA | 1 | ver abaixo |

> Se um dia usar bateria **LiHV** (3,8 V nominal, carga a 4,35 V — as da
> BETAFPV são assim), o carregador precisa ter modo LiHV. O erro perigoso é o
> inverso: **LiPo comum no modo LiHV** sobrecarrega a célula. A Leão é LiPo
> comum (4,2 V), e o carregador comum basta.

> **O TP4056 comum carrega a 1 A**, e isso é 1,5C numa célula de 650 mAh — mais
> do que LiPo de hobby costuma aceitar. Use um carregador USB de LiPo 1S, desses
> de micro drone, que carrega a ~500 mA. (O TP4056 serve para as células de
> 2200 mAh, onde 1 A é menos de 0,5C. Também dá para baixá-lo a 580 mA trocando
> o resistor de programação, R3 na maioria dos módulos, de 1,2 kΩ para 2 kΩ.)

Cada TO-220 pesa ~2,3 g; os quatro somam 9 g, quase 10 % do drone. Na bancada
o peso não importa e a facilidade de soldar importa muito — por isso os dois.

> **Os dois mini L298N que você já tem são peça de bancada, não de voo.** Eles
> derrubam ~2 V no caminho: sobram 1,7 V dos 3,7 da célula, e como o empuxo cai
> com o quadrado da tensão, isso é 22 % do empuxo. Somando os ~24 g dos dois
> módulos mais o step-up que a lógica deles exige, o empuxo/peso fica em 0,29 —
> não sai do chão. Nas Fases 2 e 3 eles são ótimos: ponte completa, invertem o
> motor por software, e ajudam a conferir a fiação. A conta inteira está em
> [`ORCAMENTO.md`](ORCAMENTO.md).

> Com motor **1020**, use **AO3400** e não SI2302. O 1020 puxa 2–3 A, e no
> SI2302 (50 mΩ) isso dá 0,45 W dissipados num SOT-23 — ele cozinha. O AO3400
> tem 22 mΩ. Na hora de soldar, dê uma gota generosa de solda no pad do dreno
> com um pedaço de fio grosso: em SOT-23, o cobre da placa é o dissipador.

> **Não use MOSFET comum** (IRF540, IRFZ44 sem o "L"). Eles precisam de 10 V na
> porta para ligar de verdade. Com os 3,3 V do Pico ficam meio ligados,
> esquentam e roubam tensão do motor. Procure **"logic level"** na descrição.

---

## Fase 0 — firmware sozinho

Nada conectado no Pico. Só o cabo USB.

```bash
cd drone
pio run -e picow -t upload      # segure BOOTSEL ao plugar o USB
pio device monitor
```

**Sucesso:** aparece `=== Controladora de voo (Raspberry Pi Pico W) ===`, depois
`[WIFI] AP "DRONE-PICO" -> http://192.168.4.1`. Conecte o celular nessa rede
(senha `voar1234`) e abra o endereço: a interface com os dois joysticks carrega.

Vai aparecer `BMI160 nao respondeu` e o LED vai piscar rápido. **É esperado** —
não há sensor ligado ainda.

Isso já valida toolchain, gravação, WiFi, servidor HTTP e WebSocket. Se a página
não abrir, o problema está aqui, e não vale seguir.

---

## Fase 1 — sensores, na protoboard

Ainda sem motor. Monte tudo em protoboard: é muito mais rápido corrigir um fio
do que dessoldar.

### I2C

| Sensor | SDA | SCL | Alimentação |
|---|---|---|---|
| BMI160 | GP4 | GP5 | 3V3 |
| BMP280 | GP4 | GP5 | 3V3 |

Os dois no mesmo barramento. A maioria dos módulos já traz pull-up; se nenhum
dos dois responder, ponha 4,7 kΩ de SDA e SCL para o 3V3.

**Sucesso:** `[BMI160] ok` e `[BMP280] ok` no serial.

Se o BMI160 não responder, tente trocar `BMI160_I2C_ADDR` de `0x69` para `0x68`
em `include/config.h` — depende de como o SDO do seu módulo está ligado. Mesma
coisa para o BMP280 entre `0x76` e `0x77`.

### Confira a orientação — este passo evita capotamento

Na página de pilotagem, incline o conjunto na mão e observe:

- Inclinar **para a direita** → `Roll` fica **positivo**
- Levantar o **nariz** → `Pitch` fica **positivo**

Se estiver trocado ou invertido, corrija **apenas** o bloco de remapeamento no
início de `AHRS::update()` (`src/ahrs.cpp`). É o único lugar do código que
conhece a orientação física do sensor. Depois rode `cd test && make` — os testes
conferem exatamente essa convenção.

### Ultrassônicos

O HC-SR04 comum precisa de 5 V (use o step-up) e o pino ECHO sai em 5 V, que
**queima** o GPIO do Pico. Divisor obrigatório:

```
ECHO ──[1 kΩ]──┬── GP3 (baixo) / GP1 (frente)
               │
            [2,2 kΩ]
               │
              GND
```

Se o seu for **HC-SR04P** ou **RCWL-9610**, ele trabalha em 3,3 V e liga direto.

| | TRIG | ECHO |
|---|---|---|
| Para baixo | GP2 | GP3 |
| Para frente | GP0 | GP1 |

### Infravermelho

FC-51 alimentado em **3,3 V** (assim a saída já sai em nível seguro).
Esquerdo em **GP18**, direito em **GP19**. Ajuste o potenciômetro para disparar
a ~20–30 cm.

**Sucesso:** aproxime a mão de cada sensor e veja `Solo`, `Frente` e `IR`
reagirem na telemetria. `Altura` deve acompanhar a distância do chão.

---

## Fase 2 — driver e motores, ainda sem hélice

### O circuito, um por motor

```
        +BAT
          │
          ├──────────┐
          │          │
      [MOTOR]    [1N5822]   ← o diodo é obrigatório: a bobina devolve um
          │          │         pico ao desligar e mata o MOSFET sem ele
          ├──────────┘
          │ dreno
    ┌──[MOSFET]
    │     │ fonte
    │     └──── GND  (comum com o GND do Pico!)
    │
GPIO ──[100Ω]── porta
                  │
              [10kΩ]
                  │
                 GND    ← segura a porta em zero no boot; sem ele o motor
                          pode dar um tranco durante o reset
```

Atenção ao diodo: a **faixa** vai para o lado do `+BAT`.

Use **1N5822 (3 A)**, não 1N5819. A corrente de roda livre é a corrente inteira
do motor — até 3 A no 1020 — e o 1N5819 é de apenas 1 A.

**Solde um capacitor cerâmico de 100 nF direto nos terminais de cada motor.**
Motor escovado gera faísca nas escovas, e isso vira ruído elétrico que corrompe
o I2C — o sintoma é o BMI160 travar em pleno voo. O capacitor custa centavos e
resolve. Mantenha também os fios do I2C curtos e longe dos fios de motor.

| Motor | GPIO |
|---|---|
| M1 frente-direita | GP6 |
| M2 trás-direita | GP7 |
| M3 trás-esquerda | GP8 |
| M4 frente-esquerda | GP9 |

### Ajuste o firmware para MOSFET

Em `include/board_pico.h`:

```c
#define MOTOR_DRIVER_L298N 0        // era 1
#define MOTOR_PWM_FREQ     20000    // era 5000
```

O L298N é lento e precisava de 5 kHz. O MOSFET chaveia rápido, e 20 kHz fica
acima da faixa audível — o motor para de assobiar.

### Teste, um motor de cada vez

Monte **um** circuito primeiro. Arme pela interface, dê throttle baixo, confirme
que o motor gira. Só então monte os outros três.

### O teste que não dá para pular

Com os 4 motores girando devagar e **sem hélice**, segure o conjunto e incline:

> Ao inclinar para um lado, os motores **do lado que baixou** têm que acelerar.

Se acelerarem os do lado que subiu, o sinal do PID está invertido e o drone vai
acelerar na direção da queda. **Pare e corrija antes de qualquer outra coisa.**

---

## Fase 3 — placa definitiva

Agora que tudo funciona na protoboard, transfira para a fenolite.

**Use a placa inteira, 130 × 30 mm.** Se ela vier maior, corte na borda de uma
fileira de ilhas — cortar no meio delas deixa você sem onde soldar na borda.
Risque com estilete contra uma régua dos dois lados e quebre, ou serre. O pó de
fenolite é irritante: máscara, de preferência ao ar livre.

Sugestão de ocupação:

```
 ┌──────────────────────────────────────────────────────────┐ 30 mm
 │  M1  M2   ┌────────────────────┐   BMI160   +  −  ┌────┐ │
 │  ┌┐  ┌┐   │                    │   BMP280         │470 │ │
 │  └┘  └┘   │      Pico W        │                  │ µF │ │
 │  ┌┐  ┌┐   │      51 x 21       │   sonar   IR  IR └────┘ │
 │  └┘  └┘   │                    │                         │
 │  M3  M4   └────────────────────┘   PH2.0 da bateria      │
 └──────────────────────────────────────────────────────────┘
                            130 mm
```

O Pico ocupa 51 × 21 e sobram **~79 × 30 mm** — folga de sobra para os quatro
circuitos de MOSFET, os barramentos de sensor e os terminais, sem nada
espremido. Solde o Pico pelas ilhas laterais (castelo), sem barra de pinos —
a barra pesa e levanta o conjunto à toa.

> Os 130 mm custam **5,8 g** contra a mesma placa cortada em 80 mm (3,8 g de
> fenolite, 2,0 g de trilho a mais no frame), o que vale ~0,08 de empuxo/peso.
> É pouco, e a área extra é o que evita fio solto pendurado numa aeronave que
> vibra — mas está contabilizado em [`ORCAMENTO.md`](ORCAMENTO.md), e se o teste
> de empuxo vier magro, cortar a placa é um dos cortes disponíveis.

**Capacitor de 470–1000 µF direto nos terminais da bateria.** Não é opcional: é
ele que segura o pico de corrente que reinicia o Pico.

**Trilhas separadas** para motor e para o Pico, unidas só no polo da bateria.
Fio compartilhado leva a queda de tensão dos motores até o microcontrolador.

---

Bateria, MOSFET e a conta de peso completa estão em
[`ORCAMENTO.md`](ORCAMENTO.md).

---

## Fase 4 — frame

```bash
cd drone/cad
python3 placa.py                    # tudo numa placa só: 41 g, 164 x 165 mm
python3 frame.py                    # ou só o frame: 27 g, 1020 + hélice 75 mm
```

PLA ou PETG, camada 0,2 mm, **4 perímetros e 40 % de preenchimento** — as peças
são finas, quase tudo vira perímetro, e é o perímetro que segura. Sem suporte.

Montagem:

- Motor entra no tubo por atrito (0,1 mm de interferência). Se ficar folgado,
  aumente `motor_fit` e reimprima; uma gota de cianoacrilato resolve o resto.
- Placa em cima do quadro, presa por abraçadeira nos vãos dos trilhos.
- **Bateria embaixo.** Aproxima o centro de gravidade do plano das hélices.
- Ultrassônico de baixo no centro, apontado para o chão, longe do fluxo das
  hélices. O da frente no nariz, sem nada na frente do cone. Os IR a 90° para
  os lados.

Sentido de giro (visto de cima) e hélice correspondente:

```
    M4 (FL)  horário          M1 (FR)  anti-horário
              \                    /
                [ nariz para cima ]
              /                    \
    M3 (RL)  anti-horário       M2 (RR)  horário
```

Diagonalmente opostos giram no mesmo sentido. **Hélice de sentido errado empurra
ar para cima e inverte o mixer de guinada** — o drone gira sem parar e não há
firmware que corrija.

---

## Fase 5 — voo amarrado e ajuste de PID

Barbante nos 4 braços, preso ao chão, com uns 20 cm de folga. Área livre.
Óculos de proteção.

Comece com **metade** dos ganhos de `PID_RATE_ROLL_KP` e `PID_RATE_PITCH_KP` em
`include/config.h`. Suba o throttle devagar até o drone ficar leve no barbante.

| Sintoma | Causa |
|---|---|
| Oscilação rápida, chiado nos motores | `KP` alto demais |
| Oscilação lenta, balanço largo | `KI` alto demais |
| Demora a responder, parece mole | `KP` baixo demais |
| Oscila só com throttle alto | `KD` alto demais (amplificando vibração) |

Suba `KP` até começar a oscilar, volte para 70 % disso, e só então mexa em `KI`.
`PID_ANGLE_KP` define quão "duro" é o auto-nivelamento.

Ajuste rolagem e arfagem juntos — o layout é quadrado, então os dois usam os
mesmos valores.

---

## Fase 6 — voo livre

Área aberta, sem gente por perto, bateria carregada, ar parado.

Primeiro voo: suba 30 cm, paire, desça. Só isso. Depois vá aumentando.

Ligue o `ALT HOLD` e o `DESVIO` **um de cada vez**, em voos separados, para
saber a quem culpar se algo ficar estranho.

---

## Se você ainda estiver com os motores 716

As fases 0 a 3 valem igual — e são a maior parte do trabalho. Os L298N que você
tem servem perfeitamente para a bancada.

O que muda é a partir da Fase 4: os 716 dão 48 g de empuxo somados, e isso limita
o drone a ~30 g. Não cabem a placa perfurada, os ultrassônicos, os IR nem a
bateria de 1000 mAh. Para provar o voo com eles, veja **"Voar com o 716"** em
[`../cad/README.md`](../cad/README.md) — um drone de 34 g, só Pico + BMI160 +
MOSFET + bateria de 250 mAh.

Não é desperdício: valida AHRS, PID e o firmware no ar. Quando os 1020
chegarem, é só juntar as duas metades.
