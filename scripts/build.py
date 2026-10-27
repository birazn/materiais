#!/usr/bin/env python3
"""Build do site de materiais.

Gera a partir de data/*.yml:
  - index.html com cards ja renderizados (funciona sem JS)
  - materiais.json (contrato publico estavel)
  - m/<slug>/index.html (pagina propria de cada palestra)
  - capas/*.webp (capa da primeira pagina de cada PDF)
  - qr/<slug>.png (QR code da pagina da palestra)
  - sitemap.xml, robots.txt, feed.xml

Executa localmente ou via GitHub Actions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constantes e caminhos
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PDFS_DIR = ROOT / "pdfs"
MDS_DIR = ROOT / "mds"
IMGS_DIR = ROOT / "imgs"
ASSETS_DIR = ROOT / "assets"
SCRIPTS_DIR = ROOT / "scripts"

# Saida (versao gerada - pode ser commitada ou publicada direto)
OUT_DIR = ROOT / "_site"          # saida local de teste
PUBLISH_DIR = ROOT                # no GitHub Pages, gera direto na raiz

CAPAS_DIR = PUBLISH_DIR / "capas"
QR_DIR = PUBLISH_DIR / "qr"
M_DIR = PUBLISH_DIR / "m"

SITEMAP_PATH = PUBLISH_DIR / "sitemap.xml"
ROBOTS_PATH = PUBLISH_DIR / "robots.txt"
FEED_PATH = PUBLISH_DIR / "feed.json"
MATERIAIS_JSON_PATH = PUBLISH_DIR / "materiais.json"
INDEX_PATH = PUBLISH_DIR / "index.html"

BASE_URL = "https://birazn.github.io/materiais"

LIMITE_TAMANHO_AVISO_MB = 5
LIMITE_TAMANHO_FALHA_MB = 50  # GitHub bloqueia acima de 100 MB

# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------

def slugify(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return re.sub(r"-+", "-", texto).strip("-")


def agora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ler_arquivo(caminho: Path) -> str:
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def escrever_arquivo(caminho: Path, conteudo: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)


def esc_html(valor: str) -> str:
    return (
        str(valor)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def esc_json(valor: str) -> str:
    return json.dumps(valor, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Leitura de PDF (tamanho e paginas)
# ---------------------------------------------------------------------------

def info_pdf(caminho: Path) -> dict:
    """Retorna {tamanho_bytes, paginas} do PDF. Tenta PyPDF2 primeiro."""
    tamanho_bytes = caminho.stat().st_size if caminho.exists() else 0
    paginas = None

    try:
        import PyPDF2  # type: ignore

        with open(caminho, "rb") as f:
            leitor = PyPDF2.PdfReader(f)
            paginas = len(leitor.pages)
    except Exception:
        try:
            resultado = subprocess.run(
                ["pdfinfo", str(caminho)],
                capture_output=True,
                text=True,
                check=True,
            )
            for linha in resultado.stdout.splitlines():
                if linha.lower().startswith("pages:"):
                    paginas = int(linha.split(":")[1].strip())
                    break
        except Exception:
            paginas = None

    return {"tamanho_bytes": tamanho_bytes, "paginas": paginas}


def tamanho_legível(bytes_valor: int) -> str:
    if bytes_valor < 1024:
        return f"{bytes_valor} B"
    if bytes_valor < 1024 * 1024:
        return f"{bytes_valor / 1024:.1f} KB"
    return f"{bytes_valor / (1024 * 1024):.1f} MB"


# ---------------------------------------------------------------------------
# Capa do PDF (primeira pagina -> WebP ~480 px)
# ---------------------------------------------------------------------------

def gerar_capa(pdf_path: Path, saida_webp: Path) -> bool:
    """Gera capa WebP da primeira pagina do PDF. Retorna True se sucesso."""
    saida_webp.parent.mkdir(parents=True, exist_ok=True)
    png_temp = saida_webp.with_suffix(".png")

    try:
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-f",
                "1",
                "-l",
                "1",
                "-r",
                "60",
                str(pdf_path),
                str(png_temp.with_suffix("")),
            ],
            capture_output=True,
            check=True,
        )
    except Exception:
        return gerar_capa_placeholder(saida_webp)

    # Encontra o PNG gerado (pdftoppm acrescenta -1.png)
    png_gerado = None
    for candidato in png_temp.parent.glob(png_temp.stem + "*.png"):
        png_gerado = candidato
        break

    if not png_gerado or not png_gerado.exists():
        return gerar_capa_placeholder(saida_webp)

    try:
        from PIL import Image  # type: ignore

        with Image.open(png_gerado) as img:
            img = img.convert("RGB")
            largura = 480
            altura = int(img.height * (largura / img.width))
            img = img.resize((largura, altura))
            img.save(saida_webp, "WEBP", quality=80)
        png_gerado.unlink(missing_ok=True)
        return True
    except Exception:
        return gerar_capa_placeholder(saida_webp)


def gerar_capa_placeholder(saida_webp: Path) -> bool:
    """Gera uma capa placeholder simples (livro azul) quando nao eh possivel ler o PDF."""
    try:
        from PIL import Image, ImageDraw  # type: ignore

        img = Image.new("RGB", (480, 640), color=(37, 99, 235))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Capa do PDF", fill=(255, 255, 255))
        saida_webp.parent.mkdir(parents=True, exist_ok=True)
        img.save(saida_webp, "WEBP", quality=80)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

def md_para_html(caminho_md: Path) -> str:
    try:
        import markdown  # type: ignore

        texto = ler_arquivo(caminho_md)
        return markdown.markdown(texto, extensions=["extra", "tables", "toc"])
    except Exception:
        texto = ler_arquivo(caminho_md)
        return f"<pre>{esc_html(texto)}</pre>"


# ---------------------------------------------------------------------------
# QR code
# ---------------------------------------------------------------------------

def gerar_qr(url: str, saida_png: Path) -> bool:
    saida_png.parent.mkdir(parents=True, exist_ok=True)
    try:
        import qrcode  # type: ignore

        img = qrcode.make(url)
        img.save(saida_png)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Carregamento e validacao dos dados
# ---------------------------------------------------------------------------

def carregar_dados() -> list[dict]:
    itens = []
    erros = []

    if not DATA_DIR.exists():
        erros.append(f"Pasta {DATA_DIR} nao encontrada.")
        return itens, erros

    for arquivo_yml in sorted(DATA_DIR.glob("*.yml")):
        slug_do_arquivo = arquivo_yml.stem

        try:
            dados = yaml.safe_load(ler_arquivo(arquivo_yml))
        except yaml.YAMLError as exc:
            erros.append(f"{arquivo_yml.name}: YAML invalido: {exc}")
            continue

        if not isinstance(dados, dict):
            erros.append(f"{arquivo_yml.name}: conteudo nao eh um mapeamento.")
            continue

        id_item = dados.get("id", "")
        if id_item != slug_do_arquivo:
            erros.append(
                f"{arquivo_yml.name}: 'id' ({id_item}) diferente do nome do arquivo ({slug_do_arquivo})."
            )

        # Campos obrigatorios
        for campo in ("titulo", "evento", "ano", "recursos"):
            if campo not in dados or dados[campo] in (None, ""):
                erros.append(f"{arquivo_yml.name}: campo obrigatorio '{campo}' ausente ou vazio.")

        # Validar recursos
        recursos = dados.get("recursos", [])
        if not isinstance(recursos, list) or len(recursos) == 0:
            erros.append(f"{arquivo_yml.name}: 'recursos' deve ser uma lista com ao menos um item.")
        else:
            for idx, rec in enumerate(recursos):
                if not isinstance(rec, dict):
                    erros.append(f"{arquivo_yml.name}: recurso {idx} nao eh um objeto.")
                    continue
                tipo = rec.get("tipo", "")
                arquivo = rec.get("arquivo", "")
                if not arquivo:
                    erros.append(f"{arquivo_yml.name}: recurso {idx} sem 'arquivo'.")
                    continue
                caminho_arquivo = ROOT / arquivo
                if not caminho_arquivo.exists():
                    erros.append(
                        f"{arquivo_yml.name}: arquivo '{arquivo}' nao encontrado para recurso '{tipo}'."
                    )

        if erros:
            # Nao interrompe: avisa e segue para nao derrubar o site inteiro
            pass

        itens.append(dados)

    return itens, erros


def enriquecer_item(item: dict) -> dict:
    """Adiciona campos computados (url, capa, recursos detalhados)."""
    slug = item["id"]
    item = dict(item)
    item["url"] = f"{BASE_URL}/m/{slug}/"

    recursos_enriquecidos = []
    for rec in item.get("recursos", []):
        rec = dict(rec)
        arquivo = rec.get("arquivo", "")
        caminho = ROOT / arquivo

        if arquivo and caminho.exists():
            info = info_pdf(caminho)
            rec["tamanho_bytes"] = info["tamanho_bytes"]
            rec["tamanho_legivel"] = tamanho_legível(info["tamanho_bytes"])
            rec["paginas"] = info["paginas"]

            # Verifica limite de tamanho
            mb = info["tamanho_bytes"] / (1024 * 1024)
            if mb > LIMITE_TAMANHO_FALHA_MB:
                print(
                    f"AVISO: {arquivo} tem {mb:.1f} MB (acima do limite de falha de {LIMITE_TAMANHO_FALHA_MB} MB).",
                    file=sys.stderr,
                )
            elif mb > LIMITE_TAMANHO_AVISO_MB:
                print(
                    f"AVISO: {arquivo} tem {mb:.1f} MB (acima do recomendado de {LIMITE_TAMANHO_AVISO_MB} MB).",
                    file=sys.stderr,
                )

            # Tipo do recurso para rotulo default
            tipo = rec.get("tipo", "")
            if tipo == "slides" and not rec.get("rotulo"):
                rec["rotulo"] = "Slides (PDF)"
            elif tipo == "tutorial" and not rec.get("rotulo"):
                rec["rotulo"] = "Tutorial (Markdown)"
            elif tipo == "codigo" and not rec.get("rotulo"):
                rec["rotulo"] = "Codigo"
            elif tipo == "video" and not rec.get("rotulo"):
                rec["rotulo"] = "Video"
            elif tipo == "outro" and not rec.get("rotulo"):
                rec["rotulo"] = "Outro"

            # URL do recurso
            if arquivo.startswith("http"):
                rec["url"] = arquivo
            else:
                rec["url"] = f"{BASE_URL}/{arquivo}"

            # Capa apenas para PDFs
            if arquivo.lower().endswith(".pdf"):
                capa_path = CAPAS_DIR / f"{slug}-{slugify(rec.get('rotulo', 'recurso'))}.webp"
                if gerar_capa(caminho, capa_path):
                    rec["capa"] = f"{BASE_URL}/capas/{capa_path.name}"
        recursos_enriquecidos.append(rec)

    item["recursos"] = recursos_enriquecidos
    return item


# ---------------------------------------------------------------------------
# Geracao de HTML
# ---------------------------------------------------------------------------

CSS_URL = f"{BASE_URL}/assets/style.css"
JS_URL = f"{BASE_URL}/assets/app.js"


def card_html(item: dict) -> str:
    slug = item["id"]
    titulo = esc_html(item["titulo"])
    evento = esc_html(item.get("evento", ""))
    ano = item.get("ano", "")
    descricao = esc_html(item.get("descricao", ""))
    tema = item.get("tema", [])
    chips_tema = "".join(
        f'<span class="chip tema" data-tema="{esc_html(t)}">{esc_html(t)}</span>' for t in tema
    )
    categorias = item.get("categorias", item.get("categoria", ""))
    if isinstance(categorias, str):
        categorias = [categorias]
    chips_cat = "".join(
        f'<span class="chip" data-cat="{esc_html(c)}">{esc_html(c)}</span>' for c in categorias
    )

    # Recursos (botoes no card)
    recursos_html = ""
    for rec in item.get("recursos", []):
        rotulo = esc_html(rec.get("rotulo", "Recurso"))
        url = rec.get("arquivo", "")
        tipo = rec.get("tipo", "")
        tamanho = rec.get("tamanho_legivel", "")
        paginas = rec.get("paginas")
        meta = ""
        if tamanho:
            meta += f" {tamanho}"
        if paginas:
            meta += f" · {paginas} págs."

        if tipo == "tutorial":
            # Link para a pagina do tutorial (dentro do site)
            tutorial_url = f"{BASE_URL}/m/{slug}/#tutorial"
            recursos_html += (
                f'<a class="btn btn--tut" href="{tutorial_url}">'
                f"{rotulo}</a>"
            )
        else:
            target = ' target="_blank" rel="noopener"' if not url.startswith(f"{BASE_URL}/") else ""
            download = ' download' if tipo == "slides" else ""
            recursos_html += (
                f'<a class="btn" href="{esc_html(url)}"{target}{download}>'
                f"{rotulo}</a>"
            )
            if meta:
                recursos_html += f'<span class="meta">{esc_html(meta.strip(" ·"))}</span>'

    destaque_classe = " card--destaque" if item.get("destaque") else ""

    return (
        '<li class="card' + destaque_classe + '" data-id="' + esc_html(slug) + '">' +
        '<div class="card__topo">' +
        chips_cat +
        (f'<span class="ano">{esc_html(ano)}</span>' if ano else "") +
        "</div>" +
        '<h2 class="card__titulo">' + titulo + "</h2>" +
        (f'<p class="card__evento">{evento}</p>' if evento else "") +
        '<p class="card__desc">' + descricao + "</p>" +
        '<div class="card__tema">' + chips_tema + "</div>" +
        '<div class="card__recursos">' + recursos_html + "</div>" +
        "</li>"
    )


def gerar_index_html(itens: list[dict], erros: list[str]) -> str:
    categorias = sorted({c for i in itens for c in (i.get("categorias") or [i.get("categoria", "")] or [""]) if c})
    temas = sorted({t for i in itens for t in (i.get("tema") or [])})

    # Ordenacao: ano decrescente, depois titulo
    itens_ordenados = sorted(
        itens,
        key=lambda i: (-(i.get("ano") or 0), str(i.get("titulo", ""))),
    )

    cards = "".join(card_html(i) for i in itens_ordenados)

    filtros_cat = "".join(
        f'<button type="button" data-cat="{esc_html(c)}">{esc_html(c)}</button>'
        for c in ["Todos"] + categorias
    )
    filtros_tema = "".join(
        f'<button type="button" data-tema="{esc_html(t)}">{esc_html(t)}</button>'
        for t in temas
    )

    contador_id = "contador"

    # Script embutido minimo para filtro/busca (melhoria progressiva)
    js_filtro = """
