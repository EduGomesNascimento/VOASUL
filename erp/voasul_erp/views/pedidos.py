"""Pedidos de venda e de compra, com baixa automática de estoque."""

import json

from .. import consultas as q
from .. import db, ui, web
from ..util import (agora_iso, data_br, esc, hoje_iso, moeda, numero,
                    para_float, para_iso, quantidade)

STATUS = [("orcamento", "Orçamento"), ("confirmado", "Confirmado"),
          ("producao", "Em produção"), ("pronto", "Pronto"),
          ("entregue", "Entregue"), ("cancelado", "Cancelado")]

# A partir de "confirmado" o pedido movimenta estoque.
STATUS_COM_BAIXA = {"confirmado", "producao", "pronto", "entregue"}


def registrar(app):

    @app.rota("/pedidos")
    def lista(req):
        busca, status, tipo = req.arg("q"), req.arg("status"), req.arg("tipo")
        filtros, valores = ["1=1"], []
        if busca:
            filtros.append("(p.numero LIKE ? OR pa.nome LIKE ?)")
            valores += [f"%{busca}%"] * 2
        if status:
            filtros.append("p.status = ?")
            valores.append(status)
        if tipo:
            filtros.append("p.tipo = ?")
            valores.append(tipo)

        with db.aberto() as con:
            pedidos = con.execute(
                f"SELECT p.*, pa.nome AS parceiro FROM pedido p "
                f"LEFT JOIN parceiro pa ON pa.id = p.parceiro_id "
                f"WHERE {' AND '.join(filtros)} ORDER BY p.id DESC LIMIT 300",
                valores).fetchall()
            totais = {p["id"]: q.total_pedido(con, p)["total"] for p in pedidos}

        linhas = [[
            f'<a href="{ui.u("/pedidos/" + str(p["id"]))}" class="mono">'
            f'{esc(p["numero"])}</a>',
            ui.rotulo(p["tipo"]),
            esc(p["parceiro"] or "—"),
            data_br(p["data_emissao"]),
            data_br(p["data_entrega"]) or "—",
            ui.tarja(p["status"]),
            ('<span class="tarja tarja--ok">baixado</span>' if p["baixado"]
             else '<span class="tarja tarja--neutro">não</span>', "meio"),
            (moeda(totais[p["id"]]), "num"),
        ] for p in pedidos]

        extra = ('<select name="tipo"><option value="">Venda e compra</option>'
                 f'<option value="venda"{" selected" if tipo == "venda" else ""}>Venda</option>'
                 f'<option value="compra"{" selected" if tipo == "compra" else ""}>Compra</option>'
                 "</select>"
                 '<select name="status"><option value="">Todas as situações</option>' +
                 "".join(f'<option value="{v}"{" selected" if v == status else ""}>'
                         f"{esc(t)}</option>" for v, t in STATUS) + "</select>")

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <div class="painel__cabeca">
    {ui.busca('/pedidos', busca, 'Número ou parceiro', extra)}
    <span class="dica">{len(pedidos)} pedido(s) · {moeda(sum(totais.values()))}</span>
  </div>
  {ui.tabela(['Número', 'Tipo', 'Parceiro', 'Emissão', 'Entrega', 'Situação',
              ('Estoque', 'meio'), ('Total', 'num')], linhas,
             'Nenhum pedido encontrado.')}
