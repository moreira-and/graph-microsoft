# Research: Download para volume Databricks

**Date**: 2026-10-25

## Decisões

### Acesso ao volume

- **Decision**: Usar o caminho POSIX do Unity Catalog `/Volumes/<catalog>/<schema>/<volume>/<file>` com operações padrão de arquivo em Python executadas no driver do Job.
- **Rationale**: É o formato documentado para volumes e permite manter a implementação simples, usando os recursos Python e o fluxo de downloads já existentes.
- **Alternatives considered**: `dbfs:/Volumes/...` para operações orientadas a Spark; caminho de armazenamento do provider; Files API do workspace. Não são necessários para a escrita Python de um arquivo completo no driver.
- **Sources**:
  - [Databricks: Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes)
  - [Databricks: Work with files in Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes/volume-files)
  - [Databricks: Work with files in Unity Catalog volumes (file access)](https://docs.databricks.com/aws/en/files)

### Escrita e sobrescrita

- **Decision**: Baixar o conteúdo completo antes de abrir o destino; em seguida, gravar sequencialmente no arquivo do volume. Sobrescrever por padrão para esse destino, sem prometer atomicidade ou preservação do conteúdo anterior em caso de falha durante a escrita.
- **Rationale**: Corresponde à escolha registrada pelo usuário e evita tocar no arquivo existente quando o download remoto falha antes de a gravação começar. Unity Catalog volumes suportam escrita sequencial; falhas de gravação no próprio destino podem, contudo, deixar conteúdo incompleto.
- **Alternatives considered**:
  - Files API com sobrescrita condicional: oferece controles de condição/ETag documentados em uma funcionalidade Beta que requer habilitação do administrador; descartada por acrescentar uma dependência operacional que o usuário não escolheu.
  - Arquivo temporário seguido por `os.rename()`/`dbutils.fs.mv()`: a documentação consultada não garante que mover/renomear no mesmo volume seja uma troca atômica.
  - Cópia local para volume com `shutil.copyfile()`: continua sendo escrita sequencial e não fornece promessa documentada de rollback do destino.
- **Source**: [Databricks: Work with files in Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes/volume-files) e [Databricks: Files API](https://docs.databricks.com/aws/en/volumes/files-api).

### Compute e permissões

- **Decision**: O Job deve usar compute habilitado para Unity Catalog, com suporte a volumes, e runtime que suporte Python 3.12 ou superior. A documentação de volumes indica DBR 13.3 LTS ou superior para acesso ao volume; deve-se selecionar um runtime que também satisfaça o requisito Python do projeto.
- **Rationale**: Volumes dependem de compute compatível com Unity Catalog e o projeto declara Python 3.12 como mínimo.
- **Alternatives considered**: Fazer o Job gravar primeiro em disco local e deixar outra etapa transferir o conteúdo; isso não atende à exigência de arquivos disponíveis diretamente no volume como resultado da execução.
- **Required privileges**: `USE CATALOG`, `USE SCHEMA` e `WRITE VOLUME` para a identidade efetiva do Job.
- **Sources**:
  - [Databricks: Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes)
  - [Databricks: Upload files to a volume](https://docs.databricks.com/aws/en/volumes/volume-files)
  - [Databricks: Unity Catalog privileges reference](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control/privileges-reference)

### Colisões de nome

- **Decision**: Detectar colisões de nomes na lista de destinos do lote antes de iniciar gravações no volume; marcar todos os pedidos conflitantes como falha e continuar com destinos sem colisão.
- **Rationale**: Todos os arquivos são gravados na raiz e mantêm o nome original. Rejeitar pares conflitantes impede que a ordem da lista decida silenciosamente qual conteúdo prevalece e implementa a clarificação escolhida.
- **Alternatives considered**: Manter o último arquivo do lote ou inserir diretórios de origem no volume; ambas alterariam o comportamento aceito na especificação.

## Limitações operacionais para documentar

- A gravação padrão diretamente no arquivo de destino não garante que conteúdo anterior permaneça íntegro se a gravação falhar após iniciar.
- Uma falha durante a escrita pode deixar incompleto um arquivo novo ou existente; o relatório do item deve indicar a falha, mas não pode prometer rollback.
- Não usar `os.rename()` ou `dbutils.fs.mv()` como garantia de atomicidade, pois as fontes consultadas não documentam atomicidade de troca dentro do mesmo volume.
- O volume precisa existir antes do Job e sua identidade efetiva deve possuir os privilégios necessários.
