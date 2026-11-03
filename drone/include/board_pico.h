#pragma once

// ============================================================================
//  Raspberry Pi Pico W  +  2x L298N (mini)
//
//  GP23, GP24, GP25 e GP29 sao usados internamente pelo modulo de WiFi:
//  nao aparecem aqui e nao devem ser usados.
// ============================================================================

#define DRONE_BOARD_NAME  "Raspberry Pi Pico W"

// ---------------------------------------------------------------- I2C
#define PIN_I2C_SDA        4     // I2C0
#define PIN_I2C_SCL        5
#define I2C_CLOCK_HZ       400000

// ---------------------------------------------------------------- MOTORES
// Dois modulos mini L298N, dois motores em cada:
//   Modulo A: OUT1/OUT2 -> M1 (FR)   OUT3/OUT4 -> M2 (RR)
//   Modulo B: OUT1/OUT2 -> M3 (RL)   OUT3/OUT4 -> M4 (FL)
//
// O modulo mini nao expoe ENA/ENB (ficam presos em nivel alto internamente),
// entao o PWM vai na propria entrada IN1/IN3 e a complementar IN2/IN4 fica
// sempre em LOW:
//     IN1=1, IN2=0  -> aciona
//     IN1=0, IN2=0  -> saidas em curto = frenagem
// Isso e PWM em "slow decay". Consome um pouco mais que o modo roda-livre,
// mas a resposta do throttle fica mais linear.
//
// O mesmo esquema serve se o seu modulo for L9110S/HG7881 no lugar do L298N:
// muitos "mini L298N" sao, e o acionamento por duas entradas e identico.
#define MOTOR_DRIVER_L298N 1
#define L298N_HAS_ENABLE   0     // 1 se o seu modulo tiver ENA/ENB de verdade

#define PIN_MOTOR_FR       6     // IN1 modulo A  (recebe PWM)
#define PIN_MOTOR_RR       7     // IN3 modulo A
#define PIN_MOTOR_RL       8     // IN1 modulo B
#define PIN_MOTOR_FL       9     // IN3 modulo B

#define PIN_MOTOR_FR_B     10    // IN2 modulo A  (fixo em LOW)
#define PIN_MOTOR_RR_B     11    // IN4 modulo A
#define PIN_MOTOR_RL_B     12    // IN2 modulo B
#define PIN_MOTOR_FL_B     13    // IN4 modulo B

// O L298N e Darlington bipolar: chaveia devagar. Acima de ~10 kHz ele passa
// mais tempo em transicao do que conduzindo, esquenta e entrega menos forca.
#define MOTOR_PWM_FREQ     5000
#define MOTOR_PWM_BITS     10

// ---------------------------------------------------------------- ULTRASSOM
#define PIN_SONAR_DOWN_TRIG   2
#define PIN_SONAR_DOWN_ECHO   3
#define PIN_SONAR_FRONT_TRIG  0
#define PIN_SONAR_FRONT_ECHO  1

// ---------------------------------------------------------------- IR
#define PIN_IR_LEFT        18
#define PIN_IR_RIGHT       19

// ---------------------------------------------------------------- BATERIA
// GP28 = ADC2. O GP29 (leitura interna do VSYS) e compartilhado com o WiFi
// no Pico W, entao usamos um divisor externo.
#define PIN_VBAT           28
#define VBAT_ADC_FULLSCALE_MV  3300.0f
#define VBAT_ADC_MAX           4095.0f

// ---------------------------------------------------------------- LED
// LED da placa: no Pico W ele fica no chip de WiFi (CYW43).
#define PIN_STATUS_LED            LED_BUILTIN
