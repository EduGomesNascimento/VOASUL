"""
Modelos 3D (VRML) dos modulos que nao existem na biblioteca do KiCad:
ESP32 DevKitC 38 pinos, MT3608, GY-BMI160 e GY-BMP280.

Medidas tipicas (ver docs/ESQUEMA.md). Unidade do VRML no KiCad = 0,1 pol
(2,54 mm); aqui tudo e escrito em mm e convertido no fim.
Eixos iguais aos da pegada: X direita, Y para cima (frente), Z para fora da placa.
"""
import os

U = 1 / 2.54

COR = {
    'pcb_preta':  (0.08, 0.08, 0.10),
    'pcb_azul':   (0.05, 0.22, 0.55),
    'pcb_roxa':   (0.38, 0.12, 0.45),
    'metal':      (0.80, 0.80, 0.82),
    'ouro':       (0.85, 0.65, 0.20),
    'preto':      (0.05, 0.05, 0.05),
    'cinza':      (0.25, 0.25, 0.27),
    'trimpot':    (0.10, 0.35, 0.85),
    'latao':      (0.80, 0.62, 0.25),
    'ceramica':   (0.72, 0.58, 0.40),
    'branco':     (0.92, 0.92, 0.90),
    'led_verm':   (0.90, 0.10, 0.10),
}


class Vrml:
    def __init__(self):
        self.s = ['#VRML V2.0 utf8\n']

    def _mat(self, cor, brilho=0.3):
        r, g, b = COR[cor] if isinstance(cor, str) else cor
        return (f'appearance Appearance {{ material Material {{ diffuseColor {r} {g} {b} '
                f'specularColor {brilho} {brilho} {brilho} shininess 0.4 }} }}')

    def caixa(self, cx, cy, z0, sx, sy, sz, cor, brilho=0.3):
        """caixa com centro (cx, cy) e base em z0"""
        self.s.append(
            f'Transform {{ translation {cx*U:.5f} {cy*U:.5f} {(z0+sz/2)*U:.5f} children [ '
            f'Shape {{ {self._mat(cor, brilho)} geometry Box {{ size {sx*U:.5f} {sy*U:.5f} {sz*U:.5f} }} }} ] }}\n')

    def cilindro(self, cx, cy, z0, r, h, cor, brilho=0.3):
        """cilindro em pe (eixo Z)"""
        self.s.append(
            f'Transform {{ translation {cx*U:.5f} {cy*U:.5f} {(z0+h/2)*U:.5f} rotation 1 0 0 1.5708 children [ '
            f'Shape {{ {self._mat(cor, brilho)} geometry Cylinder {{ radius {r*U:.5f} height {h*U:.5f} }} }} ] }}\n')

    def salvar(self, caminho):
        with open(caminho, 'w') as f:
            f.write(''.join(self.s))


def esp32_devkit(caminho, z_base=11.0):
    """ESP32 DevKitC V4 38 pinos encaixado nas barras femeas (8,5 mm) com a barra
    macho dele (2,5 mm de plastico). Antena para +X."""
    v = Vrml()
    z = z_base
    # barra macho do proprio DevKit (plastico preto entre a femea e a placa)
    for y in (12.7, -12.7):
        v.caixa(0, y, 8.5, 48.3, 2.5, z - 8.5, 'preto')
        for i in range(19):
            v.caixa(-22.86 + i * 2.54, y, z + 1.6, 0.64, 0.64, 1.8, 'ouro', 0.6)  # ponta soldada
    v.caixa(1.0, 0, z, 55.0, 28.0, 1.6, 'pcb_preta')
    zt = z + 1.6
    # WROOM-32: base + blindagem + antena
    v.caixa(15.75, 0, zt, 25.5, 18.0, 0.8, 'pcb_preta')
    v.caixa(12.6, 0, zt + 0.8, 17.6, 16.0, 2.3, 'metal', 0.8)
    for i in range(5):                                           # trilha da antena
        v.caixa(23.0 + i * 1.2, 0, zt + 0.8, 0.5, 14.0, 0.05, 'ouro', 0.6)
    v.caixa(25.4, 6.8, zt + 0.8, 5.3, 0.5, 0.05, 'ouro', 0.6)
    # USB, regulador, ponte USB-serial, botoes, LEDs
    v.caixa(-24.6, 0, zt, 5.8, 7.6, 2.7, 'metal', 0.8)
    v.caixa(-14.0, 6.5, zt, 6.5, 3.5, 1.6, 'preto')
    v.caixa(-14.0, 9.0, zt, 3.0, 1.5, 1.6, 'metal')
    v.caixa(-8.0, -4.0, zt, 5.0, 5.0, 0.9, 'preto')
    for y in (9.6, -9.6):
        v.caixa(-21.0, y, zt, 4.2, 3.2, 1.4, 'metal', 0.7)
        v.cilindro(-21.0, y, zt + 1.4, 0.8, 0.5, 'preto')
    v.caixa(-17.5, -9.0, zt, 1.6, 0.8, 0.6, 'led_verm', 0.6)
    for x in (-3.0, -1.0, 1.0):                                  # passivos
        v.caixa(x, 6.0, zt, 1.0, 0.5, 0.5, 'ceramica')
    v.salvar(caminho)


