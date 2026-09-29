"""Banco SQLite: esquema, conexão e carga inicial."""

import hashlib
import secrets
import sqlite3
from contextlib import contextmanager

from . import config
from .util import agora_iso, hoje_iso

ESQUEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuario (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  login      TEXT NOT NULL UNIQUE,
  nome       TEXT NOT NULL,
  senha      TEXT NOT NULL,          -- pbkdf2$iteracoes$sal$hash
  papel      TEXT NOT NULL DEFAULT 'operador',   -- admin | operador
  ativo      INTEGER NOT NULL DEFAULT 1,
  criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS item (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo       TEXT NOT NULL UNIQUE,
  descricao    TEXT NOT NULL,
  tipo         TEXT NOT NULL DEFAULT 'componente', -- materia_prima|componente|produto|servico
  unidade      TEXT NOT NULL DEFAULT 'UN',
  ncm          TEXT DEFAULT '',
  custo        REAL NOT NULL DEFAULT 0,
  preco        REAL NOT NULL DEFAULT 0,
  estoque_min  REAL NOT NULL DEFAULT 0,
  localizacao  TEXT DEFAULT '',
  observacao   TEXT DEFAULT '',
  ativo        INTEGER NOT NULL DEFAULT 1,
  criado_em    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_item_descricao ON item(descricao);

CREATE TABLE IF NOT EXISTS parceiro (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  nome       TEXT NOT NULL,
  tipo       TEXT NOT NULL DEFAULT 'cliente',   -- cliente | fornecedor | ambos
  documento  TEXT DEFAULT '',
  email      TEXT DEFAULT '',
  telefone   TEXT DEFAULT '',
  endereco   TEXT DEFAULT '',
  cidade     TEXT DEFAULT '',
  uf         TEXT DEFAULT '',
  cep        TEXT DEFAULT '',
  observacao TEXT DEFAULT '',
  ativo      INTEGER NOT NULL DEFAULT 1,
  criado_em  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_parceiro_nome ON parceiro(nome);

CREATE TABLE IF NOT EXISTS movimento (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id    INTEGER NOT NULL REFERENCES item(id),
  tipo       TEXT NOT NULL,          -- entrada | saida | ajuste
  quantidade REAL NOT NULL,          -- em 'ajuste' pode ser negativa
  custo_unit REAL NOT NULL DEFAULT 0,
  documento  TEXT DEFAULT '',
  observacao TEXT DEFAULT '',
  pedido_id  INTEGER REFERENCES pedido(id),
  usuario_id INTEGER REFERENCES usuario(id),
  data       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mov_item ON movimento(item_id);
CREATE INDEX IF NOT EXISTS idx_mov_data ON movimento(data);

CREATE TABLE IF NOT EXISTS pedido (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  numero        TEXT NOT NULL UNIQUE,
  tipo          TEXT NOT NULL DEFAULT 'venda',   -- venda | compra
  parceiro_id   INTEGER REFERENCES parceiro(id),
  status        TEXT NOT NULL DEFAULT 'orcamento',
  data_emissao  TEXT NOT NULL,
  data_entrega  TEXT DEFAULT '',
  frete         REAL NOT NULL DEFAULT 0,
  desconto      REAL NOT NULL DEFAULT 0,
  observacao    TEXT DEFAULT '',
  baixado       INTEGER NOT NULL DEFAULT 0,      -- 1 = estoque já movimentado
  usuario_id    INTEGER REFERENCES usuario(id),
  criado_em     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pedido_item (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  pedido_id  INTEGER NOT NULL REFERENCES pedido(id) ON DELETE CASCADE,
  item_id    INTEGER NOT NULL REFERENCES item(id),
  quantidade REAL NOT NULL DEFAULT 1,
  preco_unit REAL NOT NULL DEFAULT 0,
  desconto   REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_pedido_item ON pedido_item(pedido_id);

CREATE TABLE IF NOT EXISTS demanda (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  numero     TEXT NOT NULL UNIQUE,
  item_id    INTEGER NOT NULL REFERENCES item(id),
  quantidade REAL NOT NULL DEFAULT 1,
  origem     TEXT NOT NULL DEFAULT 'manual',   -- manual | pedido | estoque_minimo
  prioridade TEXT NOT NULL DEFAULT 'normal',   -- baixa | normal | alta | urgente
  status     TEXT NOT NULL DEFAULT 'aberta',   -- aberta | em_andamento | atendida | cancelada
  prazo      TEXT DEFAULT '',
  pedido_id  INTEGER REFERENCES pedido(id),
  observacao TEXT DEFAULT '',
  criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nota (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  numero       TEXT NOT NULL,
  serie        TEXT NOT NULL DEFAULT '1',
  natureza     TEXT NOT NULL DEFAULT 'Venda de produção do estabelecimento',
  cfop         TEXT NOT NULL DEFAULT '5101',
  parceiro_id  INTEGER REFERENCES parceiro(id),
  pedido_id    INTEGER REFERENCES pedido(id),
  data_emissao TEXT NOT NULL,
  frete        REAL NOT NULL DEFAULT 0,
  status       TEXT NOT NULL DEFAULT 'emitida',  -- emitida | cancelada
  observacao   TEXT DEFAULT '',
  usuario_id   INTEGER REFERENCES usuario(id),
  criado_em    TEXT NOT NULL,
  UNIQUE (numero, serie)
);

CREATE TABLE IF NOT EXISTS nota_item (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  nota_id    INTEGER NOT NULL REFERENCES nota(id) ON DELETE CASCADE,
  item_id    INTEGER NOT NULL REFERENCES item(id),
  quantidade REAL NOT NULL DEFAULT 1,
  preco_unit REAL NOT NULL DEFAULT 0,
  ncm        TEXT DEFAULT '',
  cfop       TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_nota_item ON nota_item(nota_id);

-- Ficha de inspeção por número de série: cada drone montado é testado em
-- voo antes da entrega, conforme o compromisso de produto da empresa.
CREATE TABLE IF NOT EXISTS producao (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  serie       TEXT NOT NULL UNIQUE,
  item_id     INTEGER NOT NULL REFERENCES item(id),
  pedido_id   INTEGER REFERENCES pedido(id),
  data        TEXT NOT NULL,
  testado     INTEGER NOT NULL DEFAULT 0,
  responsavel TEXT DEFAULT '',
  observacao  TEXT DEFAULT '',
  criado_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ajuste (            -- configurações da empresa
  chave TEXT PRIMARY KEY,
  valor TEXT NOT NULL DEFAULT ''
);

CREATE VIEW IF NOT EXISTS saldo AS
SELECT i.id AS item_id,
       COALESCE(SUM(CASE m.tipo
                      WHEN 'entrada' THEN m.quantidade
                      WHEN 'saida'   THEN -m.quantidade
                      ELSE m.quantidade          -- ajuste já vem com sinal
                    END), 0) AS quantidade
FROM item i
LEFT JOIN movimento m ON m.item_id = i.id
GROUP BY i.id;
"""


# ------------------------------------------------------------------ senhas

def cifrar_senha(senha: str, sal: str = "", iteracoes: int = 200_000) -> str:
    sal = sal or secrets.token_hex(16)
    bruto = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), iteracoes)
    return f"pbkdf2${iteracoes}${sal}${bruto.hex()}"


def senha_confere(senha: str, guardada: str) -> bool:
    try:
        _, iteracoes, sal, esperado = guardada.split("$")
    except ValueError:
        return False
    calculado = cifrar_senha(senha, sal, int(iteracoes)).split("$")[-1]
    return secrets.compare_digest(calculado, esperado)


# ------------------------------------------------------------------ acesso

def conectar() -> sqlite3.Connection:
    config.garantir_pastas()
    con = sqlite3.connect(config.BANCO, timeout=15, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def aberto():
    con = conectar()
    try:
        yield con
    finally:
        con.close()


@contextmanager
def transacao():
    """Agrupa escritas: ou tudo grava, ou nada grava."""
    con = conectar()
    try:
        con.execute("BEGIN")
        yield con
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def iniciar() -> None:
    """Cria o esquema e a carga inicial. Pode rodar quantas vezes quiser."""
    with aberto() as con:
        con.executescript(ESQUEMA)
        _semear(con)


def _semear(con: sqlite3.Connection) -> None:
    for chave, valor in config.EMPRESA_PADRAO.items():
        con.execute("INSERT OR IGNORE INTO ajuste (chave, valor) VALUES (?, ?)",
                    (chave, valor))

    if con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0:
        con.execute(
            "INSERT INTO usuario (login, nome, senha, papel, ativo, criado_em) "
            "VALUES (?,?,?,?,1,?)",
            ("admin", "Administrador", cifrar_senha("voasul"), "admin", agora_iso()))

    if con.execute("SELECT COUNT(*) FROM item").fetchone()[0] == 0:
        _itens_exemplo(con)


def _itens_exemplo(con: sqlite3.Connection) -> None:
    """Carga inicial com as linhas de produto e insumos da VOA-SUL."""
    itens = [
        # codigo,      descricao,                              tipo,            un,   ncm,        custo,  preco,  min, local
        ("VS-5",       "Drone FPV 5 polegadas — montado",       "produto",       "UN", "88062900", 1850.0, 3490.0, 2,  "A-01"),
        ("VS-LITE",    "Drone recreativo até 250 g",            "produto",       "UN", "88062900",  620.0, 1290.0, 3,  "A-02"),
        ("VS-FRAME-5", "Frame FPV 5\" impresso em 3D",          "componente",    "UN", "39269090",   48.0,  149.0, 10, "B-01"),
        ("VS-BRACO-5", "Braço avulso para frame VS-5",          "componente",    "UN", "39269090",   12.0,   39.0, 20, "B-02"),
        ("VS-CTRL",    "Controladora de voo STM32 — VOA-SUL",   "componente",    "UN", "85371090",  210.0,  480.0, 5,  "C-01"),
        ("MOT-2207",   "Motor brushless 2207 2400KV",           "materia_prima", "UN", "85015210",   89.0,  169.0, 16, "C-02"),
        ("ESC-45A",    "Controlador de velocidade 45A 4em1",    "materia_prima", "UN", "85044090",  240.0,  420.0, 4,  "C-03"),
        ("CAM-FPV",    "Câmera FPV 1200TVL",                    "materia_prima", "UN", "85258900",  130.0,  245.0, 6,  "C-04"),
        ("BAT-4S",     "Bateria LiPo 4S 1500mAh",               "materia_prima", "UN", "85076000",  165.0,  289.0, 8,  "D-01"),
        ("HEL-5",      "Hélice 5 polegadas (jogo com 4)",       "materia_prima", "JG", "88073000",   18.0,   45.0, 30, "D-02"),
        ("FIL-PETG",   "Filamento PETG 1 kg",                   "materia_prima", "KG", "39169090",   95.0,    0.0, 5,  "E-01"),
        ("SRV-REPARO", "Serviço de reparo e ajuste",            "servico",       "HR", "",            0.0,  120.0, 0,  ""),
        ("SRV-UPGR",   "Serviço de upgrade e recalibração",     "servico",       "HR", "",            0.0,  150.0, 0,  ""),
    ]
    agora = agora_iso()
    for codigo, descricao, tipo, unidade, ncm, custo, preco, minimo, local in itens:
        con.execute(
            "INSERT INTO item (codigo, descricao, tipo, unidade, ncm, custo, preco,"
            " estoque_min, localizacao, ativo, criado_em) VALUES (?,?,?,?,?,?,?,?,?,1,?)",
            (codigo, descricao, tipo, unidade, ncm, custo, preco, minimo, local, agora))

    parceiros = [
        ("Clube FPV Vale dos Sinos", "cliente",    "", "contato@fpvvale.com.br", "(51) 99000-0001", "Novo Hamburgo", "RS"),
        ("Hobby Store Portão",       "cliente",    "", "vendas@hobbyportao.com.br", "(51) 99000-0002", "Portão", "RS"),
        ("Eletrônica Sul Ltda.",     "fornecedor", "", "comercial@eletronicasul.com.br", "(51) 99000-0003", "Porto Alegre", "RS"),
        ("Import Drone Parts",       "fornecedor", "", "sales@importdroneparts.com", "", "São Paulo", "SP"),
    ]
    for nome, tipo, doc, email, tel, cidade, uf in parceiros:
        con.execute(
            "INSERT INTO parceiro (nome, tipo, documento, email, telefone, cidade, uf,"
            " ativo, criado_em) VALUES (?,?,?,?,?,?,?,1,?)",
            (nome, tipo, doc, email, tel, cidade, uf, agora))

    # Entrada inicial de estoque, para o sistema já abrir com saldo real.
    entradas = {"VS-FRAME-5": 14, "VS-BRACO-5": 26, "VS-CTRL": 7, "MOT-2207": 24,
                "ESC-45A": 6, "CAM-FPV": 9, "BAT-4S": 11, "HEL-5": 40,
                "FIL-PETG": 8, "VS-5": 2, "VS-LITE": 4}
    for codigo, qtd in entradas.items():
        linha = con.execute("SELECT id, custo FROM item WHERE codigo = ?", (codigo,)).fetchone()
        con.execute(
            "INSERT INTO movimento (item_id, tipo, quantidade, custo_unit, documento,"
            " observacao, usuario_id, data) VALUES (?, 'entrada', ?, ?, 'SALDO-INICIAL',"
            " 'Carga inicial do sistema', 1, ?)",
            (linha["id"], qtd, linha["custo"], hoje_iso()))
