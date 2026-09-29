"""Estoque: posição atual e lançamento de movimentos."""

from .. import consultas as q
from .. import db, ui, web
from ..util import (data_br, esc, hoje_iso, moeda, para_float, para_iso,
                    quantidade)

TIPOS_MOV = [("entrada", "Entrada"), ("saida", "Saída"),
             ("ajuste", "Ajuste (use sinal negativo para reduzir)")]


def registrar(app):

    @app.rota("/estoque")
    def posicao(req):
        busca = req.arg("q")
        so_minimo = req.arg("filtro") == "minimo"
        with db.aberto() as con:
            itens = [i for i in q.itens_com_saldo(con, busca, so_abaixo_minimo=so_minimo)
                     if i["tipo"] != "servico"]
            medios = {i["id"]: q.custo_medio(con, i["id"]) for i in itens}

        linhas, total = [], 0.0
        for i in itens:
            medio = medios[i["id"]]
            valor = i["saldo"] * medio
            total += valor
            baixo = i["saldo"] < i["estoque_min"]
            falta = max(i["estoque_min"] - i["saldo"], 0)
            linhas.append([
                f'<a href="{ui.u("/itens/" + str(i["id"]))}" class="mono">'
                f'{esc(i["codigo"])}</a>',
                esc(i["descricao"]),
                (esc(i["localizacao"] or "—"), "meio"),
                (quantidade(i["saldo"]) + " " + i["unidade"],
                 "num negativo" if baixo else "num"),
                (quantidade(i["estoque_min"]), "num"),
                (quantidade(falta) if falta else "—", "num"),
                (moeda(medio), "num"),
                (moeda(valor), "num"),
                (f'<a class="bt bt--claro bt--mini" '
                 f'href="{ui.u("/estoque/movimentar?item=" + str(i["id"]))}">Lançar</a>',
                 "min"),
            ])

        filtro_extra = (f'<label class="dica" style="display:flex;gap:.35rem;'
                        f'align-items:center"><input type="checkbox" name="filtro" '
                        f'value="minimo" style="width:auto"'
                        f'{" checked" if so_minimo else ""}> só abaixo do mínimo</label>')

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="grade grade--3" style="margin-bottom:1.4rem">
  {ui.cartao_indicador('Itens controlados', str(len(itens)), 'Fora os serviços')}
  {ui.cartao_indicador('Valor total', moeda(total), 'Saldo pelo custo médio')}
  {ui.cartao_indicador('Abaixo do mínimo',
                       str(len([i for i in itens if i['saldo'] < i['estoque_min']])),
                       'Precisam de reposição', '/estoque?filtro=minimo')}
</div>
<div class="painel">
  <div class="painel__cabeca">
    {ui.busca('/estoque', busca, 'Código ou descrição', filtro_extra)}
    {ui.acoes(ui.bt('Lançar movimento', '/estoque/movimentar', 'bt--principal bt--mini'),
              ui.bt('Histórico', '/estoque/movimentos', 'bt--claro bt--mini'),
              ui.bt('Exportar CSV', '/relatorios/estoque.csv', 'bt--claro bt--mini'))}
  </div>
  {ui.tabela(['Código', 'Descrição', ('Local', 'meio'), ('Saldo', 'num'),
              ('Mínimo', 'num'), ('Falta', 'num'), ('Custo méd.', 'num'),
              ('Valor', 'num'), ''], linhas, 'Nenhum item nesse filtro.')}
