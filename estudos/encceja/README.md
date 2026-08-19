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
| Matemática | 7 blocos com exemplos resolvidos: porcentagem, regra de três, média, unidades, geometria, função/juros, probabilidade |
| Redação | As 5 competências, o que zera, modelo dos 4 parágrafos, conectivos, repertórios coringa, treino com contador de linhas e autoavaliação |
| Revisão | Técnica de interpretação + varredura de Linguagens, Humanas e Natureza |
| Simulado | 34 questões no estilo da prova, com correção imediata e explicação |
| Dia da prova | Horários, o que levar, gestão de tempo em sala, véspera |

## Como rodar

Sem build e sem dependência. É um único `index.html`:

```bash
python3 -m http.server 8000    # depois acesse http://localhost:8000/estudos/encceja/
```

Ou abre o arquivo direto no navegador.

## Notas técnicas

- Todo o progresso (blocos, minutos, respostas, redação, checklist, tema) fica
  em `localStorage`, na chave `encceja6h.v1`. Nada sai do navegador.
- Segue o padrão do resto do repositório: HTML estático, sem framework, paleta
  em variáveis CSS no topo do arquivo.
- Tema claro e escuro seguem o sistema, com botão de override na faixa do topo.
- As fontes vêm do Google Fonts; sem rede, os fallbacks do sistema assumem e o
  layout continua íntegro.
