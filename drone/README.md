# Controladora de voo — Raspberry Pi Pico W

> **Novo (nov/2026):** placa de face única no KiCad para o **ESP32 DevKit 38 pinos** em
> [`kicad/`](kicad/README.md) (esquema, placa, PDF de transferência, versão profissional com
> Gerber e visualizador 3D). Plano de montagem com testes: [`docs/PLANO_DE_MONTAGEM.md`](docs/PLANO_DE_MONTAGEM.md).
> Controle: app no celular (página do próprio drone). Lista de materiais: [`docs/BOM_TOTAL.md`](docs/BOM_TOTAL.md). Para retomar o trabalho:
> [`CONTEXTO_PARA_CONTINUAR.md`](CONTEXTO_PARA_CONTINUAR.md).

Firmware completo para um quadricóptero micro: Pico W, BMI160 (giroscópio +
acelerômetro), 2 ultrassônicos HC-SR04, 2 sensores IR de obstáculo, 4
micromotores coreless e 2 módulos mini L298N. O BMP280 é opcional.

Pilotagem pelo celular: o Pico sobe uma rede WiFi própria e serve a interface
com dois joysticks e telemetria. Sem aplicativo, sem rádio.

O mesmo código compila para ESP32 (`pio run -e esp32dev`) — ver
[`docs/HARDWARE.md`](docs/HARDWARE.md).

## Antes de montar

Três pontos que mudam o resultado, detalhados em
[`docs/HARDWARE.md`](docs/HARDWARE.md):

1. **A lógica do L298N (VSS) precisa de 4,5–7 V.** Seus 3,7 V ficam abaixo da
   faixa. Use o step-up para o VSS — e **só** para o VSS: os motores puxam
   6–8 A de pico e queimariam o step-up.
2. **O mini L298N não tem ENA/ENB.** O PWM vai na própria IN1/IN3, com IN2/IN4
   fixos em LOW. O firmware já faz isso.
3. **O L298N derruba ~2 V.** Sobram 1,7 V nos motores, cerca de 20 % do empuxo —
   não levanta. Trocar por 4× MOSFET canal N (SI2302/AO3400) resolve, custa
   alguns reais, e no firmware é uma linha: `MOTOR_DRIVER_L298N` em `0`.

Até lá, o L298N valida sensores, PID e pilotagem com o drone amarrado.

## O que está implementado

| | |
|---|---|
| Estabilização | Mahony (quaternion) a 400 Hz, PID em cascata ângulo → velocidade angular |
| Modo de voo | Auto-nivelante: solta o manche e o drone volta à horizontal |
| Altitude | Fusão ultrassom + barômetro + aceleração vertical, com alt-hold |
| Obstáculos | Ultrassom frontal (recuo proporcional) + 2 IR laterais |
| Pilotagem | WiFi AP, servidor HTTP e WebSocket próprios, página embarcada; UDP para rádio futuro |
| Segurança | Failsafe por perda de sinal, pouso automático, corte por capotamento, corte por bateria |
| Núcleos | Voo isolado no núcleo 1; rede e LED no núcleo 0 |

### Como os sensores são usados

O **ultrassom de baixo** é o que dá altitude útil: 1 cm de resolução contra os
±0,5 m do BMP280. Abaixo de ~3 m ele manda; acima, o barômetro assume — e o
firmware mantém o barômetro calibrado contra o sonar enquanto pode, para que a
troca não produza um degrau. A aceleração vertical entra por cima dos dois,
porque ambos são lentos (20–26 Hz) e o controle precisa de resposta rápida.

A temperatura do BMP280 corrige a velocidade do som usada pelos ultrassônicos.
Entre 0 °C e 40 °C isso muda 7 % na distância: a 2 m são 14 cm.

Os dois HC-SR04 disparam **alternados**, nunca juntos — senão um escuta o eco do
outro. A medição do eco é por interrupção: `pulseIn()` trava a CPU por até 30 ms
e destruiria o loop de 400 Hz.

### Divisão entre os dois núcleos

- **Núcleo 1** (`setup1`/`loop1`): sensores, AHRS, PID, motores. 400 Hz, nada
  mais roda ali — jitter no loop vira oscilação no drone.
- **Núcleo 0** (`setup`/`loop`): WiFi, HTTP, WebSocket, UDP, telemetria e LED.

O LED da placa do Pico W fica pendurado no chip de WiFi, então só o núcleo 0
pode acioná-lo. Por isso o pisca-pisca vive no laço de rede.

## Sem dependências

Não há `lib_deps`. Os drivers de BMI160 e BMP280 falam direto por registradores,
e o servidor WebSocket (`src/websocket.cpp`, com SHA-1 e base64 próprios) foi
escrito à mão — as bibliotecas prontas divergem entre RP2040 e ESP32, e assim as
duas placas rodam exatamente o mesmo código, que ainda por cima dá para testar
no PC.

## Por onde começar

