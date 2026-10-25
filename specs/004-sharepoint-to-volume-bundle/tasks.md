# Tasks: Transferência direta SharePoint → Volume via bundle

**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/job-contract.md](./contracts/job-contract.md)

**Tests**: Incluídos (a constituição exige validação; o plano prevê testes unitários).

**Formato**: `- [ ] ID [P] [US] Descrição com caminho`

## Phase 1: Setup

- [x] T001 Confirmar baseline verde antes de alterar: `uv run ruff check . && uv run mypy src && uv run pytest tests/unit`

## Phase 2: Foundational

Nenhuma tarefa bloqueante; o fluxo (CLI em modo volume, Job e volume) já existe.

## Phase 3: User Story 1 - Deploy e Job copiam SharePoint para o volume (P1) 🎯 MVP

**Objetivo**: arquivos da lista explícita chegam ao volume, idênticos, sobrescrevendo atomicamente (RF-001a, RF-003, RF-004, RF-005a, RF-008).

**Teste independente**: deploy em `dev`, executar o Job e comparar o arquivo no volume com a origem; reexecutar sem deixar `.part`.

- [x] T002 [US1] Em `tests/unit/test_downloads.py`, adicionar testes: (a) falha durante a escrita no volume mantém o conteúdo anterior e não deixa arquivo `.part`; (b) após sucesso, o arquivo no volume tem exatamente os mesmos bytes da origem, inclusive ao sobrescrever (estende `test_volume_download_writes_and_overwrites_sequentially`)
- [x] T002a [P] [US1] Em `tests/unit/test_downloads.py`, adicionar teste: ao baixar `["docs/a.txt"]` com outros arquivos presentes na biblioteca fake, somente `a.txt` é resolvido e gravado no volume
- [x] T003 [US1] Em `src/sharepoint_files/downloads.py`, fazer `_download_volume_one` gravar com `_write_atomic(target, content)` em vez de `target.open("wb")`, mantendo o tratamento de `OSError` existente
- [x] T004 [P] [US1] (decisão: os valores por target permanecem fora do repositório, conforme `docs/secret_config/credential-setup.md`; o bundle declara as variáveis sem defaults) Em `databricks.yml`, definir em `targets.dev.variables` e `targets.test.variables` os valores próprios de `download_parameters` (lista explícita de caminhos, `--volume`, biblioteca), `sharepoint_site_id`, `volume_*`, `azure_*`, `job_service_principal_name` e `client_secret_reference` (`{{secrets/sharepoint-<target>/azure-client-secret}}`). Valores específicos do ambiente que não constam no repositório (IDs, biblioteca, caminhos) devem ser fornecidos pelo usuário; não inventar nem commitar segredos
- [x] T005 [P] [US1] Em `docs/secret_config/credential-setup.md`, documentar que apenas a lista explícita de caminhos é transferida e que arquivos existentes são sobrescritos
- [ ] T006 [US1] (manual, exige workspace Databricks e credenciais reais) Executar `databricks bundle validate -t dev` e `-t test`; depois seguir os passos 3–6 e 8 de [quickstart.md](./quickstart.md) (inclui confirmar que `os.replace` funciona em `/Volumes`; se falhar, registrar em `research.md` e ajustar T003)

**Checkpoint**: Job entrega arquivos idênticos e reexecução sobrescreve sem parciais.

## Phase 4: User Story 2 - Falhas claras sem vazar segredo (P2)

**Objetivo**: erro com causa e item, exit 1, sem arquivo parcial, sem segredo (RF-005, RF-006, RF-007).

**Teste independente**: caminho inexistente e credencial inválida falham com mensagem específica e sem o segredo na saída.

- [x] T007 [P] [US2] Em `tests/unit/test_cli.py`, adicionar teste que força erro de autenticação com um `AZURE_CLIENT_SECRET` sentinela e verifica que a categoria é `ErrorCategory.AUTHENTICATION` e que o valor não aparece em stdout nem stderr
- [x] T008 [P] [US2] Em `tests/unit/test_downloads.py`, adicionar teste: caminho de origem inexistente gera falha (`ErrorCategory.NOT_FOUND`) indicando o caminho e nada é gravado no volume
- [x] T009 [US2] (não necessária: T007 passou sem alteração) Se T007 falhar, corrigir a mensagem de erro em `src/sharepoint_files/client.py` ou `src/sharepoint_files/cli.py` para omitir o valor secreto
- [ ] T010 [US2] (manual, exige workspace Databricks e credenciais reais) Executar os passos de falha do [quickstart.md](./quickstart.md) (passo 7) no workspace `dev`

**Checkpoint**: falhas atribuídas à causa correta, sem vazamento.

## Phase 5: Polish e remoções (RF-009, CS-005)

- [x] T011 [P] Remover `resources/volume_smoke_job.yml`
- [x] T012 [P] Remover `notebooks/test_volume.py` (e o diretório `notebooks/` se ficar vazio)
- [x] T013 Buscar referências restantes (`grep -rn "volume_smoke\|test_volume\|smoke" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=specs .`) e atualizar `README.md`/docs se houver, além da premissa "Ainda não removido" em `spec.md`
- [x] T014 Rodar `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest tests/unit` e `databricks bundle validate -t dev`; confirmar que a saída por arquivo (`status\tnome\tmotivo`) continua coberta por `tests/unit/test_cli.py`; registrar verificações não aplicáveis
- [x] T015 Revisar a mudança quanto a legibilidade, duplicação e compatibilidade com a arquitetura (constituição, princípio V)

## Dependências

- T001 → tudo.
- US1: T002 → T003 → T006; T002a, T004 e T005 em paralelo; T006 depende de T003 e T004.
- US2: independente de US1 nos testes (T007, T008); T009 depende de T007; T010 depende de T006.
- Polish: T011–T012 podem ocorrer após T001 (independentes); T013–T015 por último.

## Paralelismo

- T002a ‖ T004 ‖ T005; T007 ‖ T008; T011 ‖ T012.

## Estratégia

MVP = US1 (T001–T006): corrige a atomicidade, fixa a configuração por target e valida o deploy. Depois US2 (garantias de falha e segredo) e, por fim, as remoções.

## Phase 6: Remoção do legado local (RF-009)

- [x] T016 Remover o modo de download local: `--dest`, `--overwrite`, `DOWNLOAD_DIR`, `download_files`, `download_paths`, `_download_one` e `Status.SKIPPED` (`src/sharepoint_files/`, `.env.example`, `README.md`, testes unitários e de integração); `--volume` passa a ser obrigatório
