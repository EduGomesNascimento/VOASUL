# Montagem — Raspberry Pi Pico W

## 1. Alimentação

O Pico W aceita **1,8 a 5,5 V no VSYS**, então a célula de 3,7 V vai direto,
sem regulador no meio. Essa é a vantagem prática dele sobre o ESP32 aqui.

```
  Bateria 3,7 V (+) ──┬── VSYS (pino 39)
                      ├── VS / VM dos dois L298N   (força dos motores)
                      └── entrada do step-up ──► 5 V ──► VSS dos dois L298N
                                                          (lógica, ~40 mA)
  Bateria (−) ────────┴── GND do Pico e dos dois módulos (terra comum!)
```

**O step-up alimenta só a lógica (VSS), nunca os motores.** Um MT3608 entrega
1–2 A; os quatro motores puxam 6–8 A de pico. Ligar os motores no step-up
derruba a saída dele e reinicia o Pico no meio do voo.

Por que o VSS precisa do step-up: a lógica do L298N é especificada para
**4,5–7 V**. Nos seus 3,7 V ele fica abaixo da faixa e chaveia de forma
imprevisível — funciona na bancada e falha no ar.

Outros dois itens que não são opcionais:

- **Capacitor de 470–1000 µF** (low ESR) direto nos terminais da bateria. É ele
  que segura o pico de corrente que reinicia a placa.
- **Trilhas separadas** para motores e para o Pico, unidas só no polo da
  bateria. Fio compartilhado leva a queda de tensão dos motores até o Pico.

Sobre a célula: os coreless 8520 puxam ~1,5–2 A cada, 6–8 A somados. Uma célula
de 1000 mAh 10–15C entrega 10–15 A e passa raspando. Uma célula de powerbank
(2–3C) afunda para menos de 3 V na primeira acelerada.

## 2. Acionamento dos motores (mini L298N, sem ENA/ENB)

O módulo mini não expõe ENA/ENB — eles ficam presos em nível alto internamente.
Então o PWM vai na **própria entrada IN1/IN3**, e a complementar IN2/IN4 fica
sempre em LOW:

| IN1 | IN2 | Saída |
|---|---|---|
| PWM | LOW | aciona (proporcional ao duty) |
| LOW | LOW | terminais em curto → **freia** |

Isso é PWM em *slow decay*. Consome um pouco mais que o modo roda-livre, mas a
resposta do throttle fica mais linear — o que ajuda o PID.

O firmware coloca IN2/IN4 em LOW **antes** de anexar o PWM, para que a ponte
comece parada em vez de depender de como o pino ficou flutuando no reset. Há
teste automatizado conferindo exatamente essa ordem.

> Se o seu módulo for **L9110S / HG7881** em vez de L298N (muitos "mini L298N"
> são), não muda nada: o acionamento por duas entradas é idêntico. O L9110S
> ainda funciona a partir de 2,5 V, o que dispensaria o step-up.

> Se você tiver um L298N grande, com ENA/ENB de verdade, mude
> `L298N_HAS_ENABLE` para `1` em `include/board_pico.h` e adicione os pinos
> `PIN_MOTOR_*_A`. Aí o PWM vai no enable e IN1/IN2 fixam o sentido.

### A conta de empuxo

Vale ter o número na mão antes de esperar que ele decole:

| | L298N | MOSFET SI2302 / AO3400 |
|---|---|---|
| Queda de tensão | ~2,0 V | ~0,05 V |
| Tensão no motor (bat. 3,7 V) | **1,7 V** | 3,65 V |
| Empuxo relativo | ~20 % | 100 % |

Com 1,7 V um 8520 dá algo como 8 g de empuxo, 32 g nos quatro. Some o peso dos
dois módulos, do Pico, dos sensores e da bateria e o resultado é que ele não
levanta. Trocar para 4× MOSFET canal N custa alguns reais e resolve — e o
firmware não muda: basta pôr `MOTOR_DRIVER_L298N` em `0`.

Enquanto isso, o L298N serve muito bem para validar sensores, PID, telemetria e
pilotagem com o drone amarrado. Esse trabalho não é perdido.

## 3. Mapa de pinos

