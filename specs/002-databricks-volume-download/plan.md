# Implementation Plan: Download para volume Databricks

**Branch**: `002-databricks-volume-download` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-databricks-volume-download/spec.md`

## Summary

Adicionar ao fluxo de download uma opção de destino em volume Unity Catalog para Jobs Databricks. O destino será resolvido como `/Volumes/<catalog>/<schema>/<volume>`, validado e usado para gravar sequencialmente o conteúdo completo já recebido do SharePoint. O modo local permanece inalterado. A gravação padrão em volume sobrescreve arquivos e pode deixar um arquivo parcial se a gravação falhar; o projeto não dependerá de atomicidade, renomeação no volume ou Files API Beta.

## Technical Context

**Language/Version**: Python 3.12 ou superior, conforme `pyproject.toml`.

**Primary Dependencies**: Dependências existentes (`msgraph-sdk`, `azure-identity`, `httpx`); sem nova dependência de runtime prevista.

**Storage**: Arquivos locais no modo atual ou arquivos na raiz de um volume Unity Catalog em `/Volumes/<catalog>/<schema>/<volume>`.

**Testing**: pytest sem rede para testes padrão; cenários com Job/volume real serão opt-in e exigirão workspace Databricks configurado.

**Target Platform**: Databricks Job em compute habilitado para Unity Catalog que suporte volumes, Python 3.12 ou superior e acesso `USE CATALOG`, `USE SCHEMA` e `WRITE VOLUME`; modo local continua em plataformas suportadas atualmente.

**Project Type**: Pacote Python com biblioteca e CLI.

**Performance Goals**: Preservar download sequencial e limites existentes de até 20 arquivos por lote e 100 MB por arquivo; não há meta nova de latência.

**Constraints**: Somente escrita sequencial completa em arquivos do volume. Uma falha durante a escrita pode deixar incompleto um arquivo existente ou novo. Não criar o volume, não ampliar permissões SharePoint e não recorrer silenciosamente a destino local. Nomes repetidos no mesmo lote são rejeitados antes da gravação dos itens conflitantes. Sobrescrita no volume é automática; `--overwrite` é exclusivo do modo local e inválido com `--volume`.

**Scale/Scope**: Até 20 arquivos por lote, com tamanho máximo individual de 100 MB; gravação na raiz do volume com nome original.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality and Simplicity**: PASS — estender a configuração, CLI e módulo de downloads existentes; nenhuma abstração, camada ou dependência adicional é necessária.
- **Preserve the Project Architecture**: PASS — mudanças limitadas ao pacote atual e aos testes unitários/integrados existentes.
- **Spec Kit Project Layout**: PASS — documentação de feature fica em `specs/002-databricks-volume-download/`.
- **Specifications Explain Intent**: PASS — [spec.md](spec.md) descreve resultados observáveis e as limitações de sobrescrita.
- **Validate and Review Changes**: PASS — planejar testes focados, suite pytest e verificações Ruff/mypy já configuradas no projeto.
- **Gates**: Nenhuma violação constitucional identificada.

## Project Structure

### Documentation (this feature)

```text
specs/002-databricks-volume-download/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── download-cli.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # Phase 2; não criado por /speckit-plan
```

### Source Code (repository root)

```text
src/sharepoint_files/
├── client.py                # Configuração do destino default de download
├── cli.py                   # Opção do volume e seleção do destino
└── downloads.py             # Validação, conflitos e gravação sequencial

tests/
├── unit/
│   ├── test_client.py       # Configuração/validação do volume
│   ├── test_cli.py          # Contrato da CLI e compatibilidade local
│   └── test_downloads.py    # Escrita, sobrescrita e nomes conflitantes
└── integration/
    └── test_databricks_volume.py  # Opt-in, requer Databricks Job e volume reais
```

**Structure Decision**: Manter o projeto Python único. Reutilizar `Config`, `download_paths` e o handler da CLI existentes. A escrita para volume será um destino selecionado no fluxo já existente, não uma segunda implementação de download ou um novo pacote.

## Constitution Check (post-design)

- **Code Quality and Simplicity**: PASS — não adicionar SDK Databricks, camada de storage genérica ou mecanismo não suportado de troca atômica.
- **Preserve the Project Architecture**: PASS — extensão coesa dos módulos de configuração, CLI e downloads; modo local conserva o comportamento atual.
- **Validate and Review Changes**: PASS — quickstart define verificações locais sem rede e validação real opt-in no Databricks.
- **Known trade-off**: por decisão do usuário, falha durante escrita padrão pode deixar incompleto o arquivo alvo; esse comportamento ficará explícito nos requisitos e na documentação operacional.

## Complexity Tracking

Não há violações da constituição que exijam exceção.
