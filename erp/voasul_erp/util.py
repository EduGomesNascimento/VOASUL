"""Formatação brasileira, validações e pequenos auxiliares."""

import html
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

MESES = ["", "jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]


def esc(valor) -> str:
    """Escapa para HTML. Tudo que vem do banco passa por aqui."""
    return html.escape("" if valor is None else str(valor), quote=True)


# ---------------------------------------------------------------- números

def moeda(valor) -> str:
    """1234.5 -> 'R$ 1.234,50'"""
    return "R$ " + numero(valor, 2)


def numero(valor, casas: int = 2) -> str:
    """Formata no padrão brasileiro: milhar com ponto, decimal com vírgula."""
    try:
        d = Decimal(str(valor or 0))
    except (InvalidOperation, ValueError):
        d = Decimal(0)
    texto = f"{d:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def quantidade(valor) -> str:
    """Mostra inteiro quando não há fração: 3 em vez de 3,000."""
    try:
        d = Decimal(str(valor or 0))
    except (InvalidOperation, ValueError):
        return "0"
    return numero(d, 0) if d == d.to_integral_value() else numero(d, 3)


def para_decimal(texto, padrao=Decimal("0")) -> Decimal:
    """Lê número digitado em português ('1.234,56') ou em inglês."""
    if texto is None or str(texto).strip() == "":
        return padrao
    t = str(texto).strip().replace("R$", "").replace(" ", "")
    if "," in t:                      # vírgula decimal: remove pontos de milhar
        t = t.replace(".", "").replace(",", ".")
    try:
        return Decimal(t)
    except InvalidOperation:
        return padrao


def para_float(texto, padrao=0.0) -> float:
    return float(para_decimal(texto, Decimal(str(padrao))))


# ------------------------------------------------------------------ datas

def hoje_iso() -> str:
    return date.today().isoformat()


def agora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def data_br(iso) -> str:
    """'2026-09-29' ou '2026-09-29T14:03:00' -> '29/09/2026'"""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(str(iso)).strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)


def data_hora_br(iso) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(str(iso)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(iso)


def para_iso(texto) -> str:
    """Aceita '29/09/2026' ou '2026-09-29' e devolve ISO."""
    t = (texto or "").strip()
    if not t:
        return ""
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(t, formato).date().isoformat()
        except ValueError:
            continue
    return t


# ------------------------------------------------------------- documentos

def so_digitos(texto) -> str:
    return re.sub(r"\D", "", texto or "")


def formata_documento(texto) -> str:
    """Formata CPF (11) ou CNPJ (14). Devolve como veio se não bater."""
    d = so_digitos(texto)
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return texto or ""


def documento_valido(texto) -> bool:
    """Valida CPF ou CNPJ pelos dígitos verificadores. Vazio é aceito."""
    d = so_digitos(texto)
    if not d:
        return True
    if len(d) == 11:
        return _cpf_valido(d)
    if len(d) == 14:
        return _cnpj_valido(d)
    return False


def _cpf_valido(d: str) -> bool:
    if d == d[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(d[tamanho]):
            return False
    return True


def _cnpj_valido(d: str) -> bool:
    if d == d[0] * 14:
        return False
    for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
                  [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        soma = sum(int(d[i]) * pesos[i] for i in range(len(pesos)))
        resto = soma % 11
        digito = 0 if resto < 2 else 11 - resto
        if digito != int(d[len(pesos)]):
            return False
    return True


# ------------------------------------------------------------------ texto

def sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def codigo_limpo(texto: str) -> str:
    """Código de item: maiúsculas, sem acento, só letras/números/hífen."""
    base = sem_acento(texto or "").upper()
    return re.sub(r"[^A-Z0-9\-\.]", "-", base).strip("-")