(function(){
  var lista = document.getElementById("lista");
  var contador = document.getElementById("contador");
  var cards = Array.from(lista.getElementsByClassName("card"));
  var catAtiva = "Todos";
  var temaAtivo = "Todos";
  var termo = "";

  function norm(v){return String(v==null?"":v).normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase();}
  function visivel(card){
    var id = card.getAttribute("data-id");
    var cat = card.querySelector('[data-cat]').getAttribute("data-cat");
    if(catAtiva!=="Todos" && cat!==catAtiva) return false;
    if(temaAtivo!=="Todos" && !card.querySelector('[data-tema="'+temaAtivo+'"]')) return false;
    if(termo){
      var texto = norm(card.textContent);
      if(texto.indexOf(norm(termo))===-1) return false;
    }
    return true;
  }
  function render(){
    var vis = cards.filter(visivel);
    contador.textContent = vis.length + (vis.length===1?" material":" materiais");
    lista.innerHTML = "";
    vis.forEach(function(c){ lista.appendChild(c); });
    if(vis.length===0){
      lista.innerHTML = '<li class="vazio">Nenhum material encontrado. Tente outra busca ou categoria.</li>';
    }
  }
  document.getElementById("filtros-cat").addEventListener("click", function(e){
    var b = e.target.closest("button[data-cat]");
    if(!b) return;
    catAtiva = b.getAttribute("data-cat");
    renderFiltros();
    render();
  });
  document.getElementById("filtros-tema").addEventListener("click", function(e){
    var b = e.target.closest("button[data-tema]");
    if(!b) return;
    temaAtivo = b.getAttribute("data-tema");
    renderFiltros();
    render();
  });
  document.getElementById("busca").addEventListener("input", function(){
    termo = this.value;
    render();
  });
  function renderFiltros(){
    var botoes = document.querySelectorAll("#filtros-cat button, #filtros-tema button");
    botoes.forEach(function(b){
      var ativo = (b.getAttribute("data-cat")===catAtiva) || (b.getAttribute("data-tema")===temaAtivo);
      b.setAttribute("aria-pressed", ativo);
      b.classList.toggle("ativo", ativo);
    });
  }
  renderFiltros();
  render();
})();
"""

    erros_html = ""
    if erros:
        erros_html = (
            '<div class="aviso-erros">'
            + "<br>".join(esc_html(e) for e in erros)
            + "</div>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Materiais complementares · Ubiratan Zakaib do Nascimento</title>
  <meta name="description" content="Slides, guias e materiais de apoio das palestras e vídeos de Ubiratan Zakaib do Nascimento sobre Linux, Software Livre, Infraestrutura, Cloud e Cibersegurança.">
  <meta name="theme-color" content="#2563eb">
  <meta name="robots" content="index, follow">

  <meta property="og:type" content="website">
  <meta property="og:title" content="Materiais complementares · Ubiratan Zakaib do Nascimento">
  <meta property="og:description" content="Slides, guias e referências das palestras e vídeos, em PDF.">
  <meta property="og:url" content="{BASE_URL}/">
  <meta property="og:image" content="{BASE_URL}/imgs/social.png">

  <link rel="canonical" href="{BASE_URL}/">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E📚%3C/text%3E%3C/svg%3E">
  <link rel="alternate" type="application/feed+json" title="Feed de materiais" href="{BASE_URL}/feed.json">
  <link rel="stylesheet" href="{CSS_URL}">
</head>
<body>
  <a class="pular" href="#lista">Ir para os materiais</a>

  <header class="topo">
    <div class="wrap topo__in">
      <a class="marca" href="https://www.onucleo.com.br">
        <img src="{BASE_URL}/imgs/logo-onucleo.png" alt="ONúcleo — Misturando Tecnologia e Educação" width="180" height="48"/>
      </a>
      <nav class="topo__links" aria-label="Links externos">
        <a href="https://www.onucleo.com.br">Site</a>
        <a href="https://www.youtube.com/birazn" target="_blank" rel="noopener">YouTube</a>
        <a href="https://github.com/birazn" target="_blank" rel="noopener">GitHub</a>
      </nav>
    </div>
  </header>

  <main>
    <section class="hero">
      <div class="wrap">
        <p class="eyebrow">Materiais complementares</p>
        <h1>Slides, guias e referências das <span>palestras e vídeos</span></h1>
        <p class="lead">
          Conteúdo de apoio sobre Linux, Software Livre, Infraestrutura, Cloud e Cibersegurança, em PDF.
        </p>
      </div>
    </section>

    <section class="wrap conteudo">
      {erros_html}

      <div class="controles">
        <div class="filtros" role="group" aria-label="Filtrar">
          <div id="filtros-cat" class="filtro-grupo">
            <span class="filtro-label">Categoria</span>
            {filtros_cat}
          </div>
          <div id="filtros-tema" class="filtro-grupo">
            <span class="filtro-label">Tema</span>
            {filtros_tema}
          </div>
        </div>
        <label class="busca">
          <span class="sr">Buscar material</span>
          <input type="search" id="busca" placeholder="Buscar material…" autocomplete="off">
        </label>
      </div>

      <p class="contador" id="contador" aria-live="polite"></p>

      <ul class="grade" id="lista">{cards}</ul>

      <noscript>
        <p class="vazio">O JavaScript esta desativado. Voce ainda pode acessar os arquivos direto em
          <a href="https://github.com/birazn/materiais/tree/main/pdfs">github.com/birazn/materiais</a>.</p>
      </noscript>
    </section>
  </main>

  <footer class="rodape">
    <div class="wrap rodape__in">
      <p>© <span id="ano">2026</span> Ubiratan Zakaib do Nascimento</p>
      <p>
        <a href="https://www.onucleo.com.br/contato">Convide para sua palestra</a> ·
        <a href="https://www.onucleo.com.br">← Voltar ao site</a>
      </p>
      <p class="licenca">Materiais sob licença <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.</p>
    </div>
  </footer>

  <script defer>{js_filtro}</script>
</body>
</html>"""


