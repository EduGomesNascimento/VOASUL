"""Cadastro de itens: matérias-primas, componentes, produtos e serviços."""

from .. import consultas as q
from .. import db, ui, web
from ..util import (agora_iso, codigo_limpo, data_br, esc, moeda, numero,
                    para_float, quantidade)

TIPOS = [("materia_prima", "Matéria-prima"), ("componente", "Componente"),
         ("produto", "Produto acabado"), ("servico", "Serviço")]
UNIDADES = ["UN", "PC", "JG", "KG", "G", "M", "CM", "L", "ML", "HR", "CX"]


def registrar(app):

    @app.rota("/itens")
    def lista(req):
        busca, tipo = req.arg("q"), req.arg("tipo")
        with db.aberto() as con:
            itens = q.itens_com_saldo(con, busca, tipo, apenas_ativos=False)

        linhas = []
        for i in itens:
            baixo = i["tipo"] != "servico" and i["saldo"] < i["estoque_min"]
            saldo = quantidade(i["saldo"]) if i["tipo"] != "servico" else "—"
            linhas.append([
                f'<a href="{ui.u("/itens/" + str(i["id"]))}" class="mono">'
                f'{esc(i["codigo"])}</a>',
                esc(i["descricao"]) + ("" if i["ativo"] else
                                       ' <span class="tarja tarja--neutro">inativo</span>'),
                ui.rotulo(i["tipo"]),
                (esc(i["unidade"]), "meio"),
                (saldo, "num negativo" if baixo else "num"),
                (quantidade(i["estoque_min"]) if i["tipo"] != "servico" else "—", "num"),
                (moeda(i["custo"]), "num"),
                (moeda(i["preco"]), "num"),
                (esc(i["localizacao"] or "—"), "meio"),
            ])

        opcoes = '<select name="tipo"><option value="">Todos os tipos</option>' + "".join(
            f'<option value="{v}"{" selected" if v == tipo else ""}>{esc(t)}</option>'
            for v, t in TIPOS) + "</select>"

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <div class="painel__cabeca">
    {ui.busca('/itens', busca, 'Código ou descrição', opcoes)}
    <span class="dica">{len(itens)} item(ns)</span>
  </div>
  {ui.tabela(['Código', 'Descrição', 'Tipo', ('Un.', 'meio'), ('Saldo', 'num'),
              ('Mínimo', 'num'), ('Custo', 'num'), ('Preço', 'num'),
              ('Local', 'meio')], linhas,
             'Nenhum item encontrado com esse filtro.')}
</div>"""
        return web.pagina(ui.layout(
            "Itens e materiais", conteudo, "itens", req.usuario,
            ui.acoes(ui.bt("Novo item", "/itens/novo", "bt--principal"),
                     ui.bt("Exportar CSV", "/relatorios/estoque.csv", "bt--claro"))))

    # ------------------------------------------------------------- formulário
    def _formulario(req, item=None, erro=""):
        novo = item is None
        d = dict(item) if item else {
            "codigo": "", "descricao": "", "tipo": "componente", "unidade": "UN",
            "ncm": "", "custo": 0, "preco": 0, "estoque_min": 0,
            "localizacao": "", "observacao": "", "ativo": 1}
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        destino = "/itens/novo" if novo else f'/itens/{item["id"]}/editar'

        corpo = f"""{alerta}
