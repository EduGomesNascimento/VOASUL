# Orçamento de peso e corrente

Configuração: **Pico W + placa de fenolite 130 × 30 mm inteira + 4× coreless
1020 + hélice 75 mm + todos os sensores.**

---

## Configuração atual: placa redonda (outubro/2026)

O projeto mudou: placa de circuito redonda de Ø 97 mm, `frame_redondo.stl`,
ESP32 DevKit de 38 pinos e bateria Leão 530 mAh. Primeiro voo só com o
ultrassônico de baixo.

| Item | g |
|---|---|
| Frame redondo impresso | 25 |
| 4 pés + suporte do sonar | 6,7 |
| **Placa redonda Ø 97, fenolite dupla face 1,6 mm** | **~18** |
| ESP32 DevKit 38 pinos | 10 |
| BMI160 + BMP280 | 2,7 |
| 4× motor 1020 + 4× hélice | 27,6 |
| MOSFETs, diodos, resistores | 2 |
| C1 + C6 | 3 |
| **Step-up MT3608** | **3** |
| HC-SR04 de baixo | 8,5 |
| Fios, solda, fita | 6 |
| Bateria Leão 530 mAh | 14 |
| **Total** | **~126** |

Empuxo estimado 180 g → **empuxo/peso ~1,43** (pairar em ~70 % do throttle,
~7 A, ~3,5 min de voo). Com os dois IR e o sonar da frente: ~141 g, **~1,28**.

O step-up não entrava nas tabelas abaixo, que eram da versão com o Pico W —
são 3 g que faltavam. A maior alavanca agora é a placa: em **0,8 mm** ela pesa
metade, e o empuxo/peso volta a ~1,5.

---

## Peso

| Item | Qtd | g/un | g |
|---|---|---|---|
| Frame impresso (PLA) | 1 | 27,0 | 27,0 |
| Pé de pouso impresso | 4 | 0,8 | 3,2 |
| Suporte do sonar de baixo | 1 | 3,5 | 3,5 |
| Placa de fenolite 130 × 30 × 1,6 | 1 | 10,0 | 10,0 |
| Pico W (sem barra de pinos) | 1 | 3,0 | 3,0 |
| BMI160 (módulo GY) | 1 | 1,5 | 1,5 |
| BMP280 (módulo GY) | 1 | 1,0 | 1,0 |
| **Motor coreless 1020** | 4 | **6,0** | **24,0** |
| Hélice 75 mm injetada | 4 | 0,9 | 3,6 |
| AO3400A + SS34 + 2 resistores | 4 | 0,75 | 3,0 |
| Capacitor 470 µF | 1 | 2,0 | 2,0 |
| **HC-SR04** | 2 | **8,5** | **17,0** |
| **IR FC-51** | 2 | **3,0** | **6,0** |
| Fios, solda, conector da bateria | — | — | 5,0 |
| Abraçadeiras e fita | — | — | 2,0 |
| **Seco (sem bateria)** | | | **111,8** |

Três números mudaram desde a versão anterior deste documento, e os três para
pior:

- **Motor 1020: 6 g, não 4.** Era chute enquanto o motor não estava comprado.
  Pela escala de volume contra o 716 (10²×20 contra 7²×16 é 2,55×) e pelas
  fichas de fabricante, o 1020 dá 5,5–6,5 g. **+8 g nos quatro.**
- **Suportes impressos entravam como zero.** Os 4 pés e o berço do sonar de
  baixo são peças que voam: **+6,7 g**.
- **Placa de 130 mm.** A fenolite inteira dá 10 g contra 6,2 g da cortada em
  80 mm, e o frame cresce 2 g junto com ela: **+5,8 g** pela sua decisão de
  manter os 13 cm. É uma escolha legítima — só não é de graça, e agora está
  contabilizada.

### O que isso faz com o empuxo/peso

**Empuxo estimado: 4 × 45 g = 180 g.** Continua sendo o número mais incerto do
documento — 1020 com hélice de 75 mm fica entre 35 e 55 g por motor. **Meça**
(ver "Meça, não confie nesta tabela", no fim).

| Bateria | Total | Empuxo/peso |
|---|---|---|
| 1S 450 mAh (11 g) | 122,8 g | 1,47 |
| 1S 650 mAh (14 g) | 125,8 g | 1,43 |
| 1S 1000 mAh (22 g) | 133,8 g | 1,35 |

