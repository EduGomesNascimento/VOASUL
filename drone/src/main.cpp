#include <Arduino.h>
#include <Wire.h>

#include "platform.h"
#include "config.h"
#include "bmi160.h"
#include "bmp280.h"
#include "ahrs.h"
#include "pid.h"
#include "motors.h"
#include "rangefinder.h"
#include "altitude.h"
#include "avoidance.h"
#include "receiver.h"
#include "battery.h"
#include "opticalflow.h"

// ============================================================================
//  Divisao de trabalho entre os dois nucleos
//
//  Nucleo de VOO  : 400 Hz, nada mais roda nele. O periodo tem de ser
//                   constante -- jitter no loop vira oscilacao no drone.
//  Nucleo de REDE : WiFi, HTTP, WebSocket, UDP, telemetria e LED. Aqui um
//                   atraso de 50 ms nao machuca ninguem.
//
//  No RP2040 isso e o par setup()/loop() (nucleo 0, rede) e setup1()/loop1()
//  (nucleo 1, voo). No ESP32, loop() e o voo e a rede vai para uma tarefa
//  fixada no nucleo 0, onde o driver de WiFi ja mora.
//
//  No Pico W o LED da placa fica pendurado no chip de WiFi, entao ele so pode
//  ser piscado pelo nucleo de rede. Por isso o blink vive em commsStep().
// ============================================================================

static BMI160            imu;
static BMP280            baro;
static AHRS              ahrs;
static Motors            motors;
static Rangefinders      range;
static AltitudeEstimator altEst;
static Avoidance         avoid;
static Receiver          rx;
static Battery           batt;
static PMW3901           flow;       // opcional: ausente = voa sem ele
static FlowEstimator     flowEst;
static FlowHold          flowHold;

static PID pidRateRoll, pidRatePitch, pidRateYaw;
static PID pidAltVz;

enum State : uint8_t { ST_BOOT, ST_CALIB, ST_DISARMED, ST_ARMED, ST_LANDING, ST_FATAL };
static volatile State state = ST_BOOT;
static const char *volatile stateMsg = "iniciando";

static plat_lock_t   shareMux;
static ControlInput  sharedCmd;      // escrito pela rede, lido pelo voo
static Telemetry     sharedTele;     // escrito pelo voo, lido pela rede
static volatile bool teleReady = false;

static bool  baroOk = false;
static float hoverThrottle = 0.50f;
static float altTarget = 0;
static bool  altHoldPrev = false;
static uint32_t landStartMs = 0;
static uint32_t tiltBadMs = 0;
static volatile uint16_t loopHz = 0;

// ---------------------------------------------------------------- utilidades

static void setState(State s, const char *msg) {
  state = s;
  stateMsg = msg;
  Serial.printf("[FC] %s\n", msg);
}

static void blink() {
  static uint32_t t = 0;
  static bool on = false;
  uint16_t period;
  switch (state) {
    case ST_CALIB:    period = 80;   break;   // piscando rapido: nao encoste
    case ST_ARMED:    period = 1000; break;
    case ST_LANDING:  period = 150;  break;
    case ST_FATAL:    period = 40;   break;
    default:          period = 400;  break;
  }
  if (millis() - t >= period) {
    t = millis();
    on = !on;
    platLedWrite(on);
  }
}

// ---------------------------------------------------------------- nucleo de rede

static void commsInit() {
  platLedBegin();
  rx.begin();
}

static void commsStep() {
  rx.poll();
  blink();

  platLock(shareMux);
  sharedCmd = rx.cmd;
  platUnlock(shareMux);

  if (teleReady) {
    Telemetry t;
    platLock(shareMux);
    t = sharedTele;
    teleReady = false;
    platUnlock(shareMux);
    t.status = stateMsg;
    rx.sendTelemetry(t);
  }
}

// ---------------------------------------------------------------- nucleo de voo

static void flightInit() {
  // Os motores vao a zero antes de qualquer outra coisa: se a placa resetar com
  // o drone armado, os pinos flutuam e as helices podem girar.
  motors.begin();
  motors.setEnabled(false);

  batt.begin();
  Serial.printf("[BAT] %.2f V\n", batt.voltage);

  platI2CBegin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_CLOCK_HZ);
