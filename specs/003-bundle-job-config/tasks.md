# Tasks: Configuração do Job via Bundle

**Input**: Design documents from `specs/003-bundle-job-config/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independently deliverable and verifiable increments.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with tasks touching different files and having no unmet dependencies
- **[Story]**: User story served by the task (US1, US2, US3)
- Every task description includes the concrete file path it changes or validates

## Phase 1: Setup

**Purpose**: Add the Declarative Automation Bundle entry points to the existing single-project repository.

- [X] T001 Create the bundle root configuration and define its project name and resource include in `databricks.yml`
- [X] T002 [P] Create the Job resource file and declare the initial SharePoint wheel task structure in `resources/sharepoint_job.yml`

## Phase 2: Foundational

**Purpose**: Make the existing Python CLI installable as a wheel command before wiring the bundle to invoke it.

- [X] T003 Add the `sharepoint-files` console entry point targeting `sharepoint_files.cli:main` in `pyproject.toml`, preserving the existing `python -m sharepoint_files` entry

**Checkpoint**: The package exposes an installable CLI entry point; user-story bundle configuration can now use it.

## Phase 3: User Story 1 - Implantar e executar o Job (Priority: P1) 🎯 MVP

**Goal**: Deploy and run the existing SharePoint download CLI through the bundle without environment-specific source edits.

**Independent Test**: With a valid test workspace, secret reference, SharePoint site, library and writable volume, run `databricks bundle validate --target dev`, deploy and run the Job; confirm a downloaded file is present in the configured volume.

### Implementation for User Story 1

- [X] T004 [US1] Add a focused packaging test that verifies `sharepoint-files` maps to `sharepoint_files.cli:main` in `tests/unit/test_bundle_entry_point.py`
- [X] T005 [US1] Configure the Job to install the built wheel and invoke `sharepoint-files download` with the configured library, volume and source paths in `resources/sharepoint_job.yml`
- [X] T006 [US1] Configure a Unity Catalog-compatible Job cluster, runtime, run identity, and Azure/SharePoint environment variables in `resources/sharepoint_job.yml`
- [X] T007 [US1] Configure required bundle variables and the `dev` target for workspace, identity, site, download arguments and secret reference in `databricks.yml`
- [X] T008 [US1] Ensure the Job task propagates the Python wheel command's nonzero exit status as a failed run in `resources/sharepoint_job.yml`

**Checkpoint**: A test target can deploy and execute the current downloader through the bundle and write to its configured volume.

## Phase 4: User Story 2 - Promover o Job entre ambientes (Priority: P2)

**Goal**: Reuse the same versioned bundle across environments while keeping each target's values, secret reference and destination isolated.

**Independent Test**: Validate and deploy the same bundle version to two configured non-production targets; confirm each target resolves its own secret reference and volume, with no client secret value in the bundle or Job parameters.

### Implementation for User Story 2

- [X] T009 [US2] Add the non-production `test` target alongside `dev`; both targets require distinct workspace, run identity, tenant, app, SharePoint, volume and secret reference values in `databricks.yml`
- [X] T010 [US2] Require environment-specific bundle variables without defaults so a target cannot silently fall back to another target's secret reference or volume in `databricks.yml`
- [X] T011 [US2] Keep `AZURE_CLIENT_SECRET` as a Databricks secret reference in each target's cluster environment and exclude it from Job parameters and task arguments in `resources/sharepoint_job.yml`

**Checkpoint**: The same bundle version can be deployed to isolated non-production targets without exposing or cross-using credentials and destinations.

## Phase 5: User Story 3 - Diagnosticar pré-requisitos ausentes (Priority: P3)

**Goal**: Give operators clear setup and failure guidance when configuration, credentials or permissions are missing.

**Independent Test**: Follow the operational guide in a test workspace and perform safe missing-reference or access-denied checks; confirm the Job fails without success-shaped output or secret disclosure.

### Implementation for User Story 3

- [X] T012 [US3] Document the bundle variables, target-specific secret reference, required secret scope ACLs, SharePoint grant, volume privileges and safe diagnostics in `docs/secret_config/credential-setup.md`
- [X] T013 [US3] Document how to validate, deploy and run the Job and confirm the output volume without printing secrets in `specs/003-bundle-job-config/quickstart.md`
- [X] T014 [US3] Link the operator credential guide from the Databricks Job and volume setup section in `README.md`

**Checkpoint**: An operator can prepare the test environment and diagnose missing configuration or access using documented steps that do not reveal secrets.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the bundle and package integration and review security and documentation consistency.

- [X] T015 Run `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` and `uv build` and record the results in `specs/003-bundle-job-config/quickstart.md`
- [ ] T016 Run `databricks bundle validate --target dev` with actual target values and test missing-secret/access-denied failures plus secret non-disclosure in a dedicated Databricks test workspace, using `specs/003-bundle-job-config/contracts/job-config.md` and `docs/secret_config/credential-setup.md`
- [X] T017 Declare a managed Unity Catalog volume with Job identity grants and prevent-destroy lifecycle in `resources/sharepoint_volume.yml`
- [X] T018 Add an independent serverless volume smoke-test Job that writes and verifies `test.txt` with UTC current time in `resources/volume_smoke_job.yml` and `notebooks/test_volume.py`
- [X] T019 Deploy and run the standalone serverless volume Job; verify `test.txt` contains the UTC execution timestamp in `workspace.default.sharepoint_files_test`

**T016 partially validated**: bundle validation passed with temporary
placeholder values, and the isolated serverless volume smoke-test Job was
deployed and run successfully. The SharePoint download Job was not deployed;
its actual target values and negative runtime scenarios remain to be validated.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; establishes the bundle and Job resource files.
- **Foundational (Phase 2)**: Depends on Setup; configures the Python wheel command that the Job invokes.
- **User Story 1 (Phase 3)**: Depends on Foundational; delivers the first deployable and runnable target.
- **User Story 2 (Phase 4)**: Depends on User Story 1; extends the same bundle and Job configuration with isolated target overrides.
- **User Story 3 (Phase 5)**: Depends on User Story 1 for accurate operational steps; documentation may be prepared in parallel with User Story 2 after the initial target contract stabilizes.
- **Polish (Phase 6)**: Depends on the desired user stories being complete and requires access to a valid Databricks test target for bundle validation.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Setup and Foundational; no dependency on another story.
- **User Story 2 (P2)**: Starts after User Story 1 because it extends the bundle targets and cluster configuration introduced by the MVP; it uses a second non-production target, not production.
- **User Story 3 (P3)**: Depends on User Story 1 for the final bundle configuration; independent of the target-isolation implementation in User Story 2 once the initial secret reference contract is stable.

### Within Each User Story

- Bundle root and Job resource files must exist before they can be configured.
- The console entry point must exist before the wheel task invokes it.
- Configure the initial target before adding environment-specific overrides.
- Document the final variable names and invocation contract after they stabilize.
- Run local package checks before relying on workspace validation.

### Parallel Opportunities

- T002 can run in parallel with T001 because it creates a separate resource file, provided both use the names established by the plan.
- T011 and T012 can be authored in parallel after T004–T006 stabilize the task's variables and arguments; T013 follows the guide update.
- The US2 target override work and US3 documentation work can proceed in parallel after US1 establishes the initial configuration contract, avoiding simultaneous edits to the same files.

## Parallel Example: User Story 1

```text
After T001 establishes bundle/resource names and T003 defines the console entry point:
Task: Configure Job wheel invocation and arguments in resources/sharepoint_job.yml (T005)
Task: Configure the initial target values in databricks.yml (T007)
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational phases.
2. Complete User Story 1 to package and deploy the CLI as a Job with one test target.
3. Validate and run the Job against a dedicated non-production SharePoint fixture and volume.
4. Confirm that files are written to the configured volume and the task reports failure for nonzero CLI results.

### Incremental Delivery

1. Deliver User Story 1 as the first runnable bundle target.
2. Add User Story 2 target isolation and verify each environment resolves only its own reference and destination.
3. Add User Story 3 operator guidance and verify safe failure diagnosis.
4. Run all local checks and final Databricks validation in the Polish phase.

## Notes

- The focused package entry-point test in `tests/unit/test_bundle_entry_point.py` protects the new wheel command while the existing `python -m sharepoint_files` invocation remains supported.
- `[P]` tasks touch separate files and have no unmet dependencies.
- Provisioning app registrations, secret scopes/values, workspace permissions and volumes is performed by the owning administrators and is not an automated bundle task.