**Nenhuma dessas linhas voa direito.** Um quad precisa de ~1,8 para ter margem
de correção: o empuxo que sobra acima do necessário para pairar é exatamente o
que o PID tem para endireitar o drone. Com 1,4, pairar já consome 70 % do
throttle e sobram 30 % para corrigir — o drone sobe, mas responde devagar a
qualquer inclinação e não se recupera de um susto.

Isso não é motivo para desistir: é motivo para tirar peso **na ordem certa**.

### O que tirar, em ordem

Cada linha é cumulativa, com a bateria de 650 mAh:

| Tirando | Poupa | Seco | Total | E/P | O que se perde |
|---|---|---|---|---|---|
| — (tudo) | — | 111,8 | 125,8 | 1,43 | nada |
| Ultrassônico da frente | 8,5 g | 103,3 | 117,3 | 1,53 | desvio frontal |
| + os 2 IR | 6,0 g | 97,3 | 111,3 | **1,62** | desvio lateral |
| + BMP280 | 1,0 g | 96,3 | 110,3 | 1,63 | baro (o sonar segura até 3 m) |
| + placa cortada a 80 mm | 5,8 g | 90,5 | 104,5 | **1,72** | área para conectores |

**A configuração de primeiro voo é a terceira linha:** só o ultrassônico de
baixo, que é o que dá o alt-hold. Ela mantém a placa de 130 mm que você quis, e
1,62 voa — devagar, mas voa e deixa ajustar o PID.

Os sensores de desvio voltam depois, um de cada vez, quando o empuxo medido
disser que cabem. O firmware já lida com sensor ausente: `avoidance.cpp` trata
leitura fora de faixa como "sem obstáculo", então basta não ligar o sensor.

### Por que o L298N não entra em nenhuma dessas contas

Você tem dois módulos mini L298N, e eles pesam. Pese os seus — os módulos
variam muito — mas a ordem de grandeza é:

| | Peso | Tensão que chega no motor | Empuxo/motor |
|---|---|---|---|
| 4× AO3400A + diodo + resistores | 3 g | 3,7 − 0,1 = **3,6 V** | ~43 g |
| 2× mini L298N + step-up | ~24 g | 3,7 − 2,0 = **1,7 V** | ~9,5 g |

São duas perdas somadas, e a segunda é fatal. O L298N é uma ponte com
transistores bipolares Darlington: ele **derruba ~2 V** entre a alimentação e o
motor, e isso não é ajustável, é física do circuito interno. Sobram 1,7 V nos
3,7 V da célula. Como o empuxo cai com o quadrado da tensão, `(1,7/3,6)² = 0,22`
— **22 % do empuxo**. Mais o step-up de 4 g que a lógica do L298N exige (ela
precisa de 4,5–7 V, e a célula dá 3,7).

Resultado: ~38 g de empuxo total contra ~132 g de drone. **Empuxo/peso 0,29.**
Não sai do chão, e nenhum ajuste de PID muda isso.

Os L298N não são lixo — são a peça certa para a **bancada**. Nas Fases 0 a 3
(ver `MONTAGEM.md`) o drone está preso, peso não conta, e a ponte completa
deixa você inverter o sentido do motor por software, o que é ótimo para
conferir a fiação e o mixer. Para voar, é MOSFET.

---

## Bateria

Você ainda não comprou, então esta é a decisão que ainda está inteira na sua
mão — e, depois dos motores, é a peça que mais mexe no resultado.

Contra os **97,3 g secos** da configuração de primeiro voo (só o ultrassônico
de baixo):

| Bateria | Peso | Peso total | Empuxo/peso | Autonomia |
|---|---|---|---|---|
| 1S 450 mAh 30C | 11 g | 108,3 g | 1,66 | ~3,5 min |
| **1S 650 mAh 30C** | **14 g** | **111,3 g** | **1,62** | **~5 min** |
| 1S 1000 mAh 25C | 22 g | 119,3 g | 1,51 | ~8 min |

Com **todos** os sensores (111,8 g secos), as mesmas três células dão 1,47,
1,43 e 1,35 — todas magras demais. Ver "O que tirar, em ordem", acima.

### Corrente

Quatro 1020 no talo puxam **~12 A**. Pairando (throttle em ~55 %), **~6 A**.

O C mínimo sai de `12 A ÷ capacidade`:

