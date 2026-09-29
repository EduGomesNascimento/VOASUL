"""Cadastro de clientes e fornecedores."""

from .. import db, ui, web
from ..util import (agora_iso, documento_valido, esc, formata_documento,
                    moeda)

TIPOS = [("cliente", "Cliente"), ("fornecedor", "Fornecedor"),
         ("ambos", "Cliente e fornecedor")]
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
       "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
       "SE", "SP", "TO"]


def registrar(app):

    @app.rota("/parceiros")
    def lista(req):
        busca, tipo = req.arg("q"), req.arg("tipo")
        filtros, valores = ["1=1"], []
        if busca:
            filtros.append("(nome LIKE ? OR documento LIKE ? OR cidade LIKE ?)")
            valores += [f"%{busca}%"] * 3
        if tipo:
            filtros.append("(tipo = ? OR tipo = 'ambos')")
            valores.append(tipo)
        with db.aberto() as con:
            registros = con.execute(
                f"SELECT * FROM parceiro WHERE {' AND '.join(filtros)} ORDER BY nome",
                valores).fetchall()

        linhas = [[
            f'<a href="{ui.u("/parceiros/" + str(p["id"]))}">{esc(p["nome"])}</a>'
            + ("" if p["ativo"] else ' <span class="tarja tarja--neutro">inativo</span>'),
            ui.rotulo(p["tipo"]),
            (f'<span class="mono">{esc(formata_documento(p["documento"]))}</span>'
             if p["documento"] else "—"),
            esc(p["telefone"] or "—"),
            esc(p["email"] or "—"),
            esc(f'{p["cidade"]}/{p["uf"]}' if p["cidade"] else "—"),
        ] for p in registros]

        opcoes = ('<select name="tipo"><option value="">Todos</option>'
                  '<option value="cliente"' + (" selected" if tipo == "cliente" else "") +
                  '>Clientes</option><option value="fornecedor"' +
                  (" selected" if tipo == "fornecedor" else "") +
                  ">Fornecedores</option></select>")

        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <div class="painel__cabeca">
    {ui.busca('/parceiros', busca, 'Nome, documento ou cidade', opcoes)}
    <span class="dica">{len(registros)} cadastro(s)</span>
  </div>
  {ui.tabela(['Nome', 'Tipo', 'CPF / CNPJ', 'Telefone', 'E-mail', 'Cidade'],
             linhas, 'Nenhum cadastro encontrado.')}
</div>"""
        return web.pagina(ui.layout(
            "Clientes e fornecedores", conteudo, "parceiros", req.usuario,
            ui.acoes(ui.bt("Novo cadastro", "/parceiros/novo", "bt--principal"))))

    def _formulario(req, registro=None, erro=""):
        novo = registro is None
        d = dict(registro) if registro else {
            "nome": "", "tipo": "cliente", "documento": "", "email": "",
            "telefone": "", "endereco": "", "cidade": "", "uf": "RS",
            "cep": "", "observacao": "", "ativo": 1}
        alerta = f'<div class="aviso aviso--erro">{esc(erro)}</div>' if erro else ""
        destino = "/parceiros/novo" if novo else f'/parceiros/{registro["id"]}/editar'

        corpo = f"""{alerta}
<form method="post" action="{ui.u(destino)}">
  <div class="painel">
    <div class="formulario">
      {ui.campo('nome', 'Nome ou razão social', d['nome'], obrigatorio=True,
                largura='campo--largo')}
      {ui.selecao('tipo', 'Tipo', TIPOS, d['tipo'], obrigatorio=True)}
      {ui.campo('documento', 'CPF / CNPJ', formata_documento(d['documento']),
                dica='Validado pelos dígitos verificadores. Pode ficar em branco.')}
      {ui.selecao('ativo', 'Situação', [(1, 'Ativo'), (0, 'Inativo')], d['ativo'])}
      {ui.campo('telefone', 'Telefone / WhatsApp', d['telefone'])}
      {ui.campo('email', 'E-mail', d['email'], tipo='email')}
      {ui.campo('cep', 'CEP', d['cep'])}
      {ui.campo('endereco', 'Endereço', d['endereco'], largura='campo--largo')}
      {ui.campo('cidade', 'Cidade', d['cidade'])}
      {ui.selecao('uf', 'UF', [(x, x) for x in UFS], d['uf'])}
      {ui.area('observacao', 'Observações', d['observacao'])}
    </div>
    <div class="rodape-form">
      {ui.bt('Salvar cadastro', classe='bt--principal', tipo='submit')}
      {ui.bt('Cancelar', '/parceiros', 'bt--claro')}
    </div>
  </div>
