"""Produção: número de série e ficha de inspeção por drone montado.

Cada aeronave sai da bancada testada em voo, com ficha arquivada por
número de série — é o compromisso de produto da empresa, e é isso que
este módulo registra.
"""

from .. import consultas as q
from .. import db, ui, web
from ..util import (agora_iso, data_br, esc, hoje_iso, para_iso)
from ..barcode import svg as codigo_barras


def registrar(app):

    @app.rota("/producao")
    def lista(req):
        busca = req.arg("q")
        filtros, valores = ["1=1"], []
        if busca:
            filtros.append("(pr.serie LIKE ? OR i.codigo LIKE ? OR i.descricao LIKE ?)")
            valores += [f"%{busca}%"] * 3
        with db.aberto() as con:
            registros = con.execute(
                f"SELECT pr.*, i.codigo, i.descricao, p.numero AS pedido "
                f"FROM producao pr JOIN item i ON i.id = pr.item_id "
                f"LEFT JOIN pedido p ON p.id = pr.pedido_id "
                f"WHERE {' AND '.join(filtros)} ORDER BY pr.id DESC LIMIT 300",
                valores).fetchall()

        linhas = [[
            f'<a href="{ui.u("/producao/" + str(r["id"]))}" class="mono">'
            f'{esc(r["serie"])}</a>',
            f'<span class="mono">{esc(r["codigo"])}</span> {esc(r["descricao"])}',
            data_br(r["data"]),
            (ui.tarja("sim" if r["testado"] else "nao",
                      "Testado em voo" if r["testado"] else "Pendente"), "meio"),
            esc(r["responsavel"] or "—"),
            (f'<a href="{ui.u("/pedidos/" + str(r["pedido_id"]))}" class="mono">'
             f'{esc(r["pedido"])}</a>' if r["pedido"] else "—"),
        ] for r in registros]

        pendentes = len([r for r in registros if not r["testado"]])
        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="grade grade--3" style="margin-bottom:1.4rem">
  {ui.cartao_indicador('Unidades registradas', str(len(registros)),
                       'Com número de série')}
  {ui.cartao_indicador('Aguardando teste de voo', str(pendentes),
                       'Não podem ser entregues',
                       tom='atencao' if pendentes else 'ok')}
  {ui.cartao_indicador('Aprovadas', str(len(registros) - pendentes),
                       'Ficha de inspeção concluída', tom='ok')}
</div>
<div class="painel">
  <div class="painel__cabeca">
    {ui.busca('/producao', busca, 'Número de série ou item')}
    <span class="dica">{len(registros)} unidade(s)</span>
  </div>
  {ui.tabela(['Número de série', 'Item', 'Data', ('Inspeção', 'meio'),
              'Responsável', 'Pedido'], linhas,
             'Nenhuma unidade registrada ainda.')}
</div>"""
        return web.pagina(ui.layout(
            "Produção e números de série", conteudo, "producao", req.usuario,
            ui.acoes(ui.bt("Registrar unidade", "/producao/nova", "bt--principal"))))

    def _proxima_serie(con, item_id):
        item = con.execute("SELECT codigo FROM item WHERE id = ?", (item_id,)).fetchone()
        prefixo = f'{item["codigo"]}-{hoje_iso()[:4]}-' if item else "SN-"
        ultimo = con.execute(
            "SELECT serie FROM producao WHERE serie LIKE ? ORDER BY serie DESC LIMIT 1",
            (prefixo + "%",)).fetchone()
        seq = int(ultimo["serie"].rsplit("-", 1)[1]) + 1 if ultimo else 1
        return f"{prefixo}{seq:03d}"

    @app.rota("/producao/nova", metodos=("GET", "POST"))
    def nova(req):
        with db.aberto() as con:
            produtos = con.execute(
                "SELECT id, codigo, descricao FROM item "
                "WHERE ativo = 1 AND tipo IN ('produto','componente') ORDER BY codigo"
            ).fetchall()
            pedidos = con.execute(
                "SELECT id, numero FROM pedido WHERE status NOT IN ('cancelado')"
                " ORDER BY id DESC LIMIT 60").fetchall()

        opcoes_item = [("", "Selecione…")] + [
            (str(p["id"]), f'{p["codigo"]} — {p["descricao"]}') for p in produtos]
        opcoes_pedido = [("", "—")] + [(str(p["id"]), p["numero"]) for p in pedidos]

        if req.metodo == "POST":
            item_id = req.texto("item_id")
            if not item_id:
                return _form(req, opcoes_item, opcoes_pedido, "Escolha o item produzido.")
            with db.transacao() as con:
                serie = req.texto("serie") or _proxima_serie(con, int(item_id))
                existe = con.execute("SELECT 1 FROM producao WHERE serie = ?",
                                     (serie,)).fetchone()
                if existe:
                    return _form(req, opcoes_item, opcoes_pedido,
                                 f"O número de série {serie} já está registrado.")
                cur = con.execute(
                    "INSERT INTO producao (serie, item_id, pedido_id, data, testado,"
                    " responsavel, observacao, criado_em) VALUES (?,?,?,?,?,?,?,?)",
                    (serie, int(item_id),
                     int(req.texto("pedido_id")) if req.texto("pedido_id") else None,
                     para_iso(req.texto("data")) or hoje_iso(),
                     1 if req.texto("testado") == "1" else 0,
                     req.texto("responsavel") or req.usuario["nome"],
                     req.texto("observacao"), agora_iso()))
                novo_id = cur.lastrowid
            return web.redirecionar(f"/producao/{novo_id}",
                                    f"Unidade {serie} registrada.")

        return _form(req, opcoes_item, opcoes_pedido)

    def _form(req, opcoes_item, opcoes_pedido, erro=""):
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        corpo = f"""{alerta}
<form method="post" action="{ui.u('/producao/nova')}">
  <div class="painel">
    <div class="formulario">
      {ui.selecao('item_id', 'Item produzido', opcoes_item, req.texto('item_id'),
                  obrigatorio=True, largura='campo--largo')}
      {ui.campo('serie', 'Número de série', req.texto('serie'),
                dica='Em branco, o sistema gera a partir do código do item.')}
      {ui.campo('data', 'Data da montagem', data_br(hoje_iso()), obrigatorio=True)}
      {ui.selecao('pedido_id', 'Pedido vinculado', opcoes_pedido, req.texto('pedido_id'))}
      {ui.campo('responsavel', 'Responsável pela montagem',
                req.texto('responsavel') or (req.usuario['nome'] if req.usuario else ''))}
      {ui.selecao('testado', 'Teste em voo',
                  [('0', 'Pendente'), ('1', 'Realizado e aprovado')],
                  req.texto('testado', '0'),
                  dica='A unidade só deve ser entregue depois de aprovada.')}
      {ui.area('observacao', 'Ficha de inspeção — observações',
               req.texto('observacao'), linhas=4,
               dica='Calibração, ajustes de firmware, ocorrências do voo de teste.')}
    </div>
    <div class="rodape-form">
      {ui.bt('Registrar unidade', classe='bt--principal', tipo='submit')}
      {ui.bt('Cancelar', '/producao', 'bt--claro')}
    </div>
  </div>
