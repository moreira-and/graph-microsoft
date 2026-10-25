# Guia de Validação

## Pré-requisitos

- Aplicação no Microsoft Entra ID com a permissão de aplicação Sites.Selected, consentimento de administrador e leitura concedida ao site de teste.
- `cp .env.example .env` e preenchimento de `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` e do site (`SHAREPOINT_SITE_ID` ou `SHAREPOINT_HOSTNAME` + `SHAREPOINT_SITE_PATH`). Nunca versionar `.env`.
- `uv sync --locked`

## Verificações padrão (sem credenciais nem rede)

```bash
uv run ruff check
uv run ruff format --check
uv run mypy
uv run pytest
```

Esperado: tudo passa; testes de integração não são executados.

## Fluxo manual de ponta a ponta

```bash
uv run python -m sharepoint_files site
uv run python -m sharepoint_files libraries
uv run python -m sharepoint_files ls --library <ID_DA_BIBLIOTECA>
uv run python -m sharepoint_files find --library <ID> --name relatorio
uv run python -m sharepoint_files download --library <ID> --dest ./downloads pasta/arquivo.docx
uv run python -m sharepoint_files download --library <ID> --dest ./downloads pasta/arquivo.docx
uv run python -m sharepoint_files download --library <ID> --dest ./downloads --overwrite pasta/arquivo.docx
```

Esperado: o primeiro `download` informa "baixado"; o segundo informa "ignorado" sem alterar o arquivo; o terceiro substitui o arquivo. Nenhum arquivo `.tmp` permanece em `./downloads`. A saída não contém tokens, segredos nem URLs de download.

## Integração opt-in

```bash
uv run pytest -m integration
```

O teste de autenticação app-only valida a obtenção de token e não exige site.
O teste de SharePoint exige `.env` local com credenciais, um site existente em
tenant com SharePoint Online licenciado e concessão `Sites.Selected` de leitura.
Testes de integração não são executados na suíte padrão.

### Estado atual da validação real

- **Autenticação Entra**: validada; o smoke test obteve token Graph válido. Isso
	não confirma acesso a um site.
- **SharePoint**: pendente. A última tentativa falhou ao resolver o site com
	HTTP 400 (`BadRequest`: `Tenant does not have a SPO license.`); listagem e
	download reais não foram executados.
- **Para concluir**: habilitar licença SharePoint Online no tenant, configurar
	hostname e caminho válidos para um site existente e conceder ao app
	`Sites.Selected` com papel `read`; então repetir o fluxo acima.

Contratos: [contracts/cli.md](contracts/cli.md). Entidades: [data-model.md](data-model.md).
