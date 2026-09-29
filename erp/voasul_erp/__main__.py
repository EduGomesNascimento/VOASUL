"""Ponto de entrada: sobe o servidor local e abre o navegador.

    python -m voasul_erp              inicia o sistema
    python -m voasul_erp --porta 9000 usa outra porta
    python -m voasul_erp --sem-navegador
"""

import argparse
import socket
import sys
import threading
import webbrowser
from wsgiref.simple_server import WSGIRequestHandler, make_server

from . import __version__, config, db
from .views import criar_app

FAIXA = "═" * 58


class Silencioso(WSGIRequestHandler):
    """Reduz o ruído no console: só mostra erro, não cada requisição."""

    def log_request(self, *args, **kwargs):
        pass

    def log_message(self, formato, *args):
        sys.stderr.write("  [servidor] " + (formato % args) + "\n")


def porta_livre(host: str, desejada: int, tentativas: int = 20) -> int:
    """Se a porta estiver ocupada, tenta as seguintes."""
    for deslocamento in range(tentativas):
        alvo = desejada + deslocamento
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, alvo))
                return alvo
            except OSError:
                continue
    raise SystemExit(
        f"Nenhuma porta livre entre {desejada} e {desejada + tentativas - 1}.")


def abertura(endereco: str) -> None:
    print(FAIXA)
    print("   VOA-SUL ERP  ·  controle de estoque e demandas")
    print(f"   versão {__version__}")
    print(FAIXA)
    print(f"   Sistema no ar:   {endereco}")
    print(f"   Banco de dados:  {config.BANCO}")
    print()
    print("   Primeiro acesso: usuário 'admin', senha 'voasul'")
    print("   (troque a senha em Configurações)")
    print()
    print("   Para encerrar, feche esta janela ou pressione Ctrl+C.")
    print(FAIXA)
    print()


def main(argv=None) -> int:
    analisador = argparse.ArgumentParser(
        prog="voasul_erp", description="VOA-SUL ERP — servidor local")
    analisador.add_argument("--porta", type=int, default=config.PORTA)
    analisador.add_argument("--host", default=config.HOST)
    analisador.add_argument("--sem-navegador", action="store_true",
                            help="não abre o navegador automaticamente")
    args = analisador.parse_args(argv)

    db.iniciar()
    config.chave_sessao()

    porta = porta_livre(args.host, args.porta)
    endereco = f"http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{porta}/"

    servidor = make_server(args.host, porta, criar_app(), handler_class=Silencioso)
    abertura(endereco)

    if not args.sem_navegador:
        threading.Timer(0.8, lambda: webbrowser.open(endereco)).start()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n   Sistema encerrado. Os dados ficam salvos em:")
        print(f"   {config.BANCO}\n")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