</form>"""
        return web.pagina(ui.layout("Registrar unidade produzida", corpo,
                                    "producao", req.usuario))

    @app.rota("/producao/<int:rid>/testar", metodos=("POST",))
    def testar(req, rid):
        with db.aberto() as con:
            con.execute("UPDATE producao SET testado = 1 WHERE id = ?", (rid,))
        return web.redirecionar(f"/producao/{rid}",
                                "Teste em voo registrado como aprovado.")

    @app.rota("/producao/<int:rid>")
    def ficha(req, rid):
        with db.aberto() as con:
            r = con.execute(
                "SELECT pr.*, i.codigo, i.descricao, i.unidade, p.numero AS pedido,"
                " pa.nome AS cliente FROM producao pr "
                "JOIN item i ON i.id = pr.item_id "
                "LEFT JOIN pedido p ON p.id = pr.pedido_id "
                "LEFT JOIN parceiro pa ON pa.id = p.parceiro_id "
                "WHERE pr.id = ?", (rid,)).fetchone()
            if not r:
                return web.nao_encontrado("Unidade não encontrada.")
            emp = q.empresa(con)

        acao = ""
        if not r["testado"]:
            acao = (f'<form method="post" action="{ui.u(f"/producao/{rid}/testar")}" '
                    f'style="display:inline">'
                    f'<button class="bt bt--principal bt--mini" type="submit">'
                    f'Registrar teste em voo aprovado</button></form>')

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <div class="doc__cabeca">
    <div>
      <img src="{ui.u('/static/img/logo-voasul.svg')}" alt="VoaSul" style="height:44px">
      <p style="margin:.4rem 0 0;font-size:.8rem">
        <strong>{esc(emp.get('razao_social', ''))}</strong><br>
        Ficha de inspeção de unidade produzida</p>
    </div>
    <div style="text-align:right">{codigo_barras(r['serie'], altura=38)}</div>
  </div>

  <div class="grade grade--3">
    <div><span class="dica">Número de série</span><br>
      <strong class="mono">{esc(r['serie'])}</strong></div>
    <div><span class="dica">Item</span><br>
      <a href="{ui.u('/itens/' + str(r['item_id']))}" class="mono">{esc(r['codigo'])}</a>
      {esc(r['descricao'])}</div>
    <div><span class="dica">Data da montagem</span><br>
      <strong>{data_br(r['data'])}</strong></div>
    <div><span class="dica">Responsável</span><br>
      <strong>{esc(r['responsavel'] or '—')}</strong></div>
    <div><span class="dica">Pedido</span><br>
      {f'<a href="{ui.u("/pedidos/" + str(r["pedido_id"]))}" class="mono">{esc(r["pedido"])}</a>' if r["pedido"] else "—"}</div>
    <div><span class="dica">Cliente</span><br><strong>{esc(r['cliente'] or '—')}</strong></div>
  </div>

  <p style="margin-top:1.2rem"><span class="dica">Teste em voo</span><br>
    {ui.tarja('sim' if r['testado'] else 'nao',
              'Realizado e aprovado' if r['testado'] else 'Pendente — não entregar')}</p>

  <p><span class="dica">Observações da inspeção</span><br>
    {esc(r['observacao'] or '—')}</p>

  <p style="margin-top:1.2rem;font-size:.78rem;color:#666">
    Garantia de 6 meses contra defeito de fabricação, a contar da entrega.
    Reposição de peças a partir do estoque da sede.
  </p>
  <div class="rodape-form nao-imprime">{acao}</div>
</div>"""
        return web.pagina(ui.layout(
            f'Unidade {r["serie"]}', conteudo, "producao", req.usuario,
            ui.acoes(ui.bt("Etiqueta", f"/etiquetas?serie={rid}", "bt--escuro"),
                     ui.bt("Imprimir ficha", "?imprimir=1", "bt--claro"),
                     ui.bt("Voltar", "/producao", "bt--claro"))))
