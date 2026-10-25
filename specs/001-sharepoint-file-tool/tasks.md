# Tasks: Ferramenta de arquivos do SharePoint

**Entrada**: documentos em `specs/001-sharepoint-file-tool/` (plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md)

**Pré-requisitos**: plan.md, spec.md

**Testes**: incluídos, pois a spec (FR-022, FR-023) os exige: unitários sem rede nem credenciais e integração opt-in.

**Organização**: por história de usuário. US4 (P1) é pré-requisito técnico de US1 (P1); a ordem é US4, US1, US2, US3.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- Convenção de caminhos: `src/sharepoint_files/` e `tests/` na raiz, conforme o plano

## Fase 1: Setup

**Objetivo**: estrutura do pacote e ferramentas de qualidade

- [X] T001 Criar o pacote `src/sharepoint_files/__init__.py` e as pastas `tests/unit/` e `tests/integration/`
- [X] T002 Atualizar `pyproject.toml`: configurar Hatchling para instalar `src/sharepoint_files` e habilitar `uv run python -m sharepoint_files`; em `[tool.pytest.ini_options]` adicionar `pythonpath = ["src"]`, `addopts = "-m 'not integration'"` e o marcador `integration`; em `[tool.mypy]` adicionar `mypy_path = "src"`; declarar `httpx` em `[project].dependencies` com a mesma versão já travada e atualizar `uv.lock`
- [X] T003 [P] Criar `.github/workflows/ci.yml` executando `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` e `uv run pytest`
- [X] T004 [P] Atualizar `.env.example` com `SHAREPOINT_HOSTNAME`, `SHAREPOINT_SITE_PATH` e `DOWNLOAD_DIR` (opcionais), mantendo `SHAREPOINT_SITE_ID` e `GRAPH_SCOPE`, e confirmar que `.env` está no `.gitignore`

---

## Fase 2: Fundação (bloqueia todas as histórias)

**Objetivo**: erros e modelos compartilhados

- [X] T005 Definir em `src/sharepoint_files/client.py` a exceção `GraphToolError(category, message)` com as categorias: configuração, autenticação, permissão, não encontrado, limitação, servidor, timeout e caminho inválido
- [X] T006 [P] Definir as dataclasses imutáveis `Site`, `Library` e `Item` em `src/sharepoint_files/sharepoint.py` conforme data-model.md (`Item.path` relativo à biblioteca, sem barra inicial; `size` apenas para arquivos)
- [X] T007 [P] Definir as dataclasses `DownloadRequest`, `DownloadResult` (status `downloaded | skipped | failed`) e `DownloadReport` em `src/sharepoint_files/downloads.py`

**Ponto de controle**: `uv run mypy` passa com os tipos definidos.

---

## Fase 3: História 4 - Autenticar e configurar o ambiente (P1)

**Objetivo**: configuração validada e cliente Graph app-only.

**Teste independente**: configuração completa gera o cliente; variável ausente falha antes de qualquer chamada de rede, citando só o nome.

### Testes

- [X] T008 [P] [US4] Testar em `tests/unit/test_client.py`: configuração completa, cada variável obrigatória ausente ou vazia citando só o nome (nunca o valor), exigência de `SHAREPOINT_SITE_ID` ou do par hostname + caminho, padrão de `GRAPH_SCOPE`, `repr` sem o segredo
- [X] T009 [P] [US4] Testar em `tests/unit/test_client.py` a tradução de erros para `GraphToolError`: 401, 403, 404, 429 (com `Retry-After` quando presente), 5xx, `httpx.TimeoutException`, e que a mensagem nunca contém token, segredo ou URL de download

### Implementação

- [X] T010 [US4] Implementar `Config` e `load_config(env)` em `src/sharepoint_files/client.py`: `tenant_id`, `client_id`, `client_secret` (obrigatórios e não vazios, fora do `repr`), `scope` (padrão `https://graph.microsoft.com/.default`), `site_id` ou `hostname` + `site_path`, `download_dir`
- [X] T011 [US4] Implementar em `src/sharepoint_files/client.py` o leitor mínimo de `.env` (não sobrescreve variáveis já definidas no ambiente) e `create_client(config, timeout)` com `ClientSecretCredential` e `httpx.AsyncClient(timeout=...)` via `GraphClientFactory.create_with_default_middleware`, mantendo o retry padrão do SDK (sem retry próprio); timeouts padrão de 30 s (listagem) e 120 s (download)
- [X] T012 [US4] Implementar em `src/sharepoint_files/client.py` a função única que traduz `ODataError`, `ClientAuthenticationError` e `httpx.TimeoutException` em `GraphToolError`, sem incluir segredos, tokens ou URLs de download

**Ponto de controle**: T008 e T009 passam sem rede.

---

## Fase 4: História 1 - Resolver site e listar bibliotecas e itens (P1) - MVP

**Objetivo**: resolver o site e listar bibliotecas e itens com paginação completa.

**Teste independente**: com fakes do SDK, resolver por ID e por hostname + caminho, listar bibliotecas e itens em 3 páginas e obter todos os itens.