#ifdef PIN_I2C2_SDA
  // Placa de face unica: o BMI160 tem barramento proprio (Wire1), assim as
  // trilhas dos dois sensores embaixo do ESP32 nao se cruzam.
  imu.setBus(platI2C2Begin(PIN_I2C2_SDA, PIN_I2C2_SCL, I2C_CLOCK_HZ));
#endif

  if (!imu.begin(BMI160_I2C_ADDR)) {
    setState(ST_FATAL, "BMI160 nao respondeu - verifique I2C e o endereco");
    return;
  }

  baroOk = baro.begin(BMP280_I2C_ADDR);
  if (!baroOk) {
    // Da para voar so com o ultrassom abaixo de 3 m; o que se perde e o
    // alt-hold acima disso. Nao e motivo para abortar.
    Serial.println("[BMP280] ausente - alt-hold limitado ao alcance do ultrassom");
  }

  range.begin();

  // Fluxo optico (opcional). Ausente nao e erro: o drone voa igual, so sem o
  // freio de deriva. O resultado aparece no Serial e na telemetria.
  if (flow.begin()) {
    Serial.println("[PMW3901] presente - freio de deriva ligado");
  } else {
    Serial.printf("[PMW3901] ausente (id 0x%02X/0x%02X) - voando sem fluxo optico\n",
                  flow.chipId, flow.chipIdInv);
  }

  pidRateRoll.init(PID_RATE_ROLL_KP,  PID_RATE_ROLL_KI,  PID_RATE_ROLL_KD,
                   PID_I_LIMIT, PID_OUT_LIMIT, PID_D_LPF_HZ);
  pidRatePitch.init(PID_RATE_PITCH_KP, PID_RATE_PITCH_KI, PID_RATE_PITCH_KD,
                    PID_I_LIMIT, PID_OUT_LIMIT, PID_D_LPF_HZ);
  pidRateYaw.init(PID_RATE_YAW_KP,   PID_RATE_YAW_KI,   PID_RATE_YAW_KD,
                  PID_I_LIMIT, PID_OUT_LIMIT, PID_D_LPF_HZ);
  pidAltVz.init(PID_ALT_VZ_KP, PID_ALT_VZ_KI, PID_ALT_VZ_KD,
                ALT_THROTTLE_SPAN, ALT_THROTTLE_SPAN, PID_ALT_D_LPF_HZ);

  setState(ST_CALIB, "calibrando - nao encoste no drone");
  delay(500);
  if (imu.calibrate(800)) {
    ahrs.reset();
    altEst.reset();
    setState(ST_DISARMED, "pronto - desarmado");
  } else {
    setState(ST_FATAL, "falha ao calibrar o giroscopio");
  }
}

static void resetControllers();

