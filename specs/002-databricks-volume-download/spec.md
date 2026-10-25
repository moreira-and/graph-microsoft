# Especificação da Funcionalidade: Download para volume Databricks

**Branch da funcionalidade**: `002-databricks-volume-download`

**Criado em**: 2026-10-25

**Status**: Rascunho

**Entrada**: "contexto: este código .py vai rodar em um JOB do databricks. A ideia é: este arquivo que hoje está sendo realizado o download escreva/sobreescreva em um volume de ${catalogo}.${shema}.${volume} no databricks."

## Objetivo e motivação

Operadores que executam a ferramenta em um Job do Databricks precisam encontrar os arquivos baixados diretamente em um volume do Unity Catalog, sem depender de uma cópia em disco local ou de uma etapa manual posterior. Quando um arquivo com o mesmo nome já existe no volume, a nova execução deve substituí-lo pelo conteúdo baixado.

## Clarifications

### Session 2026-10-25

- Q: O que o Job deve fazer quando dois arquivos solicitados têm o mesmo nome, mas vêm de caminhos diferentes do SharePoint? → A: Rejeitar os arquivos conflitantes antes de gravá-los, informar os caminhos envolvidos e processar os demais itens do lote.
- Q: Qual requisito de sobrescrita o Job deve garantir quando um arquivo já existe no volume? → A: Usar escrita padrão no volume; falhas podem deixar o arquivo existente incompleto, documentando essa limitação.

## Cenários de Usuário e Testes *(obrigatório)*

### História 1 - Gravar downloads no volume do Job (Prioridade: P1)

Como operador de um Job do Databricks, quero informar o volume de destino e receber nele os arquivos selecionados do SharePoint, substituindo arquivos com o mesmo nome, para que os dados estejam disponíveis no local compartilhado esperado após a execução.

**Por que esta prioridade**: disponibilizar os arquivos no volume é o objetivo principal e elimina a necessidade de mover manualmente downloads locais.

**Teste independente**: executar um Job com um volume de destino válido e um arquivo de origem conhecido; confirmar que o conteúdo esperado aparece no volume e que uma segunda execução atualiza esse conteúdo.

**Cenários de aceitação**:

1. **Dado** um Job com catálogo, schema e volume existentes e graváveis, **Quando** um arquivo solicitado é baixado, **Então** o arquivo aparece na raiz do volume com o mesmo nome e conteúdo de origem.
2. **Dado** um arquivo com o mesmo nome já existente na raiz do volume, **Quando** o download desse arquivo termina com sucesso, **Então** o conteúdo anterior é substituído pelo conteúdo recém-baixado.
3. **Dado** um destino ausente, inválido, inexistente ou sem permissão de gravação, **Quando** o Job tenta baixar um arquivo, **Então** a operação informa a falha e não grava o arquivo em um destino local alternativo.
4. **Dado** uma falha ao baixar o conteúdo antes de abrir o destino, **Quando** a operação termina, **Então** a falha é informada e o arquivo existente não é alterado.
5. **Dado** uma falha após o início da gravação de um arquivo no volume, **Quando** a operação termina, **Então** a falha é informada, mas o conteúdo existente ou novo pode ficar incompleto.
6. **Dado** uma falha em um arquivo de um lote, **Quando** a execução termina, **Então** cada arquivo continua tendo seu resultado individual informado e os arquivos concluídos permanecem disponíveis.
7. **Dado** um operador que usa o fluxo local existente fora de um Job do Databricks, **Quando** realiza um download local, **Então** o comportamento e o destino local existentes permanecem inalterados.
8. **Dado** um lote ou arquivo que excede um limite atual da ferramenta, **Quando** o Job processa a solicitação, **Então** o limite continua sendo aplicado e o item que não pode ser processado é informado sem gravação inválida no destino.
9. **Dado** o mesmo usuário, permissões e seleção de arquivos usados atualmente, **Quando** o destino é configurado como volume, **Então** a configuração de destino não altera quais arquivos do SharePoint podem ser listados, localizados ou baixados.
10. **Dado** dois arquivos solicitados em caminhos diferentes do SharePoint com o mesmo nome, **Quando** o lote é preparado, **Então** ambos são informados como conflitantes antes de qualquer um deles ser gravado, e os demais itens sem conflito podem ser processados.
11. **Dado** que o destino selecionado é um volume, **Quando** o operador também informa a opção `--overwrite`, **Então** a configuração é recusada antes de iniciar downloads; a sobrescrita no volume é sempre automática e essa opção permanece exclusiva do destino local.

### Casos de Borda

- Um ou mais componentes do nome qualificado do volume (catálogo, schema ou volume) estão ausentes ou vazios.
- O volume não existe, está indisponível ou o Job não tem permissão para gravar nele.
- O download remoto falha antes da abertura do destino; o arquivo existente não deve ser alterado.
- A gravação no volume falha depois de começar; o arquivo existente ou novo pode ficar incompleto.
- O download remoto falha ou é interrompido durante a execução de um lote.
- Um lote contém mais arquivos do que o limite já aceito pela ferramenta.
- Arquivos em caminhos diferentes do SharePoint têm o mesmo nome e disputariam o mesmo destino na raiz do volume.
- A opção `--overwrite` é fornecida junto com um destino de volume.

