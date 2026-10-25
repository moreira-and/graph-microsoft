# Tasks: Download para volume Databricks

**Input**: Design documents from `specs/002-databricks-volume-download/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/download-cli.md`, `quickstart.md`

**Organization**: Tasks are grouped by the only user story in the specification. Tests are included because the specification defines independent test scenarios and measurable test outcomes.

## Phase 1: Setup

**Purpose**: The repository already has the Python package, dependency management, test framework, and quality tools required by this feature. No project initialization or new dependency is needed.

## Phase 2: Foundational

**Purpose**: There is no shared infrastructure prerequisite; all changes belong to the independently testable Databricks volume download story.

## Phase 3: User Story 1 - Gravar downloads no volume do Job (Priority: P1) 🎯 MVP

**Goal**: Permitir ao operador selecionar um volume Unity Catalog, gravar nele os arquivos solicitados, sobrescrever arquivos existentes e preservar o modo local atual.

**Independent Test**: Em testes unitários, selecionar um destino de volume e confirmar gravação, sobrescrita, rejeição de nomes duplicados antes de gravar os conflitantes, falhas explícitas sem fallback local e compatibilidade do destino local. Em um Job Databricks configurado, confirmar o conteúdo no volume e uma segunda execução com conteúdo atualizado.

### Tests for User Story 1

- [X] T001 [P] [US1] Add CLI tests for `--volume`, mutual exclusion with `--dest`, volume plus `--overwrite` rejection, and unchanged local destination behavior in `tests/unit/test_cli.py`
- [X] T002 [P] [US1] Add download tests for sequential volume writes, replacement, existing 20-file and 100-MB limits, write errors, and preserving an existing file when the SharePoint fetch fails before writing in `tests/unit/test_downloads.py`
- [X] T003 [US1] Add download tests proving all same-name requests from different source paths fail before any conflicting write while non-conflicting items complete in `tests/unit/test_downloads.py`

### Implementation for User Story 1

- [X] T004 [US1] Extend `DownloadRequest` with the requested source path and preflight volume batches so every request sharing a destination name is reported as a conflict before any conflicting item is written in `src/sharepoint_files/downloads.py`
- [X] T005 [US1] Add volume destination validation for exactly three non-empty `catalog.schema.volume` components and resolve the root to `/Volumes/<catalog>/<schema>/<volume>` without creating the volume or falling back locally in `src/sharepoint_files/downloads.py`
- [X] T006 [US1] Write fully fetched file contents sequentially to the volume target, retain the existing 20-file and 100-MB limits, overwrite existing targets by default, and report write failures while documenting that a started write may leave an incomplete target in `src/sharepoint_files/downloads.py`
- [X] T007 [US1] Add the `--volume CATALOG.SCHEMA.VOLUME` option, reject simultaneous local and volume destinations and `--overwrite` with volume mode, reuse existing SharePoint resolution and permissions, dispatch to the selected destination, and retain existing local defaults in `src/sharepoint_files/cli.py`
- [X] T008 [P] [US1] Add an opt-in Databricks integration test configured by `DATABRICKS_TEST_VOLUME`, `DATABRICKS_TEST_SHAREPOINT_LIBRARY_ID`, and `DATABRICKS_TEST_SHAREPOINT_FILE_PATH`; use an isolated test volume and a dedicated uniquely named SharePoint fixture, and clean up only a target created by the test in `tests/integration/test_databricks_volume.py`
- [X] T009 [P] [US1] Document volume Job prerequisites, `--volume` usage, automatic overwrite, rejection of `--overwrite` in volume mode, failure atomicity limitation, and unchanged local usage in `README.md`

**Checkpoint**: User Story 1 is independently testable with the unit suite and can be validated against a configured Databricks Job using `tests/integration/test_databricks_volume.py`.

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Run repository quality checks after the feature tasks are complete.

- [X] T010 Run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, and `uv run mypy` across `tests/` and `src/sharepoint_files/`; resolve failures caused by this feature

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks; the existing project environment is sufficient.
- **Foundational (Phase 2)**: No tasks; no shared infrastructure is needed.
- **User Story 1 (Phase 3)**: Starts immediately; it is the only story.
- **Polish (Phase 4)**: Depends on all User Story 1 implementation and test tasks.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on another user story.

### Within User Story 1

- T001, T002, T008 and T009 can be implemented in parallel because they modify separate files.
- T003 depends on T002 because it extends the same test file.
- T004 depends on T003 and modifies `downloads.py`.
- T005 depends on T002 and modifies `downloads.py`; execute it after T004 to avoid overlapping edits.
- T006 depends on T002 and T005; execute it after T005 in `downloads.py`.
- T007 depends on T001, T005 and T006; it integrates the tested CLI contract with the volume destination implementation.
- T010 runs after T001-T009. Live execution of T008 additionally requires the dedicated Databricks test resources described in that task.

### Parallel Opportunities

```text
T001 [P] with T002 [P], T008 [P] and T009 [P] (separate files)
T003 after T002
T004 after T003
T005 after T002 and T004
T006 after T005
T007 after T001, T005 and T006
```

## Implementation Strategy

### MVP First

1. Complete T001-T007 to implement and unit-test volume selection, preflight conflict handling, writes, and local-mode compatibility.
2. Complete T009 so Job operators have accurate setup and failure guidance.
3. Validate the P1 independent test with `uv run pytest`.
4. Run the configured Databricks integration test only when a dedicated test volume and Databricks Job are available.

### Incremental Delivery

1. Verify the destination selection and volume write behavior with unit tests.
2. Add collision preflight and verify non-conflicting items continue.
3. Run the opt-in test in a Databricks workspace to confirm the Unity Catalog volume path and permissions.
4. Run all repository checks in T010; preserve local behavior throughout.
