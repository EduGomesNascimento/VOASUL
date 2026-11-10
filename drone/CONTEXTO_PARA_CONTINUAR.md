# Contexto para outro Claude continuar o projeto

Idioma: português do Brasil. Usuário: Eduardo. Estilo: respostas diretas, com tabelas, números
reais e avisos de risco. Trabalho de faculdade (Comunicações + Potência) e a marca é a **VoaSul**.

## Onde está tudo

Repositório **EduGomesNascimento/VOASUL**, pasta `drone/` (o site da VoaSul fica na raiz).

| Pasta | O que tem |
|---|---|
| `drone/src`, `drone/include`, `drone/test` | firmware (ESP32 DevKit 38p ou Pico W). `cd test && make check` (testes no PC) e `make syntax` |
| `drone/kicad/` | **placa no KiCad 7** (face única, Ø97) gerada por script. Ver `kicad/README.md` e `kicad/CONFERENCIA.md` |
| `drone/kicad/pro/` | versão para fábrica de PCB (2 camadas, furo metalizado) + Gerber |
| `drone/kicad/saidas/` | PDFs de transferência e montagem, esquema em PDF, visualizador 3D |
| `drone/cad/` | frame impresso (`frame_redondo.py/.stl`), pés, hélice de bancada |
| `drone/docs/` | `PLANO_DE_MONTAGEM.md` (fases com requisitos e testes), `BOM_TOTAL.md`, `ORCAMENTO.md` |
| `drone/pcb/proteus/` | a placa antiga do Proteus (**não fabricar**: pegada do ESP32 espelhada) |

Lista de compras com marcação (artifact): https://claude.ai/artifact/JfMoUsfyh2TjpAySVM2ZgH

## Hardware

- ESP32 DevKitC 38 pinos (WROOM-32 ou 32U; a lista diz que ele tem a antena U.FL -> provável 32U, **confirmar**).
- 4 motores coreless 1020, hélice 75 mm furo 1,0. AO3400A + SS34 + 100 nF 0805 por motor; 100 Ω na porta, 10k porta-GND.
- Bateria LiPo **1S** 500–600 mAh (Molex 51005). **Nada de 2S** (queima os 1020).
- MT3608 → 5,0 V (VIN do ESP32 e sonares). BMI160 + BMP280 **embaixo do ESP32**.

## Escopo atual (10/11/2026): o mais simples possível

- Motores coreless 1020 com os MOSFETs da placa (nada de ESC/brushless).
- Energia em aberto: bateria LiPo 1S **ou** cabo do chão, os dois pelo J1.
- Sensores: só BMI160 + BMP280. Sonar, IR e fluxo óptico ficam de fora (conectores podem ficar vazios).
- Barato acima de tudo. Sensores do drone: GY-BMI160 (giroscópio) + GY-BMP280-3.3 (barômetro, já tem).
- Controle: **só o app no celular** (página servida pelo drone em http://192.168.4.1): dois manches,
  ALT HOLD (ligado por padrão; manche esquerdo volta ao centro = mantém a altura), POUSAR (bit 8 do
  pacote) e telemetria. Sem luva e sem joystick (decisão de 10/11/2026).
- Firmware compila no PlatformIO: `pio run -e esp32dev`. Testes: `cd test && make`.
- Placa: fresada na CNC de um amigo (`drone/kicad/usinagem/`, regras 0,5/0,6/0,8/1,8); JLCPCB opcional.

## Pinagem NOVA (placa de face única)

Motores FR/RR/RL/FL = GPIO 17/4/23/19 · I²C1 (BMP280) 21/22 · **I²C2 (BMI160, Wire1) 16/18** ·
sonar baixo TRIG/ECHO 14/27 · sonar frente TRIG/ECHO 13/12 · IR esq/dir 36/39 · bateria 35 · LED 2 ·
**fluxo óptico PMW3901 (opcional, J4) MISO/SCK/MOSI/CS 32/33/25/26**.
Já está em `include/board_esp32.h`; o firmware ganhou `platI2C2Begin()` e `BMI160::setBus()`.
Fluxo óptico: `include/opticalflow.h` (driver + estimador + freio). Detecta o módulo no boot
(ID 0x49 e 0xB6); sem ele o drone voa igual. Telemetria `fl` (0 ausente, 1 sem leitura,
2 lendo, 3 segurando), `vf`/`vr` (m/s), `sq` (qualidade). Testes: `cd test && make`.

## Como a placa é gerada (não editar o .kicad_pcb à mão)

`kicad/projeto.py` é a fonte. Pipeline (KiCad 7 no Ubuntu: `apt install kicad`):
`gerar.py placa` → `gerar.py exportar` → `rotear.py geometria.json rotas.json 1` (roteador
próprio, A* em grade de 0,2 mm, face única com jumpers) → `gerar.py placa` + `gerar.py aplicar`
→ `gerar.py drc` → `gerar_esquema.py` → `gerar.py saidas` / `profissional` / `cena3d`.

Regras: trilha 2,5 (VBAT, drenos) / 1,5 (GND, 5V, 3V3) / 1,2 (sinais); folga 0,8; anel de VBAT
no raio 45; plano de GND; SMD embaixo fora dos raios do frame. GND em duas fases: o de potência
(bateria → fontes dos MOSFETs) só por cobre da placa; o resto pode usar o GND interno do ESP32/MT3608.

## Pendências

1. Confirmar WROOM-32 × 32U e a distância de 25,4 mm entre as fileiras do ESP32.
2. Firmware **nunca compilado para o ESP32** (só testes no PC). Compilar no PlatformIO local.
3. Versão profissional **compacta** (Ø ~66 mm, 2 camadas, SMD), que exige regerar o frame (`frame_redondo.py --placa 66`).
4. (Fora do escopo) luva de gestos: só o projeto em `docs/LUVA_DE_GESTOS.md`.
5. Modelo 3D do drone inteiro no Inventor (o usuário vai fazer com um Claude local).
6. Comprar o que falta (21 itens na lista).
