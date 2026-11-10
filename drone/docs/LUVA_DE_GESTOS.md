# Luva de gestos: controlar o drone com a mão

> **Versão que vale agora: a simples, com 1 sensor.** Firmware, ligações e gestos em
> [`luva/README.md`](../../luva/README.md). Este documento é o projeto completo (4 sensores, gestos
> de apontar e chamar), para depois.

**Ideia:** uma luva com giroscópios na palma e nos dedos lê a posição da mão e transforma gestos
em comandos de voo. O **celular continua funcionando** como controle: os dois convivem.

**Orçamento:** até R$ 250. A conta abaixo fica em ~R$ 130 sem o sensor de fluxo óptico e
~R$ 230 com ele.

---

## 1. Como os dois controles convivem

```
 celular ──Wi-Fi (AP DRONE-PICO)──┐
                                  ├──> ESP32 do drone (mesmo canal de rádio)
 luva (XIAO ESP32-S3) ──ESP-NOW───┘
```

- O ESP32 do drone já cria a rede Wi-Fi do celular. O **ESP-NOW** (rádio direto entre ESP32, sem
  roteador) roda **no mesmo canal** ao mesmo tempo. Por isso a luva precisa estar no canal do AP.
- **Quem manda:** o último controle que mexeu em algo assume. Se o celular mexer no acelerador
  enquanto a luva comanda, o celular ganha (é o controle "de segurança").
- **Failsafe:** se a luva parar de mandar pacote por 400 ms, o drone para onde está e pousa
  devagar, igual ao celular hoje.
- **Bônus de alcance:** o XIAO tem antena externa (U.FL), que alcança mais que o celular. É bom material para o relatório de Comunicações.

> O XIAO ESP32-S3 Sense hoje é a câmera do DAMP. Se for usado na luva, o DAMP fica sem ele
> enquanto isso. Um XIAO ESP32-S3 **sem** o Sense custa menos e serve igual para a luva.

---

## 2. Quantos sensores e onde

Com **3 sensores** não dá para separar "apontar" de "mão aberta": nos dois o indicador está esticado.
O que diferencia é o **dedo médio**. Por isso são **4 sensores**, todos MPU-6050 (~R$ 15 cada):

| Sensor | Onde | Para que |
|---|---|---|
| 1 | dorso da mão (palma) | orientação da mão: inclinação, giro e direção para onde aponta |
| 2 | indicador (falange do meio) | dobrado ou esticado; aponta |
| 3 | médio (falange do meio) | separa "apontar" de "mão aberta" |
| 4 | polegar | joinha (decolar / pousar) |

**Dedo dobrado** = ângulo entre o sensor do dedo e o da palma. Medir a diferença entre os dois
cancela o movimento do braço inteiro: só a dobra do dedo sobra.

**Ligação sem multiplexador:** o MPU-6050 tem 2 endereços (pino AD0 em GND = 0x68, em 3V3 = 0x69),
e o ESP32-S3 tem **dois barramentos I²C**:

| Barramento | Pinos do XIAO | Sensores |
|---|---|---|
| I²C 0 | D4 (SDA), D5 (SCL) | palma (0x68) + indicador (0x69) |
| I²C 1 | D8 (SDA), D9 (SCL) | médio (0x68) + polegar (0x69) |
| — | D2 | motor de vibração (por um transistor) |
| — | BAT+ / BAT− (embaixo do XIAO) | bateria 1S (o XIAO carrega pela USB-C) |

---

## 3. Os gestos

Os que você pediu, e como cada um vira comando. A coluna **dá para fazer?** é o que importa:
alguns precisam de um sensor a mais no drone.

| Gesto | Leitura dos sensores | Comando | Dá para fazer? |
|---|---|---|---|
| **Apontar** (indicador esticado, resto fechado) | indicador reto, médio dobrado; direção da palma | segue reto **na direção apontada**, se afastando | ✅ sim, com a bússola do celular/luva comparando direção da mão e do drone. Sem bússola: "para a frente do drone". |
| **Chamar** (palma para cima, dedos dobrando 2×) | dedos dobram e esticam rápido duas vezes | volta até a luva | ⚠ **só aproximado.** O drone não sabe onde a luva está. Sem sensor extra ele refaz o caminho ao contrário (erra alguns metros). Com o **fluxo óptico** fica bem melhor. "Até o ESP" exato precisa de UWB (caro) ou GPS (só ao ar livre e pesado). |
| **Mão aberta, dedos abertos, palma para cima** | todos esticados, palma para cima, parada 1 s | pousa **na mão** | ✅ com cuidado: você põe a mão embaixo do drone, ele desce devagar e **corta os motores** quando o sonar de baixo lê < 6 cm. Hélice de 75 mm na mão machuca: use luva de couro por cima ou proteção de hélice. |
| **"Pare"** (palma vertical virada para o drone) | palma de pé, dedos esticados | para onde está e paira | ✅ (fica mais firme com fluxo óptico) |
| **Apontar para baixo** | indicador esticado, palma virada para o chão | desce | ✅ |
| **Palma para baixo, parada** | palma horizontal, dedos esticados, sem mexer | desce parado, devagar | ✅ |
| **Girar a palma, dedos esticados** | giro da palma em torno do braço | gira (yaw) na mesma velocidade | ✅ |