## Requisitos *(obrigatório)*

### Requisitos Funcionais

- **FR-001**: O sistema DEVE permitir que um Job do Databricks informe um volume de destino identificado por catálogo, schema e volume.
- **FR-002**: Quando o destino de volume estiver configurado, o sistema DEVE gravar cada arquivo baixado com sucesso na raiz desse volume e manter o nome original do arquivo.
- **FR-003**: No destino de volume, o sistema DEVE substituir um arquivo existente de mesmo nome pelo conteúdo recém-baixado após a conclusão bem-sucedida do download.
- **FR-004**: O sistema DEVE informar claramente falhas de configuração, disponibilidade ou permissão do volume e NÃO DEVE redirecionar silenciosamente esses downloads para armazenamento local.
- **FR-005**: Se o download remoto falhar antes da abertura do destino, o sistema DEVE preservar o arquivo existente. Se a gravação no volume falhar após começar, o sistema DEVE informar a falha, mas o arquivo existente ou novo pode ficar incompleto; não há garantia de atomicidade.
- **FR-006**: O sistema DEVE informar o resultado individual de cada arquivo, preservando os resultados dos arquivos concluídos quando outro item do lote falhar.
- **FR-007**: O sistema DEVE manter disponível e inalterado o fluxo de download para destino local já existente.
- **FR-008**: O sistema DEVE manter os limites atuais de lote e tamanho de arquivo.
- **FR-009**: A configuração do destino de volume NÃO DEVE ampliar o acesso de leitura ao SharePoint nem alterar a seleção de arquivos permitida pelo comportamento existente.
- **FR-010**: Antes de gravar arquivos de um lote no volume, o sistema DEVE identificar nomes repetidos provenientes de caminhos diferentes do SharePoint, informar os itens conflitantes e não gravar nenhum desses itens; os demais itens sem conflito podem ser processados.
- **FR-011**: A sobrescrita de arquivos existentes DEVE ser automática quando o destino é volume. O sistema DEVE rejeitar `--overwrite` em conjunto com destino de volume antes de baixar qualquer arquivo; a opção permanece aplicável somente ao destino local.

### Entidades Principais

- **Destino de volume**: local identificado pelo catálogo, schema e volume configurados para o Job.
- **Arquivo baixado**: arquivo selecionado no SharePoint, identificado pelo nome e conteúdo; no destino de volume, ocupa a raiz do volume.
- **Resultado de download**: situação individual de cada arquivo, incluindo sucesso ou falha e uma explicação útil para o operador.
- **Execução do Job**: execução que fornece o destino do volume e reúne os resultados dos downloads solicitados.

## Critérios de Sucesso *(obrigatório)*

### Resultados Mensuráveis

- **SC-001**: Em todos os testes com destino válido, 100% dos arquivos baixados com sucesso ficam acessíveis no destino compartilhado configurado, com o nome e conteúdo esperados.
- **SC-002**: Em 100% dos testes de substituição bem-sucedida, o arquivo de mesmo nome contém o conteúdo da execução mais recente.
- **SC-003**: Em todos os testes de falha de configuração, disponibilidade, permissão ou gravação, a falha é informada e nenhum destino alternativo é usado.
- **SC-004**: Em todos os testes em que o download remoto falha antes da escrita, 100% dos arquivos existentes permanecem inalterados.
- **SC-005**: A documentação informa que uma gravação padrão no volume pode deixar incompleto o conteúdo anterior ou um arquivo novo quando a escrita falha.
- **SC-006**: Operadores conseguem obter os arquivos no volume como resultado do Job sem uma etapa manual de cópia local para o volume.
- **SC-007**: Os testes do fluxo local existente continuam a produzir os mesmos resultados e destinos de antes da mudança.

## Premissas

- O nome do destino é fornecido ao Job como catálogo, schema e volume; `shema` na descrição original refere-se a `schema`.
- Os arquivos são gravados na raiz do volume e mantêm o nome original, seguindo o comportamento atual de downloads locais.
- A identidade usada pelo Job já possui permissão de gravação no volume; configurar concessões e permissões do Unity Catalog está fora do escopo.
- A gravação no volume usa escrita padrão sequencial; sobrescritas não oferecem garantia de atomicidade nem de restauração do conteúdo anterior após falha.
- Autenticação, permissões de leitura do SharePoint, seleção dos arquivos, limites de lote e tamanho permanecem conforme o comportamento existente.
- O modo local continua disponível para execuções que não selecionam o destino de volume.

## Fora de Escopo

- Alterar, mover, renomear ou excluir arquivos no SharePoint.
- Criar volumes ou conceder permissões de acesso a eles.
- Sincronizar diretórios, excluir arquivos do volume ou preservar a estrutura de pastas do SharePoint.
- Modificar os fluxos de autenticação ou de seleção de arquivos existentes.
