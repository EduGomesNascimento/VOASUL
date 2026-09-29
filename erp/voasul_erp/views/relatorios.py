"""Relatórios gerenciais, com exportação em CSV."""

import csv
import io

from .. import consultas as q
from .. import db, ui, web
from ..util import data_br, esc, hoje_iso, moeda, numero, para_iso, quantidade

RELATORIOS = [
    ("estoque", "Posição de estoque",
     "Saldo, mínimo, custo médio e valor imobilizado de cada item."),
    ("minimo", "Itens abaixo do mínimo",
     "Lista de reposição, com a quantidade que falta para cada item."),
    ("movimentos", "Movimentações por período",
     "Entradas, saídas e ajustes em um intervalo de datas."),
    ("vendas", "Vendas por período",
     "Pedidos de venda emitidos, com total faturado e ticket médio."),
    ("abc", "Curva ABC de itens",
     "Ordena os itens pelo valor vendido e separa as classes A, B e C."),
    ("demandas", "Posição de demandas",
     "Demandas por situação e prioridade, com o que ainda falta."),
]


def _periodo(req):
    de = para_iso(req.arg("de")) or hoje_iso()[:8] + "01"
    ate = para_iso(req.arg("ate")) or hoje_iso()
    return de, ate


def _filtro_periodo(destino, de, ate):
    return f"""<form class="busca nao-imprime" method="get" action="{ui.u(destino)}">
  <label class="dica">De <input type="text" name="de" value="{esc(data_br(de))}"
    style="max-width:140px"></label>
  <label class="dica">Até <input type="text" name="ate" value="{esc(data_br(ate))}"
    style="max-width:140px"></label>
  <button class="bt bt--claro" type="submit">Aplicar</button>
</form>"""


def _csv(cabecalho, linhas):
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    return saida.getvalue()


def registrar(app):

    @app.rota("/relatorios")
    def indice(req):
        cartoes = "".join(f"""<a class="ind" href="{ui.u('/relatorios/' + chave)}">
  <span class="ind__titulo">Relatório</span>
  <strong style="display:block;font-size:1.05rem;color:var(--marinho);
                 margin:.2rem 0 .3rem">{esc(titulo)}</strong>
  <span class="ind__detalhe">{esc(descricao)}</span>
</a>""" for chave, titulo, descricao in RELATORIOS)

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <h2>Relatórios disponíveis</h2>
  <p class="dica">Todos podem ser impressos pelo navegador ou baixados em CSV
  (abre direto no Excel, separado por ponto e vírgula).</p>
  <div class="grade grade--2" style="margin-top:1rem">{cartoes}</div>
</div>"""
        return web.pagina(ui.layout("Relatórios", conteudo, "relatorios", req.usuario))

    # ------------------------------------------------------ posição de estoque
    def _dados_estoque(con, so_minimo=False):
        itens = [i for i in q.itens_com_saldo(con, so_abaixo_minimo=so_minimo)
                 if i["tipo"] != "servico"]
        dados = []
        for i in itens:
            medio = q.custo_medio(con, i["id"])
            dados.append({
                "item": i, "medio": medio, "valor": i["saldo"] * medio,
                "falta": max(float(i["estoque_min"]) - float(i["saldo"]), 0)})
        return dados

    @app.rota("/relatorios/estoque")
    def estoque(req):
        with db.aberto() as con:
            dados = _dados_estoque(con)
        linhas = [[
            f'<span class="mono">{esc(d["item"]["codigo"])}</span>',
            esc(d["item"]["descricao"]),
            ui.rotulo(d["item"]["tipo"]),
            (esc(d["item"]["localizacao"] or "—"), "meio"),
            (quantidade(d["item"]["saldo"]), "num"),
            (quantidade(d["item"]["estoque_min"]), "num"),
            (moeda(d["medio"]), "num"),
            (moeda(d["valor"]), "num"),
        ] for d in dados]
        total = sum(d["valor"] for d in dados)

        conteudo = f"""