| Função | GPIO | Pino físico | Observação |
|---|---|---|---|
| I2C0 SDA | GP4 | 6 | BMI160 + BMP280 no mesmo barramento |
| I2C0 SCL | GP5 | 7 | pull-ups 4,7 kΩ para 3V3 (a maioria dos módulos já tem) |
| M1 FR — IN1 (PWM) | GP6 | 9 | módulo A |
| M2 RR — IN3 (PWM) | GP7 | 10 | módulo A |
| M3 RL — IN1 (PWM) | GP8 | 11 | módulo B |
| M4 FL — IN3 (PWM) | GP9 | 12 | módulo B |
| M1 FR — IN2 | GP10 | 14 | fixo em LOW |
| M2 RR — IN4 | GP11 | 15 | fixo em LOW |
| M3 RL — IN2 | GP12 | 16 | fixo em LOW |
| M4 FL — IN4 | GP13 | 17 | fixo em LOW |
| Ultrassom baixo TRIG | GP2 | 4 | |
| Ultrassom baixo ECHO | GP3 | 5 | divisor de nível se o sensor for 5 V |
| Ultrassom frente TRIG | GP0 | 1 | |
| Ultrassom frente ECHO | GP1 | 2 | divisor de nível se o sensor for 5 V |
| IR esquerdo | GP18 | 24 | FC-51 alimentado em 3V3 |
| IR direito | GP19 | 25 | FC-51 alimentado em 3V3 |
| Bateria (ADC2) | GP28 | 34 | divisor 10 k/10 k |
| LED de estado | — | — | LED da placa (fica no chip de WiFi) |

**GP23, GP24, GP25 e GP29 são usados internamente pelo módulo de WiFi.** Não
use nenhum deles. É por isso que a bateria vai no GP28 com divisor externo, em
vez da leitura interna do VSYS (que passa pelo GP29).

### Divisor de nível do ECHO (obrigatório se o HC-SR04 for de 5 V)

O ECHO sai no nível do VCC do sensor. 5 V direto num GPIO de 3,3 V queima a
entrada — talvez não hoje, mas queima.

```
ECHO ──[1 kΩ]──┬── GP3 / GP1
               │
            [2 kΩ]
               │
              GND
```

Melhor ainda: use **HC-SR04P** ou **RCWL-9610**, que funcionam em 3,3 V e ligam
direto — sem divisor e sem precisar de 5 V para eles.

### Endereços I2C

- BMI160: `0x69` (padrão); `0x68` se o SDO estiver no GND.
- BMP280: `0x76` (padrão); `0x77` se o SDO estiver no VCC.

Ajuste em `include/config.h` se um scan I2C mostrar diferente. O BMP280 é
opcional: sem ele o firmware sobe igual, só perde o alt-hold acima do alcance
do ultrassom.

## 4. Orientação dos sensores e dos motores

O firmware assume o BMI160 montado com:
- **X apontando para a direita**, **Y para o nariz**, **Z para cima**.

Se a sua placa ficar girada, mude **apenas** o bloco de remapeamento no início
de `AHRS::update()` (`src/ahrs.cpp`) — ele é o único lugar do código que conhece
a orientação física do sensor. Não saia trocando sinais espalhados pelo
firmware: é assim que roll e pitch acabam trocados e o drone capota na
decolagem.

Depois de mexer ali, rode `cd test && make` antes de ligar hélice. Os testes
conferem justamente isso: inclinar 30° para a direita tem de dar `roll = +30`,
nariz 20° para cima tem de dar `pitch = +20`.

Sentido de giro (visto de cima), configuração X:

```
    M4 (FL)  horário          M1 (FR)  anti-horário
              \                    /
               \                  /
                 [ nariz para cima ]
               /                  \
              /                    \
    M3 (RL)  anti-horário       M2 (RR)  horário
```

Motores diagonalmente opostos giram no mesmo sentido. Com o L298N dá para
inverter um motor trocando IN1 com IN2 na ligação — mas é mais simples inverter
os dois fios do motor.

**Hélice certa em motor certo.** Hélice de sentido errado gera empuxo para baixo
e faz o mixer de guinada trabalhar ao contrário: o drone gira sem parar.

## 5. Posicionamento dos sensores de proximidade

- **Ultrassom para baixo**: cone de ~15°, longe do fluxo das hélices. Vento
  batendo no transdutor gera leitura errática. Aponte para baixo, no centro.
- **Ultrassom para frente**: no nariz, sem nada do frame na frente do cone.
- **IR esquerdo/direito**: a 90° para os lados. Ajuste o potenciômetro do FC-51
  para ~20–30 cm; alcance maior deixa o drone nervoso, desviando o tempo todo.

Os dois HC-SR04 pesam ~8,5 g cada — **17 g nos dois**, peso considerável nesse
porte. Se ficar apertado, o de frente sai primeiro: o de baixo é o que dá o
alt-hold, e vale muito mais.

## 6. Ordem de testes (não pule)

