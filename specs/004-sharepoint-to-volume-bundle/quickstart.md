# Quickstart: validação ponta a ponta

Pré-requisitos: CLI Databricks autenticada, scope `sharepoint-dev` com `azure-client-secret`, variáveis do target `dev` definidas (ver [credential-setup.md](../../docs/secret_config/credential-setup.md) e [contrato](./contracts/job-contract.md)).

1. Verificações locais: `uv run ruff check . && uv run mypy src && uv run pytest tests/unit`
2. Validar o bundle: `databricks bundle validate -t dev`
3. Deploy: `databricks bundle deploy -t dev`
4. Executar: `databricks bundle run sharepoint_download -t dev` — esperado: linha `baixado` por arquivo da lista e `Total: N baixado, 0 falha`.
5. Conferir no volume que o conteúdo é idêntico à origem (tamanho/hash).
6. Reexecutar o Job: os arquivos são sobrescritos e nenhum `.part` permanece no volume.
7. Falhas: usar um caminho inexistente e depois um segredo inválido; esperado exit 1, mensagem com a causa, nenhum arquivo parcial e o segredo ausente da saída.
8. Repetir 3–4 com `-t test` e confirmar site, scope e volume independentes.
