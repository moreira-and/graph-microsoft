# Quickstart: Validar Job SharePoint por Bundle

## Pré-requisitos

- Databricks CLI compatível com Declarative Automation Bundles, autenticado no workspace de teste.
- `uv` e Python local compatível com os requisitos do projeto.
- Target não produtivo (`dev` ou `test`) selecionado junto ao perfil CLI autenticado no workspace correto; runtime, tenant, app e site configurados.
- Identidade de serviço configurada em `job_service_principal_name`, com acesso de leitura ao SharePoint e privilégios necessários no volume.
- Catálogo e schema Unity Catalog existentes, com permissão para o deploy criar o volume gerenciado.
- Lista `download_parameters` com os argumentos `download`, biblioteca, volume declarado no bundle e caminho(s) não sensíveis a baixar.
- Secret scope e chave contendo o Client Secret Value provisionados no workspace. Consulte o [guia operacional de credenciais](../../docs/secret_config/credential-setup.md).
- App registration com acesso de leitura concedido ao site SharePoint de teste.
- Compute compatível com Unity Catalog/volumes e runtime Python 3.12 ou superior; identidade do Job com `USE CATALOG`, `USE SCHEMA` e `WRITE VOLUME`.
- Um arquivo SharePoint não sensível, autorizado para teste, e um volume dedicado ao teste.

## Verificação local sem credenciais

Na raiz do repositório:

```bash
uv sync --locked
uv run pytest
uv run ruff check
uv run ruff format --check
uv run mypy
uv build
```

Esperado: testes e verificações locais passam, e `uv build` gera o wheel sem exigir rede SharePoint nem valor real de segredo.

### Resultado da validação local desta implementação

- `uv run pytest`: passou; 97 testes passaram e 3 foram desmarcados pela configuração do projeto.
- `uv run ruff check`: passou.
- `uv run ruff format --check`: passou; 61 arquivos já estavam formatados.
- `uv run mypy`: passou; 16 arquivos de origem sem erros.
- `uv build`: passou; gerou source distribution e wheel.
- Parse estrutural local de `databricks.yml` e `resources/sharepoint_job.yml`: passou; os campos de identidade, parâmetros e referência de segredo foram conferidos.
- `git diff --check`: passou.

O parse estrutural local não substitui `databricks bundle validate`. A validação da configuração passou com o perfil autenticado `dev` e valores
fictícios temporários para variáveis não usadas pelo Job de teste. O Job
serverless isolado foi implantado e executado no workspace: `test.txt` foi
gravado e lido com o conteúdo UTC `current_time=2026-10-25T04:10:53+00:00`.
O Job de download SharePoint e seus cenários negativos ainda dependem de
configuração real e não foram implantados/executados.

## Teste rápido do volume sem SharePoint

Para testar somente a gravação no Unity Catalog Volume, não é necessário
executar o download SharePoint. O volume é declarado em
`resources/sharepoint_volume.yml` e pode ser implantado isoladamente em um
workspace de desenvolvimento.

1. Importe [notebooks/test_volume.py](../../notebooks/test_volume.py) como
   notebook Python no workspace Databricks. Se preferir, crie um notebook
   Python e copie o conteúdo do arquivo.
2. Configure `volume_catalog`, `volume_schema` e `volume_name` para o target.
   O catálogo e o schema devem existir; o bundle cria o volume gerenciado
   `<catalog>.<schema>.<volume_name>` e concede `READ_VOLUME` e `WRITE_VOLUME`
   à identidade configurada em `job_service_principal_name`.
3. Para implantar somente o volume em um workspace de desenvolvimento, use o
   seletor de recursos do bundle:

   ```bash
   databricks bundle deploy --target dev --select volumes.sharepoint_files
   ```

   A opção `--select` limita os recursos implantados, mas a CLI pode ainda
   exigir valores das variáveis referenciadas pela configuração do bundle.
   Não use essa seleção para implantação em produção.

   Se o volume com esse nome já existir, vincule-o ao bundle antes do deploy,
   em vez de tentar criá-lo novamente:

   ```bash
   databricks bundle deployment bind sharepoint_files <CATALOG>.<SCHEMA>.<VOLUME_NAME> --target dev
   ```

4. Anexe o notebook a um compute compatível com Unity Catalog Volumes.
   A identidade interativa que executa o notebook também precisa de
   `USE CATALOG`, `USE SCHEMA`, `READ_VOLUME` e `WRITE_VOLUME`. Para testar
   exatamente as permissões do Job, execute o Job independente
   `volume_smoke_test_job`.