static void runControl(const ControlInput &cmd, float dt) {
  // ---- partida suave ----
  // Enquanto os motores sobem de 0 ate o idle, o drone esta no chao e as
  // saidas estao presas sob o teto da rampa. Rodar o PID aqui so acumularia
  // integral contra um limite que ele nao tem como vencer, e essa integral
  // sairia como tranco no instante em que a rampa soltasse. Entao: nada de
  // controle, so a rampa.
  if (motors.spooling()) {
    resetControllers();
    motors.mix(0.0f, 0.0f, 0.0f, 0.0f, dt);
    return;
  }

  // ---- setpoints de atitude vindos do piloto ----
  float rollSp  = cmd.roll  * MAX_ANGLE_DEG;
  float pitchSp = cmd.pitch * MAX_ANGLE_DEG;
  float yawRateSp = cmd.yaw * MAX_YAW_RATE_DPS;

  const bool landing = (state == ST_LANDING);
  if (landing) { rollSp = 0; pitchSp = 0; yawRateSp = 0; }

  // ---- fluxo optico: freia a deriva com o manche solto ----
  // So corrige quando o piloto nao esta pedindo movimento e o desvio de
  // obstaculos nao esta empurrando (senao os dois brigariam).
  {
    const bool sticksFree = fabsf(cmd.roll) < 0.08f && fabsf(cmd.pitch) < 0.08f;
    const bool avoidQuiet = fabsf(avoid.frontBias) < 0.5f && fabsf(avoid.sideBias) < 0.5f;
    flowHold.update(flowEst, (sticksFree || landing) && avoidQuiet, dt);
    rollSp  += flowHold.rollBias;
    pitchSp += flowHold.pitchBias;
  }

  // ---- desvio de obstaculos ----
  avoid.setEnabled(cmd.avoid && !landing);
  avoid.apply(range, rollSp, pitchSp, dt);

  // ---- malha externa: angulo -> velocidade angular ----
  const float rollRateSp  = constrain((rollSp  - ahrs.roll)  * PID_ANGLE_KP,
                                      -PID_ANGLE_MAX_DPS, PID_ANGLE_MAX_DPS);
  const float pitchRateSp = constrain((pitchSp - ahrs.pitch) * PID_ANGLE_KP,
                                      -PID_ANGLE_MAX_DPS, PID_ANGLE_MAX_DPS);

  // ---- malha interna: velocidade angular -> motores ----
  // O AHRS ja entrega as taxas na mesma convencao dos angulos (ver ahrs.h);
  // nao ha sinal para inverter aqui.
  const float uRoll  = pidRateRoll.update(rollRateSp,   ahrs.rollRate,  dt);
  const float uPitch = pidRatePitch.update(pitchRateSp, ahrs.pitchRate, dt);
  const float uYaw   = pidRateYaw.update(yawRateSp,     ahrs.yawRate,   dt);

  // ---- throttle ----
  float throttle;

  if (landing) {
    // Descida controlada: com sonar, desce a 0,4 m/s; sem sonar, rampa cega.
    if (range.groundValid || altEst.usingSonar) {
      throttle = hoverThrottle + pidAltVz.update(-0.40f, altEst.velocity, dt);
    } else {
      const float elapsed = (millis() - landStartMs) / 1000.0f;
      throttle = hoverThrottle * constrain(1.0f - elapsed / 4.0f, 0.0f, 1.0f);
    }
  } else if (cmd.altHold) {
    if (!altHoldPrev) {                 // acabou de ligar: guarda a altura atual
      altTarget = altEst.altitude;
      pidAltVz.reset();
    }

    // O manche de throttle vira comando de subida/descida. A faixa morta ao
    // redor do centro e o que permite soltar o manche e manter a altura.
    const float stick = cmd.throttle - 0.5f;
    float vzSp;
    if (fabsf(stick) < 0.08f) {
      vzSp = constrain((altTarget - altEst.altitude) * PID_ALT_KP,
                       -ALT_HOLD_MAX_VZ, ALT_HOLD_MAX_VZ);
    } else {
      vzSp = stick * 2.0f * ALT_HOLD_MAX_VZ;
      altTarget = altEst.altitude;      // enquanto o piloto comanda, segue ele
    }

    throttle = hoverThrottle + pidAltVz.update(vzSp, altEst.velocity, dt);

    // Aprende o throttle de pairar: com o drone estavel, o que estiver saindo
    // agora e o valor de equilibrio. Isso compensa a bateria descarregando.
    if (fabsf(altEst.velocity) < 0.15f && fabsf(stick) < 0.08f) {
      hoverThrottle += (throttle - hoverThrottle) * 0.2f * dt;
      hoverThrottle = constrain(hoverThrottle, 0.20f, 0.85f);
    }
  } else {
    throttle = cmd.throttle * MOTOR_MAX;
  }

  // Compensacao de inclinacao: inclinado, so a componente vertical do empuxo
  // sustenta o drone, entao ele afunda se o throttle nao subir junto.
  throttle /= ahrs.tiltCos;
  throttle = constrain(throttle, 0.0f, MOTOR_MAX);

  motors.mix(throttle, uRoll, uPitch, uYaw, dt);
  altHoldPrev = cmd.altHold && !landing;
}

static void resetControllers() {
  pidRateRoll.reset();
  pidRatePitch.reset();
  pidRateYaw.reset();
  pidAltVz.reset();
  flowHold.reset();
  altHoldPrev = false;
}