[`docs/MONTAGEM.md`](docs/MONTAGEM.md) tem o roteiro completo em 6 fases, na
ordem que reduz risco: firmware sozinho → sensores na protoboard → driver e
motores sem hélice → placa definitiva → frame → voo amarrado → voo livre.
Cada fase valida uma coisa só, então quando algo falhar você sabe o que mudou.

## Compilar e gravar

```bash
pip install platformio
cd drone
pio run -e picow -t upload      # segure BOOTSEL ao conectar o USB
pio device monitor
```

## Pilotar

1. Ligue a bateria. O LED pisca rápido durante a calibração — **não encoste no
   drone**, é aí que os offsets do giroscópio são medidos.
2. Conecte o celular na rede WiFi **`DRONE-PICO`**, senha `voar1234`.
3. Abra **`http://192.168.4.1`**.
4. Joystick esquerdo: throttle (vertical, fica onde você soltar) e guinada.
   Joystick direito: rolagem e arfagem (volta ao centro sozinho).
5. **ARMAR** só funciona com throttle no mínimo e o drone nivelado.

`ALT HOLD` mantém a altura: manche esquerdo no meio segura, acima sobe, abaixo
desce. `DESVIO` liga os sensores de proximidade.

## Testes

```bash
cd drone/test && make          # roda os testes de lógica no PC
cd drone/test && make syntax   # checa o firmware inteiro, main.cpp incluído
```

60 verificações que rodam sem placa nenhuma: convenções de sinal do AHRS e do
mixer, fiação do L298N (inclusive a ordem em que os pinos são configurados no
boot), anti-windup e filtro do termo D no PID, fusão de altitude, lógica de desvio,
SHA-1 nas fronteiras de bloco e o enquadramento do WebSocket.

**Rode sempre que mexer em ganhos, pinos ou sinais** — sinal trocado não dá erro
de compilação, dá capotamento.

## Ajuste do PID

Os ganhos em `include/config.h` são um ponto de partida para um coreless 1020
com hélice de 75 mm e diagonal de 163 mm, não uma receita: o valor certo depende
do peso final e do braço do seu frame.

Com o drone **amarrado** e ganhos pela metade:

- Oscilação rápida, chiado nos motores → **kP alto demais**.
- Oscilação lenta, balanço largo → **kI alto demais**.
- Demora a responder, parece mole → **kP baixo demais**.
- Oscilação só com throttle alto → **kD alto demais**, ou `PID_D_LPF_HZ` alto
  demais (está deixando passar a vibração da hélice).

Suba `PID_RATE_*_KP` até começar a oscilar, volte para 70 % disso, e só então
mexa em `KI`. `PID_ANGLE_KP` define quão "duro" é o auto-nivelamento.

## Estrutura

```
drone/
├── platformio.ini      dois alvos: picow e esp32dev
├── include/
│   ├── config.h        ajustes de voo, comuns às duas placas
│   ├── board_pico.h    pinos do Pico W + L298N
│   ├── board_esp32.h   pinos do ESP32 + MOSFET
│   ├── platform.h      o que difere entre as placas — e só isso
│   └── ...
├── src/
│   ├── main.cpp        máquina de estados, loop de 400 Hz, divisão de núcleos
│   ├── ahrs.cpp        Mahony — único lugar que conhece a orientação do sensor
│   ├── bmi160.cpp      driver por registradores
│   ├── bmp280.cpp      driver por registradores
│   ├── rangefinder.cpp ultrassom por interrupção + IR
│   ├── altitude.cpp    fusão sonar/barômetro/acelerômetro
│   ├── avoidance.cpp   desvio de obstáculos
│   ├── motors.cpp      mixer X com dessaturação + acionamento do L298N
│   ├── websocket.cpp   servidor WebSocket próprio (RFC 6455)
│   ├── receiver.cpp    WiFi, HTTP, UDP, failsafe
│   └── webui.h         interface de pilotagem
├── cad/                geradores paramétricos das peças impressas
│   ├── frame.py        frame (base 130 × 30, diagonal 163 mm)
│   ├── suportes.py     berços dos sensores e pés de pouso
│   ├── helice.py       hélice torcida — bancada, não voa
│   └── placa.py        empacota tudo numa placa de impressão só
├── test/               testes de lógica que rodam no PC
└── docs/
    ├── MONTAGEM.md     roteiro de montagem, fase a fase
    ├── ORCAMENTO.md    peso, corrente, bateria, hélice e MOSFET
    ├── ESQUEMA.md      esquema elétrico, medidas das peças, regras do frame
    └── HARDWARE.md     ligações, pinos, alimentação
```

## Cuidado

Hélice de drone corta. Faça todo teste de bancada **sem hélice** até ter certeza
de que os sinais do PID estão certos (passo 3 de `docs/HARDWARE.md`). Um sinal
invertido faz o drone acelerar na direção da queda, em vez de corrigir.
