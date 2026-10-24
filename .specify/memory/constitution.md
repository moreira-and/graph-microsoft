# graph-microsoft Constitution

## Core Principles

### I. Code Quality and Simplicity

Follow Clean Code and SOLID where relevant. Keep functions, classes, and
modules cohesive, with clear responsibilities and expressive names. Prefer
simple control flow and high cohesion with low coupling. Avoid duplication,
long functions, complex conditionals, hidden side effects, and abstractions
without a concrete reason. Keep comments and docstrings concise and focused on
intent.

### II. Preserve the Project Architecture

Preserve established project conventions and architecture unless a technical
reason justifies a change. Do not introduce design patterns, interfaces,
classes, layers, dependencies, or an application stack without a concrete need.
Choose the simplest maintainable solution that meets the requirements.

### III. Spec Kit Project Layout

Keep shared Spec Kit project artifacts in the repository root: configuration,
templates, scripts, and the constitution belong under `.specify/`; feature
specifications belong under `specs/`; GitHub Copilot skills belong under
`.github/skills/speckit-<command>/SKILL.md`. Install the `specify` CLI
separately with `uv`; do not vendor the CLI or create a nested Spec Kit project.
This layout follows the upstream guidance for [existing projects](https://github.com/github/spec-kit/blob/main/docs/guides/existing-projects.md)
and the [Copilot integration](https://github.com/github/spec-kit/blob/main/docs/integrations/copilot.md).

### IV. Specifications Explain Intent

Every feature specification MUST state what outcome is requested and why it is
needed. Include observable acceptance criteria so planning and implementation
can be checked against the original intent.

### V. Validate and Review Changes

Review changed code for readability, complexity, duplication, responsibility
boundaries, and compatibility with the project architecture. Run focused tests
and the repository's available lint, formatting, and static-analysis checks.
Do not finish while relevant violations introduced by the change remain.

## Additional Constraints

Do not assume an application language, test framework, linter, formatter, or
static-analysis tool before the repository context supports that choice. When
an application language is introduced, select appropriate tools and configure
their checks in continuous integration.

## Development Workflow

Before changing the project, read `AGENTS.md` and this constitution. Use the
Spec Kit `/speckit-*` skills for specification-driven work: specify the change,
clarify material ambiguity when needed, plan, create tasks, analyze artifacts,
implement, and converge. Execute the tests and other applicable checks before
requesting review. Record checks that do not apply and why.

## Governance

This constitution governs project design and development practices. Amend it
when project standards change, and update its version and amendment date.
Version numbers follow semantic versioning: increment MAJOR for incompatible
governance changes, MINOR for new or materially expanded principles, and PATCH
for clarifications that do not change meaning. Every change review MUST check
compliance with this constitution, report applicable validation, and identify
any justified exceptions.

**Version**: 1.1.0 | **Ratified**: 2026-10-24 | **Last Amended**: 2026-10-24