</div>"""
        return web.pagina(ui.layout(
            "Pedidos", conteudo, "pedidos", req.usuario,
            ui.acoes(ui.bt("Novo pedido", "/pedidos/novo", "bt--principal"))))

    # ------------------------------------------------------------ formulário
    def _dados_form(con):
        itens = q.itens_com_saldo(con)
        opcoes = [("", "—")] + [
            (str(i["id"]), f'{i["codigo"]} — {i["descricao"]}') for i in itens]
        precos = {str(i["id"]): round(float(i["preco"]), 2) for i in itens}
        parceiros = con.execute(
            "SELECT id, nome, tipo FROM parceiro WHERE ativo = 1 ORDER BY nome").fetchall()
        return opcoes, precos, parceiros

    def _linhas_editaveis(opcoes, precos, linhas_atuais):
        """Monta a grade de itens do pedido, com folga de linhas em branco."""
        registros = list(linhas_atuais) + [None] * max(4 - len(linhas_atuais), 2)
        corpo = []
        for linha in registros:
            sel = str(linha["item_id"]) if linha else ""
            qtd = numero(linha["quantidade"], 3).rstrip("0").rstrip(",") if linha else ""
            unit = numero(linha["preco_unit"]) if linha else ""
            desc = numero(linha["desconto"]) if linha else ""
            opts = "".join(
                f'<option value="{esc(v)}"{" selected" if v == sel else ""}>'
                f"{esc(t)}</option>" for v, t in opcoes)
            corpo.append(f"""<tr>
  <td><select name="item_id">{opts}</select></td>
  <td style="width:110px"><input name="quantidade" value="{esc(qtd)}" inputmode="decimal"></td>
  <td style="width:130px"><input name="preco_unit" value="{esc(unit)}" inputmode="decimal"></td>
  <td style="width:120px"><input name="desconto" value="{esc(desc)}" inputmode="decimal"></td>
  <td class="num subtotal" style="width:120px">R$ 0,00</td>
</tr>""")
        return f"""<table class="linhas" id="linhas-itens"
       data-precos='{json.dumps(precos)}'>
  <thead><tr><th>Item</th><th>Quantidade</th><th>Preço unit. (R$)</th>
    <th>Desconto (R$)</th><th class="num">Subtotal</th></tr></thead>
  <tbody>{"".join(corpo)}</tbody>
</table>
<div class="acoes" style="margin-top:.7rem">
  <button class="bt bt--claro bt--mini" type="button" id="mais-linhas">
    + Acrescentar 3 linhas
  </button>
  <span style="margin-left:auto;font-size:1.05rem">
    <strong>Total: <span id="total-geral">R$ 0,00</span></strong>
  </span>
</div>"""

    def _formulario(req, pedido=None, erro=""):
        novo = pedido is None
        with db.aberto() as con:
            opcoes, precos, parceiros = _dados_form(con)
            atuais = q.itens_do_pedido(con, pedido["id"]) if pedido else []
            numero_novo = q.proximo_numero(con, "pedido", "PV") if novo else pedido["numero"]

        d = dict(pedido) if pedido else {
            "tipo": req.arg("tipo", "venda"), "parceiro_id": "", "status": "orcamento",
            "data_emissao": hoje_iso(), "data_entrega": "", "frete": 0,
            "desconto": 0, "observacao": ""}

        lista_parceiros = [("", "—")] + [(str(p["id"]), p["nome"]) for p in parceiros]
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        destino = "/pedidos/novo" if novo else f'/pedidos/{pedido["id"]}/editar'

        corpo = f"""{alerta}
<form method="post" action="{ui.u(destino)}">
  <div class="painel">
    <div class="formulario">
      {ui.campo('numero', 'Número', numero_novo, atributos='readonly')}
      {ui.selecao('tipo', 'Tipo', [('venda', 'Venda'), ('compra', 'Compra')], d['tipo'],
                  obrigatorio=True)}
      {ui.selecao('status', 'Situação', STATUS, d['status'], obrigatorio=True,
                  dica='De "Confirmado" em diante o estoque é movimentado.')}
      {ui.selecao('parceiro_id', 'Cliente / fornecedor', lista_parceiros,
                  d['parceiro_id'] or '', largura='campo--largo')}
      {ui.campo('data_emissao', 'Data de emissão', data_br(d['data_emissao']),
                obrigatorio=True)}
      {ui.campo('data_entrega', 'Previsão de entrega', data_br(d['data_entrega']))}
      {ui.campo('frete', 'Frete (R$)', numero(d['frete']))}
      {ui.campo('desconto_geral', 'Desconto no total (R$)', numero(d['desconto']))}
      {ui.area('observacao', 'Observações', d['observacao'])}
    </div>
  </div>

  <div class="painel">
    <h2>Itens do pedido</h2>
    {_linhas_editaveis(opcoes, precos, atuais)}
    <div class="rodape-form">
      {ui.bt('Salvar pedido', classe='bt--principal', tipo='submit')}
      {ui.bt('Cancelar', '/pedidos', 'bt--claro')}
    </div>
  </div>