<form method="post" action="{ui.u(destino)}">
  <div class="painel">
    <div class="formulario">
      {ui.campo('codigo', 'Código', d['codigo'], obrigatorio=True,
                dica='Vira o código de barras da etiqueta. Use letras, números e hífen.')}
      {ui.selecao('tipo', 'Tipo', TIPOS, d['tipo'], obrigatorio=True)}
      {ui.selecao('unidade', 'Unidade', [(x, x) for x in UNIDADES], d['unidade'])}
      {ui.campo('descricao', 'Descrição', d['descricao'], obrigatorio=True,
                largura='campo--largo')}
      {ui.campo('custo', 'Custo unitário (R$)', numero(d['custo']))}
      {ui.campo('preco', 'Preço de venda (R$)', numero(d['preco']))}
      {ui.campo('estoque_min', 'Estoque mínimo', quantidade(d['estoque_min']),
                dica='Abaixo disso o item entra no alerta de reposição.')}
      {ui.campo('localizacao', 'Localização', d['localizacao'],
                dica='Prateleira ou gaveta na sede.')}
      {ui.campo('ncm', 'NCM', d['ncm'], dica='Usado na nota fiscal.')}
      {ui.selecao('ativo', 'Situação', [(1, 'Ativo'), (0, 'Inativo')], d['ativo'])}
      {ui.area('observacao', 'Observações', d['observacao'])}
    </div>
    <div class="rodape-form">
      {ui.bt('Salvar item', classe='bt--principal', tipo='submit')}
      {ui.bt('Cancelar', '/itens', 'bt--claro')}
    </div>
  </div>
