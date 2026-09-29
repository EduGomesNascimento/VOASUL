"""Demandas de produção e compra."""

from .. import consultas as q
from .. import db, ui, web
from ..util import (agora_iso, data_br, esc, para_float, para_iso, quantidade)

PRIORIDADES = [("baixa", "Baixa"), ("normal", "Normal"),
               ("alta", "Alta"), ("urgente", "Urgente")]
SITUACOES = [("aberta", "Aberta"), ("em_andamento", "Em andamento"),
             ("atendida", "Atendida"), ("cancelada", "Cancelada")]
ORDEM_PRIORIDADE = ("CASE d.prioridade WHEN 'urgente' THEN 0 WHEN 'alta' THEN 1 "
                    "WHEN 'normal' THEN 2 ELSE 3 END")


def registrar(app):

    @app.rota("/demandas")
    def lista(req):
        busca = req.arg("q")
        status = req.arg("status", "pendentes")
        filtros, valores = ["1=1"], []
        if busca:
            filtros.append("(d.numero LIKE ? OR i.codigo LIKE ? OR i.descricao LIKE ?)")
            valores += [f"%{busca}%"] * 3
        if status == "pendentes":
            filtros.append("d.status IN ('aberta','em_andamento')")
        elif status:
            filtros.append("d.status = ?")
            valores.append(status)

        with db.aberto() as con:
            demandas = con.execute(
                f"SELECT d.*, i.codigo, i.descricao, i.unidade, p.numero AS pedido "
                f"FROM demanda d JOIN item i ON i.id = d.item_id "
                f"LEFT JOIN pedido p ON p.id = d.pedido_id "
                f"WHERE {' AND '.join(filtros)} "
                f"ORDER BY {ORDEM_PRIORIDADE}, d.prazo, d.id DESC LIMIT 300",
                valores).fetchall()

        linhas = [[
            f'<a href="{ui.u("/demandas/" + str(d["id"]))}" class="mono">'
            f'{esc(d["numero"])}</a>',
            f'<a href="{ui.u("/itens/" + str(d["item_id"]))}" class="mono">'
            f'{esc(d["codigo"])}</a> {esc(d["descricao"])}',
            (quantidade(d["quantidade"]) + " " + d["unidade"], "num"),
            ui.rotulo(d["origem"]),
            ui.tarja(d["prioridade"]),
            data_br(d["prazo"]) or "—",
            (f'<a href="{ui.u("/pedidos/" + str(d["pedido_id"]))}" class="mono">'
             f'{esc(d["pedido"])}</a>' if d["pedido"] else "—"),
            ui.tarja(d["status"]),
        ] for d in demandas]

        opcoes = ('<select name="status">'
                  f'<option value="pendentes"{" selected" if status == "pendentes" else ""}>'
                  "Pendentes</option>"
                  f'<option value=""{" selected" if status == "" else ""}>Todas</option>' +
                  "".join(f'<option value="{v}"{" selected" if v == status else ""}>'
                          f"{esc(t)}</option>" for v, t in SITUACOES) + "</select>")

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <div class="painel__cabeca">
    {ui.busca('/demandas', busca, 'Número, código ou descrição', opcoes)}
    <span class="dica">{len(demandas)} demanda(s)</span>
  </div>
  {ui.tabela(['Número', 'Item', ('Qtd.', 'num'), 'Origem', 'Prioridade', 'Prazo',
              'Pedido', 'Situação'], linhas, 'Nenhuma demanda nesse filtro.')}