def gy_modulo(caminho, n_pinos, larg, alt, chip, chip_cor, roxo=True):
    """Modulo GY soldado direto com barra macho (sem femea): plastico 2,5 mm,
    placa por cima. Origem no centro da fileira de pinos; a placa avanca p/ +Y."""
    v = Vrml()
    span = n_pinos * 2.54
    v.caixa(0, 0, 0, span, 2.5, 2.5, 'preto')
    for i in range(n_pinos):
        x = (i - (n_pinos - 1) / 2) * 2.54
        v.caixa(x, 0, -3.0, 0.64, 0.64, 3.0 + 2.5 + 1.6 + 1.2, 'ouro', 0.6)
    z = 2.5
    v.caixa(0, alt / 2 - 1.5, z, larg, alt, 1.6, 'pcb_roxa' if roxo else 'pcb_azul')
    zt = z + 1.6
    cx, cy, sx, sy, sz = chip
    v.caixa(cx, cy, zt, sx, sy, sz, chip_cor, 0.7)
    v.caixa(-larg / 2 + 3.0, alt - 5.5, zt, 2.9, 1.6, 1.1, 'preto')   # regulador 662K
    for dx in (2.5, 4.0, -2.5):
        v.caixa(dx, alt - 3.5, zt, 1.0, 0.5, 0.5, 'ceramica')
    for dx in (-larg / 2 + 2.2, larg / 2 - 2.2):                      # furos de fixacao
        v.cilindro(dx, alt - 3.2, zt, 1.1, 0.02, 'ouro', 0.6)
    v.salvar(caminho)


def mt3608(caminho, z_base=5.0):
    """Step-up MT3608 (36 x 17 mm) apoiado em 4 pernas de fio rigido."""
    v = Vrml()
    for x in (-16.5, 16.5):
        for y in (6.5, -6.5):
            v.cilindro(x, y, -2.5, 0.4, z_base + 2.5 + 1.6 + 0.6, 'metal', 0.8)
    z = z_base
    v.caixa(0, 0, z, 36.0, 17.0, 1.6, 'pcb_azul')
    zt = z + 1.6
    v.caixa(1.0, 1.0, zt, 6.0, 6.0, 4.5, 'cinza')                 # indutor CD54
    v.caixa(-8.5, -3.8, zt, 9.5, 4.8, 5.0, 'trimpot')             # trimpot multivoltas
    v.cilindro(-12.6, -3.8, zt + 2.5, 1.0, 0.8, 'latao', 0.8)     # parafuso de ajuste
    v.caixa(-7.0, 4.5, zt, 2.9, 1.6, 1.1, 'preto')                # MT3608 SOT-23-6
    v.caixa(9.0, 3.0, zt, 4.3, 2.6, 2.1, 'preto')                 # SS34
    v.caixa(9.0, 3.0 - 1.0, zt + 2.1, 4.3, 0.5, 0.02, 'branco')
    for x, y in ((-12.5, 5.0), (12.5, -4.0), (13.5, 3.0), (5.0, -5.5)):
        v.caixa(x, y, zt, 3.2, 1.6, 1.4, 'ceramica')
    v.salvar(caminho)


def gerar_todos(pasta):
    os.makedirs(pasta, exist_ok=True)
    esp32_devkit(os.path.join(pasta, 'ESP32_DevKitC_38p.wrl'))
    gy_modulo(os.path.join(pasta, 'GY_BMI160.wrl'), 7, 20.0, 13.5,
              (0.0, 6.0, 2.5, 3.0, 0.83), 'preto')
    gy_modulo(os.path.join(pasta, 'GY_BMP280.wrl'), 6, 15.0, 11.5,
              (0.0, 5.0, 2.0, 2.5, 0.95), 'metal')
    mt3608(os.path.join(pasta, 'MT3608.wrl'))


if __name__ == '__main__':
    gerar_todos(os.path.join(os.path.dirname(os.path.abspath(__file__)), '3d'))
