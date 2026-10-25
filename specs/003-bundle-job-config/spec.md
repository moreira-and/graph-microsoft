# Especificação da Funcionalidade: Configuração do Job via Bundle

**Branch da funcionalidade**: `Não criada`

**Criado em**: 2026-10-25

**Status**: Rascunho

**Entrada**: "outro detalhe: O job vai subir via bundle. isso muda muito as configurações do script python para get dos arquivos do sharepoint e persistencia no volume do bricks?"

## Objetivo e motivação

Operadores precisam implantar e executar o Job de coleta de arquivos do SharePoint por meio de um bundle, sem editar o código-fonte para cada ambiente. A implantação deve fornecer ao processo as configurações e credenciais necessárias e permitir que os arquivos continuem sendo gravados no volume Databricks configurado. A mudança é principalmente na configuração de implantação e execução; o comportamento de leitura do SharePoint e persistência no volume permanece o definido para a funcionalidade de [download para volume Databricks](../002-databricks-volume-download/spec.md).

## Cenários de Usuário e Testes *(obrigatório)*

### História 1 - Implantar e executar o Job (Prioridade: P1)

Como operador, quero implantar e iniciar o Job pelo bundle com as configurações do ambiente, para executar a coleta sem alterar o código do processo.

**Por que esta prioridade**: a implantação pelo bundle é o requisito operacional e deve funcionar sem depender de ajustes manuais no código.

**Teste independente**: implantar o bundle em um ambiente configurado e iniciar o Job; confirmar que ele recebe as configurações necessárias e executa a coleta.

**Cenários de aceitação**:

1. **Dado** um ambiente com os pré-requisitos de acesso configurados, **Quando** o operador implanta e inicia o Job pelo bundle, **Então** o Job inicia a coleta sem edição manual do código-fonte.
2. **Dado** uma execução concluída com sucesso, **Quando** os arquivos selecionados são processados, **Então** eles ficam disponíveis no volume configurado, respeitando as regras da funcionalidade de download para volume.

### História 2 - Promover o Job entre ambientes (Prioridade: P2)

Como operador, quero promover a mesma versão do Job entre ambientes usando as configurações próprias de cada um, para manter o processo consistente sem expor credenciais ou misturar destinos.

**Por que esta prioridade**: a configuração por ambiente reduz erros de implantação e evita alterações manuais no código.

**Teste independente**: implantar a mesma versão em dois ambientes de teste com configurações distintas e confirmar que cada execução usa as credenciais e o volume do respectivo ambiente.

**Cenários de aceitação**:

1. **Dado** dois ambientes com configurações válidas e distintas, **Quando** a mesma versão do Job é implantada em ambos, **Então** cada execução usa apenas as configurações e o destino definidos para seu ambiente.
2. **Dado** que as credenciais são necessárias para acessar o SharePoint, **Quando** o Job é implantado ou executado, **Então** as credenciais não aparecem em texto aberto no código-fonte, nos parâmetros publicados ou nos logs.

### História 3 - Diagnosticar pré-requisitos ausentes (Prioridade: P3)

Como operador, quero receber uma falha clara quando faltarem configurações, credenciais ou permissões, para corrigir o ambiente sem investigar uma gravação silenciosamente redirecionada.

**Por que esta prioridade**: erros explícitos facilitam a operação segura e evitam acreditar que arquivos foram persistidos quando isso não ocorreu.

**Teste independente**: executar o Job de teste com uma configuração ou permissão necessária ausente e confirmar que a execução falha com indicação útil do pré-requisito, sem expor segredos.

**Cenários de aceitação**:

1. **Dado** que uma configuração obrigatória ou credencial não está disponível, **Quando** o Job inicia, **Então** a execução informa a falha e não relata sucesso.
2. **Dado** que a identidade do Job não pode ler a origem ou gravar no destino, **Quando** o Job processa a solicitação, **Então** a falha é informada sem usar um destino alternativo silenciosamente.
3. **Dado** um operador preparando uma implantação, **Quando** consulta a documentação operacional, **Então** encontra os valores por ambiente, os pré-requisitos de acesso e as etapas para validar a implantação e a execução, sem credenciais reais.

### Casos de Borda

- O bundle é implantado em um ambiente sem uma configuração obrigatória.
- Uma referência de credencial está ausente ou não pode ser resolvida durante a execução.
- A identidade efetiva do Job não possui acesso de leitura à origem ou permissão de gravação no volume.
- O Job inicia, mas a execução falha durante a leitura ou gravação; o resultado deve seguir as regras de falha individuais já definidas para o download.
- Uma promoção entre ambientes mantém configurações de outro ambiente por engano.

## Requisitos *(obrigatório)*

