# Site VOA-SUL

Site institucional e catálogo da **VOA-SUL**, fábrica de drones FPV e recreativos
sediada em Portão (RS).

O conteúdo foi escrito a partir do *Plano Mercadológico* e do *Plano de Marketing*
da empresa: posicionamento por qualidade (e não por preço), fabricação nacional,
controladora de voo própria, homologação ANATEL e assistência técnica local.

> **Versão preliminar.** Textos, configurações de produto, preços e dados de
> contato são genéricos e servem de estrutura. Devem ser substituídos pelos dados
> reais antes da publicação.

## Estrutura

```
index.html          Página inicial: posicionamento, diferenciais, linhas e fluxo de compra
produtos.html       Catálogo das quatro linhas (FPV 5", recreativo 250 g, peças, reparo)
homologacao.html    ANATEL x ANAC, riscos do importado sem homologação, FAQ
sobre.html          A empresa, o mercado, forma de trabalho e a marca
orcamento.html      Formulário de pedido de orçamento
contato.html        Canais de atendimento
assets/
  css/style.css     Folha de estilo única (paleta da marca em variáveis CSS)
  js/main.js        Menu mobile, validação do formulário, pré-seleção de produto
  img/              Logomarca, símbolo e favicon em SVG
```

## Como rodar localmente

Não há etapa de build nem dependências. Basta abrir `index.html` no navegador,
ou servir a pasta:

```bash
python3 -m http.server 8000
# depois acesse http://localhost:8000
```

## Publicação

O site é estático e pode ser publicado no GitHub Pages direto da branch
`main` (Settings → Pages → Deploy from a branch → `main` / `/root`), ou em
qualquer hospedagem comum, apontando o domínio `voasul.com.br` para ela.

## Pontos a completar

- [ ] Fotos reais dos drones (hoje os cartões usam um marcador com o símbolo da marca)
- [ ] Especificação técnica final e preços de cada modelo
- [ ] Endereço completo, telefone/WhatsApp e horário de atendimento
- [ ] Envio do formulário de orçamento por back-end ou serviço de formulários
      (hoje o pedido é montado e aberto no cliente de e-mail do visitante)
- [ ] Fontes das estatísticas de mercado citadas em `sobre.html`

## Convenções

- HTML estático, sem framework. Cabeçalho e rodapé são repetidos em cada página.
- Toda a paleta está em variáveis CSS no topo de `assets/css/style.css`
  (`--navy`, `--sky` etc.). Mudar a cor da marca é mudar ali.
- Textos em português do Brasil.
