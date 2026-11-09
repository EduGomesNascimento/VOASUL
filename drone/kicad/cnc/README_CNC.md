# Fresar a placa na CNC

Os arquivos desta pasta fresam a **placa caseira de face única** (a mesma da folha de transferência,
com os 11 jumpers) numa CNC de PCB com GRBL, como a CNC 3018 e parecidas. Programa para mandar o
G-code: Candle, UGS ou bCNC. São gerados por `../cnc.py` a partir da placa do KiCad, e os valores
de ferramenta ficam no topo do script.

Conferido por geometria: a fresa nunca entra mais de 0,01 mm em cobre nenhum, só encosta na borda.

## Arquivos, na ordem

| # | Arquivo | Ferramenta | Tempo |
|---|---|---|---|
| 1 | `1_isolamento_vbit.nc` | fresa em V 30°, ponta 0,1 mm | ~57 min |
| 2 | `6_limpar_antena_vbit.nc` (opcional) | a mesma fresa em V | ~8 min |
| 3 | `2_furos_0.9mm.nc` | broca 0,9 mm (52 furos: pinos e jumpers) | ~8 min |
| 4 | `3_furos_1.0mm.nc` | broca 1,0 mm (81 furos) | ~12 min |
| 5 | `4_furos_1.3mm.nc` | broca 1,3 mm (2 furos, bateria) | 1 min |
| 6 | `5_contorno_fresa1mm.nc` | fresa de topo 1,0 mm | ~18 min |

- **Só tem broca de 1,0 mm?** Use `2a_furos_todos_1.0mm.nc` no lugar dos passos 3 e 4 (as ilhas de
  1,7 mm aguentam) e faça os 2 furos da bateria com 1,3 mm à mão ou na CNC.
- `previa_cnc.png` mostra todos os percursos. Confira antes de começar.

## Origem e posição (o mais importante)

- **O cobre fica para CIMA** e os arquivos já saem espelhados. Depois de pronta, olhando o lado do
  cobre, a bateria (J1) fica à **direita** e a área da antena à direita do centro.
- **X0 Y0 = CENTRO do disco.** Prenda uma placa virgem de pelo menos **100 × 100 mm** (a fenolite
  15×20 dá 2 discos) e leve a fresa até o centro da área que vai usar antes de zerar X e Y.
- **Z0 = superfície do cobre.** Zere com a sonda (jacaré na fresa e na placa) ou com uma folha de
  papel.
- **Não mexa em X/Y entre os arquivos.** Em cada troca de ferramenta, zere **só o Z** de novo.

## Passo a passo

1. **Prenda a placa bem plana**, com fita dupla face fina em toda a área, sobre uma base de
   sacrifício (MDF). Placa empenada é a causa número 1 de trilha falhando.
2. **Faça o nivelamento automático (autolevel / height map)** no Candle ou no bCNC: malha de
   ~10 × 10 mm sobre a área do disco. O isolamento corta só 0,08 mm, então um empeno de 0,1 mm já
   deixa trilha sem cortar ou corta fundo demais.
3. Fresa em V: rode `1_isolamento_vbit.nc`, com o autolevel aplicado. Aspire o pó e confira com
   lupa se todos os contornos separaram. Se ficou cobre ligando, rode de novo com Z0 0,02 mm mais
   baixo.
4. (Opcional) `6_limpar_antena_vbit.nc` raspa o cobre embaixo da antena do ESP32. Sem isso fica
   uma ilha de cobre solta ali, o que atrapalha pouco, mas é melhor tirar.
5. Furos: troque a broca, zere o Z e rode cada arquivo de furo.
6. Contorno: troque para a fresa de 1 mm, zere o Z e rode `5_contorno_fresa1mm.nc`. Ele desce de
   0,3 em 0,3 mm até 1,8 mm e deixa **4 pontes** de 0,5 mm. Corte as pontes com estilete e lixe.
7. Lixe de leve o cobre (lixa 1000 ou palha de aço), limpe com álcool isopropílico e meça com o
   multímetro: **sem curto entre VBAT↔GND, 5V↔GND e 3V3↔GND** (ver `../saidas/redes.txt`).

## Valores usados (mude no topo de `cnc.py` e rode `/usr/bin/python3 cnc.py`)

| | Valor |
|---|---|
| Isolamento | 2 passadas, profundidade 0,08 mm, avanço 150 mm/min, mergulho 50 mm/min, 10 000 rpm |
| Largura de corte | 0,14 mm (30°, ponta 0,1 mm, a 0,08 mm). As folgas da placa são de 0,8 mm, então sobra muita margem |
| Furos | 1,9 mm de profundidade, 50 mm/min |
| Contorno | Ø98 no centro da fresa (borda em Ø97), passadas de 0,3 mm até 1,8 mm, 100 mm/min |
| Altura de segurança | Z 2 mm |

## Cuidados

- **Pó de FR-4 (fibra de vidro) faz mal:** aspire durante o corte e use máscara. A fenolite (FR-2)
  é mais segura e mais macia.
- Óculos de proteção: a fresa em V de 0,1 mm quebra fácil e a ponta voa.
- O texto "VoaSul | Drones" do cobre não é fresado: fica um retângulo de cobre liso no lugar.
