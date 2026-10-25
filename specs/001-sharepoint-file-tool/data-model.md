# Modelo de Dados

Estruturas imutáveis simples (`dataclass(frozen=True)`), sem persistência.

## Config

| Campo | Tipo | Regra |
|---|---|---|
| tenant_id, client_id, client_secret | str | obrigatórios, não vazios; o segredo nunca aparece em `repr` nem em mensagens |
| scope | str | padrão `https://graph.microsoft.com/.default` |
| site_id | str ou None | usado se definido |
| hostname, site_path | str ou None | par exigido quando `site_id` não existe |
| download_dir | Path ou None | padrão do destino |

Validação: falta de variável gera `GraphToolError(configuração)` citando só os nomes.

## Site

`id: str`, `name: str`, `web_url: str`.

## Library

`id: str` (ID do drive), `name: str`.

## Item

| Campo | Tipo | Regra |
|---|---|---|
| id | str | |
| name | str | |
| path | str | caminho relativo à biblioteca, sem barra inicial |
| is_folder | bool | |
| size | int ou None | apenas arquivos |

## DownloadRequest

`drive_id: str`, `item_id: str`, `name: str`, `size: int | None` (por arquivo); lote: lista de até 20, `dest: Path`, `overwrite: bool = False`.

## DownloadResult / DownloadReport

`DownloadResult`: `item: str`, `status: downloaded | skipped | failed`, `path: Path | None`, `reason: str | None`.

`DownloadReport`: lista ordenada de `DownloadResult`, com contagens por status.

Transições por item: pendente → baixado (conteúdo completo e renomeado), ignorado (destino já existe sem `overwrite`) ou falha (caminho fora do destino, pasta, acima de 100 MB, erro HTTP, timeout, erro de gravação). Falhas nunca interrompem os itens seguintes.
