# Esquema elétrico e medidas

Tudo o que você precisa para projetar o frame e a placa no CAD.

| Arquivo | O que é |
|---|---|
| [`esquema.pdf`](esquema.pdf) | **3 folhas A3 com carimbo**: potência; controle e sensores; lista de materiais com o que buscar no Proteus e a lista de ligações |
| [`esquema.svg`](esquema.svg) / [`esquema.png`](esquema.png) | o esquema inteiro numa imagem só, para tela |
| [`layout_placa.svg`](layout_placa.svg) / [`layout_placa.png`](layout_placa.png) | distribuição em escala na placa de 130 × 30, vista de cima e de baixo |
| `esquema.py`, `layout_placa.py` | os geradores — mudou uma peça ou um pino, edite e rode de novo |

```bash
pip install schemdraw matplotlib
python3 esquema.py && python3 layout_placa.py
```

O esquema liga os blocos por **etiqueta de rede**: dois pontos com o mesmo
nome (`M_FR`, `SDA`, `+5V`…) estão ligados, mesmo sem fio desenhado entre
eles. Os GPIO são os de `include/board_esp32.h`.

---

## Componentes por referência

| Ref. | Peça | Valor / modelo | Encapsulamento |
|---|---|---|---|
| U1 | ESP32 DevKit 38 pinos | ESP32-WROOM-32 | módulo |
| U2 | step-up | MT3608, ajustado em **5,0 V** | módulo |
| U3 | IMU | BMI160 (I2C `0x69`) | módulo GY |
| U4 | barômetro | BMP280 (I2C `0x76`) | módulo GY, 3,3 V |
| U5, U6 | ultrassom | HC-SR04 (baixo, frente) | módulo |
| U7, U8 | IR | FC-51 (esquerdo, direito) | módulo |
| Q1–Q4 | MOSFET | AO3400A | SOT-23 |
| D1–D4 | diodo Schottky | SS34 (3 A, 40 V) | SMA |
| M1–M4 | motor | coreless 1020 | — |
| R1–R4 | porta | 100 Ω | 1/4 W |
| R5–R8 | porta → GND | 10 kΩ | 1/4 W |
| R9, R10 | divisor da bateria | 10 kΩ | 1/4 W |
| R11, R12 | divisor do ECHO (série) | 1 kΩ | 1/4 W |
| R13, R14 | divisor do ECHO (GND) | 2 kΩ (2,2 kΩ também serve) | 1/4 W |
| C1 | reserva dos motores | 1000 µF 10 V | eletrolítico |
| C2 | reserva do rádio | 470 µF 10 V | eletrolítico |
| C3–C6 | ruído das escovas | 100 nF | cerâmico, **soldado no motor** |
| J1 | bateria | LiPo 1S 530 mAh 30C (Leão LB530LP1) | conector Molex |

---

## Medidas das peças

> **Meça as suas com paquímetro antes de fechar o CAD.** Os módulos chineses
> variam de lote para lote. A coluna "fonte" diz o quanto confiar no número:
> **ficha** = datasheet ou anúncio do fabricante; **típico** = o comum no
> mercado, confira.

