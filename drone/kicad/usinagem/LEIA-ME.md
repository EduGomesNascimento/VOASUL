# Placa do drone VoaSul para fresar em CNC

Placa redonda de **97 mm**, espessura **1,6 mm** (FR-4 ou fenolite). Os componentes de furo
passante ficam em cima e o cobre fica **embaixo** (B.Cu). Os Gerbers estão no padrão, vistos de
cima: espelhe a face de baixo no seu CAM como de costume.

## Regras da sua CNC × placa

Conferido no KiCad com essas regras: **DRC com 0 erros e 0 pinos desligados**.

| Regra | Pedido | Na placa |
|---|---|---|
| Espaçamento mínimo entre cobres | 0,5 mm | **0,54 mm** (entre ilhas vizinhas de pino de 2,54); o resto, 0,65 a 0,8 mm |
| Largura mínima de trilha | 0,6 mm | **0,8 mm** (sinais 1,2, alimentação 1,5, potência 2,5; plano de GND sem trecho abaixo de 1,0) |
| Furo mínimo | 0,8 mm | **0,9 mm** |
| Ilha mínima | 1,8 mm | **1,9 mm** (furo 0,9) e **2,0 mm** (furo 1,0); anel de cobre de pelo menos 0,5 mm |

Furos: **52 de 0,9 mm**, **81 de 1,0 mm** e **2 de 1,3 mm** (num arquivo Excellon só, todos sem
metalização). O mapa de furos está em `*-drl_map.pdf`.

## Face única ou dupla face

A placa foi feita para **face única**. Onde duas trilhas se cruzariam há **11 jumpers**: fio por
cima da placa, entre dois furos.

| Zip | Arquivos | Quando usar |
|---|---|---|
| `VoaSul_usinagem_face_unica.zip` | B.Cu, contorno, furos, `jumpers.txt` | **recomendado**. Os 11 jumpers são soldados com fio depois |
| `VoaSul_usinagem_dupla_face.zip` | + F.Cu | se você faz dupla face: a face de cima tem **só** as 11 trilhas dos jumpers (nenhum componente liga em cima) |

Na dupla face, cada um dos **22 furos de via** (0,9 mm, ilha de 2,4 mm) precisa de um fio passado e
soldado dos dois lados, porque a placa não tem metalização. É o mesmo trabalho dos jumpers de fio e
ainda pede o alinhamento das duas faces. Por isso a face única é mais simples.

## Outros detalhes

- **Contorno:** círculo de Ø97 mm na camada Edge.Cuts (fresar por fora da linha).
- **Placa virgem:** use 110 × 110 mm ou maior. Numa de 100 × 100, o corte do contorno (fresa de 1 mm)
  passa a 0,5 mm da borda.
- **Plano de GND:** o cobre que sobra é GND, de propósito: menos cobre para tirar.
- **Área sem cobre:** um retângulo de ~6,5 × 19 mm embaixo da antena do ESP32 deve ficar sem cobre.
  O isolamento contorna a área; se der, raspe o cobre de dentro.
- Se preferir, há G-code pronto para GRBL na pasta `cnc/` do projeto (fresa em V 30°/0,1 mm,
  brocas, fresa de 1 mm). Ele usa estas mesmas ilhas.