| Capacidade | C mínimo | Compre |
|---|---|---|
| 450 mAh | 27C | 30C ou mais |
| 650 mAh | 18C | 25C ou mais |
| 1000 mAh | 12C | 15C ou mais |

**A sua célula de 1000 mAh atual provavelmente não serve.** Bateria genérica de
powerbank é 2–5C: nos 12 A ela afunda para menos de 3 V, o Pico reinicia e o
drone cai. Procure o C impresso nela. Se não estiver escrito, não é de alto C.

### A escolha: 1S ~530–650 mAh, 30C ou mais

Na prática: **Leão Modelismo LB530LP1 — LiPo 1S 530 mAh 30C**, 14 g,
40 × 25 × 8 mm, conector Molex, ~R$ 60 a unidade. Ela passa nas duas contas
abaixo: 530 mAh exigem no mínimo 13,3 g (pesa 14) e 5,6 cm³ (a caixa tem 8,0).
30C dão 16 A contra os 12 A de pico. E é LiPo comum, de 4,2 V: o carregador
barato serve.

Mais cara e um pouco melhor: **BETAFPV BT2.0 550 mAh 1S 40C** (14 g, 22 A,
conector BT2.0 que afunda menos). Mas é LiHV — exige carregador com esse modo —
e costuma vir em pacote de 4, o que pesa no bolso. A de 450 mAh 30C da mesma
marca chega a só 13,5 A, no limite, e fica de fora.

É o equilíbrio. Os 3,5 min da 450 mAh acabam antes de você terminar um ajuste de
PID; a de 1000 mAh derruba o empuxo/peso para 1,51, que já fica mole.

> Os 8 g a mais da célula de 1000 mAh custam 0,11 de empuxo/peso e compram 3
> minutos. Enquanto você estiver **ajustando PID**, os 3 minutos valem mais: o
> drone fica preso ou a 20 cm do chão, e cada carga é uma tentativa. Depois que
> ele estiver estável, a de 650 mAh é a que voa melhor. Se for comprar uma só,
> compre a de 650 — a margem de empuxo é o que perdoa erro de ajuste, e é dela
> que este drone tem menos.

Conector: o ideal é **BT2.0** ou XT30. O **Molex** da Leão (o mesmo do Syma
X5C) e o **PH2.0** funcionam, mas foram feitos para poucos ampères: a 6 A o
contato esquenta e derruba ~0,15 V, e o empuxo cai com o quadrado da tensão. Se
o teste de queda de tensão (abaixo) passar de 0,4 V, corte o conector e solde
um XT30 — um polo de cada vez, para nunca encostar os dois fios.
**JST-XH não serve**: é conector de balanceamento, de 3 A. Compre os rabichos
do mesmo tipo da bateria — um vai soldado no drone.

### Como reconhecer a bateria certa

O que separa uma bateria de drone de qualquer outra é a **taxa de descarga (C)**.
Bateria de microfone, de telefone sem fio ou de manete de videogame é projetada
para **100–500 mA**. O drone puxa **12 A** — de 25 a 100 vezes mais.

Não é diferença de grau. Numa célula com 100 mΩ de resistência interna, 12 A
derrubam 1,2 V: a tensão vai de 3,7 para 2,5 V, os motores perdem quase todo o
empuxo, e a célula esquenta a ponto de **inchar, ventilar e pegar fogo**.

**Se o anúncio não estampa o C, não é bateria de drone.** Essa ausência é a
resposta — anúncio de LiPo para modelismo sempre informa.

### Duas contas que desmascaram capacidade inflada

Anúncio de bateria de drone de brinquedo mente sobre capacidade com frequência.
Duas contas resolvem, e nenhuma depende de confiar no vendedor.

**Peso mínimo.** LiPo real armazena ~150 Wh/kg. Logo:

> uma LiPo 1S pesa no mínimo **`mAh ÷ 40`** gramas

| Capacidade | Peso mínimo (só a célula) |
|---|---|
| 250 mAh | 6 g |
| 650 mAh | 16 g |
| 1800 mAh | 45 g |
| 3600 mAh | 90 g |

**Volume mínimo — para célula que anuncia C alto.** LiPo de alta descarga
(20C ou mais) fica em ~0,25–0,35 Wh/cm³: separador mais grosso e mais coletor
de corrente ocupam volume que não guarda energia. (Célula de celular, de baixa
descarga, passa de 0,6 Wh/cm³ — por isso o teste só vale quando o anúncio
promete C alto.) A energia é `mAh × 3,7 ÷ 1000` Wh, então o volume mínimo é
`Wh ÷ 0,35` cm³. Se a conta não fecha, o anúncio infla a capacidade **ou** o
C: as duas coisas juntas não cabem naquele volume.

