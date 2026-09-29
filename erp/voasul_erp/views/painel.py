"""Painel inicial: indicadores e atalhos do dia a dia."""

from .. import consultas as q
from .. import db, ui, web
from ..util import data_br, esc, moeda, quantidade


def registrar(app):

    @app.rota("/")
    def painel(req):
        with db.aberto() as con:
            itens = q.itens_com_saldo(con)
            abaixo = [i for i in itens if i["tipo"] != "servico"
                      and i["saldo"] < i["estoque_min"]]
            valor_estoque = sum(i["saldo"] * q.custo_medio(con, i["id"])
                                for i in itens if i["tipo"] != "servico")

            pedidos_abertos = con.execute(
                "SELECT COUNT(*) AS n FROM pedido "
                "WHERE status NOT IN ('entregue','cancelado')").fetchone()["n"]
            demandas_abertas = con.execute(
                "SELECT COUNT(*) AS n FROM demanda "
                "WHERE status IN ('aberta','em_andamento')").fetchone()["n"]
            urgentes = con.execute(
                "SELECT COUNT(*) AS n FROM demanda WHERE prioridade = 'urgente' "
                "AND status IN ('aberta','em_andamento')").fetchone()["n"]

            ultimos_pedidos = con.execute(
                "SELECT p.*, pa.nome AS parceiro FROM pedido p "
                "LEFT JOIN parceiro pa ON pa.id = p.parceiro_id "
                "ORDER BY p.id DESC LIMIT 8").fetchall()
            totais = {p["id"]: q.total_pedido(con, p)["total"] for p in ultimos_pedidos}

            movimentos = con.execute(
                "SELECT m.*, i.codigo, i.descricao FROM movimento m "
                "JOIN item i ON i.id = m.item_id ORDER BY m.id DESC LIMIT 8").fetchall()

            demandas = con.execute(
                "SELECT d.*, i.codigo, i.descricao FROM demanda d "
                "JOIN item i ON i.id = d.item_id "
                "WHERE d.status IN ('aberta','em_andamento') "
                "ORDER BY CASE d.prioridade WHEN 'urgente' THEN 0 WHEN 'alta' THEN 1 "
                "WHEN 'normal' THEN 2 ELSE 3 END, d.prazo LIMIT 8").fetchall()

        indicadores = "".join([
            ui.cartao_indicador("Pedidos em aberto", str(pedidos_abertos),
                                "Fora de entregue e cancelado", "/pedidos"),
            ui.cartao_indicador("Demandas pendentes", str(demandas_abertas),
                                f"{urgentes} urgente(s)", "/demandas",
                                "erro" if urgentes else ""),
            ui.cartao_indicador("Itens abaixo do mínimo", str(len(abaixo)),
                                "Precisam de reposição", "/estoque?filtro=minimo",
                                "atencao" if abaixo else "ok"),
            ui.cartao_indicador("Valor em estoque", moeda(valor_estoque),
                                "Pelo custo médio das entradas", "/relatorios/estoque"),
        ])

        linhas_pedidos = [[
            f'<a href="{ui.u("/pedidos/" + str(p["id"]))}" class="mono">{esc(p["numero"])}</a>',
            ui.rotulo(p["tipo"]),
            esc(p["parceiro"] or "—"),
            data_br(p["data_emissao"]),
            ui.tarja(p["status"]),
            (moeda(totais[p["id"]]), "num"),
        ] for p in ultimos_pedidos]

        linhas_mov = [[
            data_br(m["data"]),
            f'<span class="mono">{esc(m["codigo"])}</span> {esc(m["descricao"])}',
            ui.tarja(m["tipo"]),
            (quantidade(m["quantidade"]), "num"),
            esc(m["documento"] or "—"),
        ] for m in movimentos]

        linhas_dem = [[
            f'<a href="{ui.u("/demandas/" + str(d["id"]))}" class="mono">{esc(d["numero"])}</a>',
            f'<span class="mono">{esc(d["codigo"])}</span> {esc(d["descricao"])}',
            (quantidade(d["quantidade"]), "num"),
            ui.tarja(d["prioridade"]),
            data_br(d["prazo"]) or "—",
            ui.tarja(d["status"]),
        ] for d in demandas]

        alerta = ""
        if abaixo:
            nomes = ", ".join(f'{esc(i["codigo"])}' for i in abaixo[:6])
            resto = f" e mais {len(abaixo) - 6}" if len(abaixo) > 6 else ""
            alerta = (f'<div class="aviso aviso--erro">'
                      f'<strong>Reposição necessária.</strong> Abaixo do estoque '
                      f'mínimo: {nomes}{resto}. '
                      f'<a href="{ui.u("/demandas/gerar")}">Gerar demandas automaticamente</a>.'
                      f'</div>')

        conteudo = f"""
{ui.aviso_da_url(req)}
{alerta}
<div class="grade grade--4" style="margin-bottom:1.4rem">{indicadores}</div>

<div class="painel">
  <div class="painel__cabeca">
    <h2>Demandas prioritárias</h2>
    {ui.bt('Ver todas', '/demandas', 'bt--claro bt--mini')}
  </div>
  {ui.tabela(['Número', 'Item', ('Qtd.', 'num'), 'Prioridade', 'Prazo', 'Situação'],
             linhas_dem, 'Nenhuma demanda pendente. Produção em dia.')}
</div>

<div class="painel">
  <div class="painel__cabeca">
    <h2>Últimos pedidos</h2>
    {ui.bt('Novo pedido', '/pedidos/novo', 'bt--principal bt--mini')}
  </div>
  {ui.tabela(['Número', 'Tipo', 'Parceiro', 'Emissão', 'Situação', ('Total', 'num')],
             linhas_pedidos, 'Nenhum pedido registrado ainda.')}
</div>

<div class="painel">
  <div class="painel__cabeca">
    <h2>Últimas movimentações de estoque</h2>
    {ui.bt('Ver estoque', '/estoque', 'bt--claro bt--mini')}
  </div>
  {ui.tabela(['Data', 'Item', 'Tipo', ('Qtd.', 'num'), 'Documento'],
             linhas_mov, 'Nenhuma movimentação lançada.')}
</div>"""

        return web.pagina(ui.layout(
            "Painel", conteudo, "painel", req.usuario,
            ui.acoes(ui.bt("Novo pedido", "/pedidos/novo", "bt--principal"),
                     ui.bt("Lançar estoque", "/estoque/movimentar", "bt--claro"))))
