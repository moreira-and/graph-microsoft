# Research: Configuração do Job via Bundle

**Date**: 2026-10-25

## Decisões

### Empacotamento da CLI para o Job

- **Decision**: Construir o pacote atual como wheel e executá-lo por uma tarefa Python wheel do Job. Expor a função `sharepoint_files.cli:main` como entry point instalável, preservando `python -m sharepoint_files` para uso local.
- **Rationale**: O projeto já é um pacote Python instalável, possui dependências declaradas e uma função `main` reaproveitável. O template oficial de bundle Python suporta artefatos wheel e tarefas `python_wheel_task`; isso evita sincronizar código fonte solto e manter uma segunda implementação do downloader no Job.
- **Alternatives considered**:
  - Executar um notebook: não há notebook nem necessidade de uma camada interativa.
  - Executar diretamente um script sincronizado: pode depender de configuração de import e instalação de dependências no cluster, duplicando a responsabilidade de empacotamento já coberta pelo projeto.
  - Criar um pacote/job Python separado: adiciona duplicação e acoplamento desnecessários.
- **Sources**:
  - [Databricks: Build a Python wheel file using Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/python-wheel)
  - [Databricks: Bundle settings](https://docs.databricks.com/aws/en/dev-tools/bundles/settings)

### Configuração do ambiente e parâmetros de execução

- **Decision**: Usar targets do bundle para os valores estáveis por ambiente, como tenant ID, client ID, site, biblioteca, volume e referência do secret scope. A tarefa passa os argumentos de download já suportados pela CLI. A primeira versão não define parâmetros variáveis de usuário por execução.
- **Rationale**: A necessidade especifica configuração por ambiente e implantação reproduzível; não exige alterar a seleção de arquivos a cada execução. Separar valores por target evita compartilhar destinos ou referências de segredo acidentalmente.
- **Alternatives considered**:
  - Job parameters substituíveis em cada execução: permitem variação sem redeploy, mas a necessidade não define quais valores devem ser dinâmicos; isso ampliaria o contrato operacional sem requisito.
  - Valores fixos embutidos no código: impedem promoção segura da mesma versão entre ambientes.
- **Sources**:
  - [Databricks: Configure job parameters in Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/job-parameters)
  - [Databricks: Variables in Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/variables)

### Injeção segura de credenciais

- **Decision**: Armazenar `AZURE_CLIENT_SECRET` em secret scope pré-provisionado e referenciá-lo em `spark_env_vars` do Job cluster via `{{secrets/<scope>/<key>}}`. Configurar `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` e as variáveis SharePoint/volume como valores não secretos do target.
- **Rationale**: A aplicação atual usa `ClientSecretCredential` com variáveis `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` e `AZURE_CLIENT_SECRET`. O Databricks documenta a referência a secret scopes em variáveis de ambiente de cluster. A referência, em vez do valor, pode ser versionada no bundle; o Job não requer alteração do fluxo de autenticação.
- **Alternatives considered**:
  - Client secret como variável comum de bundle ou argumento de tarefa: rejeitado porque valor sensível poderia ficar exposto em configuração, estado de deploy ou detalhes da execução.
  - `dbutils.secrets` chamado pelo código: mudaria o modelo de configuração do cliente Python, acoplaria a biblioteca ao runtime Databricks e não é necessário para o método de injeção já documentado.
  - Identidade sem segredo (por exemplo, workload identity): pode reduzir manutenção de segredo, mas depende de configuração e suporte organizacional não definidos; não faz parte do escopo inicial.
- **Sources**:
  - [Databricks: Use a secret in a Spark configuration property or environment variable](https://docs.databricks.com/aws/en/security/secrets/secrets-spark-conf-env-var)
  - [Microsoft Graph permissions selected overview](https://learn.microsoft.com/graph/permissions-selected-overview)
  - Implementação atual: `src/sharepoint_files/client.py` e `docs/secret_config/credential-setup.md`.

### Tipo de compute

- **Decision**: Planejar para um Job cluster clássico com Unity Catalog habilitado, runtime compatível com Python 3.12 e acesso a volumes; a primeira versão não inclui serverless.
- **Rationale**: A funcionalidade depende de volume Unity Catalog e o padrão de variável secreta em `spark_env_vars` se aplica ao cluster configurado. Limitar o primeiro desenho a um tipo de compute reduz variantes de implantação e facilita validar referências de segredo e permissões.
- **Alternatives considered**:
  - Serverless: fora do escopo desta configuração; suporte e configuração de secrets/volume precisam ser reavaliados em uma funcionalidade separada.
  - Compute existente compartilhado: não escolhido como padrão porque o lifecycle e o acesso às variáveis do cluster são mais difíceis de isolar entre ambientes.
- **Sources**:
  - [Databricks: Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes)
  - [Databricks: Use a secret in a Spark configuration property or environment variable](https://docs.databricks.com/aws/en/security/secrets/secrets-spark-conf-env-var)
  - [Databricks: Build a Python wheel file using Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/python-wheel)

## Limites e pré-requisitos

- O ambiente Databricks provisiona secret scopes e chaves antes do deploy. O bundle versiona somente o identificador da referência, nunca o valor secreto.
- O responsável por configurar o cluster precisa poder resolver a referência do secret scope; o acesso ao cluster e aos logs do driver deve ser restrito.
- A identidade efetiva do Job precisa de permissão de leitura no site SharePoint, além de `USE CATALOG`, `USE SCHEMA` e `WRITE VOLUME` no destino.
- Um runtime compatível com Python 3.12 e Unity Catalog deve ser escolhido pelo workspace; o bundle não cria a app registration, concessões Graph, secret scope, catálogo ou schema. O bundle declara o volume gerenciado e concede acesso nele à identidade do Job.
- Parâmetros dinâmicos para seleção de arquivos em cada run e autenticação sem client secret estão fora do escopo especificado.