def gerar_pagina_palestra(item: dict) -> str:
    slug = item["id"]
    titulo = esc_html(item["titulo"])
    evento = esc_html(item.get("evento", ""))
    ano = item.get("ano", "")
    descricao = esc_html(item.get("descricao", ""))
    resumo_longo = item.get("resumo_longo", "")
    tema = item.get("tema", [])
    video = item.get("video", "")
    repositorio = item.get("repositorio", "")

    # Recursos detalhados
    recursos_detalhe = ""
    for rec in item.get("recursos", []):
        rotulo = esc_html(rec.get("rotulo", "Recurso"))
        arquivo = rec.get("arquivo", "")
        tipo = rec.get("tipo", "")
        url = rec.get("url", "")
        tamanho = rec.get("tamanho_legivel", "")
        paginas = rec.get("paginas")
        capa = rec.get("capa", "")

        meta_partes = []
        if tamanho:
            meta_partes.append(tamanho)
        if paginas:
            meta_partes.append(f"{paginas} págs.")
        meta = " · ".join(meta_partes)

        if tipo == "tutorial":
            html_tutorial = md_para_html(MDS_DIR / arquivo) if arquivo else ""
            # Ajusta caminhos relativos de imagem para a pagina m/<slug>/ (dois niveis acima)
            html_tutorial = html_tutorial.replace('src="../imgs/', 'src="../../imgs/')
            recursos_detalhe += (
                f'<div class="recurso">'
                f'<h3>{rotulo}</h3>'
                f'<p>Leia o tutorial direto no site:</p>'
                f'<div class="conteudo-md">{html_tutorial}</div>'
                f'</div>'
            )
        else:
            target = ' target="_blank" rel="noopener"' if not url.startswith(f"{BASE_URL}/") else ""
            download = ' download' if tipo == "slides" else ""
            recursos_detalhe += (
                f'<div class="recurso">'
                f'<h3>{rotulo}</h3>'
                f'<p>{esc_html(meta)}</p>'
                f'<a class="btn" href="{esc_html(url)}"{target}{download}>Abrir arquivo</a>'
                f'</div>'
            )

    video_html = ""
    if video:
        video_html = (
            f'<div class="destaque-box">'
            f'<h3>🎥 Vídeo da palestra</h3>'
            f'<p><a href="{esc_html(video)}" target="_blank" rel="noopener">Assistir no YouTube</a></p>'
            f'</div>'
        )

    repositorio_html = ""
    if repositorio:
        repositorio_html = (
            f'<div class="destaque-box">'
            f'<h3>💻 Código / Repositório</h3>'
            f'<p><a href="{esc_html(repositorio)}" target="_blank" rel="noopener">Acessar no GitHub</a></p>'
            f'</div>'
        )

    qr_url = f"{BASE_URL}/qr/{slug}.png"

    json_ld = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": item["titulo"],
        "startDate": item.get("data", ""),
        "location": item.get("evento", ""),
        "description": item.get("descricao", ""),
        "url": f"{BASE_URL}/m/{slug}/",
    }

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{titulo} · Materiais complementares</title>
  <meta name="description" content="{descricao}">
  <meta name="theme-color" content="#2563eb">
  <meta name="robots" content="index, follow">

  <meta property="og:type" content="website">
  <meta property="og:title" content="{titulo} · Ubiratan Zakaib do Nascimento">
  <meta property="og:description" content="{descricao}">
  <meta property="og:url" content="{BASE_URL}/m/{slug}/">
  <meta property="og:image" content="{BASE_URL}/imgs/social.png">

  <link rel="canonical" href="{BASE_URL}/m/{slug}/">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E📚%3C/text%3E%3C/svg%3E">
  <link rel="stylesheet" href="{CSS_URL}">

  <script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>