Gestos extras que sugiro:

| Gesto | Comando | Por quê |
|---|---|---|
| **Punho fechado 2 s** | armar / desarmar | Ninguém fecha a mão 2 s sem querer. A luva vibra para confirmar. |
| **Joinha para cima** | decolar e parar a 1 m | Decolagem sempre igual. |
| **Joinha para baixo** | pousar onde está | — |
| **Mão inclinando** (como uma bandeja) | anda para o lado que inclina, proporcional | É o modo "manche": o mais fácil de aprender. |
| **Sacudir a mão forte** | **parada de emergência**: desce rápido e corta | Precisa ser bem forte (> 3 g por 0,5 s) para não disparar à toa. |
| **Dois dedos (V)** | foto, se o drone tiver câmera | Fica para depois. |

---

## 4. Como o reconhecimento funciona

1. **Orientação de cada sensor** com o mesmo filtro Mahony do drone (`src/ahrs.cpp`), a 100 Hz.
2. **Dobra de cada dedo** = ângulo entre o dedo e a palma (0° esticado, ~90° dobrado).
3. **Postura** (estado da mão): um classificador simples de limites. Exemplo: "apontar" =
   indicador < 25°, médio > 60°, polegar qualquer.
4. **Gesto** = postura **mantida** por 300 ms (evita disparar na transição de um gesto para outro),
   ou um **movimento** reconhecido por uma pequena máquina de estados ("chamar" = dobra → estica
   → dobra → estica em < 1,2 s).
5. A luva manda ao drone **comandos de alto nível** ("desce 0,3 m/s", "gira 45°/s"), nunca o
   valor de motor. Quem estabiliza continua sendo o drone.
6. **Calibração ao calçar:** mão aberta e parada 2 s, depois punho fechado 2 s. A luva aprende o
   seu 0° e o seu 90°.

Se os limites fixos errarem muito, dá para treinar um classificador pequeno (k vizinhos ou uma
rede minúscula) com 50 exemplos de cada gesto, no próprio ESP32-S3.

---

## 5. Lista de compras da luva

| Item | Qtd | Estimativa |
|---|---|---|
| MPU-6050 (GY-521) | 4 | R$ 50–80 |
| Luva fina de algodão/lycra | 1 par | R$ 8–20 |
| Bateria LiPo 1S 300–500 mAh com JST | 1 | R$ 20–40 |
| Fio de silicone 30 AWG | 5 m | R$ 15–25 |
| Motor de vibração 1027 + transistor | 1 | R$ 5–10 |
| Chave liga/desliga mini | 1 | R$ 2–5 |
| **Subtotal** | | **~R$ 100–180** |
| Sensor de fluxo óptico **PMW3901** (vai no drone) | 1 | R$ 70–120 |
| **Total com fluxo óptico** | | **~R$ 170–300** |

O XIAO ESP32-S3 você já tem. O fluxo óptico pesa ~2 g e é o que deixa "pare" e "volte" precisos.
Se o orçamento apertar, compre ele por último: os outros gestos funcionam sem.

---

## 6. Ordem de construção

1. **Um sensor só (palma)** no XIAO, na protoboard: mostrar a orientação na serial.
2. **Os 4 sensores** costurados/colados na luva, fios passando pelo dorso com folga nas juntas.
3. **Reconhecer as posturas** e mostrar o nome do gesto na serial e na página do drone.
4. **ESP-NOW** luva → drone, com o drone **sem hélice**: conferir que cada gesto chega e vira o comando certo na telemetria.
5. **Voo amarrado** (fase 9 do plano de montagem) comandado pela luva.
6. Voo livre, começando só por armar, decolar, parar e pousar.
