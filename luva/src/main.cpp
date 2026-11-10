// ============================================================================
//  Luva de gestos VoaSul: XIAO ESP32-S3 + 1 MPU-6050 nas costas da mao.
//
//  Ligacoes (so 4 fios):  MPU-6050 VCC -> 3V3   GND -> GND   SDA -> D4   SCL -> D5
//  Botao: o BOOT do proprio XIAO (nao precisa de outro).
//  Energia: USB-C (power bank no bolso) ou bateria LiPo 1S nas ilhas BAT do XIAO.
//
//  Uso:
//   1. Liga com a mao RETA (palma para baixo) e parada: 2 s de calibracao (LED piscando rapido).
//   2. Armar: mao reta, SEGURE o BOOT por 1,5 s. LED aceso = armado.
//   3. Dedos para cima = sobe; mao inclinada = anda; palma para cima = pousa.
//   4. Desarmar (corta os motores na hora): aperte o BOOT.
//  Se a luva desligar ou sair de alcance, o drone para no ar e pousa sozinho.
// ============================================================================
#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "gestos.h"

// ---------------------------------------------------------------- tem que bater com o drone
#define WIFI_CHANNEL   1        // drone/include/config.h: WIFI_CHANNEL
#define LUVA_ID        "VS1:"   // drone/include/config.h: LUVA_ID

#define PIN_BOTAO      0        // BOOT do XIAO (aperta = LOW)
#define PIN_LED        LED_BUILTIN
#define LED_LIGA       LOW      // o LED do XIAO S3 acende com LOW
#define MPU_ADDR       0x68     // AD0 solto ou no GND
#define PERIODO_MS     20       // 50 Hz

static const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

static gestos::Filtro filtro;
static gestos::Estado estado;
static float roll0 = 0, pitch0 = 0, bx = 0, by = 0, bz = 0;   // posicao neutra e bias do giroscopio
static bool armado = false;
static uint32_t armadoDesde = 0;

// ---------------------------------------------------------------- MPU-6050
static void mpuEscreve(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(v);
  Wire.endTransmission();
}

static bool mpuInicia() {
  Wire.beginTransmission(MPU_ADDR);
  if (Wire.endTransmission() != 0) return false;
  mpuEscreve(0x6B, 0x01);   // acorda, relogio do giroscopio X
  mpuEscreve(0x1A, 0x03);   // filtro passa-baixa ~44 Hz
  mpuEscreve(0x1B, 0x08);   // giroscopio +-500 graus/s
  mpuEscreve(0x1C, 0x08);   // acelerometro +-4 g
  return true;
}

// ax..az em g, gx..gz em graus/s
static bool mpuLe(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ADDR, 14) != 14) return false;
  int16_t r[7];
  for (int i = 0; i < 7; i++) r[i] = (int16_t)((Wire.read() << 8) | Wire.read());
  ax = r[0] / 8192.0f; ay = r[1] / 8192.0f; az = r[2] / 8192.0f;
  gx = r[4] / 65.5f;   gy = r[5] / 65.5f;   gz = r[6] / 65.5f;
  return true;
}

static void led(bool on) { digitalWrite(PIN_LED, on ? LED_LIGA : !LED_LIGA); }

// ---------------------------------------------------------------- calibracao
static void calibrar() {
  float sr = 0, sp = 0, sx = 0, sy = 0, sz = 0;
  int n = 0;
  const uint32_t t0 = millis();
  while (millis() - t0 < 2000) {
    float ax, ay, az, gx, gy, gz;
    if (mpuLe(ax, ay, az, gx, gy, gz)) {
      filtro.atualizar(ax, ay, az, 0, 0, 0.01f);   // so acelerometro: mao parada
      sr += filtro.roll; sp += filtro.pitch;
      sx += gx; sy += gy; sz += gz;
      n++;
    }
    led(((millis() - t0) / 100) % 2);
    delay(10);
  }
  if (n) { roll0 = sr / n; pitch0 = sp / n; bx = sx / n; by = sy / n; bz = sz / n; }
  Serial.printf("[luva] calibrada: roll0 %.1f pitch0 %.1f (%d leituras)\n", roll0, pitch0, n);
}