1. **Sem hélices**, no USB: monitor serial. Confirme `[BMI160] ok`,
   `[BMP280] ok` e `[RANGE] ... prontos`.
2. **Sem hélices**: conecte no WiFi `DRONE-PICO`, abra `http://192.168.4.1`.
   Incline o drone na mão e veja `roll`/`pitch` acompanharem. Aproxime a mão dos
   sensores e veja `Solo`, `Frente` e `IR` reagirem.
3. **Sem hélices**: arme e dê throttle. Confirme que os 4 motores giram e que
   inclinar o drone acelera os do **lado baixo**. Se acelerarem os do lado alto,
   o sinal do PID está invertido — corrija antes de seguir.
4. **Com hélices, drone amarrado** por barbante nos 4 braços, folga de ~20 cm.
   Suba o throttle devagar. Ajuste PID (comece com metade dos ganhos).
5. Só então, voo livre, em área aberta, com bateria carregada.

---

## Apêndice: pinos do ESP32

O firmware continua compilando para ESP32 (`pio run -e esp32dev`), com MOSFETs
em vez de L298N. Mapa em `include/board_esp32.h`:

| Função | GPIO |
|---|---|
| I2C SDA / SCL | 21 / 22 |
| Motores FR / RR / RL / FL | 25 / 26 / 27 / 4 |
| Ultrassom baixo TRIG / ECHO | 13 / 34 |
| Ultrassom frente TRIG / ECHO | 33 / 35 |
| IR esquerdo / direito | 39 / 32 |
| Bateria (ADC1) | 36 |
| LED | 2 |

Serve para a DevKit de **30 e de 38 pinos** — todos os GPIO acima existem nas
duas. Os da placa de 38 que sobram (GPIO 16, 17, 18, 19, 23) estão livres.

**Nunca ponha motor no GPIO 1, 3, 5, 14 ou 15.** Eles soltam sinal durante o
reset — o 14 e o 15 chegam a emitir PWM — e num pino de motor isso é um tranco
a cada reinício, com hélice. O pull-down de 10 kΩ na porta não segura, porque o
pino está acionando ativamente. (Versões anteriores deste mapa punham o motor
FL no 14. Se você já soldou assim, mude o fio para o GPIO 4.)

Evite também o **GPIO 12**: é pino de strap da tensão da flash. Puxado para
cima no boot, o módulo não inicia.

### Alcance do rádio

O enlace perde alcance muito mais na instalação do que no rádio. Na conta de
espaço livre, 19,5 dBm de transmissão e −98 dBm de sensibilidade dão centenas
de metros; na prática se chega a dezenas, e a diferença está toda aqui:

- **Antena para fora da placa.** A antena do ESP32 é a trilha em zigue-zague na
  ponta do módulo. Cobre embaixo dela ou do lado — ilhas da placa perfurada,
  bateria (o invólucro é de alumínio), fios de motor — desafina a antena e come
  de 10 a 20 dB. Monte o ESP32 numa ponta da placa de 130 mm com a antena
  **para fora da borda**, e a bateria embaixo da **outra** ponta. A Espressif
  pede 15 mm livres em volta da antena.
- **Capacitor de 220–470 µF entre VIN e GND, colado no ESP32.** Em potência
  máxima cada rajada de transmissão puxa ~250 mA. Sem reserva local, a tensão
  afunda e o ruído vai para o rádio e para o I2C.
- **Altura.** Com celular e drone a ~1 m do chão, a reflexão no solo cancela o
  sinal direto a partir de ~33 m (`4·h1·h2/λ`), e daí em diante a perda cresce
  40 dB por década em vez de 20. Celular levantado na mão já ajuda.
- **Seu corpo.** 2,4 GHz é a frequência que a água absorve. Corpo entre o
  celular e o drone custa de 3 a 10 dB: segure o celular à frente, não junto ao
  peito.
- **Ruído dos motores.** Motor com escova faz faísca, e faísca é ruído de banda
  larga. O capacitor de 100 nF nos terminais de cada motor também protege o
  rádio, e os fios do motor trançados irradiam menos.

No ESP32 a bateria **tem de** ficar no ADC1: o ADC2 não funciona com WiFi
ligado.

**Alimentação: step-up para 5 V → pino VIN.** Não ligue a LiPo direto no pino
3V3: carregada ela dá 4,2 V, e o máximo absoluto do ESP32 é 3,6 V. E não ligue
no VIN sem o step-up: o regulador AMS1117 da DevKit precisa de ~4,5 V na entrada
para entregar 3,3 V, e com 3,7 V o ESP32 reinicia sempre que o WiFi transmite.