### Testes

- [X] T013 [P] [US1] Testar em `tests/unit/test_sharepoint.py` `resolve_site` por ID e por `"{hostname}:/{caminho}"`, usando fakes dos builders do SDK, e o erro "não encontrado"
- [X] T014 [P] [US1] Testar em `tests/unit/test_sharepoint.py` a paginação por `@odata.nextLink` (mínimo de 3 páginas, SC-001) em `list_libraries` e `list_items`, pasta vazia e itens de arquivo e pasta com nome, caminho, tipo e tamanho
- [X] T015 [P] [US1] Testar em `tests/unit/test_sharepoint.py` que nenhuma função chama endpoints de busca (`get_all_sites`, `search_with_q`, `sites?search=`)

### Implementação

- [X] T016 [US1] Implementar em `src/sharepoint_files/sharepoint.py` o auxiliar privado de paginação que lê `value` e segue `odata_next_link` com `with_url(next_link).get()` até acabar
- [X] T017 [US1] Implementar `resolve_site` (por `site_id` ou `"{hostname}:/{site_path}"`, via `by_site_id`) e `list_libraries` (`sites/{id}/drives`) em `src/sharepoint_files/sharepoint.py`
- [X] T018 [US1] Implementar `list_items(client, drive_id, folder="")` (`children`, raiz via item `root`) em `src/sharepoint_files/sharepoint.py`, mapeando para `Item`
- [X] T019 [US1] Implementar em `src/sharepoint_files/cli.py` o `main()` (e criar `src/sharepoint_files/__main__.py` chamando `cli.main()`) com `argparse`, o carregamento da configuração, as opções de site e os subcomandos `site`, `libraries` e `ls` conforme contracts/cli.md (códigos de saída 0, 1 e 2; `asyncio.run`)
- [X] T020 [P] [US1] Testar em `tests/unit/test_cli.py` os subcomandos `site`, `libraries` e `ls` (saída e códigos de saída) com o cliente simulado

**Ponto de controle**: `uv run python -m sharepoint_files ls` funciona contra o site de teste (validação manual, quickstart.md).

---

## Fase 5: História 2 - Localizar arquivos por nome ou caminho (P2)

**Objetivo**: localizar dentro de uma biblioteca ou pasta, sem busca ampla.

**Teste independente**: nome parcial e caminho exato retornam só os correspondentes; sem correspondência devolve vazio sem erro.

### Testes

- [X] T021 [P] [US2] Testar em `tests/unit/test_sharepoint.py` `find_items`: nome parcial sem diferenciar maiúsculas de minúsculas, entrada em subpastas, caminho exato existente e inexistente (vazio, sem erro), escopo limitado à pasta informada
- [X] T022 [P] [US2] Testar em `tests/unit/test_cli.py` o subcomando `find` ("nenhum arquivo encontrado" com código 0 quando vazio)

### Implementação

- [X] T023 [US2] Implementar `find_items(client, drive_id, folder="", name=None, path=None)` em `src/sharepoint_files/sharepoint.py`: por nome percorre `children` recursivamente no escopo; por caminho usa acesso direto `root:/{caminho}`; trata 404 como vazio; exige exatamente um entre `name` e `path`
- [X] T024 [US2] Adicionar o subcomando `find` em `src/sharepoint_files/cli.py` conforme contracts/cli.md

---

## Fase 6: História 3 - Baixar poucos arquivos em lote com segurança (P3)

**Objetivo**: download sequencial, seguro e com relatório.

**Teste independente**: lote com arquivos novos, existentes, inválidos e com falha produz o relatório correto sem perder o que foi concluído.

### Testes

