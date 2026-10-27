(function () {
  "use strict";

  var lista = document.getElementById("lista");
  var filtros = document.getElementById("filtros");
  var busca = document.getElementById("busca");
  var contador = document.getElementById("contador");
  var itens = [];
  var categoria = "Todos";
  var termo = "";

  document.getElementById("ano").textContent = new Date().getFullYear();

  function esc(valor) {
    return String(valor == null ? "" : valor).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function norm(valor) {
    return String(valor == null ? "" : valor).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function renderFiltros() {
    var cats = ["Todos"];
    itens.forEach(function (i) {
      if (i.categoria && cats.indexOf(i.categoria) === -1) cats.push(i.categoria);
    });
    filtros.innerHTML = cats.map(function (c) {
      return '<button type="button" data-cat="' + esc(c) + '" aria-pressed="' + (c === categoria) + '">' + esc(c) + "</button>";
    }).join("");
  }

  function cardHtml(item, idx) {
    var meta = ["PDF"];
    if (item.tamanho) meta.push(esc(item.tamanho));
    if (item.paginas) meta.push(esc(item.paginas) + " págs.");
    var arquivo = esc(item.arquivo);
    return (
      '<li class="card" style="--i:' + Math.min(idx, 12) + '">' +
        '<div class="card__topo">' +
          (item.categoria ? '<span class="tag">' + esc(item.categoria) + "</span>" : "<span></span>") +
          (item.ano ? '<span class="ano">' + esc(item.ano) + "</span>" : "") +
        "</div>" +
        '<h2 class="card__titulo">' + esc(item.titulo) + "</h2>" +
        (item.evento ? '<p class="card__evento">' + esc(item.evento) + "</p>" : "") +
        (item.descricao ? '<p class="card__desc">' + esc(item.descricao) + "</p>" : '<p class="card__desc"></p>') +
        '<div class="card__rodape">' +
          '<span class="meta">' + meta.join(" · ") + "</span>" +
          '<div class="acoes">' +
            '<a class="btn btn--sec" href="' + arquivo + '" target="_blank" rel="noopener">Abrir</a>' +
            '<a class="btn" href="' + arquivo + '" download>Baixar</a>' +
          "</div>" +
        "</div>" +
      "</li>"
    );
  }

  function render() {
    var t = norm(termo);
    var visiveis = itens.filter(function (i) {
      if (categoria !== "Todos" && i.categoria !== categoria) return false;
      if (!t) return true;
      var alvo = norm([i.titulo, i.descricao, i.evento, i.categoria, (i.tags || []).join(" ")].join(" "));
      return alvo.indexOf(t) !== -1;
    });

    contador.textContent = visiveis.length + (visiveis.length === 1 ? " material" : " materiais");
    lista.innerHTML = visiveis.length
      ? visiveis.map(cardHtml).join("")
      : '<li class="vazio">Nenhum material encontrado. Tente outra busca ou categoria.</li>';
  }

  filtros.addEventListener("click", function (e) {
    var botao = e.target.closest("button[data-cat]");
    if (!botao) return;
    categoria = botao.getAttribute("data-cat");
    renderFiltros();
    render();
  });
  busca.addEventListener("input", function () {
    termo = busca.value;
    render();
  });

  fetch("materiais.json", { cache: "no-cache" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (dados) {
      itens = dados.slice().sort(function (a, b) {
        return (b.ano || 0) - (a.ano || 0) || String(a.titulo).localeCompare(String(b.titulo), "pt-BR");
      });
      renderFiltros();
      render();
    })
    .catch(function () {
      contador.textContent = "";
      lista.innerHTML = '<li class="vazio">Não foi possível carregar a lista agora. Tente novamente em instantes.</li>';
    });
})();