| Peça | C × L × A (mm) | Peso | Detalhes que importam no projeto | Fonte |
|---|---|---|---|---|
| Placa perfurada | 130 × 30 × 1,6 | ~10 g | passo 2,54 mm, ~51 × 11 furos | sua |
| ESP32 DevKit 38 pinos | ~55 × 28 × 1,6 (placa) | ~9 g | fileiras de pinos a **25,4 mm** (algumas cópias: 22,86); 19 pinos por lado; ~4 mm de componentes acima da placa; ~2,5 mm de espaçador do pino abaixo | típico |
| — módulo WROOM-32 | 18 × 25,5 × 3,1 | — | a antena são os **~6 mm da ponta** do módulo | ficha |
| BMI160 (GY) | ~13 × 18 | ~1,5 g | seta **Y → nariz, Z → cima** | típico |
| BMP280 (GY, roxo) | 11,5 × 15 | ~1 g | furo de ventilação do sensor: cubra com espuma, não com fita | típico |
| Step-up MT3608 | ~37 × 17 × ~14 | ~3 g | o trimpot azul multivoltas (3296) é o que dá os ~14 mm de altura: deixe acesso para a chave por cima | típico |
| HC-SR04 | 45 × 20 × ~15 | 8,5 g | transdutores Ø16 mm saindo ~12 mm; cone de ~15°; 4 pinos na borda | típico |
| FC-51 | 31 × 14 × ~7 | ~3 g | LEDs na ponta (é para onde ele olha); furo M3; 3 pinos | típico |
| Motor 1020 | Ø10 × 20 | 6 g | eixo Ø1,0 mm saindo ~5 mm; fios saem por trás | ficha / típico |
| Hélice 75 mm | Ø75; cubo ~Ø5 × 5 | ~0,9 g | disco livre de **Ø85** (5 mm de folga em volta) | típico |
| **Bateria Leão LB530LP1** | **40 × 25 × 8** | **14 g** | fio + conector Molex saindo de uma ponta | ficha |
| AO3400A | 2,9 × 1,3 × 1,0 | — | 2,4 mm de largura contando as pernas | ficha |
| Adaptador SOT-23 → DIP | ~10 × 8 | — | varia muito: meça | típico |
| SS34 | 4,3 × 2,6 × 2,1 | 0,1 g | 5,2 mm de ponta a ponta: solda direto em 2 ilhas com um furo vazio no meio | ficha |
| Resistor 1/4 W | Ø2,3 × 6,3 | 0,2 g | deitado ocupa 4 furos (10,2 mm); em pé, 2 furos | ficha |
| Capacitor 1000 µF 10 V | Ø8 × 12 | ~1,5 g | pernas a 3,5 mm | típico |
| Capacitor 470 µF 10 V | Ø6,3 × 11 | ~1 g | pernas a 2,5 mm | típico |
| Capacitor 100 nF | ~4 × 2,5 | — | vai soldado direto nos terminais do motor | típico |

---

## O frame que já existe (`cad/frame.py`)

Se for desenhar o seu, estes são os números que já funcionam:

| | mm |
|---|---|
| Base (quadro perimetral) | 130 × 30 × 3 |
| Largura do trilho | 5 |
| Nervuras transversais | em x = ±28,6 do centro, 4 de largura |
| Centro dos motores | **(±57,5 ; ±57,5)** — X quadrado |
| Diagonal motor a motor | 162,6 |
| Entre motores vizinhos | 115 |
| Envelope com hélices | ~190 × 190 |
| Tubo do motor | Ø interno **9,9** (0,1 de interferência), parede 2, altura 10 |
| Braço | 12 de largura na raiz, 9 na ponta |
| Pé de pouso | 19,5 de altura |
| Vão para abraçadeira | 4 |
| Peso em PLA | ~27 g |

---

## Regras para projetar o seu

O que não pode mudar, e por quê:

1. **X quadrado.** Os quatro motores à mesma distância do centro, e o braço de
   rolagem igual ao de arfagem. Senão o PID de roll e o de pitch precisariam de
   ganhos diferentes.
2. **Folga das hélices.** A distância do centro ao motor tem de ser, no mínimo,
   `largura da base / 2 + 37,5 + 5` — com a base de 30 mm, **57,5 mm**. E
   motores vizinhos a pelo menos 85 mm um do outro (75 da hélice + 10).
3. **Centro de gravidade no centro geométrico.** O ESP32 (9 g) numa ponta é
   compensado pela bateria (14 g) na outra. Prenda a bateria com velcro, não com
   cola: deslizar a bateria é o ajuste fino. Para conferir, pendure o drone
   montado por um barbante no centro — ele tem de ficar nivelado.
4. **IMU no centro e alinhada.** Seta Y do BMI160 para o nariz, Z para cima.
   Montada torta, o firmware lê inclinação onde não há.
5. **Sonar de baixo com a vista livre.** Nada dentro do cone de ~15° abaixo
   dele — nem pé, nem bateria, nem fio pendurado. E os pés têm de ser mais altos
   que ele (19,5 contra ~15 mm).
6. **Antena para fora.** A ponta do ESP32 com a antena fica na borda da placa,
   longe da bateria e dos fios de motor (ver "Alcance do rádio" em
   [`HARDWARE.md`](HARDWARE.md)).
7. **Nada acima do plano das hélices** dentro do disco delas. Com o motor
   apoiado no fundo do tubo, a hélice fica ~20–25 mm acima da face de baixo do
   frame.
8. **Peso.** O orçamento supõe ~27 g de frame. Cada grama a mais sai do
   empuxo/peso, que já está em ~1,5.
