# Plano de Implementação: Ferramenta de arquivos do SharePoint

**Branch**: `001-sharepoint-file-tool` | **Data**: 2026-10-24 | **Spec**: [spec.md](spec.md)

## Resumo

Biblioteca Python com CLI mínima para resolver um site do SharePoint, listar bibliotecas e itens, localizar arquivos dentro de uma biblioteca ou pasta e baixar até 20 arquivos em sequência. Usa `msgraph-sdk` com `ClientSecretCredential` (app-only, Sites.Selected, somente leitura). A paginação segue `@odata.nextLink`. O retry de 429 fica a cargo do middleware do SDK, que respeita `Retry-After`. Os downloads são gravados em arquivo temporário e renomeados. Decisões detalhadas em [research.md](research.md).

## Contexto Técnico

**Linguagem/Versão**: Python >=3.12 (já em `pyproject.toml`)

**Dependências principais**: `msgraph-sdk==1.65.0`, `azure-identity==1.26.0` (já declaradas); `httpx` passa a ser declarada explicitamente (já é transitiva do SDK) para configurar timeouts

**Armazenamento**: arquivos locais em diretório de destino informado

**Testes**: pytest; unitários com fakes das respostas do SDK, sem rede; integração opt-in com marcador `integration` e `.env` local

**Plataforma alvo**: Linux, macOS e Windows com Python 3.12+

**Tipo de projeto**: biblioteca com CLI mínima (`python -m sharepoint_files`)

**Metas de desempenho**: downloads sequenciais; resolver, listar e baixar um arquivo em menos de 2 minutos (SC-008)

**Restrições**: apenas leitura; sem endpoints de busca do Graph; sem registrar tokens, segredos ou URLs pré-autenticadas; timeouts de 30 s (listagem) e 120 s (download)

**Escala/Escopo**: lote de até 20 arquivos, até 100 MB cada

## Verificação da Constituição

| Princípio | Avaliação |
|---|---|
| I. Qualidade e simplicidade | Aprovado: funções simples, 4 módulos coesos, apenas dataclasses de dados. |
| II. Preservar a arquitetura | Aprovado: mantém uv, Ruff (complexidade máx. 10), mypy estrito, pytest e pre-commit; sem repositories, factories ou interfaces. |
| III. Layout Spec Kit | Aprovado: artefatos em `specs/001-sharepoint-file-tool/`. |
| IV. Especificação explica a intenção | Aprovado: critérios observáveis na spec. |
| V. Validar e revisar | Aprovado: tarefas incluem Ruff, mypy e pytest. O AGENTS.md exige essas verificações na CI e o repositório ainda não tem `.github/workflows`, então o plano inclui um workflow mínimo. |

Reavaliação pós-design: sem violações; Complexity Tracking não é necessário.

## Estrutura do Projeto

### Documentação

```text
specs/001-sharepoint-file-tool/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli.md
└── tasks.md          # criado por /speckit-tasks
```

### Código-fonte

```text
src/sharepoint_files/
├── __init__.py
├── __main__.py       # chama cli.main()
├── client.py         # configuração do ambiente, cliente Graph, GraphToolError e tradução de erros HTTP/timeout
├── sharepoint.py     # resolver site, listar bibliotecas e itens, localizar, paginação
├── downloads.py      # validação de destino, gravação temporária + rename, lote e relatório
└── cli.py            # subcomandos mínimos (argparse)

tests/
├── test_graph_dependencies.py   # existente
├── unit/
│   ├── test_client.py
│   ├── test_sharepoint.py
│   ├── test_downloads.py
│   └── test_cli.py
└── integration/
    └── test_sharepoint_live.py  # marcador integration, ignorado por padrão

.github/workflows/ci.yml          # uv sync --locked, ruff check, ruff format --check, mypy, pytest
```

**Decisão de estrutura**: layout `src/` com um único pacote, instalado em modo editável pelo uv via Hatchling para que `uv run python -m sharepoint_files` funcione após `uv sync`. Exige em `pyproject.toml` `pythonpath = ["src"]` e `addopts = "-m 'not integration'"` no pytest, além de `mypy_path = "src"`.

## Complexity Tracking

Sem violações a justificar.
