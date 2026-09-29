"""Entrada no sistema, saída e troca de senha."""

from .. import db, ui, web
from ..util import esc


def registrar(app):

    @app.rota("/entrar", metodos=("GET", "POST"), publica=True)
    def entrar(req):
        if req.usuario:
            return web.redirecionar("/")

        erro = ""
        login = req.texto("login")
        if req.metodo == "POST":
            senha = req.formulario.get("senha") or ""
            with db.aberto() as con:
                pessoa = con.execute(
                    "SELECT * FROM usuario WHERE login = ? AND ativo = 1",
                    (login,)).fetchone()
            if pessoa and db.senha_confere(senha, pessoa["senha"]):
                token = app.sessoes.criar(pessoa["id"])
                destino = req.texto("destino") or req.arg("destino") or "/"
                if not destino.startswith("/"):
                    destino = "/"
                resp = web.redirecionar(destino)
                resp.cabecalhos.append(web.cookie_sessao(token))
                return resp
            erro = "Usuário ou senha inválidos."

        destino = esc(req.arg("destino", "/"))
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        corpo = f"""<form class="entrada__caixa" method="post" action="{ui.u('/entrar')}">
  <img class="entrada__logo" src="{ui.u('/static/img/logo-voasul.svg')}" alt="VoaSul">
  {alerta}
  <input type="hidden" name="destino" value="{destino}">
  {ui.campo('login', 'Usuário', login, obrigatorio=True,
            atributos='autofocus autocomplete="username"')}
  {ui.campo('senha', 'Senha', tipo='password', obrigatorio=True,
            atributos='autocomplete="current-password"')}
  <button class="bt bt--principal" type="submit" style="width:100%;justify-content:center">
    Entrar no sistema
  </button>
  <p class="entrada__rodape">
    Controle de estoque e demandas<br>
    Primeiro acesso: <strong>admin</strong> / <strong>voasul</strong> —
    troque a senha em Configurações.
  </p>
</form>"""
        return web.pagina(ui.layout_limpo("Entrar", corpo))

    @app.rota("/sair")
    def sair(req):
        app.sessoes.encerrar(req.cookies.get(web.COOKIE_SESSAO))
        resp = web.redirecionar("/entrar")
        resp.cabecalhos.append(web.cookie_sessao("", apagar=True))
        return resp
