# Data Model: Configuração do Job via Bundle

Este recurso não introduz armazenamento persistente de dados de negócio. As entidades abaixo representam configuração versionada de implantação, referências a segredos externos e dados transitórios da execução do Job.

## Target do bundle

Representa uma implantação do Job em um ambiente Databricks.

| Campo | Tipo lógico | Regra |
|---|---|---|
| target_name | Texto | Identifica o ambiente não produtivo (`dev` ou `test`); único no bundle |
| workspace | Referência de workspace | Deve apontar ao workspace autorizado para o ambiente |
| run_identity | Identidade de serviço | Identidade específica do target que executa a tarefa |
| tenant_id | Identificador | Não secreto; obrigatório e específico do ambiente |
| client_id | Identificador | Não secreto; deve identificar a app registration autorizada naquele ambiente |
| site | Identificador ou endereço | Deve selecionar um site permitido; `SHAREPOINT_SITE_ID` ou par hostname/caminho |
| download_parameters | Lista de argumentos | Contém `download`, `--library`, `--volume` e um ou mais caminhos; valores definidos por ambiente e não alteráveis por execução nesta versão |
| secret_reference | Referência protegida | Formato lógico `{{secrets/<scope>/<key>}}`; identifica a chave que contém o client secret |

**Validação**: exigir todos os valores necessários ao comando; o ID de cliente e tenant não são vazios. A referência deve apontar ao secret scope do target e não conter valor de credencial. Os targets não devem apontar acidentalmente para referências ou volumes de outro ambiente.

## Referência de credencial

Representa um segredo provisionado fora do bundle em um secret scope Databricks.

| Campo | Tipo lógico | Regra |
|---|---|---|
| scope_name | Texto | Scope pré-provisionado no workspace do target |
| key_name | Texto | Chave que armazena o Client Secret Value |
| value | Segredo opaco | Nunca incluído no bundle, parâmetros, logs, documentação ou controle de versão |
| reader | Identidade | Responsável autorizado a resolver a referência durante a configuração do cluster |
| lifecycle | Estado operacional | Criado antes do deploy; rotacionado antes do vencimento; credencial antiga revogada após migração |

**Validação**: acesso de leitura mínimo às identidades que executam o Job; escrita/gerência reservada aos responsáveis pelo provisionamento; nenhum valor secreto é exibido durante validação.

## Volume Unity Catalog

Representa o destino gerenciado declarado pelo bundle para arquivos baixados.

| Campo | Tipo lógico | Regra |
|---|---|---|
| catalog_name | Identificador | Catálogo existente configurado para o target |
| schema_name | Identificador | Schema existente configurado para o target |
| name | Identificador | Nome configurado para o volume gerenciado |
| volume_type | Enumeração | `MANAGED`; armazenamento provisionado pelo Unity Catalog |
| grants | Permissões | Concede `READ_VOLUME` e `WRITE_VOLUME` à identidade do Job |
| lifecycle | Política | `prevent_destroy: true` protege o volume e seus arquivos |

**Validação**: a identidade de implantação precisa de `USE CATALOG`, `USE
SCHEMA` e `CREATE VOLUME`; a identidade do Job precisa de `USE CATALOG` e
`USE SCHEMA` nos objetos pai. O bundle não cria o catálogo ou schema.

## Tarefa do Job

Representa a invocação do pacote wheel pelo Databricks.

| Campo | Tipo lógico | Regra |
|---|---|---|
| package | Artefato wheel | Construído a partir do pacote de aplicação atual |
| entry_point | Nome de comando | Chama a função CLI existente |
| parameters | Lista de argumentos | Obrigatório; contém subcomando `download`, `--library`, `--volume` e um ou mais caminhos de origem |
| environment | Mapa de variáveis | Expõe os nomes de ambiente existentes; segredo recebe referência Databricks |
| compute_identity | Identidade | Deve ter leitura no site e privilégios Unity Catalog necessários |

**Validação**: a CLI existente valida as variáveis obrigatórias, o site e os argumentos de destino. A tarefa não inclui valor do segredo como parâmetro ou argumento. A seleção de caminhos é fixa nos argumentos configurados para o target; alterá-los exige atualizar e implantar novamente o bundle.

## Execução do Job

Uma tentativa de implantar ou executar o bundle.

| Campo | Tipo lógico | Regra |
|---|---|---|
| target_name | Referência | Target escolhido para o deploy/run |
| state | Estado transitório | Validação, implantação, execução e resultado |
| job_run_id | Identificador | Atribuído pelo Databricks; não usado como segredo |
| result | Estado | Sucesso somente se a tarefa conclui com código de saída zero |

**Falhas**: referência não resolvida, configuração obrigatória ausente, falha de autenticação Graph, permissão SharePoint, permissão de volume ou falha em item de download devem ser visíveis como falha da execução. A CLI mantém seus resultados individuais de arquivos conforme o contrato existente.
