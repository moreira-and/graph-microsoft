# graph-microsoft

## Spec Kit

Este repositório usa [GitHub Spec Kit](https://github.com/github/spec-kit) com
a integração GitHub Copilot. Os arquivos de configuração e os scripts ficam em
`.specify/`, e as skills do Copilot ficam em `.github/skills/`.

Para instalar o CLI e inicializar o Spec Kit na raiz do repositório:

```bash
uv tool install specify-cli
specify init --here --force --integration copilot
```

Execute a inicialização uma vez por checkout que ainda não tenha o Spec Kit.
Como `--force` permite mesclar arquivos gerenciados e substituir conflitos,
revise as alterações antes de confirmar. Para validar a instalação, execute
`specify check`.

O fluxo de especificação está disponível nas skills `/speckit-specify`,
`/speckit-plan`, `/speckit-tasks`, `/speckit-implement` e
`/speckit-converge`. Consulte `AGENTS.md` e
`.specify/memory/constitution.md` para os padrões de qualidade do projeto.
Os arquivos de scaffolding derivados do Spec Kit são licenciados conforme
`third_party/spec-kit/LICENSE`.

Fonte: [github/spec-kit](https://github.com/github/spec-kit).

## Ferramentas Python

O projeto usa `uv` para gerenciar as ferramentas de qualidade Python. Instale as
dependências de desenvolvimento e configure os hooks Git com:

```bash
uv sync --locked
uv run pre-commit install
```

O hook pré-commit executa Ruff (lint e formatação) e mypy nos arquivos Python
alterados. O hook pré-push executa a suíte completa com pytest. Como ainda não
há testes no repositório, o pytest termina com código 5 até que sejam criados;
adicione testes antes de fazer push com os hooks instalados.

Para executar as verificações manualmente:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy <arquivos-python>
uv run pytest
```

O Ruff aplica complexidade McCabe máxima 10. A configuração e as versões das
ferramentas estão em `pyproject.toml` e `uv.lock`.

## Microsoft Graph e SharePoint

As dependências Python de runtime são `msgraph-sdk`, o SDK oficial do Microsoft
Graph, e `azure-identity`, para autenticação com Microsoft Entra ID. O SDK
permite iniciar chamadas aos endpoints de sites do SharePoint, enquanto
`azure-identity` fornece credenciais para autenticar essas chamadas. As versões
diretas e transitivas estão fixadas em `uv.lock`.

### Credenciais de integração

Copie `.env.example` para `.env` e preencha os valores da app registration e do
site de teste no seu tenant Microsoft Entra. Não há credenciais oficiais
compartilhadas para usar: crie uma app registration própria e mantenha o segredo
apenas em `.env`, que é ignorado pelo Git. Para ambientes fora do desenvolvimento
local, prefira certificado ou identidade gerenciada em vez de segredo de cliente.

Para testes que leem um site, prefira a permissão de aplicativo `Sites.Selected`
e conceda explicitamente acesso de leitura somente ao site de teste. Essa
permissão requer consentimento administrativo e uma concessão específica no
site; sem ambas, a aplicação não terá acesso. Consulte a documentação oficial:

- [Fluxo OAuth 2.0 de credenciais do cliente](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow)
- [Permissões selecionadas para SharePoint e OneDrive](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)
- [Obter um site do SharePoint pelo Microsoft Graph](https://learn.microsoft.com/en-us/graph/api/site-get?view=graph-rest-1.0)