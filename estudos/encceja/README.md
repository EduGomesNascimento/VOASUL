# Encceja em 6 horas

App de estudo em arquivo único para o **Encceja 2026 — Ensino Médio** (aplicação
em 23 de agosto). Foi montado para um cenário específico: **6 horas de estudo,
distribuídas em 2 dias**, com prioridade em Matemática e Redação.

Não tem relação com o site institucional da VOA-SUL — vive aqui apenas para
ficar versionado junto.

## O que tem dentro

| Aba | Conteúdo |
| --- | --- |
| Painel | Regra de aprovação (100/180 por área + nota 5 na redação), onde o tempo rende mais, cronômetro e placar de progresso |
| Plano 6h | 12 blocos cronometrados divididos em Dia 1 e Dia 2, com checkbox |
| Matemática | 9 blocos com exemplos resolvidos (porcentagem, frações, regra de três, média, unidades, geometria, velocidade/densidade/vazão, função/juros, probabilidade) e um treino relâmpago de 24 contas curtas com conferência imediata |
| Redação | As 5 competências e a régua 0/1/2 de cada uma, o que zera, modelo dos 4 parágrafos, uma redação nota 10 anotada, conectivos, repertórios coringa, erros de português mais frequentes e o **corretor** |
| Revisão | Técnica de interpretação + varredura de Linguagens, Humanas e Natureza |
| Simulado | 48 questões no estilo da prova — 30 de Matemática, o tamanho de uma prova inteira, e 6 de cada outra área — com correção imediata e explicação |
| Dia da prova | Horários, o que levar, gestão de tempo em sala, véspera |

## O corretor de redação

Analisador determinístico, sem rede e sem IA: roda inteiro no navegador. Devolve
nota de 0 a 2 em cada uma das cinco competências do Encceja, a nota final de 0 a
10, e uma lista de apontamentos com o trecho exato marcado no texto.

O que ele checa:

- **Competência 1** — marcas de oralidade, primeira pessoa, frases longas demais,
  um dicionário de palavras que não existem sem acento e uma lista de desvios
  frequentes (`menas`, `houveram`, `fazem dez anos`, `há … atrás`, `para mim fazer`,
  `a nível de`, palavra repetida em sequência).
- **Competência 2** — cobertura das palavras do tema no texto, número de
  parágrafos, tamanho estimado em linhas e marcas de outro gênero (narrativa, carta).
- **Competência 3** — corpo dos parágrafos de desenvolvimento, presença de
  repertório (lei, instituição, autor, dado) e de relação causa/consequência.
- **Competência 4** — conectivo abrindo cada parágrafo, variedade entre eles e
  densidade de conectivos no corpo do texto.
- **Competência 5** — os quatro elementos da proposta de intervenção no último
  parágrafo: agente, ação, meio e finalidade.

O que ele **não** faz: julgar se o argumento é bom, se o dado citado é verdadeiro
ou se o texto tem estilo. A nota é uma estimativa para orientar a revisão, não a
nota do Inep. Para uma leitura de conteúdo há o botão *Copiar para correção
detalhada*, que monta um pedido pronto com tema e texto.

## Como rodar

Sem build e sem dependência. É um único `index.html`:

```bash
python3 -m http.server 8000    # depois acesse http://localhost:8000/estudos/encceja/
```

Ou abre o arquivo direto no navegador.

## Notas técnicas

- Todo o progresso (blocos, minutos, respostas, treino, redação, checklist,
  tema) fica em `localStorage`, na chave `encceja6h.v1`. Nada sai do navegador.
- O arquivo declara `<meta charset="utf-8">` na primeira linha e nenhuma
  expressão regular contém caractere fora do ASCII — acentos e marcas de
  combinação entram como `\uXXXX`. Sem isso, um servidor que não anuncie o
  charset faz o navegador decodificar errado e uma única regex inválida derruba
  o script inteiro.
- Segue o padrão do resto do repositório: HTML estático, sem framework, paleta
  em variáveis CSS no topo do arquivo.
- Tema claro e escuro seguem o sistema, com botão de override na faixa do topo.
- As fontes vêm do Google Fonts carregadas sem bloquear a renderização
  (`media="print"` trocado por `all` no `onload`); offline, os fallbacks do
  sistema assumem na hora e o app continua utilizável.
