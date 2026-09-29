/* VOA-SUL ERP — comportamentos da interface. Sem bibliotecas externas. */
(function () {
  "use strict";

  /* ---- tela de carregamento: aparece uma vez por sessão do navegador ---- */
  var splash = document.getElementById("splash");
  if (splash) {
    var jaViu = false;
    try { jaViu = sessionStorage.getItem("voasul_splash") === "1"; } catch (e) { jaViu = false; }

    var fechar = function () {
      splash.classList.add("splash--sai");
      window.setTimeout(function () { splash.remove(); }, 520);
    };

    if (jaViu) {
      splash.remove();
    } else {
      try { sessionStorage.setItem("voasul_splash", "1"); } catch (e) { /* aba anônima */ }
      window.setTimeout(fechar, 1750);
    }
  }

  /* ---- confirmação antes de ações destrutivas ---- */
  document.addEventListener("submit", function (e) {
    var pergunta = e.target.getAttribute("data-confirmar");
    if (pergunta && !window.confirm(pergunta)) e.preventDefault();
  });

  /* ---- linhas de itens de pedido/nota: somar e acrescentar linhas ---- */
  var grade = document.getElementById("linhas-itens");
  if (grade) {
    var precos = {};
    try { precos = JSON.parse(grade.getAttribute("data-precos") || "{}"); } catch (e) { precos = {}; }

    var paraNumero = function (texto) {
      var t = String(texto || "").replace(/\s|R\$/g, "");
      if (t.indexOf(",") >= 0) t = t.replace(/\./g, "").replace(",", ".");
      var n = parseFloat(t);
      return isNaN(n) ? 0 : n;
    };
    var emReais = function (n) {
      return "R$ " + n.toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    };

    var somar = function () {
      var total = 0;
      grade.querySelectorAll("tbody tr").forEach(function (linha) {
        var item = linha.querySelector("[name=item_id]");
        var qtd = paraNumero(linha.querySelector("[name=quantidade]").value);
        var unit = paraNumero(linha.querySelector("[name=preco_unit]").value);
        var desc = paraNumero(linha.querySelector("[name=desconto]").value);
        var sub = item && item.value ? Math.max(qtd * unit - desc, 0) : 0;
        linha.querySelector(".subtotal").textContent = emReais(sub);
        linha.classList.toggle("linha-sai", !(item && item.value));
        total += sub;
      });
      var frete = paraNumero((document.querySelector("[name=frete]") || {}).value);
      var abat = paraNumero((document.querySelector("[name=desconto_geral]") || {}).value);
      var geral = document.getElementById("total-geral");
      if (geral) geral.textContent = emReais(Math.max(total + frete - abat, 0));
    };

    grade.addEventListener("input", somar);
    grade.addEventListener("change", function (e) {
      /* ao escolher o item, sugere o preço cadastrado se o campo estiver zerado */
      if (e.target.name === "item_id") {
        var campo = e.target.closest("tr").querySelector("[name=preco_unit]");
        if (campo && paraNumero(campo.value) === 0 && precos[e.target.value]) {
          campo.value = String(precos[e.target.value]).replace(".", ",");
        }
      }
      somar();
    });
    document.addEventListener("input", function (e) {
      if (e.target.name === "frete" || e.target.name === "desconto_geral") somar();
    });

    var maisLinhas = document.getElementById("mais-linhas");
    if (maisLinhas) {
      maisLinhas.addEventListener("click", function () {
        var corpo = grade.querySelector("tbody");
        var modelo = corpo.querySelector("tr");
        for (var i = 0; i < 3; i++) {
          var nova = modelo.cloneNode(true);
          nova.querySelectorAll("input").forEach(function (c) { c.value = ""; });
          nova.querySelectorAll("select").forEach(function (c) { c.selectedIndex = 0; });
          nova.querySelector(".subtotal").textContent = "R$ 0,00";
          corpo.appendChild(nova);
        }
        somar();
      });
    }
    somar();
  }

  /* ---- abre a janela de impressão nas folhas de etiqueta e documentos ---- */
  if (new URLSearchParams(window.location.search).get("imprimir") === "1") {
    window.setTimeout(function () { window.print(); }, 600);
  }
})();