O quanto o anúncio passa do teto é um sinal sobre o vendedor: 10 % é
arredondamento otimista de fábrica; 60 % é alguém confortável em mentir — e aí
o "25C" impresso ao lado também não vale muito.

Exemplo real: uma "bateria de E88 de 3600 mAh" guarda 13,3 Wh e precisaria de
**45 cm³**. A carcaça do E88 tem ~18 cm³ — dois terços do volume simplesmente
não existem. Já 1800 mAh dá 6,7 Wh e ~22 cm³, que fecha.

Prometer mais capacidade em menos peso ou menos volume não é otimização: é
mentira, e não há química que contorne.

Duas células reais do mercado, pelo teste:

| Anúncio | Volume | Densidade implícita | Capacidade real |
|---|---|---|---|
| `952540 1000 mAh 25C` | 9,5 cm³ | 0,39 Wh/cm³ | ~800 mAh (10 % acima) |
| `903052 2000 mAh 25C` | 14,0 cm³ | 0,53 Wh/cm³ | ~1200 mAh (60 % acima) |

**A balança resolve na chegada:** `capacidade real ≈ peso em gramas × 40`. Uma
célula não esconde energia que a massa não comporta.

### Leve com C baixo é pior que pesada com margem

Esta é a armadilha que parece economia de peso e não é.

O empuxo cai com o **quadrado** da tensão no motor. Uma célula com C
insuficiente afunda sob carga, e o que ela economiza em gramas ela devolve
multiplicado em empuxo perdido.

Comparando duas candidatas reais para os 12 A deste drone:

| | Peso | R interna | Queda a 12 A | Tensão no motor | Empuxo restante |
|---|---|---|---|---|---|
| 1000 mAh **25C** | 22 g | ~40 mΩ | 0,4 V | 3,3 V | **~80 %** |
| 400 mAh sem C declarado | 10 g | ~100 mΩ | 1,2 V | 2,5 V | ~46 % |

Os 12 g economizados custam mais da metade do empuxo. Entre duas baterias,
**prefira sempre a que tem margem de corrente**, mesmo pesando mais — até o
ponto em que o peso extra estoure o orçamento por si só.

Erros comuns que parecem soluções:

| Isto | Por que não |
|---|---|
| Célula 18650 (mesmo LG/Samsung boa) | ~47 g cada, 3× o orçamento de peso; e ~6 A, metade do necessário |
| Pack NiMH de telefone sem fio | 2,4 V, corrente baixíssima — nem a tensão está certa |
| Bateria de manete de videogame | feita para 100 mA |
| Célula de celular (Samsung, LG, Multilaser…) | 0,2–1C. Celular puxa 1 A de uma bateria de 5000 mAh |
| Pack 7,4 V (2S) de carrinho RC | **queima o Pico**: o VSYS aceita no máximo 5,5 V |
| Pack 12 V de parafusadeira | 12 V destrói o Pico na hora, e pesa ~180 g |

O padrão: quase toda bateria de aparelho eletrônico é de baixa corrente, porque
o aparelho é de baixa corrente. Drone é a exceção.

### Circuito de proteção: o pior dos modos de falha

Célula de eletrônico de consumo (tipo 103450, 605080, as vendidas para power
bank e reposição) quase sempre vem com **PCM — circuito de proteção**. Você
reconhece pela plaquinha sob o kapton amarelo numa das pontas, com marcações
`B+` e `B-`, ou pelo anúncio dizer **"3 fios"** (o terceiro é o termistor).

Essa proteção corta tipicamente entre 5 e 8 A. **Nos 12 A do drone, ela
desarma.**

E desarmar é pior que afundar tensão. Bateria que afunda deixa o drone fraco,
e o firmware ainda pousa. Bateria que **desliga** tira os quatro motores ao
mesmo tempo, e não há failsafe que resolva: sem energia não há o que corrigir.
O drone cai como pedra.

LiPo de modelismo **não tem** proteção, de propósito. É por isso que ela exige
carregador próprio e cuidado no armazenamento — e é exatamente por isso que ela
entrega a corrente.

### Título contra etiqueta

