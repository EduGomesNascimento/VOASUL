# Frame e peças impressas

Não precisa de biblioteca nenhuma além do Python.

## Tudo de uma vez

```bash
python3 placa.py                 # placa_impressao.stl — todas as peças
python3 placa.py --essencial     # só frame, sonar de baixo e os 4 pés
python3 placa.py --helices -o placa_tudo.stl   # + 2 CCW e 2 CW, tudo num arquivo
python3 placa.py --mesa 180 180  # confere contra outra mesa
```

Sai **uma placa de 164 × 165 mm, 41 g em PLA**, com as 9 peças já apoiadas em
z = 0 e na orientação certa. Abra no fatiador e mande imprimir: **nenhuma peça
precisa de suporte.**

`placa_tudo.stl` é a mesma coisa **mais as 4 hélices** — 164 × 195 mm, 45 g,
13 peças. Aí muda uma coisa: as hélices precisam de suporte e o resto não, e
suporte **global** entope a fresta de 1,9 mm do `sonar_baixo`, de onde não sai
mais. Use **suporte pintado** só nas 4 hélices (Orca, Bambu, PrusaSlicer e Cura
têm a ferramenta). Sem paciência para isso, imprima `placa_impressao.stl` e as
hélices num job separado.

Foi por isso que os pés de pouso saíram de dentro do frame. Integrados, eles
apontam para baixo e poriam o frame 20 mm no ar — suporte sob a base e os braços
inteiros, muito material e a face inferior arruinada. Soltos, imprimem em pé e
colam depois com cianoacrilato.

| Peça | Qtd | g |
|---|---|---|
| frame | 1 | 26,9 |
| sonar_frente | 1 | 4,0 |
| sonar_baixo | 1 | 3,5 |
| suporte_ir | 2 | 3,0 |
| pé de pouso | 4 | 3,2 |
| **Total** | | **40,6** |

Desses 40,6 g, só **33,6 g voam** na configuração de primeiro voo: o frame, os
4 pés e o berço do sonar de baixo. Os outros três suportes resolvem com fita
dupla-face e abraçadeira — ver "Suportes dos sensores", abaixo.

## Frame da placa redonda

```bash
python3 frame_redondo.py                    # frame_redondo.stl
python3 frame_redondo.py --placa 97.3       # com o diâmetro da SUA placa, medido
python3 frame_redondo.py --raio 94          # motores mais perto do centro
```

Para a placa de circuito redonda de Ø 97,1 mm. É a versão corrigida do modelo
feito no Inventor (`DRONE.stl`), com a mesma ideia: disco com rebaixo e quatro
braços em X, motores a 100,4 mm do centro.

| | Modelo original | `frame_redondo.stl` |
|---|---|---|
| Furo do motor | Ø 8,5 (de motor 8520): **o 1020 não entra** | tubo de Ø 9,9 × 10 mm, com batente |
| Braços | maciços, 6,7 mm | 3 mm + nervura de 1,6 × 4 mm |
| PLA (maciço) | **~87 g** | **~28 g** |
| Suporte para imprimir | sim: os braços ficam 2 mm acima da mesa | não: tudo nasce em z = 0 |
| Fundo do rebaixo | chapa de 2 mm com furos | 4 raios; a placa apoia num degrau 2 mm acima |

A placa assenta no degrau da borda, com fita dupla-face de espuma, que também
amortece a vibração para o BMI160. Os 2 mm entre a placa e os raios deixam
livres as pontas dos pinos soldados, e os vãos entre os raios deixam o
ultrassônico ver o chão e a cinta da bateria passar.

A seta na parede marca a frente: os motores ficam FR (+,+), FL (−,+), RR (+,−)
e RL (−,−), como no mixer.

Pés de pouso: os mesmos `pe.stl`, colados sob os braços a ~15 mm do motor —
não embaixo do tubo, que é por onde saem os fios.

## Peças separadas

```bash
python3 frame.py                      # frame.stl        — 27 g em PLA
python3 frame.py --guardas            # com proteção de hélice — 47 g
python3 frame.py --diagonal 190       # frame maior
python3 frame.py --pes                # pés integrados (exige suporte, ver acima)
python3 frame.py --motor 7 --helice 55    # de volta ao 716 do E88

# Drone de prova de voo com os motores 716 (ver "Voar com o 716" abaixo)
python3 frame.py --minimo --motor 7 --helice 55 --base 56 24 -o frame_minimo.stl
```

## De onde vêm as dimensões

A **placa perfurada de 130 × 30 mm** é quem manda. Tudo o mais sai dela:

- A base é um **quadro perimetral**, não uma chapa. A placa já é rígida; o frame
  só precisa segurá-la pelas bordas. Chapa maciça de 130 × 30 × 3 pesaria
  14,5 g; o quadro pesa 8.