- [X] T025 [P] [US3] Testar em `tests/unit/test_downloads.py` a segurança de caminhos (SC-002): `..`, caminho absoluto, nome vazio, link simbólico para fora; nada gravado fora do diretório; nomes com caracteres especiais (espaços, acentos, `:`, `*`, `?`, `\`): válidos no SharePoint e no sistema local são gravados como estão, os demais são recusados com `GraphToolError(caminho inválido)`, sem normalização silenciosa
- [X] T026 [P] [US3] Testar em `tests/unit/test_downloads.py` arquivo existente ignorado sem sobrescrita (conteúdo intacto, SC-004) e substituído com `overwrite=True`; dois itens do mesmo lote com o mesmo nome de destino: sem `overwrite`, o primeiro é baixado e o segundo é `skipped` com motivo "destino já usado neste lote"; com `overwrite`, o segundo substitui o primeiro e ambos aparecem no relatório
- [X] T027 [P] [US3] Testar em `tests/unit/test_downloads.py` falhas parciais (SC-003): erro HTTP, timeout, pasta, arquivo acima de 100 MB, arquivo sem `size` informado, caminho inexistente e caminho de pasta (via `resolve_requests`) e lote acima de 20 itens recusado antes de baixar; os itens concluídos permanecem e o relatório classifica cada um
- [X] T028 [P] [US3] Testar em `tests/unit/test_downloads.py` a gravação atômica (SC-005): falha no meio da gravação não deixa arquivo final nem temporário; a ordem sequencial é preservada
- [X] T029 [P] [US3] Testar em `tests/unit/test_downloads.py` que o relatório e as mensagens nunca contêm URL pré-autenticada, token ou segredo (SC-006)

### Implementação

- [X] T030 [US3] Implementar em `src/sharepoint_files/downloads.py` o auxiliar de validação de destino: `(base / nome).resolve()` deve satisfazer `is_relative_to(base.resolve())`; recusar caminho absoluto, `..` e nome vazio como `GraphToolError(caminho inválido)`
- [X] T031 [US3] Implementar em `src/sharepoint_files/downloads.py` a gravação atômica: arquivo temporário em `tempfile.NamedTemporaryFile(delete=False, dir=destino)` seguido de `os.replace`, removendo o temporário em qualquer falha
- [X] T032 [US3] Implementar `download_files(client, requests, dest, overwrite=False)` em `src/sharepoint_files/downloads.py`: no máximo 20 itens, sequencial; por item valida tipo arquivo e tamanho informado e <= 100 MB (ausente conta como falha), ignora existente sem `overwrite`, baixa via `content.get()`, converte exceções em falha individual e nunca levanta por falha de item
- [X] T033 [US3] Implementar em `src/sharepoint_files/downloads.py` `resolve_requests(client, drive_id, paths) -> list[DownloadRequest | DownloadResult]`: para cada `CAMINHO`, chamar `find_items(path=...)`; não encontrado ou pasta vira `DownloadResult` com status `failed` (motivo "não encontrado" ou "é uma pasta"); `DownloadRequest.name` é o nome do item
- [X] T034 [US3] Adicionar o subcomando `download` em `src/sharepoint_files/cli.py` (`--library`, `--dest`, `--overwrite`, `CAMINHO...` resolvidos com `resolve_requests`; destino padrão `DOWNLOAD_DIR`), incluindo no relatório as falhas de resolução e imprimindo o relatório por item e totais; código 1 se houver falha, após processar todo o lote
- [X] T035 [P] [US3] Testar em `tests/unit/test_cli.py` o subcomando `download` (relatório, `--overwrite`, código de saída com falhas)

---

## Fase 7: Polimento e transversais

- [X] T036 [P] Criar `tests/integration/test_sharepoint_live.py` com o marcador `integration`: lê `.env` local, resolve o site, lista bibliotecas e baixa um arquivo; ignorado sem credenciais e fora da suíte padrão
- [X] T037 [P] Atualizar `README.md` com uso da CLI, variáveis de configuração, a concessão Sites.Selected e como executar os testes de integração
- [X] T038 Executar `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` e `uv run pytest` e `uv run pre-commit run --all-files`, e corrigir violações (complexidade máx. 10)
- [X] T039 Revisar o código conforme AGENTS.md (legibilidade, responsabilidades, duplicação, ausência de camadas desnecessárias e de escrita no SharePoint) e validar localmente os comandos da CLI e os testes descritos em quickstart.md
- [ ] T040 PENDENTE: executar o fluxo ponta a ponta de `specs/001-sharepoint-file-tool/quickstart.md` contra um site real; a última tentativa falhou com HTTP 400 porque o tenant não tem licença SharePoint Online. Requer tenant licenciado, hostname/caminho válidos e concessão `Sites.Selected` de leitura; o teste de token T041 não substitui esta validação
- [X] T041 Adicionar e executar `tests/integration/test_auth_connection.py` para obter um token Graph app-only sem exigir site SharePoint, sem imprimir o token e fechando a credencial; valida somente autenticação, não acesso ao SharePoint

---

## Dependências e ordem de execução

- Setup (Fase 1) antes de tudo; Fundação (Fase 2) bloqueia as histórias.
- US4 (Fase 3) antes de US1 (Fase 4); US2 e US3 dependem de US4 e de `Item`/`list_items` (US1) apenas para o CLI; `find_items` e `download_files` podem começar depois de T016.
- US2 e US3 são independentes entre si, exceto T033 (`resolve_requests`), que usa `find_items` (T023); o resto de US3 não depende de US2.
- Em cada história, os testes são escritos antes e devem falhar antes da implementação.
- Conflito de arquivo: tarefas que editam o mesmo arquivo (`cli.py`, `sharepoint.py`, `downloads.py`) não são paralelas entre si.

## Oportunidades de paralelismo

- Fase 1: T003 e T004.
- Fase 2: T006 e T007.
- US4: T008 e T009. US1: T013, T014, T015 e T020. US2: T021 e T022. US3: T025 a T029 e T035.
- Depois da Fase 3, US2 e US3 podem ser feitas em paralelo por pessoas diferentes.
- Fase 7: T036 e T037.

## Estratégia de implementação

1. **MVP**: Fases 1 a 4 (US4 + US1): configuração, site, bibliotecas e listagem com paginação. Valide com o site de teste.
2. Adicionar US2 (localizar) e validar.
3. Adicionar US3 (download) e validar.
4. Concluir com a Fase 7 e as verificações de qualidade.