<div class="painel">
  <div class="painel__cabeca">
    <h2>Posição de estoque em {data_br(hoje_iso())}</h2>
    {ui.acoes(ui.bt('Baixar CSV', '/relatorios/estoque.csv', 'bt--claro bt--mini'),
              ui.bt('Imprimir', '?imprimir=1', 'bt--claro bt--mini'))}
  </div>
  {ui.tabela(['Código', 'Descrição', 'Tipo', ('Local', 'meio'), ('Saldo', 'num'),
              ('Mínimo', 'num'), ('Custo méd.', 'num'), ('Valor', 'num')], linhas)}
  <table class="doc__totais" style="margin-top:1rem">
    <tr><td>Itens controlados</td><td class="num">{len(dados)}</td></tr>
    <tr><td>Valor total em estoque</td><td class="num">{moeda(total)}</td></tr>
  </table>
</div>"""
        return web.pagina(ui.layout("Posição de estoque", conteudo, "relatorios",
                                    req.usuario, _voltar()))

    @app.rota("/relatorios/estoque.csv")
    def estoque_csv(req):
        with db.aberto() as con:
            dados = _dados_estoque(con)
        linhas = [[d["item"]["codigo"], d["item"]["descricao"],
                   ui.rotulo(d["item"]["tipo"]), d["item"]["unidade"],
                   d["item"]["localizacao"], numero(d["item"]["saldo"], 3),
                   numero(d["item"]["estoque_min"], 3), numero(d["medio"]),
                   numero(d["valor"])] for d in dados]
        texto = _csv(["Codigo", "Descricao", "Tipo", "Unidade", "Local", "Saldo",
                      "Minimo", "Custo medio", "Valor"], linhas)
        return web.arquivo_csv(f"estoque-{hoje_iso()}.csv", texto)

    # -------------------------------------------------------- abaixo do mínimo
    @app.rota("/relatorios/minimo")
    def minimo(req):
        with db.aberto() as con:
            dados = _dados_estoque(con, so_minimo=True)
        linhas = [[
            f'<a href="{ui.u("/itens/" + str(d["item"]["id"]))}" class="mono">'
            f'{esc(d["item"]["codigo"])}</a>',
            esc(d["item"]["descricao"]),
            (quantidade(d["item"]["saldo"]), "num negativo"),
            (quantidade(d["item"]["estoque_min"]), "num"),
            (quantidade(d["falta"]), "num"),
            (moeda(d["falta"] * d["medio"]), "num"),
        ] for d in dados]
        custo = sum(d["falta"] * d["medio"] for d in dados)

        conteudo = f"""
<div class="painel">
  <div class="painel__cabeca">
    <h2>Itens abaixo do estoque mínimo</h2>
    {ui.acoes(ui.bt('Gerar demandas', '/demandas/gerar', 'bt--principal bt--mini'),
              ui.bt('Imprimir', '?imprimir=1', 'bt--claro bt--mini'))}
  </div>
  {ui.tabela(['Código', 'Descrição', ('Saldo', 'num'), ('Mínimo', 'num'),
              ('Falta', 'num'), ('Custo da reposição', 'num')], linhas,
             'Nenhum item abaixo do mínimo. Estoque em dia.')}
  <table class="doc__totais" style="margin-top:1rem">
    <tr><td>Itens a repor</td><td class="num">{len(dados)}</td></tr>
    <tr><td>Custo estimado da reposição</td><td class="num">{moeda(custo)}</td></tr>
  </table>
</div>"""
        return web.pagina(ui.layout("Itens abaixo do mínimo", conteudo, "relatorios",
                                    req.usuario, _voltar()))

    # ---------------------------------------------------------- movimentações
    @app.rota("/relatorios/movimentos")
    def movimentos(req):
        de, ate = _periodo(req)
        with db.aberto() as con:
            registros = con.execute(
                "SELECT m.*, i.codigo, i.descricao, i.unidade FROM movimento m "
                "JOIN item i ON i.id = m.item_id WHERE m.data BETWEEN ? AND ? "
                "ORDER BY m.data, m.id", (de, ate)).fetchall()

        entradas = sum(m["quantidade"] for m in registros if m["tipo"] == "entrada")
        saidas = sum(m["quantidade"] for m in registros if m["tipo"] == "saida")
        valor_entradas = sum(m["quantidade"] * m["custo_unit"]
                             for m in registros if m["tipo"] == "entrada")

        linhas = [[
            data_br(m["data"]),
            f'<span class="mono">{esc(m["codigo"])}</span> {esc(m["descricao"])}',
            ui.tarja(m["tipo"]),
            (quantidade(m["quantidade"]) + " " + m["unidade"], "num"),
            (moeda(m["custo_unit"]), "num"),
            (moeda(m["quantidade"] * m["custo_unit"]), "num"),
            esc(m["documento"] or "—"),
        ] for m in registros]

        conteudo = f"""
