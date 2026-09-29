"""Configuração da aplicação: caminhos, porta e dados da empresa."""

import configparser
import os
import secrets
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BASE = RAIZ.parent                      # pasta 'erp', onde ficam os .bat
ESTATICOS = RAIZ / "static"


def _pasta_dados() -> Path:
    """Pasta onde ficam o banco e os arquivos gerados.

    Pode ser redirecionada para uma pasta de rede (para compartilhar o
    mesmo banco entre vários PCs) pela variável VOASUL_DADOS.
    """
    env = os.environ.get("VOASUL_DADOS")
    return Path(env).expanduser().resolve() if env else BASE / "dados"


DADOS = _pasta_dados()
BANCO = Path(os.environ["VOASUL_DB"]).expanduser() if os.environ.get("VOASUL_DB") else DADOS / "voasul.db"
ARQUIVO_INI = DADOS / "config.ini"

HOST = os.environ.get("VOASUL_HOST", "127.0.0.1")
PORTA = int(os.environ.get("VOASUL_PORTA", "8770"))

# Prefixo de URL, para quando a aplicação for servida sob um caminho
# (ex.: VOASUL_PREFIXO=/voa-sul/db em um domínio hospedado).
PREFIXO = os.environ.get("VOASUL_PREFIXO", "").rstrip("/")

# Dados padrão da empresa — editáveis na tela de Configurações.
EMPRESA_PADRAO = {
    "razao_social": "VOA-SUL Drones Ltda.",
    "nome_fantasia": "VOA-SUL",
    "cnpj": "",
    "inscricao_estadual": "",
    "endereco": "Portão — RS",
    "cidade": "Portão",
    "uf": "RS",
    "cep": "",
    "telefone": "",
    "email": "sulvoa@gmail.com",
    "site": "voasul.com.br",
    "serie_nota": "1",
}


def garantir_pastas() -> None:
    DADOS.mkdir(parents=True, exist_ok=True)


def chave_sessao() -> str:
    """Segredo usado para assinar cookies, guardado na pasta de dados."""
    garantir_pastas()
    ini = configparser.ConfigParser()
    if ARQUIVO_INI.exists():
        ini.read(ARQUIVO_INI, encoding="utf-8")
    if not ini.has_section("app"):
        ini.add_section("app")
    if not ini.get("app", "chave", fallback=""):
        ini.set("app", "chave", secrets.token_hex(32))
        with ARQUIVO_INI.open("w", encoding="utf-8") as f:
            ini.write(f)
    return ini.get("app", "chave")
