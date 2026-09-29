"""Etiquetas com código de barras, prontas para impressão em folha A4."""

from .. import db, ui, web
from ..barcode import svg as codigo_barras
from ..util import data_br, esc, moeda


def registrar(app):

    @app.rota("/etiquetas")
    def escolher(req):
        # Atalho: /etiquetas?serie=<id> imprime a etiqueta daquela unidade.
        if req.arg("serie"):
            return _folha_serie(req, int(req.arg("serie")))

        busca = req.arg("q")
        with db.aberto() as con:
            filtro, valores = "ativo = 1", []
            if busca:
                filtro += " AND (codigo LIKE ? OR descricao LIKE ?)"
                valores += [f"%{busca}%"] * 2
            itens = con.execute(
                f"SELECT * FROM item WHERE {filtro} ORDER BY codigo", valores).fetchall()

        pre = req.arg("item")
        linhas = "".join(f"""<tr>
  <td class="meio"><input type="checkbox" name="item" value="{i['id']}"
      style="width:auto"{" checked" if str(i["id"]) == pre else ""}></td>
  <td class="mono">{esc(i['codigo'])}</td>
  <td>{esc(i['descricao'])}</td>
  <td class="meio">{ui.rotulo(i['tipo'])}</td>
  <td class="num">{moeda(i['preco'])}</td>
  <td style="width:90px"><input type="number" name="qtd_{i['id']}" value="1"
      min="1" max="60"></td>
</tr>""" for i in itens)

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <h2>Etiquetas de item</h2>
  <p class="dica">Marque os itens, informe quantas etiquetas de cada um e gere a
  folha. O código de barras é o código do item, no padrão Code 39 — lido por
  qualquer leitor comum.</p>
  <form method="get" action="{ui.u('/etiquetas/folha')}">
    <div class="tabela-area" style="max-height:440px;overflow:auto">
      <table class="tabela">
        <thead><tr><th class="meio">Imprimir</th><th>Código</th><th>Descrição</th>
          <th class="meio">Tipo</th><th class="num">Preço</th>
          <th>Qtd. etiquetas</th></tr></thead>
        <tbody>{linhas}</tbody>
      </table>
    </div>
    <div class="rodape-form">
      {ui.bt('Gerar folha de etiquetas', classe='bt--principal', tipo='submit')}
      <label class="dica" style="display:flex;gap:.35rem;align-items:center">
        <input type="checkbox" name="preco" value="1" style="width:auto" checked>
        incluir preço na etiqueta</label>
    </div>
  </form>
</div>

<div class="painel">
  <h2>Etiquetas de unidade produzida</h2>
  <p class="dica">Etiqueta com o número de série, para gravar no frame e colar
  na embalagem. Abra a unidade em
  <a href="{ui.u('/producao')}">Produção</a> e use o botão “Etiqueta”.</p>
