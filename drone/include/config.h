#pragma once
#include <Arduino.h>
#include "platform.h"

// ============================================================================
//  Ajustes de voo, comuns as duas placas.
//  Pinos e driver de motor ficam no arquivo de placa incluido abaixo.
// ============================================================================

#if PLATFORM_PICO
  #include "board_pico.h"
#elif PLATFORM_ESP32
  #include "board_esp32.h"
#else
  #include "board_host.h"
#endif

/* Layout quad X visto de cima, nariz para o topo da folha:
 *
 *      M4 (FL, horario)        M1 (FR, anti-horario)
 *                   \          /
 *                    \        /
 *                     [placa]            nariz ^
 *                    /        \
 *                   /          \
 *      M3 (RL, anti-horario)   M2 (RR, horario)
 */

// ---------------------------------------------------------------- SENSORES I2C
#define BMI160_I2C_ADDR    0x69   // 0x68 se SDO ligado ao GND
#define BMP280_I2C_ADDR    0x76   // 0x77 se SDO ligado ao VCC

// ---------------------------------------------------------------- MOTORES
#define MOTOR_IDLE         0.08f  // throttle minimo com o drone armado
#define MOTOR_MAX          0.95f  // teto, deixa margem para o PID corrigir

// --- partida suave ---
// Motor parado e rotor travado: a unica coisa que limita a corrente e a
// resistencia do enrolamento, ~0,7 ohm num 1020. Sao ~5 A por motor, ~20 A nos
// quatro, e baixar o duty NAO resolve -- o duty limita a media, e quem derruba
// o VSYS e o PICO de cada pulso. O rotor so deixa de travar quando ganha
// rotacao e gera contra-fem. Dai a rampa: da tempo de cada motor pegar
// rotacao, e a corrente cai sozinha.
#define MOTOR_SPOOL_MS       600  // 0 -> MOTOR_IDLE ao armar
#define MOTOR_SPOOL_STAGGER  60   // defasagem entre os 4 (ms), espalha o pico

// Teto de subida do throttle COMUM, em fracao por segundo. 4,0 = do zero ao
// maximo em 250 ms. Vale so para o valor medio dos quatro motores; o
// diferencial que o PID produz passa intacto, entao a malha de atitude nao
// ganha atraso nenhum com isso. Descida nao e limitada -- cortar potencia
// depressa e sempre seguro.
#define MOTOR_SLEW_UP        4.0f

// ---------------------------------------------------------------- BATERIA
#define VBAT_DIV_R1        10000.0f  // VBAT --[R1]--+--[R2]-- GND, meio no ADC
#define VBAT_DIV_R2        10000.0f
#define VBAT_ADC_SCALE     1.0f      // ajuste fino: tensao_real / tensao_lida
#define VBAT_WARN_V        3.55f
#define VBAT_CRITICAL_V    3.35f

// ---------------------------------------------------------------- ULTRASSOM
#define SONAR_PERIOD_MS       25    // disparos alternados -> 20 Hz por sensor
#define SONAR_TIMEOUT_US      25000 // ~4 m ida e volta
#define SONAR_MIN_M           0.03f
#define SONAR_MAX_M           3.50f
#define SONAR_MAX_TILT_DEG    30.0f

// ---------------------------------------------------------------- IR
// Modulos FC-51: saida digital, LOW = obstaculo. Alimentar em 3,3 V.
#define IR_ACTIVE_LOW      1

// ---------------------------------------------------------------- LOOP
#define LOOP_HZ            400
#define LOOP_PERIOD_US     (1000000UL / LOOP_HZ)

// ---------------------------------------------------------------- RADIO
#define WIFI_AP_SSID       "DRONE-PICO"
#define WIFI_AP_PASS       "voar1234"     // minimo 8 caracteres

// So 802.11b no ESP32. O pacote de controle tem ~20 bytes a 50 Hz, entao a
// taxa nao importa -- e taxa baixa compra sensibilidade: o receptor do ESP32
// ouve -98 dBm a 1 Mbit/s (11b) contra -93 dBm a 6 Mbit/s (11g/n). Sao 5 dB a
// mais no sentido celular -> drone, que e o sentido dos comandos.
// Todo aparelho de WiFi 2,4 GHz fala 11b; se mesmo assim o celular nao achar a
// rede, ponha 0 aqui.
#define WIFI_ONLY_11B      1
#define HTTP_PORT          80
#define WS_PORT            81
#define UDP_PORT           4210
#define FAILSAFE_TIMEOUT_MS 400           // sem comando -> pouso automatico
#define WIFI_CHANNEL       1              // canal do AP (fixo)

