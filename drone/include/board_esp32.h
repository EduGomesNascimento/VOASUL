#pragma once

// ============================================================================
//  ESP32 DevKit V1  +  4x MOSFET canal N (SI2302 / AO3400)
// ============================================================================

#define DRONE_BOARD_NAME  "ESP32 DevKit"

// ---------------------------------------------------------------- I2C
#define PIN_I2C_SDA        21
#define PIN_I2C_SCL        22
// Segundo barramento, so do BMI160 (o BMP280 fica no primeiro).
#define PIN_I2C2_SDA       16
#define PIN_I2C2_SCL       18
#define I2C_CLOCK_HZ       400000

// ---------------------------------------------------------------- MOTORES
// MOSFET single-ended: so o pino de PWM, sem pinos de sentido.
#define MOTOR_DRIVER_L298N 0

// Placa de face unica (kicad/): os pinos sairam da ordem fisica dos bracos
// na fileira da frente do ESP32 (girado 180 graus), para nenhuma trilha cruzar.
// Pinos de motor tem de ser SILENCIOSOS no boot. GPIO 1, 3, 5, 14 e 15 soltam
// sinal durante o reset (o 14 e o 15 chegam a emitir PWM), e num pino de motor
// isso e um tranco a cada reinicio -- com helice. O pull-down de 10 k na porta
// nao segura, porque o pino esta acionando ativamente. Os quatro abaixo ficam
// quietos no boot e nao sao pinos de strap (0, 2, 5, 12, 15): 17, 4, 23, 19.
#define PIN_MOTOR_FR       17
#define PIN_MOTOR_RR       4
#define PIN_MOTOR_RL       23
#define PIN_MOTOR_FL       19

#define MOTOR_PWM_FREQ     20000   // fora da faixa audivel
#define MOTOR_PWM_BITS     10

// ---------------------------------------------------------------- ULTRASSOM
#define PIN_SONAR_DOWN_TRIG   26
#define PIN_SONAR_DOWN_ECHO   25   // via divisor 1k/2k (5 V -> 3,3 V)
#define PIN_SONAR_FRONT_TRIG  27
#define PIN_SONAR_FRONT_ECHO  14   // via divisor 1k/2k (5 V -> 3,3 V)

// ---------------------------------------------------------------- IR
#define PIN_IR_LEFT        36
#define PIN_IR_RIGHT       39

// ---------------------------------------------------------------- BATERIA
// Tem de ser ADC1: o ADC2 nao funciona com o WiFi ligado.
#define PIN_VBAT           35
#define VBAT_ADC_FULLSCALE_MV  3300.0f
#define VBAT_ADC_MAX           4095.0f

// ---------------------------------------------------------------- LED
#define PIN_STATUS_LED            2
