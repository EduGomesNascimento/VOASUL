#pragma once

// Placa ficticia usada apenas pelos testes de logica que rodam no PC.
// Os numeros nao correspondem a hardware nenhum.

#define DRONE_BOARD_NAME  "host (testes)"

#define PIN_I2C_SDA        0
#define PIN_I2C_SCL        1
#define I2C_CLOCK_HZ       400000

#define MOTOR_DRIVER_L298N 1     // exercita tambem o caminho dos pinos da ponte
#define L298N_HAS_ENABLE   0

#define PIN_MOTOR_FR       6
#define PIN_MOTOR_RR       7
#define PIN_MOTOR_RL       8
#define PIN_MOTOR_FL       9

#define PIN_MOTOR_FR_B     10
#define PIN_MOTOR_RR_B     11
#define PIN_MOTOR_RL_B     12
#define PIN_MOTOR_FL_B     13

#define MOTOR_PWM_FREQ     5000
#define MOTOR_PWM_BITS     10

#define PIN_SONAR_DOWN_TRIG   2
#define PIN_SONAR_DOWN_ECHO   3
#define PIN_SONAR_FRONT_TRIG  20
#define PIN_SONAR_FRONT_ECHO  21

#define PIN_IR_LEFT        18
#define PIN_IR_RIGHT       19

#define PIN_VBAT           28
#define VBAT_ADC_FULLSCALE_MV  3300.0f
#define VBAT_ADC_MAX           4095.0f

#define PIN_STATUS_LED            25
