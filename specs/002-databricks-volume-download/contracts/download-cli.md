# Contract: CLI de download com volume Databricks

## Operação

```text
python -m sharepoint_files download --library <LIBRARY_ID> [--dest <LOCAL_DIRECTORY> | --volume <CATALOG.SCHEMA.VOLUME>] [--overwrite] <PATH>...
```

## Seleção do destino

- `--volume CATALOG.SCHEMA.VOLUME` seleciona a raiz `/Volumes/CATALOG/SCHEMA/VOLUME`.
- Se `--volume` não for informado, o modo local existente continua usando `--dest` ou `DOWNLOAD_DIR`.
- Se ambos os destinos forem especificados, a CLI rejeita a configuração antes de baixar qualquer item.
- Se o destino do modo escolhido estiver ausente, inválido ou sem permissão, a CLI informa erro e não troca para outro destino.
- No modo volume, arquivos de mesmo nome são sobrescritos após o conteúdo completo ter sido recebido do SharePoint; `--overwrite` é uma opção somente do modo local.

## Colisões

Antes de gravar qualquer item no volume, a execução identifica nomes repetidos no lote. Todos os itens conflitantes são reportados como falha, incluindo os caminhos de origem; itens sem colisão continuam.

## Resultados e falhas

- Cada item reporta nome, status e caminho ou motivo.
- Uma falha de gravação resulta em status de falha e código de saída diferente de zero.
- Uma escrita iniciada no volume não garante atomicidade: se falhar, o arquivo existente ou novo pode ficar incompleto.
- Nenhuma credencial, token ou URL pré-autenticada é incluída no relatório.
- Limite existente permanece em 20 itens por lote e 100 MB por arquivo.

## Compatibilidade

A forma de invocação local e o comportamento local existente não mudam.
