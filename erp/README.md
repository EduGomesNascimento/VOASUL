# VOA-SUL ERP

Sistema de controle de estoque e demandas da VOA-SUL: pedidos, itens e
materiais, movimentação de estoque, demandas de produção e compra, notas
fiscais, números de série, etiquetas com código de barras e relatórios.

Roda como **servidor local** no próprio computador — abre no navegador,
mas não depende de internet.

---

## Instalação no Windows

1. Instale o **Python 3.9 ou superior** de <https://www.python.org/downloads/>.
   Na primeira tela do instalador, marque **"Add Python to PATH"**.
2. Copie a pasta `erp` inteira para o computador.
3. Dê dois cliques em **`instalar.bat`**.
4. Use o atalho **VOA-SUL ERP** criado na área de trabalho, ou o
   arquivo `iniciar.bat`.

O navegador abre sozinho em `http://localhost:8770/`.

**Primeiro acesso:** usuário `admin`, senha `voasul`.
Troque a senha em *Configurações* logo no primeiro uso.

### Em Linux ou Mac

```bash
cd erp
python3 -m voasul_erp
```

---

## Sem dependências externas

O sistema usa **apenas a biblioteca padrão do Python** — `sqlite3`,
`wsgiref`, `hashlib`, `csv`. Não há `pip install`, não há `requirements.txt`
e não é preciso internet para instalar. É o que permite replicar a
instalação em qualquer PC copiando a pasta.

---

## Usar em mais de um computador

Cada PC instalado guarda seus dados em `erp/dados/voasul.db`.

Para **dois ou mais PCs usarem o mesmo banco**, coloque o banco numa pasta
de rede e aponte a variável `VOASUL_DADOS` para ela. Edite `iniciar.bat` e
tire o `REM` da linha:

```bat
set VOASUL_DADOS=\\SERVIDOR\voasul\dados
```

O SQLite trabalha em modo WAL, o que permite vários leitores e um escritor
ao mesmo tempo. Para uso simultâneo pesado (muitos lançamentos por minuto
em várias máquinas), o caminho é hospedar o sistema num único servidor e
acessar pelo navegador dos demais PCs — ver abaixo.

### Um PC servindo os outros

No PC que vai guardar os dados:

```bat
set VOASUL_HOST=0.0.0.0
iniciar.bat
```

Nos demais, abra no navegador `http://IP-DO-SERVIDOR:8770/`. Libere a porta
no firewall do Windows. Use isso apenas na rede interna: não há HTTPS.

---

## Variáveis de configuração

| Variável | Para que serve | Padrão |
|---|---|---|
| `VOASUL_DADOS` | Pasta do banco e dos backups | `erp/dados` |
| `VOASUL_DB` | Caminho exato do arquivo do banco | `<dados>/voasul.db` |
| `VOASUL_HOST` | Endereço de escuta | `127.0.0.1` |
| `VOASUL_PORTA` | Porta (se ocupada, usa a seguinte) | `8770` |
| `VOASUL_PREFIXO` | Prefixo de URL ao hospedar sob um caminho | vazio |

---

## Módulos

| Módulo | O que faz |
|---|---|
| **Painel** | Indicadores do dia: pedidos abertos, demandas pendentes, itens abaixo do mínimo, valor em estoque |
| **Pedidos** | Venda e compra, com situação (orçamento → confirmado → produção → pronto → entregue) e **baixa automática de estoque** |
| **Demandas** | Necessidades de produção e compra; geram-se à mão, a partir de um pedido sem saldo, ou automaticamente pelo estoque mínimo |
| **Estoque** | Posição atual, entradas, saídas e ajustes, custo médio e histórico |
| **Itens** | Matérias-primas, componentes, produtos acabados e serviços |
| **Clientes e fornecedores** | Cadastro único, com validação de CPF e CNPJ |
| **Notas fiscais** | Numeração, itens, CFOP, NCM e impressão |
| **Produção** | Número de série e ficha de inspeção por unidade montada |
| **Etiquetas** | Folha A4 com código de barras Code 39, para itens e números de série |
| **Relatórios** | Posição de estoque, itens abaixo do mínimo, movimentações, vendas, curva ABC e posição de demandas — com exportação em CSV |

### Como o estoque é movimentado

Um pedido baixa o estoque quando entra em **Confirmado**, **Em produção**,
**Pronto** ou **Entregue**. Venda dá saída; compra dá entrada. Serviços não
movimentam nada.

Voltar o pedido para *Orçamento* ou *Cancelado* **estorna** a baixa com
movimentos contrários, preservando o histórico. A coluna `baixado` garante
que confirmar duas vezes não duplique a saída. Editar um pedido já baixado
estorna antes de regravar as linhas.

Uma saída maior que o saldo disponível é recusada — para corrigir
divergência de inventário, use um lançamento do tipo **Ajuste**, que aceita
quantidade negativa.

---

## Sobre as notas fiscais

O módulo numera, guarda e imprime as notas para **conferência e arquivo
interno**. Ele **não transmite à SEFAZ** e **não gera DANFE com validade
jurídica** — isso exige certificado digital A1/A3 e integração com o
emissor oficial. O documento impresso traz esse aviso no rodapé.

---

## Backup

Em *Configurações → Banco de dados*, o botão **Gerar cópia de segurança**
grava um `.db` datado em `dados/backups/`. A cópia usa a API de backup do
SQLite, então funciona com o sistema em uso.

Para backup manual, basta copiar a pasta `dados` inteira com o sistema
fechado.

---

## Hospedar num domínio

A aplicação é **WSGI** (`voasul_erp.views.criar_app()`), então roda em
gunicorn, uWSGI ou mod_wsgi sem alteração de código:

```python
# wsgi.py
from voasul_erp import db
from voasul_erp.views import criar_app

db.iniciar()
application = criar_app()
```

```bash
gunicorn -w 2 -b 127.0.0.1:8770 wsgi:application
```

Para servir sob um caminho — por exemplo `exemplo.com.br/voa-sul/db` —
defina `VOASUL_PREFIXO=/voa-sul/db`; todos os links internos passam a
respeitar o prefixo.

Antes de expor na internet, três coisas são obrigatórias: **HTTPS** na
frente (nginx ou Apache), **trocar a senha do admin** e restringir o acesso.
As sessões ficam em memória, então reiniciar o servidor desconecta todo
mundo.

---

## Estrutura do código

```
erp/
  instalar.bat            Instalador para Windows
  iniciar.bat             Atalho de execução
  voasul_erp/
    __main__.py           Sobe o servidor e abre o navegador
    config.py             Caminhos, porta e dados da empresa
    db.py                 Esquema SQLite, senhas e carga inicial
    web.py                Camada WSGI: rotas, sessões, respostas
    ui.py                 Layout, menu e componentes de tela
    consultas.py          Saldos, totais, numeração e baixa de estoque
    util.py               Formatação brasileira, datas, CPF/CNPJ
    barcode.py            Code 39 em SVG
    views/                Uma tela por módulo
    static/               CSS, JS e a logomarca
  dados/                  Banco e backups (criada na instalação)
```

O código e a interface estão em português. A paleta vem da marca
(`#0A2050` azul-marinho e `#29ABE2` azul-claro) e está em variáveis CSS no
topo de `static/app.css`.