### Requisitos Funcionais

- **FR-001**: O operador DEVE poder implantar e iniciar o Job por meio do bundle, sem editar manualmente o código-fonte para cada ambiente.
- **FR-002**: A configuração do Job DEVE fornecer ao processo os valores não secretos necessários para identificar a origem SharePoint, selecionar os arquivos e definir o volume de destino.
- **FR-003**: Credenciais necessárias para acessar o SharePoint DEVEM ser fornecidas por referências protegidas disponíveis no ambiente de execução; elas NÃO DEVEM ser incluídas em texto aberto no código-fonte, em parâmetros publicados ou em logs.
- **FR-004**: Cada ambiente DEVE usar as próprias configurações, referências de credenciais, identidade de execução e destino de volume, sem reutilizar silenciosamente valores de outro ambiente.
- **FR-005**: Com configurações e permissões válidas, o Job DEVE manter o fluxo existente de leitura de arquivos do SharePoint e persistência no volume, conforme a [especificação de download para volume Databricks](../002-databricks-volume-download/spec.md).
- **FR-006**: Se configuração, credenciais, acesso à origem ou permissão de gravação estiverem ausentes ou inválidos, o Job DEVE informar a falha e NÃO DEVE indicar sucesso nem redirecionar a gravação para outro destino silenciosamente.
- **FR-007**: A documentação operacional DEVE identificar os valores que precisam ser configurados por ambiente, os pré-requisitos de acesso e como validar uma implantação e execução bem-sucedidas, sem incluir credenciais reais.
- **FR-008**: O bundle DEVE declarar o volume Unity Catalog gerenciado no catálogo e schema configurados e conceder leitura/escrita à identidade do Job, sem remover o volume em um `bundle destroy`.
- **FR-009**: O bundle DEVE fornecer um Job independente serverless que grava `test.txt` com a hora UTC da execução no volume e verifica o conteúdo sem acessar SharePoint ou exigir credenciais Microsoft.

### Entidades Principais

- **Ambiente de implantação**: contexto que define as configurações, referências de credenciais, identidade e destino próprios de uma implantação do Job.
- **Configuração do Job**: valores não secretos que orientam a origem, a seleção de arquivos e o destino de uma execução.
- **Referência de credencial**: referência protegida usada para disponibilizar credenciais necessárias ao acesso à origem durante a execução.
- **Execução do Job**: tentativa de coletar os arquivos selecionados e persistir os resultados no destino de volume configurado.

## Critérios de Sucesso *(obrigatório)*

### Resultados Mensuráveis

- **SC-001**: Em 100% das implantações válidas testadas, o operador consegue iniciar o Job sem editar o código-fonte para adaptar o ambiente.
- **SC-002**: Em 100% das execuções de teste, cada ambiente usa sua própria configuração e destino, e nenhuma credencial aparece em código-fonte, parâmetros publicados ou logs.
- **SC-003**: Em 100% das execuções válidas de ponta a ponta, os arquivos selecionados e baixados com sucesso ficam disponíveis no volume configurado, de acordo com as regras de download existentes.
- **SC-004**: Em 100% dos testes com configuração ou permissão obrigatória ausente, a execução informa uma falha em vez de indicar sucesso ou usar um destino alternativo silenciosamente.
- **SC-005**: Em 100% dos targets válidos, o bundle provisiona o volume declarado e a identidade do Job consegue ler e gravar arquivos de teste no volume.
- **SC-006**: O Job de teste do volume grava e relê `test.txt` com `current_time` UTC, reporta sucesso somente com conteúdo confirmado e não requer autenticação SharePoint.

## Pressupostos

- O Job e o processo de download já existem; esta funcionalidade cobre a implantação e a configuração por ambiente, não uma nova forma de selecionar ou baixar arquivos.
- O bundle configura o Job e seus valores por ambiente; a autenticação e a gravação continuam sendo realizadas pelo processo existente durante a execução.
- Na primeira versão, os caminhos do SharePoint são definidos na configuração do Job para cada ambiente; alterá-los exige atualizar e implantar novamente o bundle. Parâmetros para escolher caminhos a cada execução estão fora do escopo.
- Cada ambiente de destino já possui um runtime compatível, acesso de rede ao SharePoint, catálogo e schema Unity Catalog existentes e identidade autorizada a ler a origem e gravar no destino.
- As regras de sobrescrita, tratamento de falha e limites de download permanecem as definidas na especificação de download para volume.
- O bundle cria o volume Unity Catalog gerenciado e concede permissões no volume à identidade do Job. Catálogo, schema, acessos aos objetos pai, grants SharePoint e credenciais são pré-requisitos administrados por ambiente.
