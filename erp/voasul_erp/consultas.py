"""Consultas reaproveitadas pelas telas: saldos, totais e numeração."""

from .util import agora_iso, hoje_iso


# --------------------------------------------------------------- numeração

def proximo_numero(con, tabela, prefixo):
    """Gera número sequencial por ano: PV-2026-0001."""
    ano = hoje_iso()[:4]
    inicio = f"{prefixo}-{ano}-"
    ultimo = con.execute(
        f"SELECT numero FROM {tabela} WHERE numero LIKE ? ORDER BY numero DESC LIMIT 1",
        (inicio + "%",)).fetchone()
    sequencia = int(ultimo["numero"].rsplit("-", 1)[1]) + 1 if ultimo else 1
    return f"{inicio}{sequencia:04d}"


def proximo_numero_nota(con, serie):
    ultimo = con.execute(
        "SELECT numero FROM nota WHERE serie = ? "
        "ORDER BY CAST(numero AS INTEGER) DESC LIMIT 1", (str(serie),)).fetchone()
    return str(int(ultimo["numero"]) + 1) if ultimo else "1"


# ------------------------------------------------------------------ ajustes

def empresa(con):
    return {l["chave"]: l["valor"] for l in con.execute("SELECT chave, valor FROM ajuste")}


# ------------------------------------------------------------------ estoque

def saldo_item(con, item_id) -> float:
    linha = con.execute("SELECT quantidade FROM saldo WHERE item_id = ?",
                        (item_id,)).fetchone()
    return float(linha["quantidade"]) if linha else 0.0


def custo_medio(con, item_id) -> float:
    """Média ponderada das entradas. Sem entradas, usa o custo cadastrado."""
    linha = con.execute(
        "SELECT SUM(quantidade * custo_unit) AS valor, SUM(quantidade) AS qtd "
        "FROM movimento WHERE item_id = ? AND tipo = 'entrada' AND quantidade > 0",
        (item_id,)).fetchone()
    if linha and linha["qtd"]:
        return float(linha["valor"] or 0) / float(linha["qtd"])
    cadastro = con.execute("SELECT custo FROM item WHERE id = ?", (item_id,)).fetchone()
    return float(cadastro["custo"]) if cadastro else 0.0


def itens_com_saldo(con, busca="", tipo="", apenas_ativos=True, so_abaixo_minimo=False):
    filtros, valores = [], []
    if apenas_ativos:
        filtros.append("i.ativo = 1")
    if busca:
        filtros.append("(i.codigo LIKE ? OR i.descricao LIKE ?)")
        valores += [f"%{busca}%", f"%{busca}%"]
    if tipo:
        filtros.append("i.tipo = ?")
        valores.append(tipo)
    if so_abaixo_minimo:
        # `saldo` é uma view já agregada, então o corte vai no WHERE — um
        # HAVING aqui quebraria, por não haver GROUP BY nesta consulta.
        filtros.append("COALESCE(s.quantidade, 0) < i.estoque_min")
        filtros.append("i.tipo <> 'servico'")
    onde = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    return con.execute(
        f"SELECT i.*, COALESCE(s.quantidade, 0) AS saldo "
        f"FROM item i LEFT JOIN saldo s ON s.item_id = i.id "
        f"{onde} ORDER BY i.codigo", valores).fetchall()


def registrar_movimento(con, item_id, tipo, quantidade, custo_unit=0, documento="",
                        observacao="", pedido_id=None, usuario_id=None, data=None):
    con.execute(
        "INSERT INTO movimento (item_id, tipo, quantidade, custo_unit, documento,"
        " observacao, pedido_id, usuario_id, data) VALUES (?,?,?,?,?,?,?,?,?)",
        (item_id, tipo, float(quantidade), float(custo_unit or 0), documento,
         observacao, pedido_id, usuario_id, data or hoje_iso()))


# ------------------------------------------------------------------ pedidos

def itens_do_pedido(con, pedido_id):
    return con.execute(
        "SELECT pi.*, i.codigo, i.descricao, i.unidade, i.tipo AS item_tipo, i.ncm "
        "FROM pedido_item pi JOIN item i ON i.id = pi.item_id "
        "WHERE pi.pedido_id = ? ORDER BY pi.id", (pedido_id,)).fetchall()


