# Quickstart: Validar downloads no volume Databricks

## Pré-requisitos

- Um Job em compute habilitado para Unity Catalog, com runtime compatível com volumes e Python 3.12 ou superior.
- Um volume existente e a identidade efetiva do Job autorizada com `USE CATALOG`, `USE SCHEMA` e `WRITE VOLUME`.
- Credenciais SharePoint e site configurados como no [README do repositório](../../README.md).
- Biblioteca e ao menos um caminho de arquivo legível pelo app SharePoint.
- Para o teste opt-in, um volume dedicado de teste e um arquivo fixture dedicado no SharePoint, com nome exclusivo e autorizado para leitura. Não use um volume de produção.

## Validação local sem rede

1. Sincronize o ambiente e rode os testes padrão:

   ```bash
   uv sync --locked
   uv run pytest
   uv run ruff check
   uv run ruff format --check
   uv run mypy
   ```

2. Confirme que os testes exercitam configuração do destino, separação entre destino local e volume, sobrescrita, colisões de nomes e falhas reportadas. Os testes padrão devem funcionar sem Databricks ou credenciais reais.

## Validação em Databricks

1. Configure a seleção de destino `catalog.schema.volume` no Job e as credenciais SharePoint usando o mecanismo de segredos já adotado no workspace.
2. Execute o comando de download no Job com um arquivo conhecido:

   ```text
   python -m sharepoint_files download --library <LIBRARY_ID> --volume <CATALOG.SCHEMA.VOLUME> <CAMINHO>
   ```

3. Confirme que o arquivo aparece em `/Volumes/<CATALOG>/<SCHEMA>/<VOLUME>/<NOME>` e que o conteúdo corresponde ao arquivo de origem.
4. Execute novamente com um arquivo de mesmo nome e confirme que o conteúdo passa a corresponder à origem mais recente.
5. Solicite dois caminhos diferentes que resolvam para o mesmo nome e confirme que ambos são informados como conflitantes e nenhum é gravado; os demais itens do lote continuam.
6. Verifique uma identidade sem permissão ou um volume inválido em ambiente de teste e confirme erro explícito, sem gravação local alternativa.

## Teste de integração opt-in

Configure os seguintes parâmetros não secretos no ambiente de teste do Job:

| Variável | Valor |
|---|---|
| `DATABRICKS_TEST_VOLUME` | Nome qualificado de um volume isolado: `catalog.schema.volume` |
| `DATABRICKS_TEST_SHAREPOINT_LIBRARY_ID` | Identificador da biblioteca que contém o fixture |
| `DATABRICKS_TEST_SHAREPOINT_FILE_PATH` | Caminho de um fixture SharePoint dedicado com nome exclusivo |

Configure as credenciais Graph pelos segredos do Job e as variáveis SharePoint padrão já usadas pela ferramenta. O fixture e o volume devem ser reservados para esse teste. A integração não deve remover nem modificar arquivos que não tenha criado; execute-a somente no ambiente dedicado.

No compute Databricks com o código e dependências instalados, execute:

```bash
uv run pytest -m integration tests/integration/test_databricks_volume.py
```

O teste deve ser ignorável quando os parâmetros opt-in não estiverem configurados. Quando executado, deve baixar o fixture, verificar o arquivo no volume e exercitar sobrescrita no caminho de destino dedicado; credenciais nunca devem aparecer nos logs.

## Limitação a verificar

Uma falha após o início da escrita pode deixar incompleto o arquivo existente ou um arquivo novo. Não use a execução do Job como transação nem dependa de restauração automática do conteúdo anterior.

Detalhes dos parâmetros estão no [contrato da CLI](contracts/download-cli.md); entidades e validações estão em [data-model.md](data-model.md).