- **Só a largura entra na geometria.** A posição do motor sai de
  `largura/2 + raio da hélice + folga`, então estreitar encurta a diagonal e
  encurtar não mexe em nada. Os 130 mm de comprimento são pura escolha de área
  útil: custam 3,8 g de fenolite e 2,0 g de trilho contra a mesma placa cortada
  em 80 mm, e em troca sobram **79 × 30 mm** ao lado do Pico W (51 × 21) para os
  MOSFET, os barramentos e os terminais. MOSFET SOT-23 pendurado no fio quebra
  numa aeronave que vibra; nesta placa nada precisa ficar pendurado.
- Os motores ficam em **X quadrado** (±58, ±58 mm), diagonal 163 mm. Quadrado
  importa: braço de rolagem igual ao de arfagem, senão `PID_RATE_ROLL_*` e
  `PID_RATE_PITCH_*` precisariam de valores diferentes.
- A posição do motor é o **mínimo que dá folga à hélice**: metade da largura da
  base + raio da hélice + 5 mm. Mudou a hélice, o script recalcula. (Trocar a
  hélice de 75 para 65 mm encurta a diagonal para 148 mm e poupa só 1 g — a
  hélice menor não é um caminho para tirar peso.)
- Os braços têm um **contraventamento diagonal**. Sem ele o braço fica preso só
  no trilho de 5 mm, e o conjunto motor+hélice trabalha como alavanca sobre essa
  única seção — é onde frame impresso quebra. Custa ~4 g.
  O ponto de ancoragem é calculado, não fixo: com a placa de 130 mm o motor cai
  **dentro** do comprimento dela (58 de 65), então o canto da base fica quase
  debaixo do motor e ancorar lá não triangularia nada. O script escolhe, entre o
  canto e um ponto para dentro do trilho, o que dá o maior afastamento em X — e
  com esta placa dá o X que se vê na vista de cima.

## Comparação com o modelo anterior

| | Modelo antigo | Este |
|---|---|---|
| Massa (PLA maciço) | **131 g** | **27 g** (+3,2 g dos 4 pés) |
| Layout dos motores | retângulo 153 × 235 mm | quadrado, diagonal 163 mm |
| Vão da hélice | fechado por chapa de 3 mm | aberto |
| Base | caixa de 200 mm | quadro de 130 × 30 mm |

## Montagem

- **Motor**: encaixe de 9,9 mm de diâmetro para o coreless 1020 de 10 × 20 mm
  (0,1 mm de interferência, segura por atrito). Se ficar folgado, aumente
  `motor_fit`; se não entrar, diminua. Uma gota de cianoacrilato resolve
  qualquer folga residual.
  Compre **2 CW + 2 CCW**: com driver de MOSFET não dá para inverter o sentido
  por software, e motor coreless tem a escova angulada para um sentido só.
  Hélice de **75 mm com furo de 1 mm** — a especificação completa e os termos de
  busca estão em [`../docs/ORCAMENTO.md`](../docs/ORCAMENTO.md).
- **Placa**: use a fenolite inteira, **130 × 30 mm**. Se precisar cortar, corte
  na borda de uma fileira de ilhas para não perder meia-ilha. Risque dos dois
  lados contra uma régua e quebre, ou corte com serra. O pó de fenolite é
  irritante — máscara, e de preferência ao ar livre. A placa apoia em cima do
  quadro e das duas nervuras; prenda com abraçadeira pelos vãos dos trilhos
  longos (são 8).
- **Bateria**: embaixo, presa por abraçadeira nos mesmos vãos. Embaixo é o certo:
  aproxima o centro de gravidade do plano das hélices.

## Suportes dos sensores

```bash
python3 suportes.py                 # gera os três
python3 suportes.py sonar_baixo     # só um
python3 suportes.py --folga 2.1     # guia mais folgada, se a placa não entrar
```

| Peça | Peso | Vale imprimir? |
|---|---|---|
| `sonar_baixo.stl` | 3,5 g | **sim** |
| `pe.stl` (4×) | 3,2 g | **sim** — sem eles o drone pousa sobre o sonar |
| `sonar_frente.stl` | 4,0 g | não — fita dupla-face resolve |
| `suporte_ir.stl` (2×) | 3,0 g | não — abraçadeira resolve |

**Só o sonar de baixo precisa mesmo ser impresso.** Ele mede a altura, e a
leitura sai multiplicada pelo cosseno da inclinação dele: 10° de folga no
suporte viram 1,5 % de erro constante, e o alt-hold fica caçando altura a vida
toda. Rigidez ali é função, não acabamento.

Os outros três só precisam apontar aproximadamente na direção certa — o desvio
compara a distância com um limiar, não integra o valor. Dois graus de erro não
mudam nada, e os 7 g valem mais no orçamento.

