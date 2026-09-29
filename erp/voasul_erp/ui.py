"""Montagem do HTML: layout, menu, tabelas, formulários e componentes."""

from . import config
from .util import esc

MENU = [
    ("/", "Painel", "painel"),
    ("/pedidos", "Pedidos", "pedidos"),
    ("/demandas", "Demandas", "demandas"),
    ("/estoque", "Estoque", "estoque"),
    ("/itens", "Itens", "itens"),
    ("/parceiros", "Clientes e fornecedores", "parceiros"),
    ("/notas", "Notas fiscais", "notas"),
    ("/producao", "Produção", "producao"),
    ("/etiquetas", "Etiquetas", "etiquetas"),
    ("/relatorios", "Relatórios", "relatorios"),
]

ROTULOS = {
    "materia_prima": "Matéria-prima", "componente": "Componente",
    "produto": "Produto acabado", "servico": "Serviço",
    "cliente": "Cliente", "fornecedor": "Fornecedor", "ambos": "Cliente e fornecedor",
    "entrada": "Entrada", "saida": "Saída", "ajuste": "Ajuste",
    "venda": "Venda", "compra": "Compra",
    "orcamento": "Orçamento", "confirmado": "Confirmado", "producao": "Em produção",
    "pronto": "Pronto", "entregue": "Entregue", "cancelado": "Cancelado",
    "aberta": "Aberta", "em_andamento": "Em andamento", "atendida": "Atendida",
    "cancelada": "Cancelada",
    "baixa": "Baixa", "normal": "Normal", "alta": "Alta", "urgente": "Urgente",
    "manual": "Manual", "pedido": "Pedido", "estoque_minimo": "Estoque mínimo",
    "emitida": "Emitida",
    "admin": "Administrador", "operador": "Operador",
}

# Cor da tarja de cada situação.
TOM = {
    "orcamento": "neutro", "confirmado": "info", "producao": "atencao",
    "pronto": "info", "entregue": "ok", "cancelado": "erro",
    "aberta": "atencao", "em_andamento": "info", "atendida": "ok",
    "cancelada": "erro", "emitida": "ok",
    "baixa": "neutro", "normal": "info", "alta": "atencao", "urgente": "erro",
    "entrada": "ok", "saida": "atencao", "sim": "ok", "nao": "neutro",
}


def rotulo(chave):
    return ROTULOS.get(chave, (chave or "").replace("_", " ").capitalize())


def u(caminho=""):
    """Monta URL respeitando o prefixo de hospedagem."""
    return (config.PREFIXO or "") + caminho


# --------------------------------------------------------------- componentes

def tarja(valor, texto=None):
    return (f'<span class="tarja tarja--{TOM.get(valor, "neutro")}">'
            f'{esc(texto or rotulo(valor))}</span>')


def cartao_indicador(titulo, valor, detalhe="", destino="", tom=""):
    interno = (f'<span class="ind__titulo">{esc(titulo)}</span>'
               f'<strong class="ind__valor">{esc(valor)}</strong>'
               f'<span class="ind__detalhe">{esc(detalhe)}</span>')
    classe = f"ind ind--{tom}" if tom else "ind"
    if destino:
        return f'<a class="{classe}" href="{u(destino)}">{interno}</a>'
    return f'<div class="{classe}">{interno}</div>'


def tabela(colunas, linhas, vazio="Nenhum registro encontrado."):
    """colunas: lista de (título, classe). linhas: lista de listas de HTML."""
    if not linhas:
        return f'<p class="vazio">{esc(vazio)}</p>'
    cabeca = "".join(
        f'<th class="{c[1]}">{esc(c[0])}</th>' if isinstance(c, (tuple, list))
        else f"<th>{esc(c)}</th>" for c in colunas)
    corpo = []
    for linha in linhas:
        celulas = "".join(
            f'<td class="{c[1]}">{c[0]}</td>' if isinstance(c, (tuple, list))
            else f"<td>{c}</td>" for c in linha)
        corpo.append(f"<tr>{celulas}</tr>")
    return (f'<div class="tabela-area"><table class="tabela">'
            f"<thead><tr>{cabeca}</tr></thead>"
            f'<tbody>{"".join(corpo)}</tbody></table></div>')


def campo(nome, etiqueta, valor="", tipo="text", obrigatorio=False, dica="",
          atributos="", largura=""):
    marca = ' <span class="obrig">*</span>' if obrigatorio else ""
    req = " required" if obrigatorio else ""
    ajuda = f'<span class="dica">{esc(dica)}</span>' if dica else ""
    return (f'<div class="campo {largura}">'
            f'<label for="{nome}">{esc(etiqueta)}{marca}</label>'
            f'<input id="{nome}" name="{nome}" type="{tipo}" '
            f'value="{esc(valor)}"{req} {atributos}>{ajuda}</div>')


