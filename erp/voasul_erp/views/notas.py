"""Notas fiscais.

Registro fiscal interno: numeração, itens, impressão e vínculo com o
pedido. Não há transmissão à SEFAZ nem assinatura digital — o documento
gerado é um espelho para conferência e arquivo, não um DANFE válido.
"""

import json

from .. import consultas as q
from .. import db, ui, web
from ..util import (agora_iso, data_br, esc, formata_documento, hoje_iso,
                    moeda, numero, para_float, para_iso, quantidade)

NATUREZAS = [
    ("Venda de produção do estabelecimento", "5101"),
    ("Venda de mercadoria adquirida de terceiros", "5102"),
    ("Remessa para conserto", "5915"),
    ("Retorno de conserto", "5916"),
    ("Devolução de venda", "1202"),
    ("Remessa para demonstração", "5912"),
]


def registrar(app):

    @app.rota("/notas")
    def lista(req):
        busca = req.arg("q")
        filtros, valores = ["1=1"], []
        if busca:
            filtros.append("(n.numero LIKE ? OR pa.nome LIKE ? OR n.natureza LIKE ?)")
            valores += [f"%{busca}%"] * 3
        with db.aberto() as con:
            notas = con.execute(
                f"SELECT n.*, pa.nome AS parceiro, p.numero AS pedido FROM nota n "
                f"LEFT JOIN parceiro pa ON pa.id = n.parceiro_id "
                f"LEFT JOIN pedido p ON p.id = n.pedido_id "
                f"WHERE {' AND '.join(filtros)} ORDER BY n.id DESC LIMIT 300",
                valores).fetchall()
            totais = {n["id"]: q.total_nota(con, n)["total"] for n in notas}

        linhas = [[
            f'<a href="{ui.u("/notas/" + str(n["id"]))}" class="mono">'
            f'{esc(n["numero"])}/{esc(n["serie"])}</a>',
            data_br(n["data_emissao"]),
            esc(n["parceiro"] or "—"),
            esc(n["natureza"]),
            (f'<span class="mono">{esc(n["cfop"])}</span>', "meio"),
            (f'<a href="{ui.u("/pedidos/" + str(n["pedido_id"]))}" class="mono">'
             f'{esc(n["pedido"])}</a>' if n["pedido"] else "—"),
            ui.tarja(n["status"]),
            (moeda(totais[n["id"]]), "num"),
        ] for n in notas]

        validas = sum(v for n, v in totais.items()
                      if next(x for x in notas if x["id"] == n)["status"] == "emitida")

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="aviso aviso--ok" style="background:#eef3fa;border-color:#cfdcec;color:#17609c">
  <strong>Registro fiscal interno.</strong> Este módulo numera, guarda e imprime
  as notas para conferência e arquivo. Não transmite à SEFAZ nem gera DANFE
  com validade jurídica — para isso é preciso certificado digital e integração
  com o emissor oficial.
</div>
<div class="painel">
  <div class="painel__cabeca">
    {ui.busca('/notas', busca, 'Número, cliente ou natureza')}
    <span class="dica">{len(notas)} nota(s) · {moeda(validas)} emitido</span>
  </div>
  {ui.tabela(['Número/Série', 'Emissão', 'Destinatário', 'Natureza',
              ('CFOP', 'meio'), 'Pedido', 'Situação', ('Total', 'num')],
             linhas, 'Nenhuma nota registrada.')}