static void flightStep() {
  static uint32_t nextUs = micros();
  static uint32_t prevUs = micros();
  static uint32_t hzCount = 0, hzMs = 0;
  static uint32_t baroMs = 0;

  // --- tranca o periodo do loop ---
  nextUs += LOOP_PERIOD_US;
  const int32_t wait = (int32_t)(nextUs - micros());
  if (wait > 0) platYieldFor((uint32_t)wait);
  while ((int32_t)(nextUs - micros()) > 0) { /* espera fina */ }
  if ((int32_t)(micros() - nextUs) > (int32_t)LOOP_PERIOD_US * 4) {
    nextUs = micros();   // perdeu o passo: reancora em vez de correr atras
  }

  const uint32_t now = micros();
  float dt = (now - prevUs) * 1e-6f;
  prevUs = now;
  if (dt <= 0 || dt > 0.05f) dt = 1.0f / LOOP_HZ;

  hzCount++;
  if (millis() - hzMs >= 1000) { loopHz = hzCount; hzCount = 0; hzMs = millis(); }

  if (state == ST_FATAL) { motors.setEnabled(false); return; }

  // --- sensores ---
  if (!imu.read()) {
    // Uma leitura perdida acontece; perder o IMU em voo nao tem recuperacao.
    static uint8_t fails = 0;
    if (++fails > 20) {
      motors.setEnabled(false);
      setState(ST_FATAL, "IMU parou de responder");
    }
    return;
  }

  ahrs.update(imu.gx, imu.gy, imu.gz, imu.ax, imu.ay, imu.az, dt);

  const float tiltDeg = fmaxf(fabsf(ahrs.roll), fabsf(ahrs.pitch));
  range.update(baro.temperature, ahrs.tiltCos, tiltDeg);

  if (baroOk && millis() - baroMs >= 40) { baroMs = millis(); baro.read(); }

  // Fluxo optico a 100 Hz (a cada 4 passos). Sem o modulo nao custa nada.
  static uint8_t flowDiv = 0;
  static uint32_t flowUs = 0;
  if (flow.present && ++flowDiv >= 4) {
    flowDiv = 0;
    const uint32_t t = micros();
    const float fdt = flowUs ? (t - flowUs) * 1e-6f : 0.0f;
    flowUs = t;
    FlowFrame fr;
    if (flow.read(fr)) {
      flowEst.update(fr, fdt, ahrs.rollRate, ahrs.pitchRate,
                     range.groundDistance, range.groundValid);
    } else {
      flowEst.reset();
      Serial.println("[PMW3901] parou de responder - seguindo sem fluxo optico");
    }
  }

  altEst.update(range.groundDistance, range.groundValid,
                baroOk ? baro.altitude : 0.0f, ahrs.earthAccZ, dt);

  batt.update();

  // --- comando do piloto ---
  ControlInput cmd;
  platLock(shareMux);
  cmd = sharedCmd;
  platUnlock(shareMux);

  const bool link = (cmd.lastPacketMs != 0) &&
                    (millis() - cmd.lastPacketMs) < FAILSAFE_TIMEOUT_MS;

  // --- maquina de estados ---
  switch (state) {
    case ST_DISARMED:
      motors.setEnabled(false);
      resetControllers();
      if (cmd.arm && link) {
        if (cmd.throttle > 0.05f) {
          stateMsg = "baixe o throttle antes de armar";
        } else if (tiltDeg > 25.0f) {
          stateMsg = "coloque o drone nivelado para armar";
        } else if (batt.critical) {
          stateMsg = "bateria muito fraca para armar";
        } else {
          altEst.reset();
          if (baroOk) baro.zero();
          hoverThrottle = 0.50f;
          motors.setEnabled(true);
          motors.armStart();
          setState(ST_ARMED, "subindo os motores...");
        }
      }
      break;

    case ST_ARMED:
      if (!cmd.arm) {
        motors.setEnabled(false);
        setState(ST_DISARMED, "desarmado pelo piloto");
      } else if (!link) {
        landStartMs = millis();
        setState(ST_LANDING, "sinal perdido - pousando sozinho");
      } else if (batt.critical) {
        landStartMs = millis();
        setState(ST_LANDING, "bateria critica - pousando sozinho");
      } else if (tiltDeg > 70.0f) {
        // Capotou. Manter os motores girando so quebra helice e queima motor.
        if (tiltBadMs == 0) tiltBadMs = millis();
        if (millis() - tiltBadMs > 400) {
          motors.setEnabled(false);
          setState(ST_DISARMED, "inclinacao excessiva - motores cortados");
        }
      } else {
        tiltBadMs = 0;
        // A rampa de partida acabou: avisa o piloto que agora responde.
        static bool spoolMsgDone = false;
        if (motors.spooling()) {
          spoolMsgDone = false;
        } else if (!spoolMsgDone) {
          spoolMsgDone = true;
          stateMsg = "ARMADO";
        }
      }
      break;

    case ST_LANDING:
      // Sai do pouso automatico se o piloto voltar e desarmar.
      if (link && !cmd.arm) {
        motors.setEnabled(false);
        setState(ST_DISARMED, "desarmado pelo piloto");
        break;
      }
      if ((range.groundValid && range.groundDistance < 0.12f) ||
          (millis() - landStartMs > 8000)) {
        motors.setEnabled(false);
        setState(ST_DISARMED, "pousado - desarmado");
      }
      break;

    default:
      break;
  }

  // --- controle ---
  if (state == ST_ARMED || state == ST_LANDING) runControl(cmd, dt);
  else                                          motors.stop();

  // --- telemetria para o nucleo de rede ---
  static uint8_t teleDiv = 0;
  if (++teleDiv >= 20) {          // 20 Hz
    teleDiv = 0;
    platLock(shareMux);
    sharedTele.roll = ahrs.roll;
    sharedTele.pitch = ahrs.pitch;
    sharedTele.yaw = ahrs.yaw;
    sharedTele.altitude = altEst.altitude;
    sharedTele.verticalSpeed = altEst.velocity;
    sharedTele.ground = range.groundDistance;
    sharedTele.front = range.frontDistance;
    sharedTele.irL = range.irLeft;
    sharedTele.irR = range.irRight;
    sharedTele.vbat = batt.voltage;
    sharedTele.armed = (state == ST_ARMED || state == ST_LANDING);
    sharedTele.altHold = cmd.altHold;
    sharedTele.avoid = avoid.enabled();
    sharedTele.usingSonar = altEst.usingSonar;
    for (uint8_t i = 0; i < 4; i++) sharedTele.m[i] = motors.out[i];
    sharedTele.loopHz = loopHz;
    sharedTele.flow = !flow.present ? FLOW_ABSENT
                    : flowHold.holding ? FLOW_HOLDING
                    : flowEst.valid ? FLOW_READING : FLOW_IDLE;
    sharedTele.flowVf = flowEst.vFwd;
    sharedTele.flowVr = flowEst.vRight;
    sharedTele.flowSq = flowEst.squal;
    teleReady = true;
    platUnlock(shareMux);
  }
}

// ============================================================================
//  Pontos de entrada
// ============================================================================

#if PLATFORM_PICO

// Nucleo 0: rede
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== Controladora de voo (" DRONE_BOARD_NAME ") ===");
  platLockInit(shareMux);
  commsInit();
}
void loop() {
  commsStep();
}

// Nucleo 1: voo
void setup1() {
  // Espera o nucleo 0 subir o Serial e inicializar o mutex antes de tocar em
  // qualquer estado compartilhado.
  delay(800);
  flightInit();
}
void loop1() {
  flightStep();
}

#elif PLATFORM_ESP32

static void commsTask(void *) {
  commsInit();
  for (;;) {
    commsStep();
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== Controladora de voo (" DRONE_BOARD_NAME ") ===");
  platLockInit(shareMux);
  xTaskCreatePinnedToCore(commsTask, "comms", 8192, nullptr, 1, nullptr, 0);
  flightInit();
}
void loop() {
  flightStep();
}

#else   // host: existe apenas para a checagem de sintaxe

void setup() { platLockInit(shareMux); commsInit(); flightInit(); }
void loop()  { commsStep(); flightStep(); }

#endif