<div class="painel">
  <div class="painel__cabeca">
    <h2>Movimentações de {data_br(de)} a {data_br(ate)}</h2>
    {_filtro_periodo('/relatorios/movimentos', de, ate)}
  </div>
  <div class="grade grade--4" style="margin-bottom:1.2rem">
    {ui.cartao_indicador('Lançamentos', str(len(registros)), 'No período')}
    {ui.cartao_indicador('Entradas', quantidade(entradas), 'Unidades recebidas', tom='ok')}
    {ui.cartao_indicador('Saídas', quantidade(saidas), 'Unidades consumidas', tom='atencao')}
    {ui.cartao_indicador('Valor das entradas', moeda(valor_entradas), 'Custo das compras')}
  </div>
  {ui.tabela(['Data', 'Item', 'Tipo', ('Qtd.', 'num'), ('Custo un.', 'num'),
              ('Total', 'num'), 'Documento'], linhas,
             'Nenhuma movimentação nesse período.')}
</div>"""
        return web.pagina(ui.layout("Movimentações por período", conteudo,
                                    "relatorios", req.usuario, _voltar()))

    # ----------------------------------------------------------------- vendas
    @app.rota("/relatorios/vendas")
    def vendas(req):
        de, ate = _periodo(req)
        with db.aberto() as con:
            pedidos = con.execute(
                "SELECT p.*, pa.nome AS parceiro FROM pedido p "
                "LEFT JOIN parceiro pa ON pa.id = p.parceiro_id "
                "WHERE p.tipo = 'venda' AND p.status <> 'cancelado' "
                "AND p.data_emissao BETWEEN ? AND ? ORDER BY p.data_emissao, p.id",
                (de, ate)).fetchall()
            totais = {p["id"]: q.total_pedido(con, p)["total"] for p in pedidos}

        faturado = sum(totais.values())
        medio = faturado / len(pedidos) if pedidos else 0
        linhas = [[
            f'<a href="{ui.u("/pedidos/" + str(p["id"]))}" class="mono">'
            f'{esc(p["numero"])}</a>',
            data_br(p["data_emissao"]),
            esc(p["parceiro"] or "—"),
            ui.tarja(p["status"]),
            (moeda(totais[p["id"]]), "num"),
        ] for p in pedidos]

        conteudo = f"""
<div class="painel">
  <div class="painel__cabeca">
    <h2>Vendas de {data_br(de)} a {data_br(ate)}</h2>
    {_filtro_periodo('/relatorios/vendas', de, ate)}
  </div>
  <div class="grade grade--3" style="margin-bottom:1.2rem">
    {ui.cartao_indicador('Pedidos de venda', str(len(pedidos)), 'Fora os cancelados')}
    {ui.cartao_indicador('Total faturado', moeda(faturado), 'Soma dos pedidos')}
    {ui.cartao_indicador('Ticket médio', moeda(medio), 'Por pedido')}
  </div>
  {ui.tabela(['Número', 'Emissão', 'Cliente', 'Situação', ('Total', 'num')],
             linhas, 'Nenhuma venda nesse período.')}
</div>"""
        return web.pagina(ui.layout("Vendas por período", conteudo, "relatorios",
                                    req.usuario, _voltar()))

    # -------------------------------------------------------------- curva ABC
    @app.rota("/relatorios/abc")
    def abc(req):
        de, ate = _periodo(req)
        with db.aberto() as con:
            registros = con.execute(
                "SELECT i.id, i.codigo, i.descricao, "
                " SUM(pi.quantidade) AS qtd, "
                " SUM(pi.quantidade * pi.preco_unit - pi.desconto) AS valor "
                "FROM pedido_item pi JOIN pedido p ON p.id = pi.pedido_id "
                "JOIN item i ON i.id = pi.item_id "
                "WHERE p.tipo = 'venda' AND p.status <> 'cancelado' "
                "AND p.data_emissao BETWEEN ? AND ? "
                "GROUP BY i.id ORDER BY valor DESC", (de, ate)).fetchall()

        total = sum(r["valor"] or 0 for r in registros)
        linhas, acumulado = [], 0.0
        for r in registros:
            valor = float(r["valor"] or 0)
            acumulado += valor
            fatia = (acumulado / total * 100) if total else 0
            classe = "A" if fatia <= 80 else ("B" if fatia <= 95 else "C")
            tom = {"A": "ok", "B": "info", "C": "neutro"}[classe]
            linhas.append([
                f'<a href="{ui.u("/itens/" + str(r["id"]))}" class="mono">'
                f'{esc(r["codigo"])}</a>',
                esc(r["descricao"]),
                (quantidade(r["qtd"]), "num"),
                (moeda(valor), "num"),
                (numero((valor / total * 100) if total else 0, 1) + "%", "num"),
                (numero(fatia, 1) + "%", "num"),
                (f'<span class="tarja tarja--{tom}">Classe {classe}</span>', "meio"),
            ])

        conteudo = f"""
