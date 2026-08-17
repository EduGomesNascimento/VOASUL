/* =========================================================
   VOA-SUL — scripts do site
   Site estático: nenhuma requisição a servidor é feita aqui.
   ========================================================= */
(function () {
  "use strict";

  /* ----- menu mobile ----- */
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector("#nav-principal");

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });

    nav.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ----- ano no rodapé ----- */
  Array.prototype.forEach.call(document.querySelectorAll("[data-ano]"), function (el) {
    el.textContent = new Date().getFullYear();
  });

  /* ----- cabeçalho compacto ao rolar ----- */
  var header = document.querySelector(".site-header");
  if (header) {
    var marcarRolagem = function () {
      header.classList.toggle("is-scrolled", window.scrollY > 20);
    };
    marcarRolagem();
    window.addEventListener("scroll", marcarRolagem, { passive: true });
  }

  /* ----- entrada dos blocos conforme a página é rolada -----
     Os elementos recebem a classe aqui, e não no HTML, para que a
     página continue legível se este script não carregar. */
  var ALVOS = [
    ".section-head",
    ".pledge",
    ".card",
    ".steps li",
    ".band",
    ".table-wrap",
    ".faq",
    ".form-card",
    ".notice"
  ].join(", ");

  var blocos = document.querySelectorAll(ALVOS);

  if ("IntersectionObserver" in window && blocos.length) {
    var observador = new IntersectionObserver(
      function (entradas) {
        entradas.forEach(function (entrada) {
          if (!entrada.isIntersecting) return;
          entrada.target.classList.add("is-visible");
          observador.unobserve(entrada.target);
        });
      },
      /* threshold 0: basta o bloco encostar na área visível. Evita que
         um bloco muito alto nunca atinja a fração exigida e fique oculto. */
      { rootMargin: "0px 0px -10% 0px", threshold: 0 }
    );

    Array.prototype.forEach.call(blocos, function (el) {
      /* itens irmãos entram em cascata, um logo após o outro */
      var irmaos = Array.prototype.filter.call(el.parentNode.children, function (filho) {
        return filho.matches(ALVOS);
      });
      var posicao = irmaos.indexOf(el);
      if (posicao > 0) el.style.setProperty("--atraso", Math.min(posicao, 4) * 0.09 + "s");

      el.classList.add("revelar");
      observador.observe(el);
    });
  }

  /* ----- pré-seleção de produto vindo da URL (?produto=...) ----- */
  var params = new URLSearchParams(window.location.search);
  var produtoParam = params.get("produto");
  var selectProduto = document.querySelector("#produto");
  if (produtoParam && selectProduto) {
    Array.prototype.forEach.call(selectProduto.options, function (opt) {
      if (opt.value === produtoParam) selectProduto.value = produtoParam;
    });
  }

  /* ----- formulário de orçamento ----- */
  var form = document.querySelector("#form-orcamento");
  if (!form) return;

  var status = document.querySelector("#form-status");

  function campo(input) {
    return input.closest(".field");
  }

  function erro(input, mensagem) {
    var wrapper = campo(input);
    if (!wrapper) return;
    wrapper.classList.add("has-error");
    var alvo = wrapper.querySelector(".field-error");
    if (alvo && mensagem) alvo.textContent = mensagem;
  }

  function limpar(input) {
    var wrapper = campo(input);
    if (wrapper) wrapper.classList.remove("has-error");
  }

  form.addEventListener("input", function (e) {
    if (e.target.matches("input, select, textarea")) limpar(e.target);
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    var obrigatorios = form.querySelectorAll("[required]");
    var valido = true;
    var primeiroInvalido = null;

    Array.prototype.forEach.call(obrigatorios, function (input) {
      limpar(input);
      var valor = (input.value || "").trim();

      if (!valor) {
        erro(input, "Campo obrigatório.");
        valido = false;
      } else if (input.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(valor)) {
        erro(input, "Informe um e-mail válido.");
        valido = false;
      } else if (input.name === "telefone" && valor.replace(/\D/g, "").length < 10) {
        erro(input, "Informe DDD e número.");
        valido = false;
      }

      if (!valido && !primeiroInvalido && campo(input) && campo(input).classList.contains("has-error")) {
        primeiroInvalido = input;
      }
    });

    if (!valido) {
      if (primeiroInvalido) primeiroInvalido.focus();
      return;
    }

    /* Sem back-end nesta fase: o pedido é montado como texto e enviado
       pelo cliente de e-mail do visitante. Trocar por um endpoint quando
       o site tiver hospedagem com processamento. */
    var dados = new FormData(form);
    var linhas = [];
    var rotulos = {
      nome: "Nome",
      email: "E-mail",
      telefone: "Telefone / WhatsApp",
      cidade: "Cidade",
      produto: "Produto de interesse",
      prazo: "Prazo desejado",
      mensagem: "Detalhes do pedido"
    };

    Object.keys(rotulos).forEach(function (chave) {
      var valor = (dados.get(chave) || "").toString().trim();
      if (valor) linhas.push(rotulos[chave] + ": " + valor);
    });

    var corpo = "Pedido de orçamento enviado pelo site voasul.com.br\n\n" + linhas.join("\n");
    var assunto = "Orçamento VOA-SUL — " + ((dados.get("produto") || "pedido").toString());

    window.location.href =
      "mailto:sulvoa@gmail.com?subject=" +
      encodeURIComponent(assunto) +
      "&body=" +
      encodeURIComponent(corpo);

    if (status) {
      status.classList.add("is-visible");
      status.textContent =
        "Pedido montado. Seu programa de e-mail foi aberto com os dados preenchidos — " +
        "basta enviar. Se nada abrir, copie as informações e mande para sulvoa@gmail.com " +
        "ou chame no WhatsApp.";
      status.scrollIntoView({ block: "nearest" });
    }
  });
})();