</div>"""
        return web.pagina(ui.layout("Estoque", conteudo, "estoque", req.usuario))

    # ------------------------------------------------------------- movimentar
    @app.rota("/estoque/movimentar", metodos=("GET", "POST"))
    def movimentar(req):
        with db.aberto() as con:
            itens = q.itens_com_saldo(con)
            opcoes = [("", "Selecione o item…")] + [
                (str(i["id"]),
                 f'{i["codigo"]} — {i["descricao"]} (saldo {quantidade(i["saldo"])} '
                 f'{i["unidade"]})')
                for i in itens if i["tipo"] != "servico"]

        if req.metodo == "POST":
            item_id = req.texto("item_id")
            tipo = req.texto("tipo", "entrada")
            qtd = para_float(req.texto("quantidade"))
            if not item_id:
                return _form_mov(req, opcoes, "Escolha o item.")
            if tipo != "ajuste" and qtd <= 0:
                return _form_mov(req, opcoes,
                                 "A quantidade deve ser maior que zero.")
            if tipo == "ajuste" and qtd == 0:
                return _form_mov(req, opcoes,
                                 "No ajuste, informe um valor diferente de zero.")
            with db.transacao() as con:
                if tipo == "saida":
                    disponivel = q.saldo_item(con, int(item_id))
                    if qtd > disponivel:
                        return _form_mov(
                            req, opcoes,
                            f"Saída de {quantidade(qtd)} maior que o saldo disponível "
                            f"({quantidade(disponivel)}). Ajuste a quantidade ou "
                            f"lance um ajuste de inventário.")
                q.registrar_movimento(
                    con, int(item_id), tipo, qtd,
                    para_float(req.texto("custo_unit")),
                    req.texto("documento"), req.texto("observacao"),
                    usuario_id=req.usuario["id"],
                    data=para_iso(req.texto("data")) or hoje_iso())
            return web.redirecionar(f"/itens/{item_id}", "Movimento lançado.")

        return _form_mov(req, opcoes)

    def _form_mov(req, opcoes, erro=""):
        pre = req.arg("item") or req.texto("item_id")
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        corpo = f"""{alerta}
<form method="post" action="{ui.u('/estoque/movimentar')}">
  <div class="painel">
    <div class="formulario">
      {ui.selecao('item_id', 'Item', opcoes, pre, obrigatorio=True, largura='campo--largo')}
      {ui.selecao('tipo', 'Tipo de movimento', TIPOS_MOV, req.texto('tipo', 'entrada'),
                  obrigatorio=True)}
      {ui.campo('quantidade', 'Quantidade', req.texto('quantidade'), obrigatorio=True,
                dica='No ajuste, use sinal negativo para reduzir o saldo.')}
      {ui.campo('custo_unit', 'Custo unitário (R$)', req.texto('custo_unit'),
                dica='Usado no cálculo do custo médio. Só vale para entradas.')}
      {ui.campo('data', 'Data', data_br(hoje_iso()),
                dica='Formato dd/mm/aaaa.')}
      {ui.campo('documento', 'Documento', req.texto('documento'),
                dica='Nota do fornecedor, número do pedido ou ordem interna.')}
      {ui.area('observacao', 'Observação', req.texto('observacao'))}
    </div>
    <div class="rodape-form">
      {ui.bt('Lançar movimento', classe='bt--principal', tipo='submit')}
      {ui.bt('Cancelar', '/estoque', 'bt--claro')}
    </div>
  </div>
</form>"""
        return web.pagina(ui.layout("Lançar movimento de estoque", corpo,
                                    "estoque", req.usuario))

    # -------------------------------------------------------------- histórico
    @app.rota("/estoque/movimentos")
    def historico(req):
        busca, tipo = req.arg("q"), req.arg("tipo")
        de, ate = para_iso(req.arg("de")), para_iso(req.arg("ate"))
        filtros, valores = ["1=1"], []
        if busca:
            filtros.append("(i.codigo LIKE ? OR i.descricao LIKE ? OR m.documento LIKE ?)")
            valores += [f"%{busca}%"] * 3
        if tipo:
            filtros.append("m.tipo = ?")
            valores.append(tipo)
        if de:
            filtros.append("m.data >= ?")
            valores.append(de)
        if ate:
            filtros.append("m.data <= ?")
            valores.append(ate)

        with db.aberto() as con:
            movimentos = con.execute(
                f"SELECT m.*, i.codigo, i.descricao, i.unidade, u.nome AS usuario "
                f"FROM movimento m JOIN item i ON i.id = m.item_id "
                f"LEFT JOIN usuario u ON u.id = m.usuario_id "
                f"WHERE {' AND '.join(filtros)} ORDER BY m.id DESC LIMIT 400",
                valores).fetchall()

        linhas = [[
            data_br(m["data"]),
            f'<a href="{ui.u("/itens/" + str(m["item_id"]))}" class="mono">'
            f'{esc(m["codigo"])}</a> {esc(m["descricao"])}',
            ui.tarja(m["tipo"]),
            (quantidade(m["quantidade"]) + " " + m["unidade"], "num"),
            (moeda(m["custo_unit"]), "num"),
            esc(m["documento"] or "—"),
            esc(m["usuario"] or "—"),
            esc(m["observacao"] or ""),
        ] for m in movimentos]

        extra = (f'<select name="tipo"><option value="">Todos os tipos</option>' +
                 "".join(f'<option value="{v}"{" selected" if v == tipo else ""}>'
                         f'{esc(t.split(" (")[0])}</option>' for v, t in TIPOS_MOV) +
                 "</select>"
                 f'<input type="text" name="de" value="{esc(req.arg("de"))}" '
                 f'placeholder="De dd/mm/aaaa" style="max-width:150px">'
                 f'<input type="text" name="ate" value="{esc(req.arg("ate"))}" '
                 f'placeholder="Até dd/mm/aaaa" style="max-width:150px">')

        conteudo = f"""
<div class="painel">
  <div class="painel__cabeca">
    {ui.busca('/estoque/movimentos', busca, 'Item ou documento', extra)}
    <span class="dica">{len(movimentos)} movimento(s)</span>
  </div>
  {ui.tabela(['Data', 'Item', 'Tipo', ('Qtd.', 'num'), ('Custo un.', 'num'),
              'Documento', 'Usuário', 'Observação'], linhas,
             'Nenhum movimento nesse período.')}
</div>"""
        return web.pagina(ui.layout(
            "Histórico de movimentações", conteudo, "estoque", req.usuario,
            ui.acoes(ui.bt("Voltar ao estoque", "/estoque", "bt--claro"))))