</div>"""
        return web.pagina(ui.layout(
            "Demandas", conteudo, "demandas", req.usuario,
            ui.acoes(ui.bt("Nova demanda", "/demandas/nova", "bt--principal"),
                     ui.bt("Gerar por estoque mínimo", "/demandas/gerar", "bt--escuro"))))

    # ------------------------------------------------------------ automáticas
    @app.rota("/demandas/gerar")
    def gerar(req):
        with db.transacao() as con:
            criadas = q.gerar_demandas_de_estoque_minimo(con)
        if criadas:
            return web.redirecionar("/demandas",
                                    f"{criadas} demanda(s) gerada(s) por estoque mínimo.")
        return web.redirecionar(
            "/demandas", "Nenhuma demanda nova: todos os itens abaixo do mínimo "
                         "já possuem demanda aberta.")

    @app.rota("/demandas/do-pedido/<int:pid>")
    def do_pedido(req, pid):
        """Abre uma demanda para cada item do pedido sem saldo suficiente."""
        with db.transacao() as con:
            pedido = con.execute("SELECT * FROM pedido WHERE id = ?", (pid,)).fetchone()
            if not pedido:
                return web.nao_encontrado("Pedido não encontrado.")
            criadas = 0
            for linha in q.itens_do_pedido(con, pid):
                if linha["item_tipo"] == "servico":
                    continue
                saldo = q.saldo_item(con, linha["item_id"])
                falta = float(linha["quantidade"]) - saldo
                if falta <= 0:
                    continue
                ja_tem = con.execute(
                    "SELECT 1 FROM demanda WHERE pedido_id = ? AND item_id = ? "
                    "AND status IN ('aberta','em_andamento')",
                    (pid, linha["item_id"])).fetchone()
                if ja_tem:
                    continue
                con.execute(
                    "INSERT INTO demanda (numero, item_id, quantidade, origem,"
                    " prioridade, status, prazo, pedido_id, observacao, criado_em)"
                    " VALUES (?,?,?,'pedido','alta','aberta',?,?,?,?)",
                    (q.proximo_numero(con, "demanda", "DM"), linha["item_id"], falta,
                     pedido["data_entrega"] or "", pid,
                     f"Falta {falta:g} para atender o pedido {pedido['numero']}.",
                     agora_iso()))
                criadas += 1
        if criadas:
            return web.redirecionar(f"/pedidos/{pid}",
                                    f"{criadas} demanda(s) aberta(s) para este pedido.")
        return web.redirecionar(
            f"/pedidos/{pid}",
            "Nenhuma demanda necessária: há saldo para todos os itens do pedido.")

    # ------------------------------------------------------------- formulário
    def _formulario(req, demanda=None, erro=""):
        novo = demanda is None
        with db.aberto() as con:
            itens = q.itens_com_saldo(con)
            opcoes = [("", "Selecione o item…")] + [
                (str(i["id"]),
                 f'{i["codigo"]} — {i["descricao"]} (saldo {quantidade(i["saldo"])})')
                for i in itens]
            numero_novo = (q.proximo_numero(con, "demanda", "DM") if novo
                           else demanda["numero"])

        d = dict(demanda) if demanda else {
            "item_id": req.arg("item", ""), "quantidade": "", "prioridade": "normal",
            "status": "aberta", "prazo": "", "observacao": ""}
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        destino = "/demandas/nova" if novo else f'/demandas/{demanda["id"]}/editar'

        corpo = f"""{alerta}
<form method="post" action="{ui.u(destino)}">
  <div class="painel">
    <div class="formulario">
      {ui.campo('numero', 'Número', numero_novo, atributos='readonly')}
      {ui.selecao('prioridade', 'Prioridade', PRIORIDADES, d['prioridade'],
                  obrigatorio=True)}
      {ui.selecao('status', 'Situação', SITUACOES, d['status'], obrigatorio=True)}
      {ui.selecao('item_id', 'Item', opcoes, d['item_id'] or '', obrigatorio=True,
                  largura='campo--largo')}
      {ui.campo('quantidade', 'Quantidade necessária',
                quantidade(d['quantidade']) if d['quantidade'] else '',
                obrigatorio=True)}
      {ui.campo('prazo', 'Prazo', data_br(d['prazo']), dica='Formato dd/mm/aaaa.')}
      {ui.area('observacao', 'Observações', d['observacao'])}
    </div>
    <div class="rodape-form">
      {ui.bt('Salvar demanda', classe='bt--principal', tipo='submit')}
      {ui.bt('Cancelar', '/demandas', 'bt--claro')}
    </div>
  </div>