Quando o anúncio e a foto do produto discordarem, **a etiqueta ganha**. Exemplo
real: anúncio de "500 mAh" cuja etiqueta na foto dizia `DC3.7V 300mAh 1.11Wh` —
e 300 × 3,7 ÷ 1000 = 1,11 Wh, ou seja, a etiqueta bate consigo mesma e o título
estava 67 % inflado. Sempre confira o Wh: ele denuncia o mAh.

Termos de busca que trazem a peça certa:

- `bateria lipo 1s 650mah 30c drone`
- `bateria lipo 1s tiny whoop ph2.0`
- `bateria lipo 3.7v 450mah 80c`

### A alternativa pronta: bateria de drone de brinquedo

Baterias de E88 / E99 / K6 / V8 e similares são LiPo 1S numa carcaça de plástico
**com carregador USB embutido**. Elas servem: são projetadas para exatamente
quatro motores coreless, então a corrente está certa por construção.

A vantagem não está na ficha: você **não precisa de carregador de LiPo**.
Carregar LiPo com carregador errado é uma das formas mais comuns de começar um
incêndio neste hobby, e a carcaça já traz o circuito de carga e proteção.

O custo é o peso: a carcaça e o circuito somam. Espere ~40 g contra os 14 g de
uma LiPo 1S 650 mAh nua — o que derruba o empuxo/peso de 1,62 para ~1,31.

**Compre duas.** Uma carregando enquanto a outra voa; você vai passar muito mais
tempo ajustando PID do que voando.

Duas ressalvas que só aparecem na prática:

- **Peso.** A de 1800 mAh do E88 dá ~52 g com a carcaça (45 g de célula pela
  regra acima, mais o plástico e o circuito). Com o motor 1020 nos 6 g reais,
  isso não fecha mais em configuração nenhuma — ver a tabela abaixo.
- **Conector.** É um pacote de encaixe com contatos de mola, feito para deslizar
  no corpo do E88 — não tem rabicho de fio. No seu frame, exige imprimir um
  berço com contatos ou soldar direto nos terminais.

A comparação que decide, com números da bateria do E88 medida (72 × 28,7 ×
12,3 mm, ~50 g):

| | Peso total | Empuxo/peso |
|---|---|---|
| LiPo 650 mAh 30C (14 g) — só o sonar de baixo | 111,3 g | **1,62** |
| LiPo 1000 mAh 25C (22 g) — com **todos** os sensores | 133,8 g | 1,35 |
| E88 1800 mAh (~50 g) — só o sonar de baixo | 147,3 g | 1,22 |
| E88 1800 mAh (~50 g) — com todos os sensores | 161,8 g | 1,11 |

Na versão anterior desta tabela o pacote do E88 empatava com a LiPo, desde que
se abrisse mão dos sensores. **Com o motor 1020 nos 6 g reais, esse empate
sumiu:** as duas últimas linhas não voam, com sensor ou sem. 1,11 nem sustenta
o próprio peso com margem para corrigir; 1,22 sai do chão e não se recupera de
um empurrão.

Não é uma questão de abrir mão de sensor — é que os 36 g de carcaça e circuito
de carga passaram a ser mais peso do que este drone tem para dar.

Por isso: **use-a na bancada** (Fases 0–3), onde peso não importa e o carregador
embutido é uma conveniência real, e compre uma LiPo 1S de hobby para voar. Os
~R$ 20 de um carregador USB de LiPo 1S resolvem isso, e é o que a LiPo nua
exige em troca. (Não o TP4056 comum: ele carrega a 1 A, que é 1,5C numa célula
de 650 mAh — ver `MONTAGEM.md`.)

> Aplicando o teste de volume à bateria do E88: 72 × 28,7 × 12,3 mm dá 25,4 cm³
> de **caixa**. Descontando parede e placa de carga, a célula fica em ~17 cm³, e
> 1800 mAh (6,66 Wh) exigiriam 0,39 Wh/cm³ — o topo absoluto do que LiPo
> alcança. A capacidade real deve estar entre 1200 e 1500 mAh.

Como reconhecer a LiPo de hobby certa: bolsa chata prateada ou preta envolta em
filme, dois fios (vermelho e preto), conector **BT2.0** ou PH2.0, etiqueta com
`1S 3.7V 650mAh 30C`, ~16 g. Marcas que fazem a peça certa: **GNB (Gaoneng),
BetaFPV, Tattu, Happymodel, EMAX Tinyhawk**.

