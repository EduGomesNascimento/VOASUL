# Luva de gestos (versão simples: 1 sensor)

Uma luva com **um MPU-6050** nas costas da mão e um **XIAO ESP32-S3** no pulso. O drone voa para
onde a mão inclina. O controle pelo celular continua funcionando: enquanto a luva está ligada, ela
manda; desligou, o celular volta a mandar.

## Peças

| Peça | Qtd | Observação |
|---|---|---|
| XIAO ESP32-S3 (ou o Sense) | 1 | você já tem |
| MPU-6050 (GY-521) | 1 | já está no carrinho do Mercado Livre |
| 4 fios de ~20 cm | 4 | jumper fêmea-fêmea serve para testar |
| Luva fina | 1 | o sensor vai costurado ou com velcro nas costas da mão |
| Power bank USB-C no bolso **ou** LiPo 1S 250–400 mAh nas ilhas BAT do XIAO | 1 | o power bank é o mais simples |

Não precisa de botão: o **BOOT** do próprio XIAO arma e desarma.

## Ligações

| MPU-6050 | XIAO |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SDA | D4 |
| SCL | D5 |

**Posição do sensor:** nas costas da mão, componentes para cima, seta **X para os dedos**.

## Gestos

Sempre a partir da **mão reta** (palma para baixo), que é a posição gravada na calibração.

| Mão | Drone |
|---|---|
| Reta | fica parado no ar (mantém a altura) |
| Inclinar para frente / para trás | anda para frente / para trás |
| Inclinar para a direita / esquerda | anda para o lado |
| Girar a mão deitada (como um volante) | gira no lugar |
| Dedos para cima (mão em pé) | sobe |
| Dedos para baixo | desce |
| Palma para cima, por meio segundo | pousa sozinho |
| Apertar o **BOOT** | **corta os motores** (emergência) |

Para armar: mão reta e **segure o BOOT por 1,5 s**. O LED acende. Para decolar, aponte os dedos
para cima.

Se a luva desligar ou sair do alcance, o drone fica parado no ar e pousa sozinho (failsafe).

## Gravar e testar

```bash
cd luva
pio run -t upload
pio device monitor
```

1. **Calibração:** ligue com a mão reta e parada. O LED pisca rápido por 2 s.
2. **Na serial:** mexa a mão e confira que o "roll", o "pitch" e o modo ("andando", "subindo",
   "pousando") mudam como na tabela.
3. **Com o drone sem hélice:** na página do celular, o quadro **Luva** mostra "no controle". Arme
   pela luva e confira, motor por motor, que cada gesto acelera os motores certos.
4. Só então voe **amarrado** (fase 9 do plano de montagem).

Os testes da lógica rodam no PC: `cd luva/test && make`.

## Ajustes

Ficam no topo de `include/gestos.h`: zona morta (8°), inclinação para o comando máximo (30°),
quanto o drone inclina (60% do máximo, ~15°), ângulo para subir/descer (55°), velocidade de subida
e o giro. Os dois firmwares precisam usar o mesmo canal de rádio (`WIFI_CHANNEL 1`) e o mesmo
prefixo (`LUVA_ID`).
