# Implementation Plan: Transferência direta SharePoint → Volume via bundle

**Branch**: `004-sharepoint-to-volume-bundle` | **Date**: 2026-10-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-sharepoint-to-volume-bundle/spec.md`

## Summary

O fluxo já existe quase completo (CLI `sharepoint-files download --volume`, Job `sharepoint-download` e volume gerenciado no bundle). O plano é fechar as lacunas contra a spec, sem novas camadas:

1. Tornar a gravação no volume **atômica** e **sobrescrevendo** (RF-005a, RF-006): hoje `_download_volume_one` abre o destino com `open("wb")` e deixa arquivo parcial em falha.
2. Garantir que a **lista explícita de caminhos** por target (RF-001a) e a configuração/segredo por target (RF-008) estejam em `download_parameters` e documentadas.
3. Garantir que nenhum segredo apareça em saída ou erro (RF-007) com teste.
4. **Remover** o Job de teste de escrita e o notebook (RF-009, CS-005).

## Technical Context

**Language/Version**: Python 3.12+ (Databricks Runtime com Unity Catalog volumes)
**Primary Dependencies**: msgraph-sdk (já em uso); Databricks Asset Bundles (`databricks.yml`, `resources/`)
**Storage**: Unity Catalog managed volume (`/Volumes/<catalog>/<schema>/<volume>`)
**Testing**: pytest (unit com fakes em `tests/unit/fakes.py`; integração opcional em `tests/integration/`), ruff e mypy via `uv`
**Target Platform**: Job Databricks em cluster `SINGLE_USER` executando como service principal; targets `dev` e `test`
**Project Type**: CLI/biblioteca empacotada como wheel e implantada por bundle
**Performance Goals**: sem meta nova; mantém limites existentes (100 MB por arquivo, `MAX_BATCH`)
**Constraints**: nenhum segredo em parâmetros, logs ou erros; sem arquivo parcial no volume
**Scale/Scope**: lista explícita de arquivos por execução

## Constitution Check

- I. Simplicidade: mudança localizada em `downloads.py`, reutilizando `_write_atomic`. PASS
- II. Preservar arquitetura: sem novas camadas ou dependências. PASS
- III. Layout Spec Kit: artefatos em `specs/004-...`. PASS
- IV. Spec explica intenção: spec com critérios observáveis. PASS
- V. Validar e revisar: testes unitários, ruff, mypy e `databricks bundle validate`. PASS

Pós-design: sem violações; Complexity Tracking não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/004-sharepoint-to-volume-bundle/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/job-contract.md
└── tasks.md   # /speckit-tasks
```

### Source Code (repository root)

```text
src/sharepoint_files/             # gravação atômica no volume; modo local removido (T016)
databricks.yml                         # variáveis/targets (lista de caminhos por target)
resources/sharepoint_job.yml           # Job de transferência (mantido)
resources/sharepoint_volume.yml        # volume gerenciado (mantido)
resources/volume_smoke_job.yml         # REMOVIDO
notebooks/test_volume.py               # REMOVIDO
tests/unit/test_downloads.py           # novos testes; ajustar referência a "smoke"
docs/secret_config/credential-setup.md # alinhar à lista explícita de caminhos
```

**Structure Decision**: projeto único existente; sem novos módulos.

## Complexity Tracking

Sem violações.
