# graph-microsoft

Projeto Python para consultar sites do SharePoint e arquivos via Microsoft
Graph. O repositório contém a configuração inicial do SDK, autenticação Entra
ID e ferramentas de qualidade. As operações de consulta e download ainda não
estão implementadas; não há comando de aplicação para iniciar neste estágio.

## Dependências

As dependências de runtime estão declaradas em `pyproject.toml` e travadas em
`uv.lock`:

| Dependência | Uso |
| --- | --- |
| `msgraph-sdk` | Cliente oficial tipado para chamar a API Microsoft Graph, incluindo recursos de SharePoint. |
| `azure-identity` | Credenciais Microsoft Entra ID compatíveis com o cliente Graph. |

As ferramentas de desenvolvimento ficam no grupo `dev`:

| Dependência | Uso |
| --- | --- |
| `ruff` | Lint, formatação e limite de complexidade McCabe 10. |
| `mypy` | Verificação estática de tipos em modo estrito. |
| `pytest` | Testes automatizados. |
| `pre-commit` | Instala e executa os hooks Git locais. |

## Como iniciar

Requisitos: Python 3.12 ou superior e [`uv`](https://docs.astral.sh/uv/).

Instale as dependências travadas e configure os hooks:

```bash
uv sync --locked
uv run pre-commit install
```

O hook de pré-commit executa Ruff e mypy nos arquivos Python alterados. O hook
de pré-push executa a suíte pytest. Para rodar as verificações manualmente:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy tests
uv run pytest
```

Atualmente, os testes verificam a disponibilidade dos imports do SDK e da
credencial Entra; eles não acessam um tenant ou site SharePoint real.

## Configuração de integração

Copie `.env.example` para `.env` e preencha os valores de uma app registration
e de um site de teste no seu próprio tenant Microsoft Entra. O `.env` é
ignorado pelo Git. Não há credenciais compartilhadas; não versione segredos.

Para integração de leitura, prefira `Sites.Selected` e conceda à aplicação
acesso somente ao site de teste. A configuração dessa permissão exige
consentimento administrativo e uma concessão explícita no site.

Quando houver comandos de aplicação ou testes de integração que leiam o `.env`,
carregue-o explicitamente, por exemplo com `uv run --env-file .env ...`.
Nenhuma chamada real ao Microsoft Graph está implementada ainda.

Documentação oficial:

- [SDK Microsoft Graph para Python](https://github.com/microsoftgraph/msgraph-sdk-python)
- [Fluxo OAuth 2.0 de credenciais do cliente](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow)
- [Permissões selecionadas para SharePoint e OneDrive](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)
- [Obter um site do SharePoint pelo Microsoft Graph](https://learn.microsoft.com/en-us/graph/api/site-get?view=graph-rest-1.0)

## Spec Kit

O repositório usa [GitHub Spec Kit](https://github.com/github/spec-kit) com a
integração GitHub Copilot. Os artefatos compartilhados ficam em `.specify/`;
as skills ficam em `.github/skills/`. Instale o CLI separadamente:

```bash
uv tool install specify-cli
specify init --here --force --integration copilot
```

Use `/speckit-specify`, `/speckit-plan`, `/speckit-tasks` e
`/speckit-implement` para o fluxo de especificação. Revise os arquivos
gerenciados e conflitos antes de confirmar uma inicialização com `--force`.
