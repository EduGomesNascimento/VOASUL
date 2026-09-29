"""Montagem da aplicação: registra todas as telas no roteador."""

from .. import db, web
from . import (auth, configuracoes, demandas, estoque, etiquetas, itens,
               notas, painel, parceiros, pedidos, producao, relatorios)

# A ordem importa pouco, mas manter 'auth' primeiro deixa claro que as
# demais telas só existem para quem já entrou.
MODULOS = (auth, painel, itens, parceiros, estoque, pedidos, demandas,
           notas, producao, etiquetas, relatorios, configuracoes)


def criar_app() -> web.Aplicacao:
    app = web.Aplicacao()

    @app.carregador_usuario
    def carregar(usuario_id):
        with db.aberto() as con:
            return con.execute(
                "SELECT * FROM usuario WHERE id = ? AND ativo = 1",
                (usuario_id,)).fetchone()

    for modulo in MODULOS:
        modulo.registrar(app)

    return app
