# Data Model: Download para volume Databricks

Este fluxo não introduz armazenamento de metadados persistente. As entidades abaixo são valores de configuração e resultados transitórios de uma execução.

## Destino de volume

Identifica a raiz onde os arquivos baixados são gravados.

| Campo | Tipo lógico | Regra |
|---|---|---|
| catalog | Texto | Obrigatório quando modo volume é selecionado; componente não vazio de nome qualificado |
| schema | Texto | Obrigatório quando modo volume é selecionado; componente não vazio de nome qualificado |
| volume | Texto | Obrigatório quando modo volume é selecionado; componente não vazio de nome qualificado |
| qualified_name | Texto | Forma de configuração `catalog.schema.volume`; deve conter exatamente três componentes não vazios |
| root_path | Caminho | Resolvido como `/Volumes/<catalog>/<schema>/<volume>` |

**Validação**: recusar nome ausente, vazio ou malformado com erro de configuração. A raiz do volume é fornecida pelo Unity Catalog; o programa não a cria. Erros de inexistência e permissão são reportados sem fallback local.

## Pedido de download

Representa um arquivo de origem previamente resolvido no SharePoint.

| Campo | Tipo lógico | Regra |
|---|---|---|
| source_path | Texto | Caminho solicitado dentro da biblioteca |
| name | Texto | Nome de arquivo remoto; é o nome do destino na raiz do volume |
| item_id | Texto | Identificador do arquivo de origem |
| size | Inteiro opcional | Ausência ou valor acima do limite existente causa falha individual |
| destination_name | Texto | Nome resolvido para gravação; igual a `name` |

**Identidade/uniqueness**: `destination_name` identifica o alvo no lote. Se mais de um pedido resolver para o mesmo nome, todos os pedidos com aquele nome são conflitos e não são gravados.

## Resultado de download

| Campo | Tipo lógico | Regra |
|---|---|---|
| name | Texto | Nome do pedido reportado |
| status | Enum | Baixado, falha ou ignorado conforme o contrato de download |
| path | Caminho opcional | Destino gravado ou alvo associado ao resultado |
| reason | Texto opcional | Mensagem sem segredos/URLs pré-autenticadas; inclui conflitos e falhas de gravação |

No modo volume, um arquivo existente é sobrescrito. Se a escrita falhar depois de iniciada, o estado do alvo pode ficar incompleto; o resultado será falha e não implica restauração.

## Execução do Job

Agrupa destino de volume, biblioteca e a sequência de pedidos. O limite existente é de 20 pedidos por lote e 100 MB por arquivo. Resultados são individuais; falha de um item não apaga os resultados dos demais.
