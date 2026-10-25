# Implementation Plan: Configuração do Job via Bundle

**Branch**: `003-bundle-job-config` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-bundle-job-config/spec.md`

## Summary

Adicionar um Databricks Declarative Automation Bundle que empacota e publica a CLI Python existente como wheel e define um Job para executá-la. O target do bundle fornece valores não secretos específicos do ambiente; o client secret é resolvido de um secret scope Databricks e injetado somente no ambiente de execução. A autenticação Graph, seleção de arquivos e gravação no volume continuam no processo e fluxo existentes.

## Technical Context

**Language/Version**: Python 3.12 ou superior; YAML para a configuração do bundle.

**Primary Dependencies**: Dependências Python já declaradas no `pyproject.toml` (`azure-identity`, `httpx`, `msgraph-sdk`); Databricks CLI e Declarative Automation Bundles para validar, implantar e executar o Job.

**Storage**: Unity Catalog volume gerenciado pelo bundle para os arquivos baixados; catálogo e schema devem existir previamente. Secret scope Databricks (ou scope respaldado por Azure Key Vault compatível com o workspace) para o client secret. Nenhum armazenamento novo de metadados.

**Testing**: pytest, Ruff, mypy e `uv build` localmente; `databricks bundle validate` para validação estática; deploy e execução ponta a ponta opt-in em workspace Databricks com app SharePoint, secret scope e volume de teste.

**Target Platform**: Databricks Job cluster habilitado para Unity Catalog e volumes, com runtime que suporte Python 3.12 ou superior; targets não produtivos `dev` e `test` isolados. Serverless e implantação em produção não fazem parte desta primeira configuração.

**Project Type**: Pacote Python com CLI existente, empacotado como wheel e invocado por Job Databricks.

**Performance Goals**: Não introduzir metas de desempenho ou concorrência. Preservar a execução sequencial e os limites existentes de downloads.

**Constraints**: Nunca incluir o valor do client secret em arquivos do bundle, parâmetros de Job, código, argumentos de linha de comando ou logs. Usar secret reference Databricks em variável de ambiente do Job cluster. Cada target aponta para valores e destino do seu próprio ambiente. O catálogo e schema devem existir previamente; o bundle cria o volume gerenciado e concede acesso nele à identidade do Job. Não alterar os fluxos local ou de download.

**Scale/Scope**: Um Job e seus targets configurados para executar a CLI existente com biblioteca, volume e caminhos de SharePoint definidos na configuração de cada ambiente. O bundle gerencia o volume de destino, mas não cria catálogo ou schema. Alterar caminhos exige atualização e novo deploy do bundle; parâmetros por execução estão fora do escopo. O provisionamento de app registration, secret scopes, permissões nos objetos pai e demais acessos permanece responsabilidade dos administradores dos respectivos serviços.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality and Simplicity**: PASS — empacotar a CLI existente e configurar um Job, sem novo cliente Graph ou camada de armazenamento.
- **Preserve the Project Architecture**: PASS — manter configuração e autenticação no pacote atual; o bundle é configuração de implantação que delega à CLI.
- **Spec Kit Project Layout**: PASS — artefatos da funcionalidade permanecem em `specs/003-bundle-job-config/`; o bundle de implantação fica na raiz do projeto, fora de `.specify/`.
- **Specifications Explain Intent**: PASS — [spec.md](spec.md) define a necessidade de implantação reproduzível por ambiente, proteção de credenciais e persistência no destino configurado.
- **Validate and Review Changes**: PASS — validar wheel, suíte e ferramentas atuais, validação do bundle e execução real opt-in sem segredos em saída.
- **Gates**: Nenhuma violação constitucional identificada.

## Project Structure

### Documentation (this feature)

```text
specs/003-bundle-job-config/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── job-config.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # Phase 2; não criado por /speckit-plan
```

### Source Code (repository root)

```text
databricks.yml                # Bundle, targets e variáveis de ambiente
resources/
├── sharepoint_job.yml        # Definição do Job e tarefa Python wheel
└── sharepoint_volume.yml     # Volume Unity Catalog e grants da identidade do Job
pyproject.toml                # Entry point da CLI e configuração do wheel
src/sharepoint_files/
├── __main__.py               # Execução atual via python -m
└── cli.py                    # Entry point reaproveitado pelo Job e pela CLI local
docs/secret_config/
└── credential-setup.md       # Procedimento operacional para provisionar e referenciar segredos
tests/
├── unit/                     # Compatibilidade de entry point e configuração existente
└── integration/              # Execução Databricks opt-in já estabelecida
```

**Structure Decision**: Manter o pacote Python e testes existentes. Declarar o bundle e o Job na raiz e em `resources/`; definir um entry point de console para chamar a função `main` existente e permitir a execução do wheel pelo Job. O guia operacional existente é o ponto de referência para provisionar o secret scope e ACLs; não duplicar valores ou incluir segredos em arquivos versionados.

## Constitution Check (post-design)

- **Code Quality and Simplicity**: PASS — a tarefa chama a CLI existente; não duplica seleção SharePoint, autenticação ou gravação.
- **Preserve the Project Architecture**: PASS — o bundle apenas empacota e configura a execução; os destinos e autenticação continuam sob responsabilidade dos módulos existentes.
- **Validate and Review Changes**: PASS — quickstart combina verificações sem rede e validação opt-in no Databricks; alterações de entry point serão cobertas por testes focados.
- **Security**: PASS — `AZURE_CLIENT_SECRET` é uma referência Databricks resolvida em runtime; não é valor de variável do bundle nem parâmetro de tarefa.
- **Known operational prerequisite**: a identidade de implantação necessita criar o volume no schema configurado; a identidade que configura o compute deve poder resolver a referência de secret scope; a identidade de execução necessita acesso ao site SharePoint, privilégios no catálogo/schema e permissões de leitura/escrita no volume.
- **Gates**: Nenhuma violação constitucional identificada.

## Complexity Tracking

Não há violações da constituição que exijam exceção.
