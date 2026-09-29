"""Configurações: dados da empresa, usuários, senha e backup do banco."""

import shutil

from .. import config
from .. import consultas as q
from .. import db, ui, web
from ..util import agora_iso, data_hora_br, esc

CAMPOS_EMPRESA = [
    ("razao_social", "Razão social"), ("nome_fantasia", "Nome fantasia"),
    ("cnpj", "CNPJ"), ("inscricao_estadual", "Inscrição estadual"),
    ("endereco", "Endereço"), ("cidade", "Cidade"), ("uf", "UF"),
    ("cep", "CEP"), ("telefone", "Telefone"), ("email", "E-mail"),
    ("site", "Site"), ("serie_nota", "Série padrão da nota fiscal"),
]


def registrar(app):

    @app.rota("/configuracoes")
    def tela(req):
        with db.aberto() as con:
            emp = q.empresa(con)
            usuarios = con.execute(
                "SELECT * FROM usuario ORDER BY nome").fetchall()

        campos = "".join(
            ui.campo(chave, etiqueta, emp.get(chave, "")) for chave, etiqueta in CAMPOS_EMPRESA)

        linhas = [[
            esc(x["nome"]),
            f'<span class="mono">{esc(x["login"])}</span>',
            ui.rotulo(x["papel"]),
            (ui.tarja("sim" if x["ativo"] else "nao",
                      "Ativo" if x["ativo"] else "Inativo"), "meio"),
            data_hora_br(x["criado_em"]),
        ] for x in usuarios]

        tamanho = config.BANCO.stat().st_size / 1024 if config.BANCO.exists() else 0

        conteudo = f"""
{ui.aviso_da_url(req)}

<div class="painel">
  <h2>Dados da empresa</h2>
  <p class="dica">Aparecem no cabeçalho dos pedidos, das notas fiscais e das
  fichas de inspeção.</p>
  <form method="post" action="{ui.u('/configuracoes/empresa')}">
    <div class="formulario">{campos}</div>
    <div class="rodape-form">
      {ui.bt('Salvar dados da empresa', classe='bt--principal', tipo='submit')}
    </div>
  </form>
</div>

<div class="painel">
  <h2>Minha senha</h2>
  <form method="post" action="{ui.u('/configuracoes/senha')}">
    <div class="formulario">
      {ui.campo('atual', 'Senha atual', tipo='password', obrigatorio=True)}
      {ui.campo('nova', 'Nova senha', tipo='password', obrigatorio=True,
                dica='Use ao menos 6 caracteres.')}
      {ui.campo('confirma', 'Repita a nova senha', tipo='password', obrigatorio=True)}
    </div>
    <div class="rodape-form">
      {ui.bt('Alterar senha', classe='bt--escuro', tipo='submit')}
    </div>
  </form>
</div>

<div class="painel">
  <div class="painel__cabeca">
    <h2>Usuários</h2>
    {ui.bt('Novo usuário', '/configuracoes/usuarios/novo', 'bt--principal bt--mini')}
  </div>
  {ui.tabela(['Nome', 'Login', 'Papel', ('Situação', 'meio'), 'Criado em'], linhas)}
</div>

<div class="painel">
  <h2>Banco de dados e backup</h2>
  <div class="grade grade--3">
    <div><span class="dica">Arquivo do banco</span><br>
      <strong class="mono" style="word-break:break-all">{esc(config.BANCO)}</strong></div>
    <div><span class="dica">Tamanho</span><br><strong>{tamanho:.0f} KB</strong></div>
    <div><span class="dica">Pasta de dados</span><br>
      <strong class="mono" style="word-break:break-all">{esc(config.DADOS)}</strong></div>
  </div>
  <p class="dica" style="margin-top:1rem">
    Para usar o mesmo banco em vários PCs, aponte a variável
    <span class="mono">VOASUL_DADOS</span> para uma pasta de rede compartilhada
    antes de iniciar o sistema — o instalador explica como.
  </p>
  <div class="rodape-form">
    <form method="post" action="{ui.u('/configuracoes/backup')}" style="display:inline">
      {ui.bt('Gerar cópia de segurança', classe='bt--escuro', tipo='submit')}
    </form>
  </div>
</div>"""
        return web.pagina(ui.layout("Configurações", conteudo, "", req.usuario))

    @app.rota("/configuracoes/empresa", metodos=("POST",))
    def salvar_empresa(req):
        with db.aberto() as con:
            for chave, _ in CAMPOS_EMPRESA:
                con.execute(
                    "INSERT INTO ajuste (chave, valor) VALUES (?, ?) "
                    "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                    (chave, req.texto(chave)))
        return web.redirecionar("/configuracoes", "Dados da empresa salvos.")

    @app.rota("/configuracoes/senha", metodos=("POST",))
    def trocar_senha(req):
        atual = req.formulario.get("atual") or ""
        nova = req.formulario.get("nova") or ""
        confirma = req.formulario.get("confirma") or ""

        with db.aberto() as con:
            pessoa = con.execute("SELECT * FROM usuario WHERE id = ?",
                                 (req.usuario["id"],)).fetchone()
            if not db.senha_confere(atual, pessoa["senha"]):
                return web.redirecionar("/configuracoes", "Erro: a senha atual não confere.")
            if len(nova) < 6:
                return web.redirecionar("/configuracoes",
                                        "Erro: a nova senha precisa de ao menos 6 caracteres.")
            if nova != confirma:
                return web.redirecionar("/configuracoes",
                                        "Erro: a confirmação não bate com a nova senha.")
            con.execute("UPDATE usuario SET senha = ? WHERE id = ?",
                        (db.cifrar_senha(nova), req.usuario["id"]))
        return web.redirecionar("/configuracoes", "Senha alterada.")

    @app.rota("/configuracoes/usuarios/novo", metodos=("GET", "POST"))
    def novo_usuario(req):
        if req.usuario["papel"] != "admin":
            return web.redirecionar("/configuracoes",
                                    "Erro: só o administrador cadastra usuários.")
        if req.metodo == "POST":
            login = req.texto("login").lower()
            senha = req.formulario.get("senha") or ""
            if not login or not req.texto("nome"):
                return _form_usuario(req, "Nome e login são obrigatórios.")
            if len(senha) < 6:
                return _form_usuario(req, "A senha precisa de ao menos 6 caracteres.")
            with db.aberto() as con:
                if con.execute("SELECT 1 FROM usuario WHERE login = ?", (login,)).fetchone():
                    return _form_usuario(req, f"O login {login} já está em uso.")
                con.execute(
                    "INSERT INTO usuario (login, nome, senha, papel, ativo, criado_em)"
                    " VALUES (?,?,?,?,?,?)",
                    (login, req.texto("nome"), db.cifrar_senha(senha),
                     req.texto("papel", "operador"),
                     1 if req.texto("ativo", "1") == "1" else 0, agora_iso()))
            return web.redirecionar("/configuracoes", f"Usuário {login} cadastrado.")
        return _form_usuario(req)

    def _form_usuario(req, erro=""):
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        corpo = f"""{alerta}
<form method="post" action="{ui.u('/configuracoes/usuarios/novo')}">
  <div class="painel">
    <div class="formulario">
      {ui.campo('nome', 'Nome completo', req.texto('nome'), obrigatorio=True)}
      {ui.campo('login', 'Login', req.texto('login'), obrigatorio=True,
                dica='Sem espaços e sem acento.')}
      {ui.campo('senha', 'Senha inicial', tipo='password', obrigatorio=True,
                dica='Ao menos 6 caracteres.')}
      {ui.selecao('papel', 'Papel',
                  [('operador', 'Operador'), ('admin', 'Administrador')],
                  req.texto('papel', 'operador'),
                  dica='Só o administrador cadastra outros usuários.')}
      {ui.selecao('ativo', 'Situação', [(1, 'Ativo'), (0, 'Inativo')], 1)}
    </div>
    <div class="rodape-form">
      {ui.bt('Cadastrar usuário', classe='bt--principal', tipo='submit')}
      {ui.bt('Cancelar', '/configuracoes', 'bt--claro')}
    </div>
  </div>
</form>"""
        return web.pagina(ui.layout("Novo usuário", corpo, "", req.usuario))

    @app.rota("/configuracoes/backup", metodos=("POST",))
    def backup(req):
        config.garantir_pastas()
        pasta = config.DADOS / "backups"
        pasta.mkdir(exist_ok=True)
        carimbo = agora_iso().replace(":", "-")
        destino = pasta / f"voasul-{carimbo}.db"
        with db.aberto() as con:
            # A API de backup do sqlite copia o banco mesmo em uso (modo WAL).
            import sqlite3
            copia = sqlite3.connect(destino)
            con.backup(copia)
            copia.close()
        return web.redirecionar("/configuracoes", f"Cópia gerada em {destino.name}.")