</head>
<body>
  <a class="pular" href="#conteudo">Ir para o conteúdo</a>

  <header class="topo">
    <div class="wrap topo__in">
      <a class="marca" href="{BASE_URL}/">
        <img src="{BASE_URL}/imgs/logo-onucleo.png" alt="ONúcleo — Misturando Tecnologia e Educação" width="180" height="48"/>
      </a>
      <nav class="topo__links" aria-label="Links externos">
        <a href="{BASE_URL}/">Materiais</a>
        <a href="https://www.youtube.com/birazn" target="_blank" rel="noopener">YouTube</a>
        <a href="https://github.com/birazn" target="_blank" rel="noopener">GitHub</a>
      </nav>
    </div>
  </header>

  <main>
    <section class="wrap conteudo" id="conteudo">
      <nav class="paginacao">
        <a href="{BASE_URL}/">← Voltar aos materiais</a>
      </nav>

      <article class="palestra">
        <div class="capa-qr">
          <img src="{qr_url}" alt="QR code da página" width="120" height="120"/>
          <p class="qr-legenda">Leia com o celular para abrir esta página</p>
        </div>

        <h1>{titulo}</h1>
        <div class="meta-evento">
          <span class="ano">{esc_html(ano)}</span>
          {f'<span class="evento">{evento}</span>' if evento else ""}
          {''.join(f'<span class="chip tema">{esc_html(t)}</span>' for t in tema)}
        </div>

        <p class="lead">{descricao}</p>

        {f'<div class="resumo-longo">{resumo_longo}</div>' if resumo_longo else ""}

        <h2>Recursos</h2>
        <div class="recursos-lista">
          {recursos_detalhe}
        </div>

        {video_html}
        {repositorio_html}
      </article>
    </section>
  </main>

  <footer class="rodape">
    <div class="wrap rodape__in">
      <p>© <span id="ano">2026</span> Ubiratan Zakaib do Nascimento</p>
      <p>
        <a href="{BASE_URL}/">← Voltar aos materiais</a> ·
        <a href="https://www.onucleo.com.br/contato">Convide para sua palestra</a>
      </p>
      <p class="licenca">Materiais sob licença <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.</p>
    </div>
  </footer>

  <script>document.getElementById("ano").textContent = new Date().getFullYear();</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Feed, sitemap, robots