</div>"""
        return web.pagina(ui.layout(
            "Notas fiscais", conteudo, "notas", req.usuario,
            ui.acoes(ui.bt("Nova nota", "/notas/nova", "bt--principal"))))

    # ------------------------------------------------------------- formulário
    def _formulario(req, erro="", pre_linhas=None, pedido=None):
        with db.aberto() as con:
            emp = q.empresa(con)
            serie = emp.get("serie_nota", "1")
            numero_novo = q.proximo_numero_nota(con, serie)
            itens = q.itens_com_saldo(con)
            opcoes = [("", "—")] + [
                (str(i["id"]), f'{i["codigo"]} — {i["descricao"]}') for i in itens]
            precos = {str(i["id"]): round(float(i["preco"]), 2) for i in itens}
            parceiros = con.execute(
                "SELECT id, nome FROM parceiro WHERE ativo = 1 ORDER BY nome").fetchall()

        lista_parceiros = [("", "—")] + [(str(p["id"]), p["nome"]) for p in parceiros]
        registros = list(pre_linhas or []) + [None] * max(4 - len(pre_linhas or []), 2)
        corpo_linhas = []
        for linha in registros:
            sel = str(linha["item_id"]) if linha else ""
            qtd = quantidade(linha["quantidade"]) if linha else ""
            unit = numero(linha["preco_unit"]) if linha else ""
            opts = "".join(
                f'<option value="{esc(v)}"{" selected" if v == sel else ""}>'
                f"{esc(t)}</option>" for v, t in opcoes)
            corpo_linhas.append(f"""<tr>
  <td><select name="item_id">{opts}</select></td>
  <td style="width:110px"><input name="quantidade" value="{esc(qtd)}" inputmode="decimal"></td>
  <td style="width:130px"><input name="preco_unit" value="{esc(unit)}" inputmode="decimal"></td>
  <td style="width:110px"><input name="desconto" value="" inputmode="decimal"></td>
  <td class="num subtotal" style="width:120px">R$ 0,00</td>
</tr>""")

        nat_opcoes = [(n, f"{n} (CFOP {c})") for n, c in NATUREZAS]
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        campo_pedido = (f'<input type="hidden" name="pedido_id" value="{pedido["id"]}">'
                        if pedido else "")
        aviso_pedido = (
            f'<div class="aviso aviso--ok">Itens trazidos do pedido '
            f'<strong>{esc(pedido["numero"])}</strong>.</div>' if pedido else "")

        corpo = f"""{alerta}{aviso_pedido}
<form method="post" action="{ui.u('/notas/nova')}">
  {campo_pedido}
  <div class="painel">
    <div class="formulario">
      {ui.campo('numero', 'Número', numero_novo, atributos='readonly')}
      {ui.campo('serie', 'Série', serie)}
      {ui.campo('data_emissao', 'Data de emissão', data_br(hoje_iso()), obrigatorio=True)}
      {ui.selecao('natureza', 'Natureza da operação', nat_opcoes,
                  pedido and 'Venda de produção do estabelecimento'
                  or NATUREZAS[0][0], obrigatorio=True, largura='campo--largo')}
      {ui.selecao('parceiro_id', 'Destinatário', lista_parceiros,
                  str(pedido['parceiro_id']) if pedido and pedido['parceiro_id'] else '',
                  largura='campo--largo')}
      {ui.campo('frete', 'Frete (R$)',
                numero(pedido['frete']) if pedido else '0,00')}
      {ui.area('observacao', 'Informações complementares',
               'Mercadoria testada em voo antes da entrega. '
               'Acompanha manual e orientação de cadastro na ANAC.')}
    </div>
  </div>
  <div class="painel">
    <h2>Itens da nota</h2>
    <table class="linhas" id="linhas-itens" data-precos='{json.dumps(precos)}'>
      <thead><tr><th>Item</th><th>Quantidade</th><th>Valor unit. (R$)</th>
        <th>Desconto (R$)</th><th class="num">Subtotal</th></tr></thead>
      <tbody>{"".join(corpo_linhas)}</tbody>
    </table>
    <div class="acoes" style="margin-top:.7rem">
      <button class="bt bt--claro bt--mini" type="button" id="mais-linhas">
        + Acrescentar 3 linhas</button>
      <span style="margin-left:auto;font-size:1.05rem">
        <strong>Total: <span id="total-geral">R$ 0,00</span></strong></span>
    </div>
    <div class="rodape-form">
      {ui.bt('Emitir nota', classe='bt--principal', tipo='submit')}
      {ui.bt('Cancelar', '/notas', 'bt--claro')}
    </div>
  </div>