> Célula de **400 mAh (802035)** não serve para os 1020 (exigiria 30C), mas
> serve bem para o drone mínimo com os motores 716, que puxa ~5 A: 12C é
> plausível numa célula genérica, e os ~10 g cabem no orçamento de 34 g
> daquele build.

**Antes de comprar, olhe a célula de 1000 mAh que você já tem.** Se estiver
impresso **20C ou mais**, ela serve: 22 g, empuxo/peso 1,51 e ~8 min de voo.
Sem C impresso, é quase certo que seja de 2–5C e não serve.

---

## Hélice: o que comprar para o 1020

A especificação inteira cabe em quatro linhas, e as quatro têm de bater:

| | |
|---|---|
| **Diâmetro** | **75 mm** (aceitável: 65 mm) |
| **Furo do eixo** | **1,0 mm** — é o eixo do 1020 |
| **Pás** | 2 |
| **Sentido** | **2 CW + 2 CCW** (às vezes vendidas como A/B) |

Termos de busca que trazem a peça certa:

- `hélice 75mm furo 1mm drone`
- `hélice 8520 75mm CW CCW` — o 8520 usa o mesmo eixo de 1 mm, e é o motor
  para o qual essas hélices são vendidas em quantidade
- `propeller 75mm 1mm shaft coreless` (importado)

Vêm em jogo de 4 (2 de cada sentido) por uns R$ 10. **Compre dois jogos.** A
primeira coisa que quebra num drone é hélice, e trocar uma só desbalanceia o
conjunto — é jogo inteiro que se troca.

### O furo é o que costuma dar errado

É o único número que não perdoa:

| Furo do anúncio | Serve? |
|---|---|
| 1,0 mm | ✅ |
| 0,8 mm | ❌ não entra — é do motor 716/720 |
| 1,5 mm ou 2,0 mm | ❌ folga no eixo; a hélice patina e sai voando |

Se o anúncio não diz o furo, olhe para que motor ela é vendida: **8520 e 1020
usam 1 mm; 716, 720 e 615 usam 0,8 mm.** Um drone de brinquedo que use 75 mm
(E58, JY019, S168) tem hélice de 1 mm.

### Sobre o sentido de giro

Motor coreless tem a escova angulada para um sentido só, e o driver de MOSFET
não inverte (é meia-ponte, não ponte completa). Então o sentido é decidido na
compra, e é assim que o mixer da `main.cpp` espera:

```
   FL (CW)  ...  FR (CCW)        vistos DE CIMA
   RL (CCW) ...  RR (CW)
```

Diagonais opostas giram no mesmo sentido — é isso que cancela o torque de
reação e deixa o guinada controlável. Confira antes de colar: com o drone
preso e throttle baixíssimo, um pedacinho de fita em cada eixo mostra o sentido
a olho nu.

### Se você quiser conferir a folga antes de as hélices chegarem

`cad/helice.py` gera uma hélice torcida de verdade — 75 mm, furo de 1 mm,
passo 30 mm, ~1 g — para imprimir e encaixar no frame:

```bash
python3 cad/helice.py                # helice_ccw.stl e helice_cw.stl
python3 cad/placa.py --helices       # 2+2 junto com o resto das peças
```

**Ela não é para voar.** Sai desbalanceada, e desbalanceamento a 30.000 rpm é
vibração que o BMI160 lê como movimento e o termo D do PID amplifica. Pior:
camada de FDM delamina sob força centrífuga, e o fragmento sai a ~100 km/h.
Serve para conferir folga no frame, testar o encaixe de 1 mm e girar devagar na
bancada para checar sentido e mixer — **de óculos.**

---

## MOSFET

Corrente de 3 A por motor. Através do transistor, a corrente eficaz é
`I × √duty`: pairando (55 %) dá **2,04 A**; no talo, os 3 A cheios.

A perda por condução é `I² × RDS(on)`, e o SOT-23 dissipa mal (~200 °C/W):

| Peça | RDS(on) @ 2,5 V | Perda no talo | Aquecimento | |
|---|---|---|---|---|
| **AO3400A** | 25 mΩ | 0,23 W | ~45 °C | ✅ **use este** |
| AO3402 | 35 mΩ | 0,32 W | ~63 °C | serve |
| IRLML2502 | 45 mΩ | 0,41 W | ~80 °C | no limite |
| SI2302 | 50–85 mΩ | 0,45–0,77 W | 90–150 °C | ❌ cozinha |
| IRLZ44N (TO-220) | 25 mΩ | 0,23 W | desprezível | bancada — pesa 2,3 g |

