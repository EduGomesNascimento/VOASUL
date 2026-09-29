"""Código de barras Code 39 desenhado como SVG.

Code 39 foi escolhido por ser auto-verificável (dispensa dígito de
controle), aceito por qualquer leitor comum e simples o bastante para
ser gerado sem biblioteca externa. Cada caractere ocupa 9 elementos
(5 barras e 4 espaços alternados, começando por barra), dos quais
exatamente 3 são largos.
"""

from .util import sem_acento

# 'n' = elemento estreito, 'w' = elemento largo.
PADROES = {
    "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw", "3": "wnwwnnnnn",
    "4": "nnnwwnnnw", "5": "wnnwwnnnn", "6": "nnwwwnnnn", "7": "nnnwnnwnw",
    "8": "wnnwnnwnn", "9": "nnwwnnwnn",
    "A": "wnnnnwnnw", "B": "nnwnnwnnw", "C": "wnwnnwnnn", "D": "nnnnwwnnw",
    "E": "wnnnwwnnn", "F": "nnwnwwnnn", "G": "nnnnnwwnw", "H": "wnnnnwwnn",
    "I": "nnwnnwwnn", "J": "nnnnwwwnn", "K": "wnnnnnnww", "L": "nnwnnnnww",
    "M": "wnwnnnnwn", "N": "nnnnwnnww", "O": "wnnnwnnwn", "P": "nnwnwnnwn",
    "Q": "nnnnnnwww", "R": "wnnnnnwwn", "S": "nnwnnnwwn", "T": "nnnnwnwwn",
    "U": "wwnnnnnnw", "V": "nwwnnnnnw", "W": "wwwnnnnnn", "X": "nwnnwnnnw",
    "Y": "wwnnwnnnn", "Z": "nwwnwnnnn",
    "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn",
    "$": "nwnwnwnnn", "/": "nwnwnnnwn", "+": "nwnnnwnwn", "%": "nnnwnwnwn",
    "*": "nwnnwnwnn",          # delimitador de início e fim
}

DELIMITADOR = "*"


def normalizar(texto: str) -> str:
    """Deixa o texto no conjunto que o Code 39 aceita."""
    limpo = sem_acento(str(texto or "")).upper()
    return "".join(c if c in PADROES and c != DELIMITADOR else "-" for c in limpo)


def svg(texto: str, altura: int = 44, estreito: int = 2, largo_por_estreito: int = 3,
        margem: int = 8, mostrar_texto: bool = True) -> str:
    """Devolve o código de barras como um `<svg>` pronto para embutir."""
    conteudo = normalizar(texto)
    if not conteudo:
        return ""

    largo = estreito * largo_por_estreito
    sequencia = DELIMITADOR + conteudo + DELIMITADOR

    barras = []          # (x, largura) apenas dos elementos escuros
    x = margem
    for indice, caractere in enumerate(sequencia):
        padrao = PADROES[caractere]
        for posicao, tipo in enumerate(padrao):
            largura = largo if tipo == "w" else estreito
            if posicao % 2 == 0:                 # posições pares são barras
                barras.append((x, largura))
            x += largura
        if indice < len(sequencia) - 1:
            x += estreito                        # espaço entre caracteres

    altura_texto = 15 if mostrar_texto else 0
    total_largura = x + margem
    total_altura = altura + altura_texto + margem

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="cb" '
        f'viewBox="0 0 {total_largura} {total_altura}" '
        f'width="{total_largura}" height="{total_altura}" '
        f'role="img" aria-label="Código de barras {conteudo}">',
        f'<rect width="{total_largura}" height="{total_altura}" fill="#ffffff"/>',
    ]
    for posicao_x, largura in barras:
        partes.append(
            f'<rect x="{posicao_x}" y="{margem // 2}" width="{largura}" '
            f'height="{altura}" fill="#000000"/>')
    if mostrar_texto:
        partes.append(
            f'<text x="{total_largura / 2:.1f}" y="{margem // 2 + altura + 12}" '
            f'text-anchor="middle" font-family="monospace" font-size="12" '
            f'letter-spacing="1.5" fill="#000000">{conteudo}</text>')
    partes.append("</svg>")
    return "".join(partes)
