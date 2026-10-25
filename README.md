# graph-microsoft

Ferramenta Python de leitura para listar, localizar e baixar arquivos de um site
SharePoint usando Microsoft Graph e autenticação app-only no Microsoft Entra ID.
O acesso deve usar `Sites.Selected` com uma concessão de leitura explícita ao
site de teste. A ferramenta não faz upload nem altera conteúdo do SharePoint.

## Requisitos

- Python 3.12 ou superior
- [`uv`](https://docs.astral.sh/uv/)
- App registration com `Sites.Selected`, consentimento administrativo e
  concessão de leitura no site desejado

Instale as dependências travadas:

```bash
uv sync --locked
```

O pacote usa `msgraph-sdk` e `azure-identity`; `httpx` é declarada diretamente
para configurar os timeouts do cliente HTTP. Hatchling instala o pacote local em
modo editável para habilitar `uv run python -m sharepoint_files`.

## Configuração

Copie `.env.example` para `.env` e configure:

| Variável | Obrigatória | Uso |
|---|---|---|
| `AZURE_TENANT_ID` | Sim | Tenant Microsoft Entra ID |
| `AZURE_CLIENT_ID` | Sim | ID da aplicação |
| `AZURE_CLIENT_SECRET` | Sim | Segredo da aplicação |
| `SHAREPOINT_SITE_ID` | Uma das opções de site | ID do site padrão |
| `SHAREPOINT_HOSTNAME` | Uma das opções de site | Hostname, como `contoso.sharepoint.com` |
| `SHAREPOINT_SITE_PATH` | Junto com hostname | Caminho relativo, como `/sites/equipe` |
| `GRAPH_SCOPE` | Não | Padrão: `https://graph.microsoft.com/.default` |
| `DOWNLOAD_DIR` | Não | Diretório padrão de download; `--dest` prevalece |

O site padrão pode ser informado por `SHAREPOINT_SITE_ID` ou pelo par
`SHAREPOINT_HOSTNAME` e `SHAREPOINT_SITE_PATH`. Variáveis exportadas no ambiente
têm precedência sobre `.env`. Nunca versione credenciais.

## Uso

Os comandos usam o site padrão configurado, exceto quando `site` ou
`libraries` recebem opções explícitas de site.

```bash
uv run python -m sharepoint_files site
uv run python -m sharepoint_files site --hostname contoso.sharepoint.com --site-path /sites/equipe
uv run python -m sharepoint_files libraries
uv run python -m sharepoint_files ls --library <ID_DA_BIBLIOTECA>
uv run python -m sharepoint_files ls --library <ID> --folder documentos/2025
uv run python -m sharepoint_files find --library <ID> --name relatorio
uv run python -m sharepoint_files find --library <ID> --path documentos/relatorio.docx
uv run python -m sharepoint_files download --library <ID> --dest ./downloads documentos/relatorio.docx
uv run python -m sharepoint_files download --library <ID> --dest ./downloads --overwrite documentos/relatorio.docx
```

Downloads são sequenciais, com limite de 20 arquivos por lote e 100 MB por
arquivo. Sem `--overwrite`, arquivos existentes são ignorados. Cada item do
lote é reportado individualmente; falhas não removem arquivos concluídos. O
destino é validado para permanecer dentro do diretório configurado, e o arquivo
final só aparece após a gravação completa.

## Testes e qualidade

Os testes padrão não usam rede nem credenciais. Integrações reais são opt-in:

```bash
uv run pytest
uv run pytest -m integration
```

O teste de integração lê `.env` e pode ser ignorado se credenciais e site não
estiverem configurados. Verificações usadas na CI e nos hooks:

```bash
uv run ruff check
uv run ruff format --check
uv run mypy
uv run pre-commit run --all-files
```

O workflow GitHub Actions executa sincronização bloqueada de dependências, Ruff,
mypy e pytest.