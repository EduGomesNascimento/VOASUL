"""Camada HTTP: aplicação WSGI, roteamento, sessões e respostas.

É WSGI de propósito: o mesmo código roda no servidor local embutido e,
sem alteração, sob mod_wsgi/gunicorn se um dia for hospedado num domínio.
"""

import io
import mimetypes
import re
import secrets
import time
from http import cookies as http_cookies
from urllib.parse import parse_qs, quote

from . import config

COOKIE_SESSAO = "voasul_sessao"
VALIDADE_SESSAO = 12 * 60 * 60          # 12 horas


# ------------------------------------------------------------- requisição

class Requisicao:
    def __init__(self, ambiente):
        self.ambiente = ambiente
        self.metodo = ambiente.get("REQUEST_METHOD", "GET").upper()
        caminho = ambiente.get("PATH_INFO", "/") or "/"
        if config.PREFIXO and caminho.startswith(config.PREFIXO):
            caminho = caminho[len(config.PREFIXO):] or "/"
        self.caminho = caminho
        self.consulta = self._ler_consulta(ambiente.get("QUERY_STRING", ""))
        self.formulario = self._ler_corpo()
        self.cookies = self._ler_cookies()
        self.sessao = None              # preenchido pela aplicação
        self.usuario = None
        self.params = {}                # partes variáveis da rota

    @staticmethod
    def _ler_consulta(bruto):
        return {k: v[-1] for k, v in parse_qs(bruto, keep_blank_values=True).items()}

    def _ler_corpo(self):
        if self.metodo not in ("POST", "PUT", "PATCH"):
            return {}
        try:
            tamanho = int(self.ambiente.get("CONTENT_LENGTH") or 0)
        except ValueError:
            tamanho = 0
        if tamanho <= 0 or tamanho > 8 * 1024 * 1024:
            return {}
        bruto = self.ambiente["wsgi.input"].read(tamanho).decode("utf-8", "replace")
        analisado = parse_qs(bruto, keep_blank_values=True)
        # Campos repetidos (linhas de itens) ficam acessíveis pela lista.
        self.formulario_listas = analisado
        return {k: v[-1] for k, v in analisado.items()}

    def _ler_cookies(self):
        bruto = self.ambiente.get("HTTP_COOKIE", "")
        jarra = http_cookies.SimpleCookie()
        try:
            jarra.load(bruto)
        except http_cookies.CookieError:
            return {}
        return {k: m.value for k, m in jarra.items()}

    def lista(self, campo):
        """Todos os valores de um campo repetido (ex.: item_id de cada linha)."""
        return getattr(self, "formulario_listas", {}).get(campo, [])

    def texto(self, campo, padrao=""):
        return (self.formulario.get(campo) or padrao).strip()

    def arg(self, campo, padrao=""):
        return (self.consulta.get(campo) or padrao).strip()

    @property
    def url_base(self):
        return config.PREFIXO or ""


# ---------------------------------------------------------------- resposta

class Resposta:
    def __init__(self, corpo=b"", status="200 OK", tipo="text/html; charset=utf-8",
                 cabecalhos=None):
        if isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.corpo = corpo
        self.status = status
        self.cabecalhos = [("Content-Type", tipo)] + list(cabecalhos or [])

    def cabecalho(self, nome, valor):
        self.cabecalhos.append((nome, valor))
        return self


def pagina(html_texto, status="200 OK"):
    return Resposta(html_texto, status=status)


def redirecionar(destino, aviso=""):
    alvo = (config.PREFIXO or "") + destino
    if aviso:
        separador = "&" if "?" in alvo else "?"
        alvo = f"{alvo}{separador}aviso={quote(aviso)}"
    return Resposta(b"", status="303 See Other", cabecalhos=[("Location", alvo)])


def arquivo_csv(nome, texto):
    # BOM para o Excel abrir acentuação corretamente.
    corpo = "﻿" + texto
    return Resposta(corpo, tipo="text/csv; charset=utf-8",
                    cabecalhos=[("Content-Disposition",
                                 f'attachment; filename="{nome}"')])


def nao_encontrado(mensagem="Página não encontrada."):
    return Resposta(mensagem, status="404 Not Found",
                    tipo="text/plain; charset=utf-8")


# ----------------------------------------------------------------- sessões

class Sessoes:
    """Sessões em memória. Em app local isso basta; reiniciar desconecta."""

    def __init__(self):
        self._dados = {}

    def criar(self, usuario_id):
        token = secrets.token_urlsafe(32)
        self._dados[token] = {"usuario_id": usuario_id, "expira": time.time() + VALIDADE_SESSAO}
        return token

    def ler(self, token):
        registro = self._dados.get(token or "")
        if not registro:
            return None
        if registro["expira"] < time.time():
            self._dados.pop(token, None)
            return None
        return registro

    def encerrar(self, token):
        self._dados.pop(token or "", None)

    def limpar_vencidas(self):
        agora = time.time()
        for token in [t for t, r in self._dados.items() if r["expira"] < agora]:
            self._dados.pop(token, None)


