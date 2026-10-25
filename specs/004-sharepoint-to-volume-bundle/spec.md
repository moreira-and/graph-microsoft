# Especificação da Funcionalidade: Transferência direta SharePoint → Volume Databricks via deploy do bundle

**Branch da funcionalidade**: `Não criada`

**Criado em**: 2026-10-25

**Status**: Rascunho

**Entrada**: "como já testamos a escrita no databricks, pode fazer o túnel direto do sharepoint -> databricks volumes via deploy do bundle. O que for diferente disso pode ser removido."

## Clarificações

### Sessão 2026-10-25

- Q: Quando um arquivo do SharePoint já existe no volume, o Job deve sobrescrevê-lo, ignorá-lo ou falhar? → A: Sobrescrever, com gravação atômica.
- Q: Como a pessoa define quais arquivos do SharePoint o Job transfere? → A: Lista explícita de caminhos por target, no bundle.

## Cenários de Usuário e Testes *(obrigatório)*

### História 1 - Deploy do bundle e execução do Job que copia SharePoint para o volume (Prioridade: P1)

A pessoa responsável faz o deploy do bundle em um target e executa o Job. O Job autentica no SharePoint com as credenciais do ambiente, lê os arquivos selecionados e os grava diretamente no volume gerenciado, sem passar por disco local nem por etapa intermediária.

**Por que esta prioridade**: É o único fluxo de valor da integração. A escrita no volume já foi validada, então esta é a peça que falta.

**Teste independente**: Fazer o deploy em `dev`, executar o Job com um arquivo conhecido do site e conferir que ele aparece no volume com o mesmo conteúdo.

**Cenários de aceitação**:

1. **Dado** um bundle implantado com configuração e segredo do ambiente válidos, **Quando** o Job é executado, **Então** os arquivos selecionados do SharePoint existem no volume com conteúdo idêntico à origem.
2. **Dado** que o arquivo já existe no volume, **Quando** o Job é executado novamente, **Então** o arquivo do volume é sobrescrito pelo conteúdo atual da origem e o resultado é informado por arquivo.
3. **Dado** o mesmo bundle, **Quando** é implantado nos targets `dev` e `test`, **Então** cada um usa seu próprio site, segredo e volume, sem interferência.

---

### História 2 - Falhas claras e sem vazamento de segredo (Prioridade: P2)

Quando algo falha (credencial inválida, site sem permissão, arquivo inexistente, volume inacessível), o Job termina com erro indicando a causa e o arquivo afetado, sem expor o client secret.

**Por que esta prioridade**: Operar o Job sem diagnóstico claro obriga a investigar logs manualmente.

**Teste independente**: Executar o Job com um caminho inexistente e com credencial inválida; ambos devem falhar com mensagem específica e sem valores secretos.

**Cenários de aceitação**:

1. **Dado** um caminho de origem inexistente, **Quando** o Job é executado, **Então** ele falha indicando o caminho e não grava arquivo parcial no volume.
2. **Dado** credencial inválida ou sem permissão no site, **Quando** o Job é executado, **Então** a falha identifica autenticação ou autorização e não exibe o segredo.

---

### Casos de Borda

- Arquivo grande que excede o tempo normal de transferência.
- Nome de arquivo ou pasta com caracteres especiais ou acentos.
- Transferência interrompida no meio: não deve restar arquivo corrompido apresentado como completo.
- Segredo cadastrado em escopo de outro ambiente.

## Requisitos *(obrigatório)*

### Requisitos Funcionais

- **RF-001**: O deploy do bundle DEVE criar ou atualizar o Job que transfere arquivos do SharePoint diretamente para o volume gerenciado do target.
- **RF-001a**: Os arquivos transferidos DEVEM ser definidos por uma lista explícita de caminhos de origem configurada em cada target; o Job NÃO DEVE transferir nada fora dessa lista.
- **RF-002**: O Job DEVE usar a configuração não secreta do target e o client secret guardado no escopo de segredos do workspace.
- **RF-003**: Os arquivos DEVEM ser gravados no volume sem etapa intermediária persistida fora dele.
- **RF-004**: O conteúdo gravado DEVE ser idêntico ao da origem.
- **RF-005**: O Job DEVE informar, por arquivo, o resultado da transferência.
- **RF-005a**: Se o arquivo já existir no volume, o Job DEVE sobrescrevê-lo, de forma que o volume nunca apresente conteúdo parcial ou misto durante a substituição.
- **RF-006**: Em falha, o Job DEVE terminar com erro, indicar a causa e o item afetado, e não deixar arquivo parcial no volume.
- **RF-007**: Valores secretos NUNCA DEVEM aparecer em parâmetros do bundle, logs, saídas ou mensagens de erro.
- **RF-008**: Cada target (`dev`, `test`) DEVE ter site, segredo e volume independentes.
- **RF-009**: Tudo que não contribui para esse fluxo (artefatos de teste de escrita já validado, verificações de prontidão e caminhos de download local no Job) DEVE ser removido do bundle e da documentação do fluxo.

### Entidades-Chave

- **Bundle/target**: conjunto de configuração implantável de um ambiente.
- **Job de transferência**: execução que lê do SharePoint e grava no volume.
- **Volume gerenciado**: destino final dos arquivos.
- **Segredo do ambiente**: client secret referenciado, nunca copiado.

## Critérios de Sucesso *(obrigatório)*

### Resultados Mensuráveis

- **CS-001**: Após o deploy, uma execução do Job entrega os arquivos selecionados no volume em uma única execução, sem passos manuais.
- **CS-002**: 100% dos arquivos transferidos têm conteúdo idêntico à origem nos testes.
- **CS-003**: Em 100% das execuções, nenhum valor secreto aparece em saídas ou registros.
- **CS-004**: Falhas por caminho, credencial ou permissão são atribuídas à causa correta em 100% dos casos de teste.
- **CS-005**: Nenhum recurso do bundle existe sem uso no fluxo SharePoint → volume.

## Premissas

- A escrita no volume já foi validada; não será retestada como funcionalidade própria.
- A autenticação, o segredo no escopo e a identidade do Job seguem a especificação 003 e `docs/secret_config/credential-setup.md`.
- O `.env` serve apenas ao desenvolvimento local; o Job usa a configuração do bundle.
- Fora de escopo: verificador de prontidão do `.env`, download para disco local via Job, implantação em produção.
- O Job de teste de escrita (`resources/volume_smoke_job.yml`) e o notebook `notebooks/test_volume.py` foram removidos nesta implementação (RF-009).