</form>"""
        titulo = "Nova demanda" if novo else f'Demanda {demanda["numero"]}'
        return web.pagina(ui.layout(titulo, corpo, "demandas", req.usuario))

    @app.rota("/demandas/nova", metodos=("GET", "POST"))
    def nova(req):
        if req.metodo == "GET":
            return _formulario(req)
        item_id, qtd = req.texto("item_id"), para_float(req.texto("quantidade"))
        if not item_id:
            return _formulario(req, erro="Escolha o item.")
        if qtd <= 0:
            return _formulario(req, erro="A quantidade deve ser maior que zero.")
        with db.transacao() as con:
            num = q.proximo_numero(con, "demanda", "DM")
            con.execute(
                "INSERT INTO demanda (numero, item_id, quantidade, origem, prioridade,"
                " status, prazo, observacao, criado_em)"
                " VALUES (?,?,?,'manual',?,?,?,?,?)",
                (num, int(item_id), qtd, req.texto("prioridade", "normal"),
                 req.texto("status", "aberta"), para_iso(req.texto("prazo")),
                 req.texto("observacao"), agora_iso()))
        return web.redirecionar("/demandas", f"Demanda {num} criada.")

    @app.rota("/demandas/<int:did>/editar", metodos=("GET", "POST"))
    def editar(req, did):
        with db.aberto() as con:
            demanda = con.execute("SELECT * FROM demanda WHERE id = ?", (did,)).fetchone()
        if not demanda:
            return web.nao_encontrado("Demanda não encontrada.")
        if req.metodo == "GET":
            return _formulario(req, demanda)
        qtd = para_float(req.texto("quantidade"))
        if qtd <= 0:
            return _formulario(req, demanda, "A quantidade deve ser maior que zero.")
        with db.aberto() as con:
            con.execute(
                "UPDATE demanda SET item_id=?, quantidade=?, prioridade=?, status=?,"
                " prazo=?, observacao=? WHERE id=?",
                (int(req.texto("item_id") or demanda["item_id"]), qtd,
                 req.texto("prioridade", "normal"), req.texto("status", "aberta"),
                 para_iso(req.texto("prazo")), req.texto("observacao"), did))
        return web.redirecionar(f"/demandas/{did}", "Demanda atualizada.")

    @app.rota("/demandas/<int:did>/situacao", metodos=("POST",))
    def situacao(req, did):
        novo_status = req.texto("status")
        if novo_status not in dict(SITUACOES):
            return web.redirecionar(f"/demandas/{did}", "Erro: situação inválida.")
        with db.aberto() as con:
            con.execute("UPDATE demanda SET status = ? WHERE id = ?", (novo_status, did))
        return web.redirecionar(f"/demandas/{did}",
                                f"Demanda marcada como {ui.rotulo(novo_status)}.")

    @app.rota("/demandas/<int:did>")
    def ficha(req, did):
        with db.aberto() as con:
            d = con.execute(
                "SELECT d.*, i.codigo, i.descricao, i.unidade, i.estoque_min,"
                " p.numero AS pedido FROM demanda d JOIN item i ON i.id = d.item_id "
                "LEFT JOIN pedido p ON p.id = d.pedido_id WHERE d.id = ?",
                (did,)).fetchone()
            if not d:
                return web.nao_encontrado("Demanda não encontrada.")
            saldo = q.saldo_item(con, d["item_id"])

        botoes = "".join(
            f'<form method="post" action="{ui.u(f"/demandas/{did}/situacao")}" '
            f'style="display:inline"><input type="hidden" name="status" value="{v}">'
            f'<button class="bt bt--claro bt--mini" type="submit">{esc(t)}</button></form> '
            for v, t in SITUACOES if v != d["status"])

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="grade grade--4" style="margin-bottom:1.4rem">
  {ui.cartao_indicador('Quantidade pedida',
                       quantidade(d['quantidade']) + ' ' + d['unidade'], 'Necessário')}
  {ui.cartao_indicador('Saldo em estoque', quantidade(saldo) + ' ' + d['unidade'],
                       'Disponível agora',
                       tom='erro' if saldo < d['quantidade'] else 'ok')}
  {ui.cartao_indicador('Ainda falta',
                       quantidade(max(d['quantidade'] - saldo, 0)) + ' ' + d['unidade'],
                       'Para atender por completo')}
  {ui.cartao_indicador('Prazo', data_br(d['prazo']) or 'sem prazo',
                       ui.rotulo(d['prioridade']) + ' prioridade')}
</div>

<div class="painel">
  <h2>Demanda {esc(d['numero'])}</h2>
  <div class="grade grade--3">
    <div><span class="dica">Item</span><br>
      <a href="{ui.u('/itens/' + str(d['item_id']))}" class="mono">{esc(d['codigo'])}</a>
      {esc(d['descricao'])}</div>
    <div><span class="dica">Origem</span><br><strong>{ui.rotulo(d['origem'])}</strong></div>
    <div><span class="dica">Situação</span><br>{ui.tarja(d['status'])}</div>
    <div><span class="dica">Pedido de origem</span><br>
      {f'<a href="{ui.u("/pedidos/" + str(d["pedido_id"]))}" class="mono">{esc(d["pedido"])}</a>' if d["pedido"] else "—"}</div>
    <div><span class="dica">Criada em</span><br><strong>{data_br(d['criado_em'])}</strong></div>
  </div>
  {f'<p style="margin-top:1rem"><span class="dica">Observações</span><br>{esc(d["observacao"])}</p>' if d["observacao"] else ""}
  <div class="rodape-form">
    <span class="dica" style="align-self:center;margin-right:.3rem">Marcar como:</span>
    {botoes}
  </div>
</div>"""
        return web.pagina(ui.layout(
            f'Demanda {d["numero"]}', conteudo, "demandas", req.usuario,
            ui.acoes(ui.bt("Editar", f"/demandas/{did}/editar", "bt--principal"),
                     ui.bt("Lançar entrada",
                           f'/estoque/movimentar?item={d["item_id"]}', "bt--escuro"),
                     ui.bt("Voltar", "/demandas", "bt--claro"))))
