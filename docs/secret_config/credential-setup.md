# Configuração de credenciais do SharePoint para Jobs Databricks

Este guia é para a pessoa que provisiona credenciais e configura o Job. O Job
usa autenticação app-only do Microsoft Graph: a aplicação registrada no
Microsoft Entra ID acessa o SharePoint, e o processo Python lê as variáveis de
ambiente `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` e `AZURE_CLIENT_SECRET`.

## Resumo: o que vai para cada lugar

| Item | Onde configurar | É segredo? |
|---|---|---|
| Tenant ID (`AZURE_TENANT_ID`) | Configuração do ambiente no bundle | Não |
| Application (client) ID (`AZURE_CLIENT_ID`) | Configuração do ambiente no bundle | Não |
| Client secret **Value** (`AZURE_CLIENT_SECRET`) | Secret scope do workspace Databricks | **Sim** |
| Nome do site (`SHAREPOINT_SITE_ID` ou `SHAREPOINT_HOSTNAME` e `SHAREPOINT_SITE_PATH`) | Configuração do ambiente no bundle | Não |
| Biblioteca, volume e caminhos selecionados | Argumentos não secretos da CLI no target do bundle | Não |

O bundle deve conter somente uma referência ao segredo do Databricks, nunca o
valor do segredo. O valor é buscado no ambiente Databricks durante a execução
do cluster.

## Quem precisa fazer o quê

1. **Administrador Microsoft Entra/SharePoint** registra ou identifica a
   aplicação, concede somente as permissões Graph necessárias e autoriza o
   acesso de leitura ao site.
2. **Responsável pelos segredos Databricks** cria ou atualiza o segredo no
   secret scope usado pelo ambiente. Pode ser o mesmo administrador ou uma
   pessoa autorizada a gerenciar segredos.
3. **Responsável pelo bundle/Job** configura IDs, site, volume e referência ao
   scope no bundle, sem obter nem copiar o valor do segredo para o repositório.
4. **Administrador do workspace/compute** garante que a identidade que
   configura ou possui o cluster possa ler o scope e que a identidade efetiva
   do Job tenha as permissões necessárias para executar a tarefa e gravar no
   volume.

Separe os scopes por ambiente, por exemplo `sharepoint-dev` e
`sharepoint-test`, e conceda `READ` somente às identidades que precisam
executar aquele ambiente. Conceda `WRITE` e `MANAGE` apenas a responsáveis por
provisionar e rotacionar segredos. Os nomes exatos de identidades e ACLs
dependem das políticas do workspace; valide-os com o administrador
Databricks.

O bundle do projeto define targets não produtivos `dev` e `test`. Produção
precisa de revisão e configuração operacional próprias e não é implantada por
esses targets.

## 1. Preparar a aplicação Microsoft Entra

1. Use a app registration aprovada pela organização para este Job.
2. Registre o **Directory (tenant) ID** e o **Application (client) ID**. Esses
   identificadores não são credenciais secretas.
3. Para a leitura limitada ao site, configure `Sites.Selected`, obtenha o
   consentimento administrativo necessário e conceda à aplicação acesso de
   leitura explicitamente ao site SharePoint desejado. Não conceda acesso mais
   amplo do que a necessidade do Job.
4. Crie uma credencial de aplicação de acordo com a política da organização.
   Ao usar um client secret, copie o campo **Value** quando ele for criado:
   ele pode não ser mostrado novamente. **Não copie o Secret ID** no lugar do
   Value.
5. Transfira o Value diretamente ao responsável pelo secret scope usando o
   canal aprovado pela organização. Não o envie em chat, e-mail, ticket, linha
   de comando, arquivo do bundle ou repositório.
6. Registre a data de expiração e o responsável pela rotação. Planeje a
   renovação antes do vencimento e remova a credencial antiga quando não for
   mais necessária.