### A escolha: AO3400A (SOT-23)

Ao soldar, **dê uma gota generosa de solda no pad do dreno e prenda um pedaço
de fio grosso nele**. Em SOT-23 quem dissipa o calor é o cobre ligado ao dreno,
não o corpo do transistor.

Na bancada, use IRLZ44N: mesma resistência, pernas grossas, e o peso não importa
enquanto nada voa.

**Nunca use MOSFET não-logic-level** (IRF540, IRFZ44 sem o "L"). Eles precisam
de 10 V na porta; com os 3,3 V do Pico ficam meio ligados e cozinham.

### Diodo: SS34 ou 1N5822, nunca 1N5819

A corrente de roda livre é a corrente inteira do motor, até **3 A**. O 1N5819 é
de **1 A** — queima. O **1N5822** é o mesmo Schottky de 40 V em 3 A, mas no
encapsulamento DO-201 pesa ~1,1 g; quatro deles são 4 g a mais no drone. Para
voar, use o **SS34**: mesmo diodo (3 A, 40 V) em SMD, ~0,1 g. Na bancada, o
1N5822 é mais fácil de soldar.

### Porta

Resistor de **100 Ω** entre o GPIO e a porta, e **10 kΩ** da porta para o GND.

O firmware já configura os pinos de PWM para **12 mA de capacidade e slew rate
rápido** (`platPwmAttach`, em `src/platform.cpp`). O padrão do RP2040 é 4 mA, e
com isso a porta levaria ~1,6 µs para carregar — a 20 kHz o transistor passaria
3 % do tempo em transição, dissipando mais do que conduzindo.

Se mesmo assim o MOSFET esquentar, baixe `MOTOR_PWM_FREQ` para `12000`.

---

## Meça, não confie nesta tabela

Uma **balança de cozinha de 0,1 g** custa ~R$ 30 e substitui todas as estimativas
acima por números reais. É o melhor investimento do projeto.

**Peso:** pese cada peça conforme montar e vá anotando. Você vai descobrir onde
está o peso de verdade — e provavelmente não é onde eu chutei.

**Empuxo — o teste que vale mais que tudo:**

1. Monte o drone completo, com hélices, e apoie na balança, na horizontal.
2. Tare (zere) a balança.
3. Arme e suba o throttle devagar, segurando o drone pelos lados sem apertar
   para baixo.
4. A leitura vai ficando **negativa** conforme os motores empurram. Quando ela
   chegar a menos o peso do drone, o empuxo igualou o peso.

Se no throttle máximo a leitura não passar de metade do peso do drone, não
adianta ajustar PID: falta propulsão. Se passar do dobro, você tem folga de
sobra e pode devolver o ultrassônico frontal para o projeto.

Faça esse teste **antes** do primeiro voo livre. Ele responde em dois minutos a
pergunta que todo o resto deste documento tenta estimar.

---

## Teste de queda de tensão: vale mais que o C do anúncio

O firmware já mostra `Bateria` na telemetria. Use isso para medir a bateria de
verdade, seja ela qual for.

Com o drone montado e **sem hélices**, suba o throttle do mínimo ao máximo
observando o campo `Bateria`:

| Queda | Veredito |
|---|---|
| até ~0,4 V | a bateria aguenta |
| 0,6 V ou mais | ela é o gargalo — com hélices vai afundar o dobro |

Isso mede a resistência interna da célula **somada à da fiação e do conector**,
que é o que de fato limita o drone. Uma bateria "30C" com fio fino e conector
ruim se comporta como uma de 10C, e nenhum anúncio conta isso.

Se a queda for grande, teste na ordem: fio mais grosso, conector melhor,
capacitor maior nos terminais. Só depois culpe a célula.

---

## Onde comprar, não o que buscar

Lojas de peça de reparo de celular não estocam LiPo de modelismo, por mais que
se refine a busca. Vá pela categoria:

> **Hobbies e Brinquedos → Modelismo → Aeromodelismo → Baterias**
>
> ou **Câmeras e Drones → Acessórios de Drones → Baterias**

Ou busque pela marca, que pula o problema da categoria: **GNB (Gaoneng),
BetaFPV, Tattu, Happymodel, EMAX**.