5. No widget `volume`, informe o nome qualificado criado pelo bundle.
6. Execute a célula. O notebook grava
   `/Volumes/<catalog>/<schema>/<volume>/test.txt` com o timestamp UTC da
   execução,
   lê o arquivo de volta e falha explicitamente se a gravação ou leitura não
   funcionar.

O teste deixa `test.txt` no volume e sobrescreve esse arquivo se já existir.
Use um volume de teste ou confirme que o arquivo pode ser substituído. O teste
valida as permissões da identidade que executa o notebook; para validar as
permissões do Job, execute-o como Job com a identidade de serviço configurada.
O deploy precisa de `USE CATALOG`, `USE SCHEMA` e `CREATE VOLUME` no schema;
a identidade do Job precisa de `USE CATALOG` e `USE SCHEMA` no pai do volume.

O bundle também declara um Job independente `volume_smoke_test_job` em
`resources/volume_smoke_job.yml`. Ele usa o entry point
notebook `notebooks/test_volume.py` em serverless, sem variáveis de
autenticação Microsoft. Depois de implantar o recurso, execute-o:

```bash
databricks bundle run --target dev --profile dev volume_smoke_test_job
```

O Job cria ou substitui `test.txt` na raiz do volume, grava
`current_time=<timestamp UTC ISO>` usando a hora da execução e valida o
conteúdo lendo-o de volta. Ele não chama SharePoint nem depende de
`azure_tenant_id`, `azure_client_id` ou client secret. Sem `run_as` explícito,
o Job executa como seu proprietário (a identidade que fez o deploy); essa
identidade precisa de `USE CATALOG`, `USE SCHEMA`, `READ_VOLUME` e
`WRITE_VOLUME` para o volume. O ambiente serverless pode incorrer em cobrança
de compute de acordo com a política do workspace.

## Validar e implantar o bundle

Os targets `dev` e `test` usam o workspace do perfil Databricks selecionado e
não têm valores padrão para compute,
credenciais ou argumentos do Job. Na primeira validação de cada target, forneça
os valores não secretos e a referência `{{secrets/<scope>/<key>}}` quando a
CLI Databricks solicitar. Para `download_parameters`, informe uma lista JSON,
com o mesmo volume definido por `volume_catalog`, `volume_schema` e
`volume_name`, por exemplo:

```json
["download", "--library", "<LIBRARY_ID>", "--volume", "<CATALOG>.<SCHEMA>.<VOLUME_NAME>", "<CAMINHO>"]
```

Não informe o valor real do client secret: somente sua referência no secret
scope. A CLI Databricks armazena overrides por target em `.databricks/`, que é
ignorado pelo Git.

```bash
databricks bundle validate --target dev
databricks bundle deploy --target dev
```

Quando há um perfil nomeado, passe-o explicitamente, por exemplo:

```bash
databricks bundle validate --target dev --profile dev
databricks bundle deploy --target dev --profile dev
```

Esperado: validação do bundle concluída sem valores secretos na saída; o Job e o artefato wheel são publicados no workspace de destino.

## Executar e verificar

```bash
databricks bundle run --target dev sharepoint_download
```

Esperado:

1. O Job resolve as variáveis não secretas e a referência do secret scope.
2. A CLI autentica no Microsoft Graph e lê o arquivo de teste autorizado.
3. O resultado aparece no volume configurado, sob o nome original.
4. O Job reporta sucesso somente quando a CLI termina com código zero.
5. Nenhum valor de segredo, token ou conteúdo sensível aparece nos logs.

## Cenários negativos seguros

- Aponte um target de teste para uma referência de segredo inexistente: a tarefa deve falhar explicitamente e não registrar sucesso.
- Use uma identidade sem permissão de leitura no site ou escrita no volume em ambiente dedicado: o erro deve ser visível sem imprimir credenciais.
- Revise os logs da execução negativa e confirme que não contêm valor de segredo, token ou ambiente completo do processo.
- Não teste falhas de permissão em produção e não remova arquivos que não pertençam ao fixture de teste.

## Segurança e encerramento

- Não execute `env`, `printenv`, `echo "$AZURE_CLIENT_SECRET"` nem comandos que exibam a configuração resolvida do cluster.
- Não passe o valor do client secret em argumentos, parâmetros de Job ou variáveis de shell de deploy.
- Após o teste, preserve o secret scope e o volume segundo a política do ambiente; limpe somente arquivos fixture de teste explicitamente dedicados.

O contrato de variáveis, argumentos e limites de segredo está em [contracts/job-config.md](contracts/job-config.md); as entidades estão em [data-model.md](data-model.md).
