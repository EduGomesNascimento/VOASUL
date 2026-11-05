"""
Drone quadricoptero -- definicao UNICA do circuito (pecas, redes, posicoes).

Daqui saem o esquema (.kicad_sch), a placa (.kicad_pcb) e os modelos 3D.
Mudou alguma coisa? Mude AQUI e rode `python3 gerar.py tudo`.

PLACA DE FACE UNICA: todo o cobre fica EMBAIXO (B.Cu). Onde duas trilhas
precisariam se cruzar entra um JUMPER (fio por cima, do lado dos componentes).

Coordenadas: mm, origem no CENTRO do disco, X para a direita, Y para a FRENTE
(o lado da seta do frame). Angulo em graus, anti-horario.
"""
import math

DISCO_D = 97.0            # placa medida: 97,08 mm (rebaixo do frame: 97,9)
RAIO_LARG = 8.0           # raios do frame embaixo da placa (diagonais 45/135)

# ---------------------------------------------------------------- larguras
# placa caseira (transferencia termica): trilha grossa e folga grande, para o
# toner amassado nao encostar e um defeitinho nao cortar a trilha.
FOLGA = 0.8               # entre cobres de redes diferentes
FOLGA_BORDA = 0.8
LARG_PESCOCO = 0.8        # trilha so afina encostando em pino apertado (<= 3 mm dele)
CLASSES = {
    #  nome        largura  redes
    'POTENCIA': (2.5, ['VBAT', 'DRENO_FR', 'DRENO_RR', 'DRENO_RL', 'DRENO_FL']),
    'ALIM':     (1.5, ['GND', '+5V', '+3V3']),
    'Default':  (1.2, []),
}
R_ANEL = 45.0             # anel de VBAT por dentro da borda (2,5 mm)
JUMPER_FURO, JUMPER_ILHA = 0.9, 2.4

# ---------------------------------------------------------------- ESP32
# ESP32 DevKitC V4 (38 pinos, WROOM-32 ou 32U). Girado 180 graus:
# antena p/ a ESQUERDA (-X), USB p/ a DIREITA (+X).
# Fileira de TRAS (J2):  3V3 EN VP VN 34 35 32 33 25 26 27 14 12 GND 13 SD2 SD3 CMD 5V  (esq -> dir)
# Fileira da FRENTE (J3): GND 23 22 TX RX 21 GND 19 18 5 17 16 4 0 2 15 SD1 SD0 CLK      (esq -> dir)
ESP_J2 = ['3V3', 'EN', 'VP', 'VN', 'IO34', 'IO35', 'IO32', 'IO33', 'IO25', 'IO26',
          'IO27', 'IO14', 'IO12', 'GND', 'IO13', 'SD2', 'SD3', 'CMD', '5V']
ESP_J3 = ['GND', 'IO23', 'IO22', 'TX', 'RX', 'IO21', 'GND', 'IO19', 'IO18', 'IO5',
          'IO17', 'IO16', 'IO4', 'IO0', 'IO2', 'IO15', 'SD1', 'SD0', 'CLK']
ESP_ROT = 180

# Pinos escolhidos para a placa sair de face unica (sem cruzamento):
#  - motores na fileira da FRENTE, na mesma ordem dos bracos (RL FL FR RR),
#    todos pinos quietos no boot (nada de 0/2/5/12/15);
#  - sonares, IR e bateria na fileira de TRAS, na ordem dos conectores.
# >>> include/board_esp32.h tem de bater com esta tabela <<<
ESP_REDES = {
    '3V3': '+3V3', '5V': '+5V', 'GND': 'GND',
    'IO23': 'M_RL', 'IO19': 'M_FL', 'IO17': 'M_FR', 'IO4': 'M_RR',
    'IO22': 'SCL', 'IO21': 'SDA',          # I2C 1: BMP280
    'IO18': 'SCL2', 'IO16': 'SDA2',        # I2C 2: BMI160 (barramento proprio = sem cruzamento)
    'VP': 'IR_E',                # IO36 (so entrada)
    'VN': 'IR_D',                # IO39 (so entrada)
    'IO35': 'VBAT_ADC',          # ADC1 (o ADC2 nao funciona com Wi-Fi)
    # (IO34 fica livre: o J3 esta logo abaixo dele)
    # fluxo optico PMW3901 (opcional, SPI): 4 pinos vizinhos -> J4 sem cruzamento
    'IO32': 'FLOW_MISO', 'IO33': 'FLOW_SCK', 'IO25': 'FLOW_MOSI', 'IO26': 'FLOW_CS',
    # sonares, dos dois lados do GND do ESP32 (pino 14), que serve o 2k do ECHO da frente.
    # IO12 e pino de strap (tem de estar em 0 no boot): como ECHO ele fica preso ao
    # GND pelo 2k do divisor, entao o boot e sempre certo.
    'IO27': 'ECHO_B', 'IO14': 'TRIG_B', 'IO12': 'ECHO_F', 'IO13': 'TRIG_F',
}
GPIO = {  # para o board_esp32.h
    'PIN_MOTOR_FR': 17, 'PIN_MOTOR_RR': 4, 'PIN_MOTOR_RL': 23, 'PIN_MOTOR_FL': 19,
    'PIN_I2C_SDA': 21, 'PIN_I2C_SCL': 22, 'PIN_I2C2_SDA': 16, 'PIN_I2C2_SCL': 18,
    'PIN_SONAR_DOWN_TRIG': 14, 'PIN_SONAR_DOWN_ECHO': 27,
    'PIN_SONAR_FRONT_TRIG': 13, 'PIN_SONAR_FRONT_ECHO': 12,
    'PIN_IR_LEFT': 36, 'PIN_IR_RIGHT': 39, 'PIN_VBAT': 35, 'PIN_STATUS_LED': 2,
    'PIN_FLOW_MISO': 32, 'PIN_FLOW_SCK': 33, 'PIN_FLOW_MOSI': 25, 'PIN_FLOW_CS': 26,
}