</form>"""
        titulo = "Novo cadastro" if novo else esc(registro["nome"])
        return web.pagina(ui.layout(titulo, corpo, "parceiros", req.usuario))

    def _ler(req):
        return {
            "nome": req.texto("nome"), "tipo": req.texto("tipo", "cliente"),
            "documento": req.texto("documento"), "email": req.texto("email"),
            "telefone": req.texto("telefone"), "endereco": req.texto("endereco"),
            "cidade": req.texto("cidade"), "uf": req.texto("uf", "RS"),
            "cep": req.texto("cep"), "observacao": req.texto("observacao"),
            "ativo": 1 if req.texto("ativo", "1") == "1" else 0,
        }

    @app.rota("/parceiros/novo", metodos=("GET", "POST"))
    def novo(req):
        if req.metodo == "GET":
            return _formulario(req)
        d = _ler(req)
        if not d["nome"]:
            return _formulario(req, erro="O nome é obrigatório.")
        if not documento_valido(d["documento"]):
            return _formulario(req, erro="CPF ou CNPJ inválido — confira os dígitos.")
        with db.aberto() as con:
            con.execute(
                "INSERT INTO parceiro (nome, tipo, documento, email, telefone,"
                " endereco, cidade, uf, cep, observacao, ativo, criado_em)"
                " VALUES (:nome,:tipo,:documento,:email,:telefone,:endereco,"
                ":cidade,:uf,:cep,:observacao,:ativo,:criado_em)",
                {**d, "criado_em": agora_iso()})
        return web.redirecionar("/parceiros", f'{d["nome"]} cadastrado.')

    @app.rota("/parceiros/<int:pid>/editar", metodos=("GET", "POST"))
    def editar(req, pid):
        with db.aberto() as con:
            registro = con.execute("SELECT * FROM parceiro WHERE id = ?", (pid,)).fetchone()
        if not registro:
            return web.nao_encontrado("Cadastro não encontrado.")
        if req.metodo == "GET":
            return _formulario(req, registro)
        d = _ler(req)
        if not d["nome"]:
            return _formulario(req, registro, "O nome é obrigatório.")
        if not documento_valido(d["documento"]):
            return _formulario(req, registro, "CPF ou CNPJ inválido — confira os dígitos.")
        with db.aberto() as con:
            con.execute(
                "UPDATE parceiro SET nome=:nome, tipo=:tipo, documento=:documento,"
                " email=:email, telefone=:telefone, endereco=:endereco, cidade=:cidade,"
                " uf=:uf, cep=:cep, observacao=:observacao, ativo=:ativo WHERE id=:id",
                {**d, "id": pid})
        return web.redirecionar(f"/parceiros/{pid}", "Cadastro atualizado.")

    @app.rota("/parceiros/<int:pid>")
    def ficha(req, pid):
        with db.aberto() as con:
            p = con.execute("SELECT * FROM parceiro WHERE id = ?", (pid,)).fetchone()
            if not p:
                return web.nao_encontrado("Cadastro não encontrado.")
            pedidos = con.execute(
                "SELECT * FROM pedido WHERE parceiro_id = ? ORDER BY id DESC LIMIT 25",
                (pid,)).fetchall()
            from .. import consultas as q
            totais = {x["id"]: q.total_pedido(con, x)["total"] for x in pedidos}
            notas = con.execute(
                "SELECT * FROM nota WHERE parceiro_id = ? ORDER BY id DESC LIMIT 25",
                (pid,)).fetchall()

        from ..util import data_br
        linhas_ped = [[
            f'<a href="{ui.u("/pedidos/" + str(x["id"]))}" class="mono">{esc(x["numero"])}</a>',
            ui.rotulo(x["tipo"]), data_br(x["data_emissao"]),
            ui.tarja(x["status"]), (moeda(totais[x["id"]]), "num"),
        ] for x in pedidos]
        linhas_nf = [[
            f'<a href="{ui.u("/notas/" + str(n["id"]))}" class="mono">'
            f'{esc(n["numero"])}/{esc(n["serie"])}</a>',
            data_br(n["data_emissao"]), esc(n["natureza"]), ui.tarja(n["status"]),
        ] for n in notas]

        faturado = sum(totais.values())
        conteudo = f"""
{ui.aviso_da_url(req)}
<div class="painel">
  <h2>Dados cadastrais</h2>
  <div class="grade grade--3">
    <div><span class="dica">Tipo</span><br><strong>{ui.rotulo(p['tipo'])}</strong></div>
    <div><span class="dica">CPF / CNPJ</span><br><strong class="mono">{esc(formata_documento(p['documento']) or '—')}</strong></div>
    <div><span class="dica">Situação</span><br>{ui.tarja('sim' if p['ativo'] else 'nao', 'Ativo' if p['ativo'] else 'Inativo')}</div>
    <div><span class="dica">Telefone</span><br><strong>{esc(p['telefone'] or '—')}</strong></div>
    <div><span class="dica">E-mail</span><br><strong>{esc(p['email'] or '—')}</strong></div>
    <div><span class="dica">Cidade</span><br><strong>{esc((p['cidade'] + '/' + p['uf']) if p['cidade'] else '—')}</strong></div>
    <div><span class="dica">Endereço</span><br><strong>{esc(p['endereco'] or '—')}</strong></div>
    <div><span class="dica">CEP</span><br><strong>{esc(p['cep'] or '—')}</strong></div>
    <div><span class="dica">Total em pedidos</span><br><strong>{moeda(faturado)}</strong></div>
  </div>
  {f'<p style="margin-top:1rem"><span class="dica">Observações</span><br>{esc(p["observacao"])}</p>' if p["observacao"] else ""}
</div>

<div class="painel">
  <h2>Pedidos</h2>
  {ui.tabela(['Número', 'Tipo', 'Emissão', 'Situação', ('Total', 'num')],
             linhas_ped, 'Nenhum pedido para este cadastro.')}
</div>

<div class="painel">
  <h2>Notas fiscais</h2>
  {ui.tabela(['Número/Série', 'Emissão', 'Natureza', 'Situação'],
             linhas_nf, 'Nenhuma nota emitida para este cadastro.')}
</div>"""
        return web.pagina(ui.layout(
            esc(p["nome"]), conteudo, "parceiros", req.usuario,
            ui.acoes(ui.bt("Editar", f"/parceiros/{pid}/editar", "bt--principal"),
                     ui.bt("Voltar", "/parceiros", "bt--claro"))))
