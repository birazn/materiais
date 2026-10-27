(function () {
  "use strict";

  var lista = document.getElementById("lista");
  var contador = document.getElementById("contador");
  var busca = document.getElementById("busca");
  var cards = Array.from(lista.getElementsByClassName("card"));
  var catAtiva = "Todos";
  var temaAtivo = "Todos";
  var termo = "";

  document.getElementById("ano").textContent = new Date().getFullYear();

  function norm(v) {
    return String(v == null ? "" : v).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function renderFiltros() {
    var botoes = document.querySelectorAll("#filtros-cat button, #filtros-tema button");
    botoes.forEach(function (b) {
      var ativo =
        (b.getAttribute("data-cat") === catAtiva) ||
        (b.getAttribute("data-tema") === temaAtivo);
      b.setAttribute("aria-pressed", ativo);
      b.classList.toggle("ativo", ativo);
    });
  }

  function visivel(card) {
    if (catAtiva !== "Todos") {
      var catEl = card.querySelector('[data-cat]');
      if (!catEl || catEl.getAttribute("data-cat") !== catAtiva) return false;
    }
    if (temaAtivo !== "Todos") {
      if (!card.querySelector('[data-tema="' + temaAtivo + '"]')) return false;
    }
    if (termo) {
      var texto = norm(card.textContent);
      if (texto.indexOf(norm(termo)) === -1) return false;
    }
    return true;
  }

  function render() {
    var vis = cards.filter(visivel);
    contador.textContent = vis.length + (vis.length === 1 ? " material" : " materiais");
    lista.innerHTML = "";
    vis.forEach(function (c) { lista.appendChild(c); });
    if (vis.length === 0) {
      lista.innerHTML = '<li class="vazio">Nenhum material encontrado. Tente outra busca ou categoria.</li>';
    }
  }

  document.getElementById("filtros-cat").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-cat]");
    if (!b) return;
    catAtiva = b.getAttribute("data-cat");
    renderFiltros();
    render();
  });

  document.getElementById("filtros-tema").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-tema]");
    if (!b) return;
    temaAtivo = b.getAttribute("data-tema");
    renderFiltros();
    render();
  });

  busca.addEventListener("input", function () {
    termo = busca.value;
    render();
  });

  renderFiltros();
  render();
})();