# ---------------------------------------------------------------------------

def gerar_feed(itens: list[dict]) -> str:
    feed_itens = []
    for item in itens:
        feed_itens.append({
            "id": item["id"],
            "title": item["titulo"],
            "summary": item.get("descricao", ""),
            "url": item["url"],
            "date_published": item.get("data", ""),
        })
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "Materiais complementares · ONúcleo",
        "description": "Slides, guias e referências das palestras e vídeos.",
        "home_page_url": BASE_URL,
        "feed_url": f"{BASE_URL}/feed.json",
        "items": feed_itens,
    }
    return json.dumps(feed, ensure_ascii=False, indent=2)


def gerar_sitemap(itens: list[dict]) -> str:
    urls = [f"{BASE_URL}/"]
    for item in itens:
        urls.append(item["url"])
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        xml.append("  <url><loc>" + esc_html(u) + "</loc></url>")
    xml.append("</urlset>")
    return "\n".join(xml)


def gerar_robots() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"\nSitemap: {BASE_URL}/sitemap.xml\n"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=== Build de materiais ===")
    print(f"Raiz: {ROOT}")
    print(f"Data: {DATA_DIR}")

    itens, erros = carregar_dados()
    print(f"Palestras carregadas: {len(itens)}")
    if erros:
        print("Erros de validacao:")
        for e in erros:
            print(f"  - {e}")

    # Enriquecer (tamanho, paginas, capas, qr)
    itens_enriquecidos = [enriquecer_item(i) for i in itens]

    # Gerar QR codes
    for item in itens_enriquecidos:
        gerar_qr(item["url"], QR_DIR / f"{item['id']}.png")

    # Criar diretorios de saida
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)
    QR_DIR.mkdir(parents=True, exist_ok=True)
    M_DIR.mkdir(parents=True, exist_ok=True)

    # index.html
    index_html = gerar_index_html(itens_enriquecidos, erros)
    escrever_arquivo(INDEX_PATH, index_html)
    print(f"Gerado: {INDEX_PATH}")

    # materiais.json (contrato publico)
    contrato = {
        "gerado_em": agora_iso(),
        "base_url": BASE_URL,
        "itens": itens_enriquecidos,
    }
    escrever_arquivo(MATERIAIS_JSON_PATH, json.dumps(contrato, ensure_ascii=False, indent=2))
    print(f"Gerado: {MATERIAIS_JSON_PATH}")

    # Paginas individuais
    for item in itens_enriquecidos:
        pagina = gerar_pagina_palestra(item)
        caminho_pagina = M_DIR / item["id"] / "index.html"
        escrever_arquivo(caminho_pagina, pagina)
    print(f"Geradas {len(itens_enriquecidos)} paginas em m/")

    # Feed, sitemap, robots
    escrever_arquivo(FEED_PATH, gerar_feed(itens_enriquecidos))
    escrever_arquivo(SITEMAP_PATH, gerar_sitemap(itens_enriquecidos))
    escrever_arquivo(ROBOTS_PATH, gerar_robots())
    print(f"Gerado: {FEED_PATH}")
    print(f"Gerado: {SITEMAP_PATH}")
    print(f"Gerado: {ROBOTS_PATH}")

    # Copiar assets se nao existirem na raiz (para uso local)
    print("\n=== Build concluido com sucesso ===")
    if erros:
        print("ATENCAO: ha erros de validacao listados acima. O site continua no ar, mas corrija os YAMLs.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