</div>"""
        return web.pagina(ui.layout(
            "Etiquetas", conteudo, "etiquetas", req.usuario,
            ui.acoes(ui.bt("Buscar item", "/etiquetas", "bt--claro"))))

    @app.rota("/etiquetas/folha")
    def folha(req):
        escolhidos = req.consulta  # querystring simples; item repetido vira lista
        ids = [v for k, v in escolhidos.items() if k == "item"]
        # parse_qs guarda só o último valor; relemos a querystring bruta:
        from urllib.parse import parse_qs
        bruto = parse_qs(req.ambiente.get("QUERY_STRING", ""))
        ids = bruto.get("item", [])
        mostrar_preco = bruto.get("preco", ["0"])[0] == "1"

        if not ids:
            return web.redirecionar("/etiquetas",
                                    "Erro: marque ao menos um item para gerar a folha.")

        with db.aberto() as con:
            marcadores = ",".join("?" * len(ids))
            itens = con.execute(
                f"SELECT * FROM item WHERE id IN ({marcadores}) ORDER BY codigo",
                ids).fetchall()
            emp = con.execute(
                "SELECT valor FROM ajuste WHERE chave = 'nome_fantasia'").fetchone()

        marca = emp["valor"] if emp else "VOA-SUL"
        etiquetas = []
        for item in itens:
            try:
                quantas = max(1, min(int(bruto.get(f"qtd_{item['id']}", ["1"])[0]), 60))
            except ValueError:
                quantas = 1
            preco = (f'<div class="etiqueta__rodape"><strong>{moeda(item["preco"])}'
                     f'</strong></div>') if mostrar_preco and item["preco"] else ""
            for _ in range(quantas):
                etiquetas.append(f"""<div class="etiqueta">
  <img class="etiqueta__marca" src="{ui.u('/static/img/simbolo-voasul.svg')}" alt="">
  <div class="etiqueta__cod">{esc(item['codigo'])}</div>
  <div class="etiqueta__desc">{esc(item['descricao'])}</div>
  {codigo_barras(item['codigo'], altura=34, estreito=2)}
  <div class="etiqueta__rodape">{esc(marca)} · {esc(item['unidade'])}
    {f"· {esc(item['localizacao'])}" if item['localizacao'] else ""}</div>
  {preco}
</div>""")

        corpo = f"""<div class="folha">
  <p class="nao-imprime" style="margin-bottom:1rem">
    <a class="bt bt--principal" href="?{esc(req.ambiente.get('QUERY_STRING', ''))}&amp;imprimir=1">Imprimir</a>
    <a class="bt bt--claro" href="{ui.u('/etiquetas')}">Voltar</a>
    <span class="dica" style="margin-left:.6rem">{len(etiquetas)} etiqueta(s) —
    3 por linha, cabem 24 por folha A4.</span>
  </p>
  <div class="etiquetas">{"".join(etiquetas)}</div>
</div>"""
        return web.pagina(ui.layout_limpo("Etiquetas", corpo, corpo_classe="folha-doc"))

    def _folha_serie(req, producao_id):
        with db.aberto() as con:
            r = con.execute(
                "SELECT pr.*, i.codigo, i.descricao FROM producao pr "
                "JOIN item i ON i.id = pr.item_id WHERE pr.id = ?",
                (producao_id,)).fetchone()
            if not r:
                return web.nao_encontrado("Unidade não encontrada.")
            emp = con.execute(
                "SELECT valor FROM ajuste WHERE chave = 'nome_fantasia'").fetchone()
        marca = emp["valor"] if emp else "VOA-SUL"

        etiqueta = f"""<div class="etiqueta" style="max-width:74mm">
  <img class="etiqueta__marca" src="{ui.u('/static/img/simbolo-voasul.svg')}" alt=""
       style="height:10mm">
  <div class="etiqueta__cod">{esc(r['codigo'])}</div>
  <div class="etiqueta__desc">{esc(r['descricao'])}</div>
  {codigo_barras(r['serie'], altura=40, estreito=2)}
  <div class="etiqueta__rodape">
    Série {esc(r['serie'])}<br>
    Montado em {data_br(r['data'])} · {esc(marca)}<br>
    {"Testado em voo · Garantia 6 meses" if r['testado'] else "AGUARDANDO TESTE DE VOO"}
  </div>
</div>"""
        corpo = f"""<div class="folha">
  <p class="nao-imprime" style="margin-bottom:1rem">
    <a class="bt bt--principal" href="?serie={producao_id}&amp;imprimir=1">Imprimir</a>
    <a class="bt bt--claro" href="{ui.u('/producao/' + str(producao_id))}">Voltar</a>
  </p>
  <div class="etiquetas" style="grid-template-columns:1fr;max-width:80mm">{etiqueta}</div>
</div>"""
        return web.pagina(ui.layout_limpo(f'Etiqueta {r["serie"]}', corpo,
                                          corpo_classe="folha-doc"))