<div class="painel">
  <div class="painel__cabeca">
    <h2>Curva ABC de {data_br(de)} a {data_br(ate)}</h2>
    {_filtro_periodo('/relatorios/abc', de, ate)}
  </div>
  <p class="dica">Classe A: itens que somam até 80% do valor vendido.
  Classe B: de 80% a 95%. Classe C: o restante.</p>
  {ui.tabela(['Código', 'Descrição', ('Qtd. vendida', 'num'), ('Valor', 'num'),
              ('% do total', 'num'), ('% acumulado', 'num'), ('Classe', 'meio')],
             linhas, 'Nenhuma venda nesse período.')}
  <table class="doc__totais" style="margin-top:1rem">
    <tr><td>Valor total vendido</td><td class="num">{moeda(total)}</td></tr>
  </table>
</div>"""
        return web.pagina(ui.layout("Curva ABC", conteudo, "relatorios",
                                    req.usuario, _voltar()))

    # --------------------------------------------------------------- demandas
    @app.rota("/relatorios/demandas")
    def demandas(req):
        with db.aberto() as con:
            registros = con.execute(
                "SELECT d.*, i.codigo, i.descricao, i.unidade, "
                " COALESCE(s.quantidade, 0) AS saldo FROM demanda d "
                "JOIN item i ON i.id = d.item_id "
                "LEFT JOIN saldo s ON s.item_id = i.id "
                "ORDER BY CASE d.status WHEN 'aberta' THEN 0 WHEN 'em_andamento' "
                "THEN 1 WHEN 'atendida' THEN 2 ELSE 3 END, d.id DESC").fetchall()

        por_situacao = {}
        for r in registros:
            por_situacao[r["status"]] = por_situacao.get(r["status"], 0) + 1
        cartoes = "".join(
            ui.cartao_indicador(ui.rotulo(s), str(n), "demanda(s)")
            for s, n in sorted(por_situacao.items()))

        linhas = [[
            f'<a href="{ui.u("/demandas/" + str(r["id"]))}" class="mono">'
            f'{esc(r["numero"])}</a>',
            f'<span class="mono">{esc(r["codigo"])}</span> {esc(r["descricao"])}',
            (quantidade(r["quantidade"]) + " " + r["unidade"], "num"),
            (quantidade(r["saldo"]), "num"),
            (quantidade(max(r["quantidade"] - r["saldo"], 0)), "num"),
            ui.rotulo(r["origem"]),
            ui.tarja(r["prioridade"]),
            data_br(r["prazo"]) or "—",
            ui.tarja(r["status"]),
        ] for r in registros]

        conteudo = f"""
<div class="painel">
  <div class="painel__cabeca">
    <h2>Posição de demandas</h2>
    {ui.bt('Imprimir', '?imprimir=1', 'bt--claro bt--mini')}
  </div>
  <div class="grade grade--4" style="margin-bottom:1.2rem">{cartoes}</div>
  {ui.tabela(['Número', 'Item', ('Pedido', 'num'), ('Saldo', 'num'),
              ('Falta', 'num'), 'Origem', 'Prioridade', 'Prazo', 'Situação'],
             linhas, 'Nenhuma demanda registrada.')}
</div>"""
        return web.pagina(ui.layout("Posição de demandas", conteudo, "relatorios",
                                    req.usuario, _voltar()))

    def _voltar():
        return ui.acoes(ui.bt("Todos os relatórios", "/relatorios", "bt--claro"))