</form>"""
        titulo = "Novo pedido" if novo else f'Pedido {pedido["numero"]}'
        return web.pagina(ui.layout(titulo, corpo, "pedidos", req.usuario))

    def _ler_linhas(req):
        """Lê a grade de itens, descartando linhas em branco."""
        ids = req.lista("item_id")
        qtds = req.lista("quantidade")
        precos = req.lista("preco_unit")
        descontos = req.lista("desconto")
        resultado = []
        for pos, item_id in enumerate(ids):
            if not item_id.strip():
                continue
            qtd = para_float(qtds[pos] if pos < len(qtds) else 0)
            if qtd <= 0:
                continue
            resultado.append((
                int(item_id),
                qtd,
                para_float(precos[pos] if pos < len(precos) else 0),
                para_float(descontos[pos] if pos < len(descontos) else 0)))
        return resultado

    def _gravar_linhas(con, pedido_id, linhas):
        con.execute("DELETE FROM pedido_item WHERE pedido_id = ?", (pedido_id,))
        for item_id, qtd, preco, desconto in linhas:
            con.execute(
                "INSERT INTO pedido_item (pedido_id, item_id, quantidade, preco_unit,"
                " desconto) VALUES (?,?,?,?,?)",
                (pedido_id, item_id, qtd, preco, desconto))

    def _sincronizar_estoque(con, pedido_id, usuario_id):
        """Deixa o estoque coerente com a situação atual do pedido."""
        pedido = con.execute("SELECT * FROM pedido WHERE id = ?", (pedido_id,)).fetchone()
        deve_baixar = pedido["status"] in STATUS_COM_BAIXA
        if deve_baixar and not pedido["baixado"]:
            return q.baixar_estoque_do_pedido(con, pedido, usuario_id), "baixado"
        if not deve_baixar and pedido["baixado"]:
            return q.estornar_estoque_do_pedido(con, pedido, usuario_id), "estornado"
        return 0, ""

    @app.rota("/pedidos/novo", metodos=("GET", "POST"))
    def novo(req):
        if req.metodo == "GET":
            return _formulario(req)
        linhas = _ler_linhas(req)
        if not linhas:
            return _formulario(req, erro="Inclua ao menos um item com quantidade.")
        with db.transacao() as con:
            num = q.proximo_numero(con, "pedido", "PV")
            cur = con.execute(
                "INSERT INTO pedido (numero, tipo, parceiro_id, status, data_emissao,"
                " data_entrega, frete, desconto, observacao, usuario_id, criado_em)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (num, req.texto("tipo", "venda"),
                 int(req.texto("parceiro_id")) if req.texto("parceiro_id") else None,
                 req.texto("status", "orcamento"),
                 para_iso(req.texto("data_emissao")) or hoje_iso(),
                 para_iso(req.texto("data_entrega")),
                 para_float(req.texto("frete")),
                 para_float(req.texto("desconto_geral")),
                 req.texto("observacao"), req.usuario["id"], agora_iso()))
            pedido_id = cur.lastrowid
            _gravar_linhas(con, pedido_id, linhas)
            _sincronizar_estoque(con, pedido_id, req.usuario["id"])
        return web.redirecionar(f"/pedidos/{pedido_id}", f"Pedido {num} criado.")

    @app.rota("/pedidos/<int:pid>/editar", metodos=("GET", "POST"))
    def editar(req, pid):
        with db.aberto() as con:
            pedido = con.execute("SELECT * FROM pedido WHERE id = ?", (pid,)).fetchone()
        if not pedido:
            return web.nao_encontrado("Pedido não encontrado.")
        if req.metodo == "GET":
            return _formulario(req, pedido)

        linhas = _ler_linhas(req)
        if not linhas:
            return _formulario(req, pedido, "Inclua ao menos um item com quantidade.")
        with db.transacao() as con:
            atual = con.execute("SELECT * FROM pedido WHERE id = ?", (pid,)).fetchone()
            # Se o pedido já movimentou estoque, estorna antes de regravar as
            # linhas — senão a baixa antiga ficaria órfã.
            if atual["baixado"]:
                q.estornar_estoque_do_pedido(con, atual, req.usuario["id"])
            con.execute(
                "UPDATE pedido SET tipo=?, parceiro_id=?, status=?, data_emissao=?,"
                " data_entrega=?, frete=?, desconto=?, observacao=? WHERE id=?",
                (req.texto("tipo", "venda"),
                 int(req.texto("parceiro_id")) if req.texto("parceiro_id") else None,
                 req.texto("status", "orcamento"),
                 para_iso(req.texto("data_emissao")) or hoje_iso(),
                 para_iso(req.texto("data_entrega")),
                 para_float(req.texto("frete")),
                 para_float(req.texto("desconto_geral")),
                 req.texto("observacao"), pid))
            _gravar_linhas(con, pid, linhas)
            _sincronizar_estoque(con, pid, req.usuario["id"])
        return web.redirecionar(f"/pedidos/{pid}", "Pedido atualizado.")

    @app.rota("/pedidos/<int:pid>/situacao", metodos=("POST",))
    def mudar_situacao(req, pid):
        novo_status = req.texto("status")
        if novo_status not in dict(STATUS):
            return web.redirecionar(f"/pedidos/{pid}", "Erro: situação inválida.")
        with db.transacao() as con:
            con.execute("UPDATE pedido SET status = ? WHERE id = ?", (novo_status, pid))
            qtd, acao = _sincronizar_estoque(con, pid, req.usuario["id"])
        extra = f" Estoque {acao}: {qtd} item(ns)." if acao else ""
        return web.redirecionar(
            f"/pedidos/{pid}", f"Situação alterada para {ui.rotulo(novo_status)}.{extra}")

    # ------------------------------------------------------------------ ficha
    @app.rota("/pedidos/<int:pid>")
    def ficha(req, pid):
        with db.aberto() as con:
            pedido = con.execute(
                "SELECT p.*, pa.nome AS parceiro, pa.documento, pa.cidade, pa.uf,"
                " u.nome AS usuario FROM pedido p "
                "LEFT JOIN parceiro pa ON pa.id = p.parceiro_id "
                "LEFT JOIN usuario u ON u.id = p.usuario_id "
                "WHERE p.id = ?", (pid,)).fetchone()
            if not pedido:
                return web.nao_encontrado("Pedido não encontrado.")
            resumo = q.total_pedido(con, pedido)
            notas = con.execute(
                "SELECT * FROM nota WHERE pedido_id = ? ORDER BY id DESC", (pid,)).fetchall()
            demandas = con.execute(
                "SELECT d.*, i.codigo FROM demanda d JOIN item i ON i.id = d.item_id "
                "WHERE d.pedido_id = ? ORDER BY d.id DESC", (pid,)).fetchall()

        linhas = [[
            f'<a href="{ui.u("/itens/" + str(l["item_id"]))}" class="mono">'
            f'{esc(l["codigo"])}</a>',
            esc(l["descricao"]),
            (quantidade(l["quantidade"]) + " " + l["unidade"], "num"),
            (moeda(l["preco_unit"]), "num"),
            (moeda(l["desconto"]), "num"),
            (moeda(l["quantidade"] * l["preco_unit"] - l["desconto"]), "num"),
        ] for l in resumo["linhas"]]

        botoes_status = "".join(
            f'<form method="post" action="{ui.u(f"/pedidos/{pid}/situacao")}" '
            f'style="display:inline">'
            f'<input type="hidden" name="status" value="{v}">'
            f'<button class="bt bt--claro bt--mini" type="submit">{esc(t)}</button></form> '
            for v, t in STATUS if v != pedido["status"])

        linhas_nf = [[
            f'<a href="{ui.u("/notas/" + str(n["id"]))}" class="mono">'
            f'{esc(n["numero"])}/{esc(n["serie"])}</a>',
            data_br(n["data_emissao"]), ui.tarja(n["status"]),
        ] for n in notas]
        linhas_dem = [[
            f'<a href="{ui.u("/demandas/" + str(d["id"]))}" class="mono">'
            f'{esc(d["numero"])}</a>',
            esc(d["codigo"]), (quantidade(d["quantidade"]), "num"),
            ui.tarja(d["status"]),
        ] for d in demandas]

        aviso_baixa = (
            '<span class="tarja tarja--ok">estoque baixado</span>' if pedido["baixado"]
            else '<span class="tarja tarja--neutro">estoque não movimentado</span>')

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <div class="grade grade--4">
    <div><span class="dica">Tipo</span><br><strong>{ui.rotulo(pedido['tipo'])}</strong></div>
    <div><span class="dica">Situação</span><br>{ui.tarja(pedido['status'])}</div>
    <div><span class="dica">Estoque</span><br>{aviso_baixa}</div>
    <div><span class="dica">Total</span><br><strong style="font-size:1.2rem">{moeda(resumo['total'])}</strong></div>
    <div><span class="dica">Parceiro</span><br><strong>{esc(pedido['parceiro'] or '—')}</strong></div>
    <div><span class="dica">Emissão</span><br><strong>{data_br(pedido['data_emissao'])}</strong></div>
    <div><span class="dica">Entrega prevista</span><br><strong>{data_br(pedido['data_entrega']) or '—'}</strong></div>
    <div><span class="dica">Registrado por</span><br><strong>{esc(pedido['usuario'] or '—')}</strong></div>
  </div>
  {f'<p style="margin-top:1rem"><span class="dica">Observações</span><br>{esc(pedido["observacao"])}</p>' if pedido["observacao"] else ""}
  <div class="rodape-form nao-imprime">
    <span class="dica" style="align-self:center;margin-right:.3rem">Mudar situação para:</span>
    {botoes_status}
  </div>
</div>

<div class="painel">
  <h2>Itens</h2>
  {ui.tabela(['Código', 'Descrição', ('Qtd.', 'num'), ('Preço un.', 'num'),
              ('Desconto', 'num'), ('Subtotal', 'num')], linhas)}
  <table class="doc__totais" style="margin-top:1rem">
    <tr><td>Produtos e serviços</td><td class="num">{moeda(resumo['produtos'])}</td></tr>
    <tr><td>Frete</td><td class="num">{moeda(pedido['frete'])}</td></tr>
    <tr><td>Desconto no total</td><td class="num">− {moeda(pedido['desconto'])}</td></tr>
    <tr><td>Total do pedido</td><td class="num">{moeda(resumo['total'])}</td></tr>
  </table>
</div>

<div class="grade grade--2">
  <div class="painel">
    <h2>Notas fiscais</h2>
    {ui.tabela(['Número/Série', 'Emissão', 'Situação'], linhas_nf,
               'Nenhuma nota emitida para este pedido.')}
  </div>
  <div class="painel">
    <h2>Demandas geradas</h2>
    {ui.tabela(['Número', 'Item', ('Qtd.', 'num'), 'Situação'], linhas_dem,
               'Nenhuma demanda vinculada.')}
  </div>
</div>"""

        acoes_topo = ui.acoes(
            ui.bt("Editar", f"/pedidos/{pid}/editar", "bt--principal"),
            ui.bt("Emitir nota", f"/notas/nova?pedido={pid}", "bt--escuro"),
            ui.bt("Gerar demandas", f"/demandas/do-pedido/{pid}", "bt--claro"),
            ui.bt("Imprimir", f"/pedidos/{pid}/imprimir", "bt--claro"),
            ui.bt("Voltar", "/pedidos", "bt--claro"))
        return web.pagina(ui.layout(
            f'Pedido {pedido["numero"]}', conteudo, "pedidos", req.usuario, acoes_topo))

    @app.rota("/pedidos/<int:pid>/imprimir")
    def imprimir(req, pid):
        with db.aberto() as con:
            pedido = con.execute(
                "SELECT p.*, pa.nome AS parceiro, pa.documento, pa.endereco,"
                " pa.cidade, pa.uf, pa.telefone FROM pedido p "
                "LEFT JOIN parceiro pa ON pa.id = p.parceiro_id WHERE p.id = ?",
                (pid,)).fetchone()
            if not pedido:
                return web.nao_encontrado("Pedido não encontrado.")
            resumo = q.total_pedido(con, pedido)
            emp = q.empresa(con)

        linhas = "".join(
            f'<tr><td class="mono">{esc(l["codigo"])}</td><td>{esc(l["descricao"])}</td>'
            f'<td class="num">{quantidade(l["quantidade"])} {esc(l["unidade"])}</td>'
            f'<td class="num">{moeda(l["preco_unit"])}</td>'
            f'<td class="num">{moeda(l["quantidade"] * l["preco_unit"] - l["desconto"])}</td></tr>'
            for l in resumo["linhas"])

        titulo = ("Orçamento" if pedido["status"] == "orcamento"
                  else f'Pedido de {ui.rotulo(pedido["tipo"]).lower()}')
        corpo = f"""<div class="documento">
  <div class="doc__cabeca">
    <div>
      <img src="{ui.u('/static/img/logo-voasul.svg')}" alt="VoaSul">
      <p style="margin:.5rem 0 0;font-size:.8rem;line-height:1.4">
        <strong>{esc(emp.get('razao_social', ''))}</strong><br>
        {esc(emp.get('endereco', ''))} — {esc(emp.get('cidade', ''))}/{esc(emp.get('uf', ''))}<br>
        {esc(emp.get('email', ''))} · {esc(emp.get('site', ''))}
      </p>
    </div>
    <div style="text-align:right">
      <h2 style="margin:0">{esc(titulo)}</h2>
      <p style="margin:.2rem 0 0" class="mono"><strong>{esc(pedido['numero'])}</strong></p>
      <p style="margin:.2rem 0 0;font-size:.8rem">Emissão {data_br(pedido['data_emissao'])}</p>
    </div>
  </div>

  <div class="doc__bloco">
    <h3>Cliente / fornecedor</h3>
    <strong>{esc(pedido['parceiro'] or '—')}</strong><br>
    {esc(pedido['endereco'] or '')} {esc(pedido['cidade'] or '')}
    {esc('/' + pedido['uf'] if pedido['uf'] else '')}<br>
    {esc(pedido['telefone'] or '')}
  </div>

  <table class="tabela">
    <thead><tr><th>Código</th><th>Descrição</th><th class="num">Qtd.</th>
      <th class="num">Preço un.</th><th class="num">Subtotal</th></tr></thead>
    <tbody>{linhas}</tbody>
  </table>

  <table class="doc__totais">
    <tr><td>Produtos e serviços</td><td class="num">{moeda(resumo['produtos'])}</td></tr>
    <tr><td>Frete</td><td class="num">{moeda(pedido['frete'])}</td></tr>
    <tr><td>Desconto</td><td class="num">− {moeda(pedido['desconto'])}</td></tr>
    <tr><td>Total</td><td class="num">{moeda(resumo['total'])}</td></tr>
  </table>

  {f'<div class="doc__bloco" style="margin-top:1rem"><h3>Observações</h3>{esc(pedido["observacao"])}</div>' if pedido["observacao"] else ""}

  <p style="margin-top:2rem;font-size:.75rem;color:#666">
    Entrega prevista: {data_br(pedido['data_entrega']) or 'a combinar'}.
    Todo drone é testado em voo antes da entrega e acompanha ficha de inspeção
    por número de série, manual de operação e orientação de cadastro na ANAC.
    Garantia de 6 meses contra defeito de fabricação.
  </p>
  <p class="nao-imprime" style="margin-top:1.5rem">
    <a class="bt bt--principal" href="?imprimir=1">Imprimir</a>
    <a class="bt bt--claro" href="{ui.u('/pedidos/' + str(pid))}">Voltar</a>
  </p>
</div>"""
        return web.pagina(ui.layout_limpo(f'Pedido {pedido["numero"]}', corpo,
                                          corpo_classe="folha-doc"))
