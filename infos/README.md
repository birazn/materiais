# Materiais complementares

Página estática (GitHub Pages) com os PDFs de apoio às palestras e vídeos.

## Estrutura

```
index.html        página
assets/style.css  estilos
assets/app.js     lê o materiais.json e monta os cards
materiais.json    lista dos materiais (é o único arquivo que você edita no dia a dia)
pdfs/             coloque os PDFs aqui
```

## Como adicionar um material

1. Copie o PDF para a pasta `pdfs/` (nome sem espaços, com ano/versão: `guia-linux-2026.pdf`).
2. Adicione um bloco no `materiais.json`.
3. Faça o commit. Em cerca de 1 minuto a página é atualizada.

| Campo       | Obrigatório | Exemplo                                  |
|-------------|-------------|------------------------------------------|
| `titulo`    | sim         | "Guia de Linux para iniciantes"          |
| `arquivo`   | sim         | "pdfs/guia-linux-2026.pdf"               |
| `descricao` | não         | frase curta sobre o conteúdo             |
| `categoria` | não         | "Palestras", "Guias", "Referências"      |
| `ano`       | não         | 2026                                     |
| `evento`    | não         | "Latinoware 2024"                        |
| `tamanho`   | não         | "2,4 MB"                                 |
| `paginas`   | não         | 42                                       |
| `tags`      | não         | ["linux", "cloud"] (ajudam na busca)     |

> Os três itens que vêm no `materiais.json` são **exemplos** baseados nas suas palestras. Os PDFs correspondentes não existem até você enviá-los para `pdfs/`. Troque ou apague os que não usar.

## Testar no seu computador

O `fetch` do navegador não funciona abrindo o arquivo direto. Use um servidor local:

```
python3 -m http.server 8000
# abra http://localhost:8000
```

## Cuidados

- O repositório é público: tudo que estiver em `pdfs/` fica acessível a qualquer pessoa, e versões antigas continuam no histórico do Git.
- Limites do GitHub Pages: site de até 1 GB e cerca de 100 GB de tráfego por mês (limite flexível). O Git também não aceita arquivos de 100 MB ou mais.
- Comprima os PDFs antes de enviar (ideal abaixo de 5 MB).