// ---------------------------------------------------------------- envio
static void enviar(const gestos::Comando &c, bool armar) {
  // O mesmo pacote de texto que o celular manda ao drone, com o prefixo da luva.
  // Bits: 1 armar, 2 alt-hold (sempre), 8 pousar. Desvio de obstaculo desligado.
  const int flags = (armar ? 1 : 0) | 2 | (c.pousar ? 8 : 0);
  char buf[80];
  const int n = snprintf(buf, sizeof(buf), LUVA_ID "C,%.3f,%.3f,%.3f,%.3f,%d",
                         c.roll, c.pitch, c.yaw, c.throttle, flags);
  esp_now_send(BROADCAST, (const uint8_t *)buf, n);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BOTAO, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  led(false);

  Wire.begin();                     // XIAO ESP32-S3: SDA = D4, SCL = D5
  Wire.setClock(400000);
  while (!mpuInicia()) {            // sem sensor: pisca lento e tenta de novo
    Serial.println("[luva] MPU-6050 nao respondeu: confira SDA=D4, SCL=D5, 3V3 e GND");
    led(true); delay(500); led(false); delay(500);
  }

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) Serial.println("[luva] ESP-NOW falhou");
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST, 6);
  peer.channel = WIFI_CHANNEL;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  calibrar();
}

void loop() {
  static uint32_t proximo = 0, ultimoUs = micros(), apertadoDesde = 0;
  static bool botaoAntes = false;
  if ((int32_t)(millis() - proximo) < 0) return;
  proximo = millis() + PERIODO_MS;

  float ax, ay, az, gx, gy, gz;
  if (!mpuLe(ax, ay, az, gx, gy, gz)) return;
  const uint32_t agora = micros();
  const float dt = (agora - ultimoUs) * 1e-6f;
  ultimoUs = agora;
  filtro.atualizar(ax, ay, az, gx - bx, gy - by, dt);

  gestos::Mao m;
  m.roll = filtro.roll - roll0;
  m.pitch = filtro.pitch - pitch0;
  m.giro = gz - bz;
  gestos::Comando c = gestos::interpretar(m, millis(), estado);

  // ---- botao BOOT: segurar 1,5 s com a mao reta = armar; apertar = desarmar ----
  const bool botao = digitalRead(PIN_BOTAO) == LOW;
  if (botao && !botaoAntes) {
    apertadoDesde = millis();
    if (armado) {                         // qualquer toque desarma: e o botao de emergencia
      armado = false;
      apertadoDesde = 0;                  // segurar depois de desarmar NAO arma de novo
      Serial.println("[luva] DESARMADO");
    }
  }
  const bool maoReta = fabsf(m.roll) < 15 && fabsf(m.pitch) < 15;
  if (botao && !armado && apertadoDesde && millis() - apertadoDesde > 1500 && maoReta) {
    armado = true;
    armadoDesde = millis();
    apertadoDesde = 0;                    // so arma de novo depois de soltar e segurar outra vez
    Serial.println("[luva] ARMADO");
  }
  if (!botao) apertadoDesde = 0;
  botaoAntes = botao;

  // desarmado (ou no primeiro segundo depois de armar, enquanto os motores sobem):
  // manche de altura em zero, como o drone exige para armar
  if (!armado || millis() - armadoDesde < 1000) {
    c.throttle = 0.0f;
    c.roll = c.pitch = c.yaw = 0.0f;
  }
  enviar(c, armado);

  // LED: apagado = desarmado; aceso = armado; piscando = pousando
  led(armado && !(c.pousar && (millis() / 150) % 2));

  static uint32_t dbg = 0;
  if (millis() - dbg > 250) {
    dbg = millis();
    static const char *nomes[] = {"parado", "andando", "subindo", "descendo", "pousando"};
    Serial.printf("roll %6.1f pitch %6.1f giro %6.1f | %-8s | cmd r %.2f p %.2f y %.2f thr %.2f %s\n",
                  m.roll, m.pitch, m.giro, nomes[c.modo], c.roll, c.pitch, c.yaw, c.throttle,
                  armado ? "ARMADO" : "");
  }
}
