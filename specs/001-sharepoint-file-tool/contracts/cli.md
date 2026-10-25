# Contrato: CLI e funções públicas

## CLI

`uv run python -m sharepoint_files [--env-file CAMINHO] <comando> [opções]`

| Comando | Opções | Saída |
|---|---|---|
| `site` | `--site-id` ou `--hostname` + `--site-path` (padrão: configuração) | id, nome e URL do site |
| `libraries` | opções de site | uma linha por biblioteca: id e nome |
| `ls` | `--library ID`, `--folder CAMINHO` (padrão: raiz) | uma linha por item: tipo, tamanho, caminho |
| `find` | `--library ID`, `--folder CAMINHO`, `--name TEXTO` ou `--path CAMINHO` | itens correspondentes; "nenhum arquivo encontrado" se vazio |
| `download` | `--library ID`, `--dest DIR`, `--overwrite`, um ou mais `CAMINHO` de arquivo, relativo à biblioteca (inexistente ou pasta é falha individual) | relatório por item e totais |

Códigos de saída: `0` sucesso (inclui itens ignorados e resultado vazio); `1` erro de configuração, autenticação ou operação; `2` argumentos inválidos; no `download`, `1` se houver ao menos uma falha, após processar todo o lote.

Mensagens e relatórios vão para a saída padrão ou de erro, nunca contêm segredos, tokens ou URLs de download.

## Funções públicas (módulos)

| Módulo | Função | Contrato |
|---|---|---|
| client | `load_config(env) -> Config` | levanta `GraphToolError(configuração)` |
| client | `create_client(config, timeout) -> GraphServiceClient` | app-only, escopo de `config.scope` |
| sharepoint | `resolve_site(client, config_or_ids) -> Site` | por ID ou hostname + caminho |
| sharepoint | `list_libraries(client, site_id) -> list[Library]` | segue paginação |
| sharepoint | `list_items(client, drive_id, folder="") -> list[Item]` | segue paginação |
| sharepoint | `find_items(client, drive_id, folder="", name=None, path=None) -> list[Item]` | escopo restrito; sem busca do Graph |
| downloads | `download_files(client, requests, dest, overwrite=False) -> DownloadReport` | máx. 20 itens, sequencial, nunca levanta por falha de item |

As funções de rede são assíncronas (o SDK é assíncrono); a CLI as executa com `asyncio.run`.