def esp_pinos():
    """numero do pino -> (nome, rede)"""
    return {str(i + 1): (n, ESP_REDES.get(n)) for i, n in enumerate(ESP_J2 + ESP_J3)}


# ---------------------------------------------------------------- pecas
PECAS = []


def peca(ref, valor, tipo, x, y, rot=0, lado='F', pinos=None, nota='', pino_fora=None):
    """pino_fora: o giro da peca e escolhido para este pino ficar o mais longe
    possivel do centro (VBAT para o anel, dreno para o motor)"""
    PECAS.append(dict(ref=ref, valor=valor, tipo=tipo, x=round(x, 3), y=round(y, 3), rot=rot,
                      lado=lado, pinos=pinos or {}, nota=nota, pino_fora=pino_fora))


def polar(r, ang, t=0.0):
    """ponto a raio r no angulo ang, deslocado t na tangente (anti-horario)"""
    a = math.radians(ang)
    return (r * math.cos(a) - t * math.sin(a), r * math.sin(a) + t * math.cos(a))


# ESP32 no centro
peca('U1', 'ESP32 DevKitC 38p', 'ESP32_DEVKIT', 0, 0, rot=ESP_ROT,
     pinos={k: v[1] for k, v in esp_pinos().items() if v[1]})

# sensores de bordo EMBAIXO do ESP32 (entre as barras femea, 8,5 mm de vao),
# soldados direto com barra macho (perfil baixo)
peca('U4', 'GY-BMP280', 'GY_BMP280', -12.5, -3.0,
     pinos={'1': '+3V3', '2': 'GND', '3': 'SCL', '4': 'SDA', '5': '+3V3', '6': 'GND'},
     nota='VCC GND SCL SDA CSB SDO | CSB no 3V3 (I2C), SDO no GND -> 0x76')
peca('U3', 'GY-BMI160', 'GY_BMI160', 7.5, -3.0,
     pinos={'1': None, '2': '+3V3', '3': 'GND', '4': 'SCL2', '5': 'SDA2', '6': '+3V3', '7': '+3V3'},
     nota='VIN 3V3 GND SCL SDA CS SAO | VIN solto; CS e SAO no 3V3 -> 0x69')

# ---- alimentacao
# bateria do lado ESQUERDO: ilha + no anel de VBAT, ilha - para dentro
peca('J1', 'LiPo 1S', 'BATERIA', -41.0, 0.0, rot=0, pinos={'1': 'VBAT', '2': 'GND'},
     nota='rabicho Molex da bateria: + na ilha quadrada (de fora)')
peca('C1', '1000uF 10V', 'CP_D8', -41.2, -10.5, rot=0, pinos={'1': 'VBAT', '2': 'GND'})
# step-up na FRENTE, entrada a esquerda, saida a direita
peca('U2', 'MT3608 5,0V', 'MT3608', 0.0, 31.0,
     pinos={'1': 'VBAT', '2': 'GND', '3': '+5V', '4': 'GND'},
     nota='IN+ IN- OUT+ OUT- | ajuste 5,0 V ANTES de encaixar o ESP32')
peca('C2', '470uF 10V', 'CP_D6', 31.5, -9.5, rot=90, pinos={'1': '+5V', '2': 'GND'})

# ---- sensores externos (tras): conectores na ordem dos pinos do ESP32
# de cima (visto de cima), da esquerda p/ a direita: J3 (IR) | divisor da bateria |
# J4 (fluxo optico) | sonar (resistores + J2)
peca('J3', 'IR (FC-51 x2)', 'CONN4', -20.5, -17.0, rot=90,
     pinos={'1': '+3V3', '2': 'IR_E', '3': 'IR_D', '4': 'GND'},
     nota='1 VCC(3V3) 2 OUT esq 3 OUT dir 4 GND')
