# Contract: Configuração do Job Databricks

## Responsabilidade

O bundle constrói e publica a CLI Python existente como wheel, configura um Job Databricks e encaminha seus argumentos ao entry point do pacote. A lógica de autenticação Graph e de downloads permanece na CLI.

## Configuração por target

Cada target do bundle deve definir valores próprios para:

| Valor | Tipo | Regra |
|---|---|---|
| `AZURE_TENANT_ID` | Não secreto | ID do tenant Microsoft Entra para o ambiente |
| `AZURE_CLIENT_ID` | Não secreto | ID da aplicação app-only autorizada |
| `AZURE_CLIENT_SECRET` | Referência protegida | Referência Databricks `{{secrets/<scope>/<key>}}`; não o valor |
| `job_service_principal_name` | Identificador | Identidade efetiva específica do target para executar o Job |
| `SHAREPOINT_SITE_ID` ou `SHAREPOINT_HOSTNAME` e `SHAREPOINT_SITE_PATH` | Não secreto | Site SharePoint permitido pela concessão da aplicação |
| `GRAPH_SCOPE` | Não secreto, opcional | Se ausente, a CLI usa `https://graph.microsoft.com/.default` |
| `volume_catalog`, `volume_schema`, `volume_name` | Não secretos | Catálogo/schema existentes e nome do volume gerenciado declarado pelo bundle |
| `download_parameters` | Lista não secreta | Argumentos completos da CLI: `download`, `--library`, ID da biblioteca, `--volume`, mesmo nome qualificado criado pelo bundle e um ou mais caminhos |

O target de desenvolvimento não pode herdar a referência ou destino de produção sem uma configuração intencional e revisada. Valores com aparência secreta não devem ser aceitos como parâmetros de execução.

O bundle cria um volume `MANAGED` no catálogo e schema configurados. O deploy
exige `USE CATALOG`, `USE SCHEMA` e `CREATE VOLUME` no schema. O recurso concede
`READ_VOLUME` e `WRITE_VOLUME` à identidade do Job; essa identidade também
precisa de `USE CATALOG` e `USE SCHEMA` nos objetos pai. A proteção
`prevent_destroy` evita remover o volume e seus dados ao destruir o bundle.

## Comando da tarefa

A tarefa invoca o entry point instalado no wheel com a forma equivalente a:

```text
sharepoint-files download --library <LIBRARY_ID> --volume <CATALOG.SCHEMA.VOLUME> <PATH>...
```

Além do Job de download, o bundle declara o Job independente
`volume_smoke_test_job`, executado em serverless sem credenciais Graph. Ele
executa o notebook `notebooks/test_volume.py`, grava/sobrescreve `test.txt`
com `current_time=<timestamp UTC ISO>` e lê o conteúdo de volta; qualquer erro
de acesso ou divergência resulta em falha. O Job usa o proprietário como
identidade de execução.

Os argumentos, incluindo um ou mais caminhos, são definidos para cada target nesta primeira versão. Alterá-los exige atualizar e implantar novamente o bundle; parâmetros para substituí-los a cada execução não fazem parte do contrato. A CLI rejeita configurações inválidas, mantém os limites existentes e reporta falhas por arquivo. A tarefa deve propagar código de saída não zero como execução malsucedida.

## Regras de segredo

- O bundle guarda apenas `{{secrets/<scope>/<key>}}` para `AZURE_CLIENT_SECRET`.
- O client secret Value não pode ser armazenado em YAML do bundle, variável comum do bundle, job parameter, argumento CLI, arquivo de ambiente versionado, saída de validação, log ou documentação.
- O provisionamento do scope/key e ACLs ocorre antes do deploy, pelo processo aprovado do workspace.
- Quem configura ou possui o cluster deve conseguir resolver a referência; a exposição a usuários do cluster e logs é limitada por ACLs operacionais.
- A identidade efetiva da tarefa deve ter acesso de leitura ao SharePoint e `USE CATALOG`, `USE SCHEMA`, `WRITE VOLUME` para o destino.
- A identidade efetiva deve ser configurada explicitamente por target e ter permissão para ler a referência do secret scope e executar o Job.

## Compatibilidade

- Não altera o contrato da CLI local nem o comportamento de `python -m sharepoint_files`.
- Não introduz autenticação ou cliente Graph paralelo.
- Cria o volume Unity Catalog gerenciado e concede permissões no próprio volume; não cria catálogo ou schema nem provisiona permissões SharePoint, segredos ou scopes.
- Os targets iniciais são ambientes não produtivos `dev` e `test`; produção e compute serverless não fazem parte deste escopo.
- Não oferece parâmetros de seleção de caminhos por execução neste escopo.