Encaixe por atrito: a placa desliza na guia em C. Folgou, aumente `--folga`;
não entrou, diminua.

## Hélice

```bash
python3 helice.py                # helice_ccw.stl e helice_cw.stl — 1,0 g cada
python3 helice.py --d 65 --p 26  # outro diâmetro e passo
python3 placa.py --helices       # 2+2 junto com o resto das peças
```

> ### Hélice impressa não é para voar
>
> Ela sai **desbalanceada**, e desbalanceamento a 30.000 rpm vira vibração que o
> BMI160 lê como movimento, o termo D do PID amplifica, e o drone chia parado no
> ar. Pior: camada de FDM **delamina** sob força centrífuga, e o fragmento sai a
> ~100 km/h. **Use óculos de proteção mesmo para testar.**
>
> Para que ela serve: conferir a folga no frame antes das de verdade chegarem,
> verificar o encaixe de 1 mm no eixo, e girar devagar na bancada para checar
> sentido de giro e o mixer. Para voar, compre injetada — a especificação está
> em [`../docs/ORCAMENTO.md`](../docs/ORCAMENTO.md).

Não é uma chapa plana torcida na ponta: o ângulo em cada raio sai do passo,
`θ(r) = atan(P / 2πr)`, que é a condição para a pá inteira trabalhar com o mesmo
ângulo de ataque em vez de só o meio dela empurrar ar.

| Raio | Torção |
|---|---|
| 3 mm (raiz) | 57,9° |
| 10 mm | 25,5° |
| 20 mm | 13,4° |
| 37,5 mm (ponta) | 7,3° |

Padrão: 75 mm de diâmetro, passo 30 mm (0,4 × diâmetro), 2 pás, furo de 1,0 mm,
corda de 5 mm na raiz a 9 mm em 0,6 R, espessura de 1,1 mm na raiz a 0,5 mm na
ponta.

Imprime deitada, cubo no plano. **É a única peça deste diretório que pode pedir
suporte**: os 58° da raiz ficam em balanço. Ligue suporte só nela, ou aceite a
barriga — é peça de bancada.

## Voar com o 716

Os motores 716 do E88 dão ~12 g de empuxo cada, **48 g nos quatro**. Isso limita
o drone inteiro a ~30 g — não cabe a placa perfurada, nem os ultrassônicos, nem
os IR, nem a bateria de 1000 mAh.

Ainda assim dá para voar, como prova de conceito do firmware:

```bash
python3 frame.py --minimo --motor 7 --helice 55 --base 56 24 -o frame_minimo.stl
```

8 g, diagonal 123 mm, base de 56 × 24 mm (o tamanho do Pico W, que vai soldado
direto, sem placa perfurada). O perfil `--minimo` leva todas as seções ao mínimo
que ainda imprime com 3 perímetros de bico 0,4.

| Item | Peso |
|---|---|
| Frame `--minimo` | 8 g |
| 4× motor 716 | 10 g |
| 4× hélice 55 mm | 2 g |
| Pico W (sem barra de pinos) | 3 g |
| BMI160 | 1,5 g |
| 4× MOSFET + diodo + fio | 3 g |
| Bateria 1S 250 mAh | 7 g |
| **Total** | **~34 g** |

Empuxo/peso ≈ **1,4**. Voa em ambiente fechado e ar parado, devagar, uns 2
minutos por carga. Não é um drone bom — é a prova de que o firmware, o AHRS e o
PID funcionam no ar. Com bateria de 150 mAh cai para ~31 g e melhora um pouco.

**Os L298N não servem para voar aqui**: os ~2 V que eles derrubam deixariam 1,7 V
no motor, e o 716 nessa tensão dá uns 3 g — 12 g nos quatro. Para esta etapa é
MOSFET ou nada. (Na bancada, com o drone preso, os L298N servem muito bem.)

## Impressão

- PLA ou PETG, bico de 0,4 mm, camada 0,2 mm.
- **4 perímetros, 40 % de preenchimento.** As peças são finas: quase tudo vira
  perímetro, e é o perímetro que segura.
- Sem suporte — o modelo foi feito para imprimir apoiado na base.
- Deitado no plano, com os tubos de motor para cima (é como o STL já vem).

## Observação sobre o STL

Sai como vários sólidos fechados que se sobrepõem. Todo fatiador (Cura,
PrusaSlicer, Orca, Bambu) faz a união ao fatiar. É a forma mais robusta de
montar essa geometria sem um kernel CAD — e o motivo de o peso real sair um
pouco abaixo do que o script informa, já que ele soma as sobreposições.

Para voltar ao Inventor: importe o STL e use **Malha → Converter em sólido**.