// ---------------------------------------------------------------- COMANDOS
#define MAX_ANGLE_DEG      25.0f
#define MAX_YAW_RATE_DPS   180.0f

// ---------------------------------------------------------------- PID
// Erro em graus/s -> saida em fracao do throttle (0..1).
// Comece com metade destes valores no primeiro voo amarrado.
#define PID_RATE_ROLL_KP   0.00180f
#define PID_RATE_ROLL_KI   0.00600f
#define PID_RATE_ROLL_KD   0.000040f

#define PID_RATE_PITCH_KP  0.00180f
#define PID_RATE_PITCH_KI  0.00600f
#define PID_RATE_PITCH_KD  0.000040f

#define PID_RATE_YAW_KP    0.00400f
#define PID_RATE_YAW_KI    0.01000f
#define PID_RATE_YAW_KD    0.0f

#define PID_I_LIMIT        0.20f
#define PID_OUT_LIMIT      0.40f

// Corte do filtro passa-baixa do termo D, em Hz. Derivar amplifica ruido, e a
// vibracao das helices chega ao giroscopio em centenas de Hz. Sem este filtro
// o termo D vira comando de motor e o drone "chia" parado no ar.
// Helice maior vibra mais: com 75 mm ou mais, va para 60 Hz. Se depois de
// baixar o corte ainda oscilar so com throttle alto, o problema e helice
// desbalanceada, e nao ganho de PID.
#define PID_D_LPF_HZ       80.0f
#define PID_ALT_D_LPF_HZ   15.0f   // a velocidade vertical ja vem suave do estimador

// Malha externa de angulo: erro em graus -> setpoint de graus/s
#define PID_ANGLE_KP       4.5f
#define PID_ANGLE_MAX_DPS  250.0f

// Altitude: erro em metros -> velocidade vertical desejada (m/s)
#define PID_ALT_KP         1.60f
#define PID_ALT_VZ_KP      0.25f
#define PID_ALT_VZ_KI      0.12f
#define PID_ALT_VZ_KD      0.010f
#define ALT_HOLD_MAX_VZ    0.8f
#define ALT_THROTTLE_SPAN  0.35f

// ---------------------------------------------------------------- AHRS
#define AHRS_MAHONY_KP     1.5f
#define AHRS_MAHONY_KI     0.005f

// ---------------------------------------------------------------- OBSTACULOS
#define AVOID_FRONT_STOP_M     0.35f  // recuo maximo
#define AVOID_FRONT_SLOW_M     0.90f  // onde o recuo comeca
#define AVOID_MAX_TILT_DEG     12.0f
#define AVOID_IR_TILT_DEG      8.0f

// ---------------------------------------------------------------- FLUXO OPTICO (opcional)
// PMW3901 no J4. Sem o modulo nada disto roda (o firmware detecta no boot).
// O fluxo so tem escala (m/s) com o sonar de baixo lendo a altura.
#define FLOW_MIN_HEIGHT_M      0.08f  // abaixo disso o PMW3901 fica fora de foco
#define FLOW_MAX_HEIGHT_M      2.50f
#define FLOW_MIN_SQUAL         20     // qualidade minima da imagem (chao liso demais = 0)
#define FLOW_OUTLIER_COUNTS    120    // salto maior que isto num quadro e erro de leitura
#define FLOW_RAD_PER_COUNT     0.0205f // 42 graus de campo / 35 pixels (mesmo valor da Bitcraze)
#define FLOW_LPF_HZ            6.0f

// Montagem do modulo (lente para baixo). Confira com o teste do PLANO_DE_MONTAGEM:
// empurrando o drone para a FRENTE com a mao, "vf" tem de ficar positivo;
// para a DIREITA, "vr" positivo. Se nao, troque o sinal aqui.
// Modulo girado 90 graus: FLOW_SWAP_XY 1.
#define FLOW_SWAP_XY           0
#define FLOW_SIGN_FWD         -1      // frente = -dy (como no Crazyflie)
#define FLOW_SIGN_RIGHT        1      // direita = +dx

// Freio da deriva: inclinacao contra a velocidade lida.
#define FLOW_KP_DEG_PER_MPS    8.0f   // graus por m/s
#define FLOW_KI_DEG_PER_M      3.0f   // graus por m de deriva acumulada
#define FLOW_I_LIMIT_DEG       4.0f
#define FLOW_MAX_TILT_DEG      8.0f   // teto da correcao (o piloto sempre manda mais)
#define FLOW_RAMP_DPS          60.0f  // quao depressa a correcao entra e sai