</form>"""
        return web.pagina(ui.layout("Nova nota fiscal", corpo, "notas", req.usuario))

    @app.rota("/notas/nova", metodos=("GET", "POST"))
    def nova(req):
        if req.metodo == "GET":
            pedido_id = req.arg("pedido")
            if pedido_id:
                with db.aberto() as con:
                    pedido = con.execute("SELECT * FROM pedido WHERE id = ?",
                                         (int(pedido_id),)).fetchone()
                    if pedido:
                        return _formulario(req, pre_linhas=q.itens_do_pedido(con, pedido["id"]),
                                           pedido=pedido)
            return _formulario(req)

        ids = req.lista("item_id")
        qtds, precos = req.lista("quantidade"), req.lista("preco_unit")
        linhas = []
        for pos, item_id in enumerate(ids):
            if not item_id.strip():
                continue
            qtd = para_float(qtds[pos] if pos < len(qtds) else 0)
            if qtd <= 0:
                continue
            linhas.append((int(item_id), qtd,
                           para_float(precos[pos] if pos < len(precos) else 0)))
        if not linhas:
            return _formulario(req, "Inclua ao menos um item com quantidade.")

        natureza = req.texto("natureza", NATUREZAS[0][0])
        cfop = dict(NATUREZAS).get(natureza, "5101")
        with db.transacao() as con:
            serie = req.texto("serie", "1")
            num = q.proximo_numero_nota(con, serie)
            cur = con.execute(
                "INSERT INTO nota (numero, serie, natureza, cfop, parceiro_id,"
                " pedido_id, data_emissao, frete, status, observacao, usuario_id,"
                " criado_em) VALUES (?,?,?,?,?,?,?,?, 'emitida', ?,?,?)",
                (num, serie, natureza, cfop,
                 int(req.texto("parceiro_id")) if req.texto("parceiro_id") else None,
                 int(req.texto("pedido_id")) if req.texto("pedido_id") else None,
                 para_iso(req.texto("data_emissao")) or hoje_iso(),
                 para_float(req.texto("frete")), req.texto("observacao"),
                 req.usuario["id"], agora_iso()))
            nota_id = cur.lastrowid
            for item_id, qtd, preco in linhas:
                item = con.execute("SELECT ncm FROM item WHERE id = ?",
                                   (item_id,)).fetchone()
                con.execute(
                    "INSERT INTO nota_item (nota_id, item_id, quantidade, preco_unit,"
                    " ncm, cfop) VALUES (?,?,?,?,?,?)",
                    (nota_id, item_id, qtd, preco, item["ncm"] if item else "", cfop))
        return web.redirecionar(f"/notas/{nota_id}", f"Nota {num}/{serie} emitida.")

    @app.rota("/notas/<int:nid>/cancelar", metodos=("POST",))
    def cancelar(req, nid):
        with db.aberto() as con:
            con.execute("UPDATE nota SET status = 'cancelada' WHERE id = ?", (nid,))
        return web.redirecionar(f"/notas/{nid}", "Nota cancelada.")

    # ------------------------------------------------------------------ ficha
    def _carregar(nid):
        with db.aberto() as con:
            nota = con.execute(
                "SELECT n.*, pa.nome AS parceiro, pa.documento, pa.endereco,"
                " pa.cidade, pa.uf, pa.cep, pa.telefone, p.numero AS pedido "
                "FROM nota n LEFT JOIN parceiro pa ON pa.id = n.parceiro_id "
                "LEFT JOIN pedido p ON p.id = n.pedido_id WHERE n.id = ?",
                (nid,)).fetchone()
            if not nota:
                return None, None, None
            return nota, q.total_nota(con, nota), q.empresa(con)

    @app.rota("/notas/<int:nid>")
    def ficha(req, nid):
        nota, resumo, emp = _carregar(nid)
        if not nota:
            return web.nao_encontrado("Nota não encontrada.")

        linhas = [[
            f'<a href="{ui.u("/itens/" + str(l["item_id"]))}" class="mono">'
            f'{esc(l["codigo"])}</a>',
            esc(l["descricao"]),
            (f'<span class="mono">{esc(l["ncm"] or "—")}</span>', "meio"),
            (quantidade(l["quantidade"]) + " " + l["unidade"], "num"),
            (moeda(l["preco_unit"]), "num"),
            (moeda(l["quantidade"] * l["preco_unit"]), "num"),
        ] for l in resumo["linhas"]]

        acao_cancelar = ""
        if nota["status"] == "emitida":
            acao_cancelar = (
                f'<form method="post" action="{ui.u(f"/notas/{nid}/cancelar")}" '
                f'data-confirmar="Cancelar a nota {esc(nota["numero"])}/'
                f'{esc(nota["serie"])}? A numeração não é reaproveitada." '
                f'style="display:inline">'
                f'<button class="bt bt--perigo bt--mini" type="submit">'
                f'Cancelar nota</button></form>')

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <div class="grade grade--4">
    <div><span class="dica">Número / Série</span><br>
      <strong class="mono">{esc(nota['numero'])}/{esc(nota['serie'])}</strong></div>
    <div><span class="dica">Emissão</span><br><strong>{data_br(nota['data_emissao'])}</strong></div>
    <div><span class="dica">CFOP</span><br><strong class="mono">{esc(nota['cfop'])}</strong></div>
    <div><span class="dica">Situação</span><br>{ui.tarja(nota['status'])}</div>
    <div style="grid-column:span 2"><span class="dica">Natureza da operação</span><br>
      <strong>{esc(nota['natureza'])}</strong></div>
    <div><span class="dica">Destinatário</span><br><strong>{esc(nota['parceiro'] or '—')}</strong></div>
    <div><span class="dica">Pedido</span><br>
      {f'<a href="{ui.u("/pedidos/" + str(nota["pedido_id"]))}" class="mono">{esc(nota["pedido"])}</a>' if nota["pedido"] else "—"}</div>
  </div>
  <div class="rodape-form nao-imprime">{acao_cancelar}</div>
</div>

<div class="painel">
  <h2>Itens</h2>
  {ui.tabela(['Código', 'Descrição', ('NCM', 'meio'), ('Qtd.', 'num'),
              ('Valor un.', 'num'), ('Total', 'num')], linhas)}
  <table class="doc__totais" style="margin-top:1rem">
    <tr><td>Produtos</td><td class="num">{moeda(resumo['produtos'])}</td></tr>
    <tr><td>Frete</td><td class="num">{moeda(nota['frete'])}</td></tr>
    <tr><td>Total da nota</td><td class="num">{moeda(resumo['total'])}</td></tr>
  </table>
</div>"""
        return web.pagina(ui.layout(
            f'Nota {nota["numero"]}/{nota["serie"]}', conteudo, "notas", req.usuario,
            ui.acoes(ui.bt("Imprimir", f"/notas/{nid}/imprimir", "bt--principal"),
                     ui.bt("Voltar", "/notas", "bt--claro"))))

    @app.rota("/notas/<int:nid>/imprimir")
    def imprimir(req, nid):
        nota, resumo, emp = _carregar(nid)
        if not nota:
            return web.nao_encontrado("Nota não encontrada.")

        linhas = "".join(
            f'<tr><td class="mono">{esc(l["codigo"])}</td><td>{esc(l["descricao"])}</td>'
            f'<td class="mono meio">{esc(l["ncm"] or "—")}</td>'
            f'<td class="meio">{esc(l["cfop"] or nota["cfop"])}</td>'
            f'<td class="num">{quantidade(l["quantidade"])} {esc(l["unidade"])}</td>'
            f'<td class="num">{moeda(l["preco_unit"])}</td>'
            f'<td class="num">{moeda(l["quantidade"] * l["preco_unit"])}</td></tr>'
            for l in resumo["linhas"])

        cancelada = ('<p style="color:#b3261e;font-weight:700;font-size:1.1rem;'
                     'border:2px solid #b3261e;padding:.4rem;text-align:center">'
                     'NOTA CANCELADA</p>' if nota["status"] == "cancelada" else "")

        corpo = f"""<div class="documento">
  {cancelada}
  <div class="doc__cabeca">
    <div>
      <img src="{ui.u('/static/img/logo-voasul.svg')}" alt="VoaSul">
      <p style="margin:.5rem 0 0;font-size:.78rem;line-height:1.45">
        <strong>{esc(emp.get('razao_social', ''))}</strong><br>
        CNPJ {esc(emp.get('cnpj') or '—')} · IE {esc(emp.get('inscricao_estadual') or '—')}<br>
        {esc(emp.get('endereco', ''))} — {esc(emp.get('cidade', ''))}/{esc(emp.get('uf', ''))}<br>
        {esc(emp.get('email', ''))} · {esc(emp.get('site', ''))}
      </p>
    </div>
    <div style="text-align:right">
      <h2 style="margin:0">Nota fiscal</h2>
      <p style="margin:.2rem 0 0" class="mono">
        <strong>Nº {esc(nota['numero'])} · Série {esc(nota['serie'])}</strong></p>
      <p style="margin:.2rem 0 0;font-size:.8rem">Emissão {data_br(nota['data_emissao'])}</p>
      <p style="margin:.2rem 0 0;font-size:.8rem">CFOP {esc(nota['cfop'])}</p>
    </div>
  </div>

  <div class="doc__bloco">
    <h3>Natureza da operação</h3>{esc(nota['natureza'])}
  </div>

  <div class="doc__bloco">
    <h3>Destinatário</h3>
    <strong>{esc(nota['parceiro'] or '—')}</strong><br>
    {esc(formata_documento(nota['documento']) or '')}<br>
    {esc(nota['endereco'] or '')} {esc(nota['cidade'] or '')}
    {esc('/' + nota['uf'] if nota['uf'] else '')} {esc(nota['cep'] or '')}<br>
    {esc(nota['telefone'] or '')}
  </div>

  <table class="tabela">
    <thead><tr><th>Código</th><th>Descrição</th><th class="meio">NCM</th>
      <th class="meio">CFOP</th><th class="num">Qtd.</th>
      <th class="num">Valor un.</th><th class="num">Total</th></tr></thead>
    <tbody>{linhas}</tbody>
  </table>

  <table class="doc__totais">
    <tr><td>Valor dos produtos</td><td class="num">{moeda(resumo['produtos'])}</td></tr>
    <tr><td>Frete</td><td class="num">{moeda(nota['frete'])}</td></tr>
    <tr><td>Valor total da nota</td><td class="num">{moeda(resumo['total'])}</td></tr>
  </table>

  <div class="doc__bloco" style="margin-top:1rem">
    <h3>Informações complementares</h3>
    {esc(nota['observacao'] or '—')}
  </div>

  <p style="margin-top:1.5rem;font-size:.7rem;color:#777;border-top:1px solid #ddd;
            padding-top:.6rem">
    Documento gerado pelo VOA-SUL ERP para conferência e arquivo interno.
    Não substitui a NF-e transmitida à SEFAZ nem constitui DANFE com
    validade jurídica.
  </p>
  <p class="nao-imprime" style="margin-top:1.2rem">
    <a class="bt bt--principal" href="?imprimir=1">Imprimir</a>
    <a class="bt bt--claro" href="{ui.u('/notas/' + str(nid))}">Voltar</a>
  </p>
</div>"""
        return web.pagina(ui.layout_limpo(
            f'Nota {nota["numero"]}', corpo, corpo_classe="folha-doc"))