</form>"""
        titulo = "Novo item" if novo else f'Item {item["codigo"]}'
        return web.pagina(ui.layout(titulo, corpo, "itens", req.usuario))

    def _ler(req):
        return {
            "codigo": codigo_limpo(req.texto("codigo")),
            "descricao": req.texto("descricao"),
            "tipo": req.texto("tipo", "componente"),
            "unidade": req.texto("unidade", "UN"),
            "ncm": req.texto("ncm"),
            "custo": para_float(req.texto("custo")),
            "preco": para_float(req.texto("preco")),
            "estoque_min": para_float(req.texto("estoque_min")),
            "localizacao": req.texto("localizacao"),
            "observacao": req.texto("observacao"),
            "ativo": 1 if req.texto("ativo", "1") == "1" else 0,
        }

    @app.rota("/itens/novo", metodos=("GET", "POST"))
    def novo(req):
        if req.metodo == "GET":
            return _formulario(req)
        d = _ler(req)
        if not d["codigo"] or not d["descricao"]:
            return _formulario(req, erro="Código e descrição são obrigatórios.")
        with db.aberto() as con:
            if con.execute("SELECT 1 FROM item WHERE codigo = ?", (d["codigo"],)).fetchone():
                return _formulario(req, erro=f'Já existe um item com o código {d["codigo"]}.')
            con.execute(
                "INSERT INTO item (codigo, descricao, tipo, unidade, ncm, custo, preco,"
                " estoque_min, localizacao, observacao, ativo, criado_em)"
                " VALUES (:codigo,:descricao,:tipo,:unidade,:ncm,:custo,:preco,"
                ":estoque_min,:localizacao,:observacao,:ativo,:criado_em)",
                {**d, "criado_em": agora_iso()})
        return web.redirecionar("/itens", f'Item {d["codigo"]} cadastrado.')

    @app.rota("/itens/<int:item_id>/editar", metodos=("GET", "POST"))
    def editar(req, item_id):
        with db.aberto() as con:
            item = con.execute("SELECT * FROM item WHERE id = ?", (item_id,)).fetchone()
        if not item:
            return web.nao_encontrado("Item não encontrado.")
        if req.metodo == "GET":
            return _formulario(req, item)

        d = _ler(req)
        if not d["codigo"] or not d["descricao"]:
            return _formulario(req, item, "Código e descrição são obrigatórios.")
        with db.aberto() as con:
            duplicado = con.execute(
                "SELECT 1 FROM item WHERE codigo = ? AND id <> ?",
                (d["codigo"], item_id)).fetchone()
            if duplicado:
                return _formulario(req, item, f'Já existe outro item com o código {d["codigo"]}.')
            con.execute(
                "UPDATE item SET codigo=:codigo, descricao=:descricao, tipo=:tipo,"
                " unidade=:unidade, ncm=:ncm, custo=:custo, preco=:preco,"
                " estoque_min=:estoque_min, localizacao=:localizacao,"
                " observacao=:observacao, ativo=:ativo WHERE id=:id",
                {**d, "id": item_id})
        return web.redirecionar(f"/itens/{item_id}", "Item atualizado.")

    # ---------------------------------------------------------------- ficha
    @app.rota("/itens/<int:item_id>")
    def ficha(req, item_id):
        with db.aberto() as con:
            item = con.execute("SELECT * FROM item WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return web.nao_encontrado("Item não encontrado.")
            saldo = q.saldo_item(con, item_id)
            medio = q.custo_medio(con, item_id)
            movimentos = con.execute(
                "SELECT * FROM movimento WHERE item_id = ? ORDER BY id DESC LIMIT 40",
                (item_id,)).fetchall()
            demandas = con.execute(
                "SELECT * FROM demanda WHERE item_id = ? AND status IN"
                " ('aberta','em_andamento') ORDER BY id DESC", (item_id,)).fetchall()

        baixo = item["tipo"] != "servico" and saldo < item["estoque_min"]
        indicadores = "".join([
            ui.cartao_indicador("Saldo atual",
                                quantidade(saldo) + " " + item["unidade"],
                                f'Mínimo {quantidade(item["estoque_min"])}',
                                tom="erro" if baixo else "ok"),
            ui.cartao_indicador("Custo médio", moeda(medio), "Média das entradas"),
            ui.cartao_indicador("Preço de venda", moeda(item["preco"]), "Tabela atual"),
            ui.cartao_indicador("Valor em estoque", moeda(saldo * medio),
                                "Saldo pelo custo médio"),
        ])

        linhas_mov = [[
            data_br(m["data"]), ui.tarja(m["tipo"]),
            (quantidade(m["quantidade"]), "num"),
            (moeda(m["custo_unit"]), "num"),
            esc(m["documento"] or "—"),
            esc(m["observacao"] or ""),
        ] for m in movimentos]

        linhas_dem = [[
            f'<a href="{ui.u("/demandas/" + str(d["id"]))}" class="mono">'
            f'{esc(d["numero"])}</a>',
            (quantidade(d["quantidade"]), "num"),
            ui.tarja(d["prioridade"]), ui.tarja(d["status"]),
            data_br(d["prazo"]) or "—",
        ] for d in demandas]

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="grade grade--4" style="margin-bottom:1.4rem">{indicadores}</div>

<div class="painel">
  <h2>Dados do item</h2>
  <div class="grade grade--3">
    <div><span class="dica">Código</span><br><strong class="mono">{esc(item['codigo'])}</strong></div>
    <div><span class="dica">Tipo</span><br><strong>{ui.rotulo(item['tipo'])}</strong></div>
    <div><span class="dica">Unidade</span><br><strong>{esc(item['unidade'])}</strong></div>
    <div><span class="dica">Localização</span><br><strong>{esc(item['localizacao'] or '—')}</strong></div>
    <div><span class="dica">NCM</span><br><strong>{esc(item['ncm'] or '—')}</strong></div>
    <div><span class="dica">Situação</span><br>{ui.tarja('sim' if item['ativo'] else 'nao', 'Ativo' if item['ativo'] else 'Inativo')}</div>
  </div>
  {f'<p style="margin-top:1rem"><span class="dica">Observações</span><br>{esc(item["observacao"])}</p>' if item["observacao"] else ""}
</div>

<div class="painel">
  <h2>Demandas em aberto</h2>
  {ui.tabela(['Número', ('Qtd.', 'num'), 'Prioridade', 'Situação', 'Prazo'],
             linhas_dem, 'Nenhuma demanda aberta para este item.')}
</div>

<div class="painel">
  <div class="painel__cabeca">
    <h2>Movimentações</h2>
    {ui.bt('Lançar movimento', f'/estoque/movimentar?item={item_id}',
           'bt--principal bt--mini')}
  </div>
  {ui.tabela(['Data', 'Tipo', ('Qtd.', 'num'), ('Custo un.', 'num'),
              'Documento', 'Observação'], linhas_mov,
             'Nenhuma movimentação registrada.')}
</div>"""

        return web.pagina(ui.layout(
            f'{item["codigo"]} — {item["descricao"]}', conteudo, "itens", req.usuario,
            ui.acoes(ui.bt("Editar", f"/itens/{item_id}/editar", "bt--principal"),
                     ui.bt("Etiquetas", f"/etiquetas?item={item_id}", "bt--claro"),
                     ui.bt("Voltar", "/itens", "bt--claro"))))