def area(nome, etiqueta, valor="", linhas=3, dica=""):
    ajuda = f'<span class="dica">{esc(dica)}</span>' if dica else ""
    return (f'<div class="campo campo--largo"><label for="{nome}">{esc(etiqueta)}</label>'
            f'<textarea id="{nome}" name="{nome}" rows="{linhas}">{esc(valor)}</textarea>'
            f"{ajuda}</div>")


def selecao(nome, etiqueta, opcoes, valor="", obrigatorio=False, dica="", largura=""):
    """opcoes: lista de (valor, texto)."""
    marca = ' <span class="obrig">*</span>' if obrigatorio else ""
    itens = "".join(
        f'<option value="{esc(v)}"{" selected" if str(v) == str(valor) else ""}>'
        f"{esc(t)}</option>" for v, t in opcoes)
    ajuda = f'<span class="dica">{esc(dica)}</span>' if dica else ""
    return (f'<div class="campo {largura}"><label for="{nome}">{esc(etiqueta)}{marca}</label>'
            f'<select id="{nome}" name="{nome}"{" required" if obrigatorio else ""}>'
            f"{itens}</select>{ajuda}</div>")


def busca(destino, valor="", texto="Buscar por código ou descrição", extra=""):
    return (f'<form class="busca" method="get" action="{u(destino)}">'
            f'<input type="search" name="q" value="{esc(valor)}" placeholder="{esc(texto)}">'
            f"{extra}"
            f'<button class="bt bt--claro" type="submit">Buscar</button></form>')


def aviso_da_url(req):
    texto = req.arg("aviso")
    if not texto:
        return ""
    tom = "erro" if texto.lower().startswith(("erro", "não", "nao")) else "ok"
    return f'<div class="aviso aviso--{tom}">{esc(texto)}</div>'


def acoes(*botoes):
    return f'<div class="acoes">{"".join(botoes)}</div>'


def bt(texto, destino="", classe="bt--claro", tipo="", confirmar=""):
    atributo = f' onclick="return confirm(\'{esc(confirmar)}\')"' if confirmar else ""
    if tipo:
        return f'<button class="bt {classe}" type="{tipo}"{atributo}>{esc(texto)}</button>'
    return f'<a class="bt {classe}" href="{u(destino)}"{atributo}>{esc(texto)}</a>'


# -------------------------------------------------------------------- layout

def _menu(ativo):
    itens = []
    for destino, texto, chave in MENU:
        marca = ' class="ativo"' if chave == ativo else ""
        itens.append(f'<li><a href="{u(destino)}"{marca}>{esc(texto)}</a></li>')
    return "".join(itens)


def _splash():
    """Tela de carregamento com a logomarca, mostrada uma vez por sessão."""
    return f"""<div id="splash" class="splash">
  <div class="splash__caixa">
    <img src="{u('/static/img/logo-voasul-branco.svg')}" alt="VoaSul" class="splash__logo">
    <p class="splash__texto">Controle de estoque e demandas</p>
    <div class="splash__barra"><span></span></div>
  </div>
</div>"""


def layout(titulo, conteudo, ativo="", usuario=None, acoes_topo="", largo=False):
    nome = esc(usuario["nome"]) if usuario else ""
    # Mostra o login junto do papel: só o papel acabava repetindo o nome
    # no caso do usuário "Administrador".
    identificacao = (f'@{esc(usuario["login"])} · {rotulo(usuario["papel"])}'
                     if usuario else "")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)} — VOA-SUL ERP</title>
<link rel="icon" href="{u('/static/img/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{u('/static/app.css')}">
<meta name="theme-color" content="#0a2050">
</head>
<body>
{_splash()}
<div class="app">
  <aside class="lateral">
    <a class="lateral__marca" href="{u('/')}">
      <img src="{u('/static/img/logo-voasul-branco.svg')}" alt="VoaSul">
      <span>ERP</span>
    </a>
    <nav><ul>{_menu(ativo)}</ul></nav>
    <div class="lateral__rodape">
      <a href="{u('/configuracoes')}">Configurações</a>
      <a href="{u('/sair')}">Sair</a>
    </div>
  </aside>
  <main class="conteudo">
    <header class="topo">
      <div>
        <h1>{esc(titulo)}</h1>
      </div>
      <div class="topo__direita">
        {acoes_topo}
        <div class="usuario"><strong>{nome}</strong><span>{identificacao}</span></div>
      </div>
    </header>
    <div class="{'area area--larga' if largo else 'area'}">
      {conteudo}
    </div>
  </main>
</div>
<script src="{u('/static/app.js')}"></script>
</body>
</html>"""


def layout_limpo(titulo, conteudo, corpo_classe="entrada"):
    """Páginas sem menu: login e folhas de impressão."""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)} — VOA-SUL</title>
<link rel="icon" href="{u('/static/img/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{u('/static/app.css')}">
</head>
<body class="{corpo_classe}">
{conteudo}
<script src="{u('/static/app.js')}"></script>
</body>
</html>"""