Consulte a documentação Microsoft sobre
[permissões selecionadas do Microsoft Graph](https://learn.microsoft.com/graph/permissions-selected-overview)
para validar o consentimento e a concessão específica ao site.

## 2. Guardar o segredo no Databricks

1. Selecione o workspace e o ambiente corretos. Confirme o nome aprovado do
   secret scope, por exemplo `sharepoint-prod`.
2. Crie o scope, se ainda não existir, usando o processo autorizado do
   workspace. Conforme a plataforma e a política da organização, o scope pode
   guardar o segredo no Databricks ou ser respaldado por um Azure Key Vault.
   Um scope respaldado por Key Vault só se aplica a workspaces e configurações
   compatíveis.
3. Crie ou atualize a chave `azure-client-secret` com o **Client Secret
   Value** recebido no passo anterior. A chave deve conter apenas o Value, sem
   aspas adicionadas, prefixo ou quebra de linha.
4. Configure ACLs para que a identidade responsável pela configuração do
   cluster/Job possa resolver a referência durante a inicialização. Dê acesso
   de leitura apenas às identidades que necessitam executar o Job.
5. Confirme o scope e o nome da chave com o responsável pelo bundle. Nunca
   confirme o Value em uma captura de tela, log ou mensagem.

O método de criação e as permissões de scopes variam com as configurações do
workspace. Siga o procedimento de administração Databricks da organização;
não use um comando ou pipeline que exponha o Value em histórico de terminal,
argumentos de processo ou logs.

## 3. Referenciar o segredo no bundle

O Job precisa expor as três variáveis que o cliente Python lê. No cluster do
Job, configure os valores não secretos e use a referência Databricks para o
segredo. O recurso `resources/sharepoint_job.yml` recebe a referência pela variável
`client_secret_reference`. Configure-a com o caminho do scope específico do
target; os exemplos abaixo são valores para fornecer ao target, não credenciais
nem valores que devam ser copiados em defaults versionados:

| Target | Valor de `client_secret_reference` |
|---|---|
| `dev` | `{{secrets/sharepoint-dev/azure-client-secret}}` |
| `test` | `{{secrets/sharepoint-test/azure-client-secret}}` |

O exemplo mostra somente referências, nunca o valor do segredo. Não é
necessário codificar valores específicos dos targets no repositório: o projeto
declara as variáveis sem valores padrão, que devem ser preenchidas
separadamente para cada target durante a validação/implantação ou por
overrides locais ignorados pelo Git.
Autentique a CLI no workspace correto e selecione o perfil com `--profile`;
o bundle usa o host do perfil selecionado. Configure `spark_version`,
`node_type_id`, `azure_tenant_id`,
`job_service_principal_name`, `azure_client_id`, `sharepoint_site_id`,
`client_secret_reference`, `volume_catalog`, `volume_schema`, `volume_name` e
`download_parameters` com os valores aprovados para o target.
`volume_catalog` e `volume_schema` devem apontar para objetos existentes; o
bundle cria neles um volume Unity Catalog gerenciado usando `volume_name`.
O deploy precisa de `USE CATALOG`, `USE SCHEMA` e `CREATE VOLUME` no schema.
O recurso em `resources/sharepoint_volume.yml` concede `READ_VOLUME` e
`WRITE_VOLUME` à identidade indicada por `job_service_principal_name`; essa
identidade ainda precisa de `USE CATALOG` e `USE SCHEMA` nos objetos pai.
O `job_service_principal_name` é o application ID da identidade de serviço
que executa o Job; conceda a ela também acesso ao site SharePoint. O último
valor é uma lista JSON de argumentos da CLI, por exemplo:

```json
["download", "--library", "<LIBRARY_ID>", "--volume", "<CATALOG>.<SCHEMA>.<VOLUME_NAME>", "<CAMINHO>"]
```

O Job transfere somente os caminhos dessa lista explícita; nada fora dela é
lido. Se um arquivo já existir no volume, ele é sobrescrito de forma atômica:
em caso de falha, o conteúdo anterior permanece e nenhum arquivo parcial fica no
volume.

Os caminhos fazem parte da configuração do target; alterá-los requer atualizar
os argumentos configurados e implantar novamente o bundle. O Job configura
`AZURE_CLIENT_SECRET` com a referência ao scope durante a execução. O bundle
cria o volume gerenciado, mas não cria catálogo ou schema. `prevent_destroy`
está habilitado no recurso para evitar que um `bundle destroy` remova o volume
e seus arquivos.

### O que não fazer

- Não escreva o Client Secret Value em `databricks.yml`, arquivos de variável,
  parâmetros do Job, `pyproject.toml`, `.env.example`, scripts ou arquivos
  versionados.
- Não use `${var.azure_client_secret}` para inserir o segredo como variável
  comum do bundle.
- Não passe o segredo como argumento da tarefa ou parâmetro de execução: esses
  valores podem aparecer na configuração ou nos detalhes da execução.
- Não imprima `AZURE_CLIENT_SECRET`, todo o ambiente do processo, tokens ou
  objetos de credencial em logs.
- Não trate o mascaramento de segredos como proteção suficiente. Acesso ao
  cluster e aos logs do driver também precisa ser limitado; variáveis de
  ambiente do cluster podem estar visíveis para usuários com acesso ao compute.
- Não reutilize o scope de produção em desenvolvimento nem conceda permissões
  mais amplas para contornar erros de acesso.
- Não coloque client secret Value em `download_parameters`; essa variável
  contém somente argumentos de download não secretos.

## 4. Implantar e validar

Antes do deploy, confirme:

- [ ] O scope e a chave já existem no workspace de destino.
- [ ] O segredo foi guardado como `azure-client-secret` e contém o Client
      Secret **Value**, não o Secret ID.
- [ ] O tenant ID, client ID e site ID correspondem ao ambiente do target.
- [ ] A referência no bundle aponta para o scope e a chave desse mesmo
      ambiente.
- [ ] A aplicação tem consentimento e concessão de leitura ao site correto.
- [ ] O catálogo e o schema de destino existem, e quem implanta o bundle tem
      `USE CATALOG`, `USE SCHEMA` e `CREATE VOLUME` no schema.
- [ ] O bundle declara o volume de destino e concede `READ_VOLUME` e
      `WRITE_VOLUME` à identidade do Job.
- [ ] A identidade do Job pode resolver o segredo e tem as permissões
      `USE CATALOG` e `USE SCHEMA`, além da leitura SharePoint necessária.

1. Valide e implante o bundle pelo fluxo de CI/CD ou Databricks CLI aprovado
   para o workspace. O bundle publica a referência do segredo; não é preciso
   colocar o Value em uma variável de deploy.
2. Execute o Job com um arquivo de teste autorizado e não sensível.
3. Confirme que a execução autentica no Graph e grava o arquivo no volume
   esperado.
4. Em caso de falha, consulte a categoria da mensagem e os logs autorizados.
   Não habilite logging de valores secretos para diagnosticar a integração.
5. Após substituir um segredo, garanta que o compute carregue a versão
   atualizada. Clusters existentes podem precisar ser reiniciados; um cluster
   de Job criado novamente deve iniciar com a referência atual.

### Diagnóstico sem revelar o segredo

| Sintoma | Verificações seguras |
|---|---|
| Variável obrigatória ausente | Confira que `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` e a referência `AZURE_CLIENT_SECRET` estão configuradas para a tarefa e cluster. Verifique nomes, nunca imprima valores. |
| Falha de autenticação | Confirme tenant ID, client ID, validade do segredo e se foi armazenado o Value correto. Não copie o segredo para logs ou mensagens. |
| Acesso negado ao SharePoint | Confirme consentimento administrativo, `Sites.Selected` e concessão de leitura da aplicação ao site solicitado. |
| Acesso negado ao volume | Confirme a identidade efetiva do Job e as permissões `USE CATALOG`, `USE SCHEMA` e `WRITE VOLUME`. |
| Referência do segredo não resolvida | Confirme workspace, nome do scope, nome da chave e ACL `READ` da identidade que configura/inicia o cluster. |

## Execução local

Para desenvolvimento local, o projeto pode ler as variáveis de um arquivo
`.env` ignorado pelo Git. Use `.env.example` como referência e nunca compartilhe
nem versione um `.env` com valores reais. Essa configuração local não substitui
o secret scope do Job Databricks.

## Referências

- [Segredos em variáveis de ambiente no Databricks](https://docs.databricks.com/aws/en/security/secrets/secrets-spark-conf-env-var)
- [Variáveis em Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/variables)
- [Parâmetros de Job em Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/job-parameters)
- [Permissões selecionadas do Microsoft Graph](https://learn.microsoft.com/graph/permissions-selected-overview)