# divisor da bateria (IO34): 10k/10k, em pe
# (encostado no anel de VBAT: so o sinal fino VBAT_ADC atravessa a placa)
peca('R9', '10k', 'R_PE', -14.5, -39.3, rot=90, pinos={'1': 'VBAT', '2': 'VBAT_ADC'})
peca('R10', '10k', 'R_PE', -14.5, -33.6, rot=90, pinos={'1': 'VBAT_ADC', '2': 'GND'})
# fluxo optico PMW3901: OPCIONAL. Sem o modulo o drone voa igual; o firmware
# descobre sozinho no boot se ele esta ligado (le o ID do chip).
peca('J4', 'FLUXO (PMW3901)', 'CONN6F', -11.1, -24.0, rot=90,
     pinos={'1': '+3V3', '2': 'FLOW_MISO', '3': 'FLOW_SCK', '4': 'FLOW_MOSI', '5': 'FLOW_CS', '6': 'GND'},
     nota='1 VCC(3V3) 2 MISO 3 SCK 4 MOSI 5 CS 6 GND | ligue com o drone DESLIGADO')
# sonar a direita do J4. Divisores do ECHO (5 V -> 3,3 V): 1k em serie, 2k para o GND, em pe.
#  - ECHO baixo: R13 (2k) pega o GND do J4.6, logo acima dele; R11 (1k) desce para o J2.
#  - ECHO frente: R14 (2k) pega o GND do pino 14 do ESP32; R12 (1k), logo abaixo, desce para o J2.
peca('R13', '2k', 'R_PE', 1.6, -29.54, rot=90, pinos={'1': 'ECHO_B', '2': 'GND'})
peca('R11', '1k', 'R_PE', 5.4, -29.54, rot=-90, pinos={'1': 'ECHO_B', '2': 'ECHO_B5'})
peca('R14', '2k', 'R_PE', 11.6, -20.54, rot=90, pinos={'1': 'ECHO_F', '2': 'GND'})
peca('R12', '1k', 'R_PE', 11.6, -24.5, rot=-90, pinos={'1': 'ECHO_F', '2': 'ECHO_F5'})
# ordem dos pinos = ordem das trilhas que chegam (nada cruza)
peca('J2', 'SONAR (HC-SR04 x2)', 'CONN6', 3.46, -37.0, rot=90,
     pinos={'1': 'GND', '2': 'ECHO_B5', '3': 'TRIG_B', '4': 'ECHO_F5', '5': 'TRIG_F', '6': '+5V'},
     nota='1 GND 2 ECHO baixo 3 TRIG baixo 4 ECHO frente 5 TRIG frente 6 VCC(5V)')

# ---- 4 canais de motor, na ponta de cada diagonal
# de fora p/ dentro: anel VBAT | ilhas do motor, C, diodo | MOSFET | resistores
MOTORES = [('FR', 45, 'M_FR'), ('RR', -45, 'M_RR'), ('RL', -135, 'M_RL'), ('FL', 135, 'M_FL')]
for n, (nome, ang, rede_pwm) in enumerate(MOTORES, start=1):
    dreno, porta = 'DRENO_' + nome, 'PORTA_' + nome
    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    s = -1 if ux * uy > 0 else 1        # lado "lateral" (longe da frente/tras)
    x, y = polar(42.0, ang)
    peca(f'M{n}', f'motor {nome}', 'MOTOR', x, y, rot=ang + 180,
         pinos={'1': 'VBAT', '2': dreno}, nota='1 = + (vermelho), 2 = - (preto/azul)')
    # capacitor 100 nF SMD 0805 (os que voce tem), embaixo, ao lado das ilhas do motor
    x, y = polar(41.0, ang, -5.0)      # lado da porta (t < 0)
    peca(f'C{n + 2}', '100nF 0805', 'C_0805', x, y, lado='B', pino_fora='1',
         pinos={'1': 'VBAT', '2': dreno})
    x, y = polar(41.8, ang, 6.5)       # lado da fonte (t > 0)
    peca(f'D{n}', 'SS34', 'SMA', x, y, lado='B', pino_fora='1', pinos={'1': 'VBAT', '2': dreno})
    x, y = polar(35.5, ang)
    peca(f'Q{n}', 'AO3400A', 'SOT23', x, y, lado='B', pino_fora='3',
         pinos={'1': porta, '2': 'GND', '3': dreno})
    # pull-down em pe logo atras do MOSFET, deitado na tangente: ponta PORTA junto da
    # porta (t = -0,95) e ponta GND junto da fonte (t = +0,95). Assim o GND chega na fonte
    # sem cruzar a porta.
    x, y = polar(31.0, ang, -1.27)
    peca(f'R{n + 4}', '10k', 'R_PE', x, y, rot=ang + 90, pinos={'1': porta, '2': 'GND'})
    # resistor de porta do lado da porta, radial: PORTA por fora, sinal do ESP32 por dentro
    x, y = polar(37.1, ang, -4.9)
    peca(f'R{n}', '100', 'R_PE', x, y, rot=ang + 180, pinos={'1': porta, '2': rede_pwm})