# ---------------------------------------------------------------- roteador

class Rota:
    CONVERSORES = {"int": r"\d+", "str": r"[^/]+"}

    def __init__(self, metodos, padrao, funcao, publica=False):
        self.metodos = set(metodos)
        self.funcao = funcao
        self.publica = publica
        self.tipos = {}
        self.regex = re.compile("^" + self._compilar(padrao) + "$")

    def _compilar(self, padrao):
        def troca(m):
            tipo, nome = m.group(1), m.group(2)
            self.tipos[nome] = tipo
            return f"(?P<{nome}>{self.CONVERSORES[tipo]})"
        return re.sub(r"<(int|str):([a-z_]+)>", troca, padrao)

    def casa(self, metodo, caminho):
        if metodo not in self.metodos:
            return None
        achado = self.regex.match(caminho)
        if not achado:
            return None
        return {nome: (int(valor) if self.tipos[nome] == "int" else valor)
                for nome, valor in achado.groupdict().items()}


class Aplicacao:
    def __init__(self):
        self.rotas = []
        self.sessoes = Sessoes()
        self._carregador_usuario = None

    def rota(self, padrao, metodos=("GET",), publica=False):
        def registrar(funcao):
            self.rotas.append(Rota(metodos, padrao, funcao, publica))
            return funcao
        return registrar

    def carregador_usuario(self, funcao):
        self._carregador_usuario = funcao
        return funcao

    # -------------------------------------------------------------- WSGI
    def __call__(self, ambiente, iniciar_resposta):
        req = Requisicao(ambiente)

        if req.caminho.startswith("/static/"):
            resp = self._servir_estatico(req.caminho[len("/static/"):])
            return self._enviar(resp, iniciar_resposta)

        token = req.cookies.get(COOKIE_SESSAO)
        req.sessao = self.sessoes.ler(token)
        if req.sessao and self._carregador_usuario:
            req.usuario = self._carregador_usuario(req.sessao["usuario_id"])

        for rota in self.rotas:
            params = rota.casa(req.metodo, req.caminho)
            if params is None:
                continue
            req.params = params
            if not rota.publica and not req.usuario:
                destino = quote(req.caminho)
                return self._enviar(
                    redirecionar(f"/entrar?destino={destino}"), iniciar_resposta)
            try:
                resp = rota.funcao(req, **params)
            except Exception:
                resp = self._erro_interno()
            return self._enviar(resp, iniciar_resposta)

        # Método errado no caminho certo → 405 em vez de 404.
        if any(r.regex.match(req.caminho) for r in self.rotas):
            return self._enviar(
                Resposta("Método não permitido.", status="405 Method Not Allowed",
                         tipo="text/plain; charset=utf-8"), iniciar_resposta)
        return self._enviar(nao_encontrado(), iniciar_resposta)

    def _erro_interno(self):
        import traceback
        traceback.print_exc()
        return Resposta(
            "Erro interno. O detalhe foi registrado no console do servidor.",
            status="500 Internal Server Error", tipo="text/plain; charset=utf-8")

    def _servir_estatico(self, relativo):
        alvo = (config.ESTATICOS / relativo).resolve()
        try:
            alvo.relative_to(config.ESTATICOS.resolve())   # barra "../"
        except ValueError:
            return nao_encontrado()
        if not alvo.is_file():
            return nao_encontrado()
        tipo = mimetypes.guess_type(alvo.name)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("image/svg+xml", "application/javascript"):
            tipo += "; charset=utf-8"
        return Resposta(alvo.read_bytes(), tipo=tipo,
                        cabecalhos=[("Cache-Control", "max-age=3600")])

    @staticmethod
    def _enviar(resp, iniciar_resposta):
        cabecalhos = list(resp.cabecalhos)
        cabecalhos.append(("Content-Length", str(len(resp.corpo))))
        cabecalhos.append(("X-Content-Type-Options", "nosniff"))
        iniciar_resposta(resp.status, cabecalhos)
        return [resp.corpo]


def cookie_sessao(token, apagar=False):
    if apagar:
        return ("Set-Cookie",
                f"{COOKIE_SESSAO}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")
    return ("Set-Cookie",
            f"{COOKIE_SESSAO}={token}; Path=/; Max-Age={VALIDADE_SESSAO};"
            " HttpOnly; SameSite=Lax")
