# Prompt para o Claude no navegador (Claude in Chrome): montar o carrinho da JLCPCB

**Antes de colar o prompt:**

1. Baixe o arquivo **`drone_VoaSul_JLCPCB.zip`** para a pasta Downloads. Ele está no chat ou no
   GitHub, em `drone/kicad/pro/` do branch `claude/loving-rubin-q4d17q` (botão "Download raw").
2. Só se for usar a versão B, baixe também **`BOM_JLCPCB.csv`** e **`CPL_JLCPCB.csv`**
   (`drone/kicad/pro/montagem_jlc/`).
3. Entre em **jlcpcb.com** e faça login, com o endereço de entrega já cadastrado.
4. Cole **uma** das versões abaixo (A ou B) no Claude do navegador.

---

## Versão A: só a placa (recomendada)

```text
Monte um pedido de placa de circuito na JLCPCB (jlcpcb.com) e SALVE NO CARRINHO.
NÃO pague e NÃO finalize o pedido: pare no carrinho e me mostre o resultado.

REGRAS
- Eu já estou logado. Não mude nada da conta, do endereço ou da forma de pagamento.
- Se aparecer captcha, login, verificação por e-mail ou tela de pagamento: pare e me chame.
- Feche pop-ups de propaganda e cupom. Não aceite nenhum extra pago que eu não pedi (stencil,
  montagem, "upgrade", cor diferente, acabamento melhor).
- Se não conseguir anexar o arquivo sozinho, clique no botão de upload e me peça para escolher o
  arquivo "drone_VoaSul_JLCPCB.zip" na pasta Downloads.

PASSO 1: SUBIR O GERBER
- Na página inicial, clique em "Order now" / "Add gerber file" e envie drone_VoaSul_JLCPCB.zip.
- Espere a análise terminar e confira o que o site detectou:
  * Layers: 2
  * Dimensions: cerca de 97,1 x 97,1 mm (placa redonda)
  Se detectar outra coisa (1 camada, outro tamanho, erro de arquivo), PARE e me mostre.
- Abra a pré-visualização do Gerber (Gerber Viewer) e confira: disco redondo; face de cima com
  um plano de cobre e o texto "VoaSul Drones rev C 2026"; face de baixo com trilhas grossas.
  Me diga se viu isso.

PASSO 2: CONFIGURAR (deixe exatamente assim; o que não estiver na lista fica no padrão)
- Base Material: FR-4
- Layers: 2
- Dimensions: o que o site detectou (não mexa)
- PCB Qty: 5
- Product Type: Industrial/Consumer electronics
- Different Design: 1
- Delivery Format: Single PCB
- PCB Thickness: 1.6
- PCB Color: Green
- Silkscreen: White
- Material Type: FR4-Standard TG 135-140 (padrão)
- Surface Finish: HASL(with lead)
- Outer Copper Weight: 1 oz
- Via Covering: Tented
- Min via hole size/diameter: o padrão (0,3 mm / 0,4-0,45 mm)
- Board Outline Tolerance: ±0.2mm (Regular)
- Confirm Production file: No
- Mark on PCB / Remove Mark: o padrão (sem pagar a mais)
- Electrical Test: Flying Probe Fully Test (padrão)
- Gold Fingers: No | Castellated Holes: No | Edge Plating: No | Press-Fit Hole: No
- Na seção "High-spec Options" ou "Advanced Options": tudo no padrão
- PCB Assembly: DESLIGADO
- SMT-Stencil: NÃO

PASSO 3: FRETE (só consultar)
- Na estimativa de frete do lado direito ("Shipping Estimate" / "Charge Details"), escolha o país
  Brazil (CEP de Novo Hamburgo, RS, se pedir) e anote TODAS as opções que aparecerem: nome,
  preço, prazo e se o imposto já vem incluído (DDP / "tax included") ou não.
- Anote também o tempo de produção ("Build Time") e se a opção de 24 horas sai sem custo.

PASSO 4: SALVAR
- Clique em "SAVE TO CART" (salvar no carrinho). NÃO clique em "Checkout" nem em pagar.
- Abra o carrinho e confirme que o item está lá, com a quantidade 5.

QUANDO TERMINAR, me mande:
1. A configuração final, campo por campo, apontando qualquer campo que ficou diferente da lista
   e o motivo.
2. O preço das placas e o tempo de produção.
3. Tabela das opções de frete para o Brasil: nome, preço, prazo e se o imposto já vem pago.
4. O total estimado com a opção mais barata e com a mais rápida.
5. Qualquer aviso que o site mostrou (DFM, arquivo, tamanho, etc.).
```

---

## Versão B: placa + soldagem das peças SMD pela JLCPCB (opcional)

Com essa versão, a placa chega com os 4 MOSFETs (SOT-23), os 4 diodos (SMA) e os 4 capacitores 0805
da face de baixo já soldados. São peças do tipo **Basic** da JLCPCB, sem taxa de peça extra, mas a
montagem tem uma taxa fixa e deixa o pedido alguns dias mais lento. O resto (resistores, conectores,
módulos) você solda à mão de qualquer jeito.

```text
Faça TUDO da "Versão A" (mesmas regras, mesmo PASSO 1 e PASSO 2), com UMA diferença no PASSO 2:
ligue "PCB Assembly" e configure a montagem assim, sem pagar e sem finalizar:

MONTAGEM (PCB Assembly)
- PCBA Type: Economic
- Assembly Side: Bottom Side (as peças SMD ficam na face de BAIXO)
- PCBA Qty: 2 (as outras 3 placas vêm sem montagem)
- Tooling holes: Added by JLCPCB
- Confirm Parts Placement: Yes
- O resto no padrão.
- Clique em NEXT. Quando pedir os arquivos, envie BOM_JLCPCB.csv (como BOM) e CPL_JLCPCB.csv
  (como CPL/Pick and Place), os dois na pasta Downloads. Se não conseguir anexar, me peça para
  escolher.
- Na tela da BOM, confira que as 3 linhas foram reconhecidas e marcadas para montar:
  * C49678 (capacitor 100 nF 0805): C3, C4, C5, C6
  * C8678 (diodo SS34, SMA): D1, D2, D3, D4
  * C20917 (MOSFET AO3400A, SOT-23): Q1, Q2, Q3, Q4
  Se alguma peça estiver sem estoque ou como "Extended" (taxa extra), PARE e me mostre.
- Na tela de posicionamento (placement), tire um print e me mostre ANTES de seguir. Confira se cada
  peça está em cima das ilhas dela. Se alguma estiver girada ou deslocada, me diga qual.
- Siga até o botão "SAVE TO CART". NÃO pague.

No relatório final, inclua também: a taxa de montagem, o custo das peças e o prazo total.
```