def total_pedido(con, pedido):
    linhas = itens_do_pedido(con, pedido["id"])
    produtos = sum(l["quantidade"] * l["preco_unit"] - l["desconto"] for l in linhas)
    total = produtos + float(pedido["frete"] or 0) - float(pedido["desconto"] or 0)
    return {"produtos": produtos, "total": max(total, 0.0), "linhas": linhas}


def baixar_estoque_do_pedido(con, pedido, usuario_id):
    """Dá entrada (compra) ou saída (venda) dos itens físicos do pedido.

    Serviços não movimentam estoque. Roda uma vez só: a coluna `baixado`
    impede que uma segunda confirmação duplique o movimento.
    """
    if pedido["baixado"]:
        return 0
    movimentados = 0
    for linha in itens_do_pedido(con, pedido["id"]):
        if linha["item_tipo"] == "servico" or linha["quantidade"] <= 0:
            continue
        tipo = "entrada" if pedido["tipo"] == "compra" else "saida"
        custo = (linha["preco_unit"] if pedido["tipo"] == "compra"
                 else custo_medio(con, linha["item_id"]))
        registrar_movimento(
            con, linha["item_id"], tipo, linha["quantidade"], custo,
            documento=pedido["numero"],
            observacao=f"Baixa automática do pedido {pedido['numero']}",
            pedido_id=pedido["id"], usuario_id=usuario_id)
        movimentados += 1
    con.execute("UPDATE pedido SET baixado = 1 WHERE id = ?", (pedido["id"],))
    return movimentados


def estornar_estoque_do_pedido(con, pedido, usuario_id):
    """Desfaz a baixa lançando movimentos contrários (mantém o histórico)."""
    if not pedido["baixado"]:
        return 0
    estornados = 0
    for linha in itens_do_pedido(con, pedido["id"]):
        if linha["item_tipo"] == "servico" or linha["quantidade"] <= 0:
            continue
        tipo = "saida" if pedido["tipo"] == "compra" else "entrada"
        registrar_movimento(
            con, linha["item_id"], tipo, linha["quantidade"],
            custo_medio(con, linha["item_id"]), documento=pedido["numero"],
            observacao=f"Estorno do pedido {pedido['numero']}",
            pedido_id=pedido["id"], usuario_id=usuario_id)
        estornados += 1
    con.execute("UPDATE pedido SET baixado = 0 WHERE id = ?", (pedido["id"],))
    return estornados


# ------------------------------------------------------------------- notas

def itens_da_nota(con, nota_id):
    return con.execute(
        "SELECT ni.*, i.codigo, i.descricao, i.unidade "
        "FROM nota_item ni JOIN item i ON i.id = ni.item_id "
        "WHERE ni.nota_id = ? ORDER BY ni.id", (nota_id,)).fetchall()


def total_nota(con, nota):
    linhas = itens_da_nota(con, nota["id"])
    produtos = sum(l["quantidade"] * l["preco_unit"] for l in linhas)
    return {"produtos": produtos,
            "total": produtos + float(nota["frete"] or 0),
            "linhas": linhas}


# ---------------------------------------------------------------- demandas

def gerar_demandas_de_estoque_minimo(con):
    """Cria demanda para item abaixo do mínimo que ainda não tenha uma aberta."""
    criadas = 0
    for item in itens_com_saldo(con, so_abaixo_minimo=True):
        existe = con.execute(
            "SELECT 1 FROM demanda WHERE item_id = ? AND origem = 'estoque_minimo' "
            "AND status IN ('aberta','em_andamento')", (item["id"],)).fetchone()
        if existe:
            continue
        falta = float(item["estoque_min"]) - float(item["saldo"])
        con.execute(
            "INSERT INTO demanda (numero, item_id, quantidade, origem, prioridade,"
            " status, observacao, criado_em)"
            " VALUES (?,?,?,'estoque_minimo',?,'aberta',?,?)",
            (proximo_numero(con, "demanda", "DM"), item["id"], max(falta, 1),
             "alta" if item["saldo"] <= 0 else "normal",
             f"Gerada automaticamente: saldo {item['saldo']:g} abaixo do mínimo "
             f"{item['estoque_min']:g}.", agora_iso()))
        criadas += 1
    return criadas
