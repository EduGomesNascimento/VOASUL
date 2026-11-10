# Estação terra: ESP32-C3 na capinha do celular

```
celular ──Wi-Fi──> ESP32-C3 "terra" ──ESP-NOW──> drone
celular <──Wi-Fi── ESP32-C3 "terra" <──ESP-NOW── drone   (telemetria)
```

O celular não fala direto com o drone: ele conecta no Wi-Fi da **terra**, um ESP32-C3 preso atrás
do celular. A terra repassa cada comando ao drone por **ESP-NOW**, o rádio direto entre ESP32, e
devolve a telemetria. A página é a mesma de sempre, só que servida pela terra.

**Por que assim:** o ESP-NOW é mais rápido e tem mais alcance que o Wi-Fi do celular, e o drone não
precisa mais segurar a conexão Wi-Fi do celular enquanto voa.

## Peças

| Peça | Qtd | Preço | Observação |
|---|---|---|---|
| ESP32-C3 Super Mini | 1 | ~R$ 11 | a versão **Plus**, com conector de antena externa, alcança mais |
| Cabo USB-C ↔ USB-C curto (OTG) | 1 | ~R$ 8 | a terra é alimentada pelo próprio celular |
| Fita dupla face ou velcro | — | já tem | prende o C3 na capinha |

Se o celular não alimentar acessórios pelo USB-C (alguns precisam ligar o "OTG" nas configurações),
use um power bank pequeno.

## Gravar

```bash
cd drone
pio run -e terra -t upload        # terra (ESP32-C3)
pio run -e esp32dev -t upload     # drone (ESP32)
```

Se o upload não começar no C3: segure o BOOT, aperte e solte o RESET e solte o BOOT.

## Usar

1. Ligue o drone e plugue a terra no celular.
2. No celular, conecte na rede **VOASUL-TERRA** (senha `voar1234`) e abra **http://192.168.4.1**.
3. No topo da página aparece **"terra + drone ok"** com o ponto verde aceso. Se aparecer
   **"SEM SINAL DO DRONE"**, o drone não está respondendo (desligado, longe ou em outro canal).
4. Pilote como antes: ALT HOLD, ARMAR, POUSAR e os dois manches.

**LED da terra:** aceso = drone respondendo; piscando = sem sinal do drone.

## Segurança

- Se o celular desconectar da terra, ou a terra perder o drone, o drone recebe nada por 0,4 s e
  **pousa sozinho**.
- Enquanto a terra manda, um celular ligado direto no Wi-Fi do drone (**VOASUL-DRONE**, a rede
  reserva) só vê a telemetria, não comanda. Sem a terra, ele volta a comandar.

## Como funciona (para o relatório de Comunicações)

| | |
|---|---|
| Canal | 1 (fixo, `WIFI_CHANNEL` em `include/config.h`), o mesmo nos dois |
| Comando | o texto `C,roll,pitch,yaw,throttle,flags` com o prefixo `VS1:`, 50 por segundo |
| Telemetria | JSON com o prefixo `VT1:`, 10 por segundo, abaixo de 250 bytes por pacote |
| Endereço | antes de ouvir o drone, a terra manda em broadcast; depois manda direto para o MAC do drone, e o rádio confirma e repete o pacote perdido |
| Código | terra: `src/terra/terra.cpp` (reaproveita o `websocket.cpp` e a página `webui.h`); drone: `src/receiver.cpp` |

**Para testar o alcance:** o Serial da terra mostra a cada 0,5 s quantos comandos foram e quantas
telemetrias voltaram. Comparando os dois números a cada 10 m, sai a taxa de perda de pacotes.
