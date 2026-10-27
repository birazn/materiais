# Materiais complementares

Página estática (GitHub Pages) com os PDFs de apoio às palestras e vídeos de Ubiratan Zakaib do Nascimento.

Publicado em: https://birazn.github.io/materiais/

---

## Como publicar um material novo (fluxo atual)

O usuário edita **só arquivos de metadados**. Uma GitHub Action executa o build a cada push e publica sozinho.

### Passo 1 — Adicione os arquivos

- Coloque o PDF na pasta `pdfs/` (nome em minúsculas, sem acentos nem espaços, padrão `AAAA-evento-assunto.pdf`).
- Se houver tutorial em Markdown, coloque em `mds/` com o mesmo padrão.

### Passo 2 — Crie o arquivo de metadados

Crie `data/AAAA-evento-assunto.yml` copiando o modelo abaixo e preenchendo os campos.

```yaml
id: 2026-ferpatechday-prompt-injection   # igual ao nome do arquivo (sem .yml)
titulo: "Título da palestra"
evento: "Nome do Evento 2026"
data: 2026-MM-DD                         # data real da palestra (ISO), opcional
ano: 2026
tema:
  - Cibersegurança
  - IA
descricao: "Resumo curto (~200 caracteres) para o card."
resumo_longo: "Texto completo, exibido só na página da palestra."
video: ""                                # URL do YouTube, se houver
repositorio: ""                          # URL do GitHub, se houver
destaque: false
recursos:
  - tipo: slides                         # slides | tutorial | codigo | video | outro
    rotulo: "Slides (PDF)"
    arquivo: pdfs/2026-evento-assunto.pdf
  - tipo: tutorial
    rotulo: "Tutorial (Markdown)"
    arquivo: mds/2026-evento-assunto.md
```

### Passo 3 — Faça o commit

Pode ser pelo navegador, no site do GitHub.

### Passo 4 — Aguarde

Em cerca de 2 minutos a GitHub Action roda o build, valida os arquivos, gera capas, QR codes, sitemap, feed e páginas individuais, e publica no GitHub Pages.

Se houver erro (YAML inválido, arquivo inexistente, PDF muito grande), a mensagem aparece claramente na aba **Actions** do repositório. O site continua no ar com a versão anterior.

---

## Estrutura do repositório

```
data/              1 .yml por palestra (único arquivo editado no dia a dia)
pdfs/              PDFs originais
mds/               tutoriais em Markdown
capas/             gerado automaticamente (capas .webp dos PDFs)
qr/                gerado automaticamente (QR codes por palestra)
m/<slug>/          gerado automaticamente (página própria de cada palestra)
assets/            style.css e app.js (filtro/busca — melhoria progressiva)
scripts/build.py   script de build executado pela Action
.github/workflows/pages.yml  Action de build e deploy
materiais.json     contrato público estável (gerado pelo build)
sitemap.xml        gerado pelo build
feed.json          gerado pelo build
robots.txt         permite indexação
```

---

## Campos do `.yml`

| Campo | Obrigatório | Exemplo |
|---|---|---|
| `id` | sim | `2026-ferpatechday-prompt-injection` |
| `titulo` | sim | `"Segurança na Era dos LLMs..."` |
| `evento` | sim | `"ferpaTechDay 2026"` |
| `ano` | sim | `2026` |
| `data` | não | `2026-10-24` |
| `tema` | não | `["Cibersegurança", "IA"]` |
| `descricao` | sim | resumo curto para o card |
| `resumo_longo` | não | texto completo para a página da palestra |
| `video` | não | URL do YouTube |
| `repositorio` | não | URL do GitHub |
| `destaque` | não | `true` ou `false` |
| `recursos` | sim | lista com `tipo`, `rotulo`, `arquivo` |

---

## Cuidados

- O repositório é público: tudo que estiver em `pdfs/` fica acessível a qualquer pessoa, e versões antigas continuam no histórico do Git.
- Limites do GitHub Pages: site de até 1 GB. O Git não aceita arquivos de 100 MB ou mais.
- Comprima os PDFs antes de enviar (ideal abaixo de 5 MB). Acima de 5 MB o build avisa; acima de 50 MB falha.
- Não renomeie PDFs já divulgados sem manter o caminho antigo.

---

## Testar localmente

```bash
python3 -m pip install PyYAML Pillow markdown qrcode[pil] PyPDF2
sudo apt-get install -y poppler-utils  # apenas para gerar capas dos PDFs
python3 scripts/build.py
python3 -m http.server 8000
# abra http://localhost:8000
```

---

## Integração com WordPress

O `materiais.json` é um contrato público estável. A seção "Materiais" do WordPress pode lê-lo diretamente (testar CORS se necessário), evitando cadastro duplicado.

---

## Licença

Os materiais estão sob licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Veja `LICENSE`.
