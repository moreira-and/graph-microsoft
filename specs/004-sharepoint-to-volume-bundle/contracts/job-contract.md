# Contrato do Job `sharepoint-download`

**Entrada** (`download_parameters`, JSON array, sem segredos):
`["download", "--library", "<drive-id>", "--volume", "<catalog.schema.volume>", "<caminho1>", "<caminho2>", ...]`

**Ambiente do cluster**: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` (`{{secrets/<scope>/azure-client-secret}}`), `SHAREPOINT_SITE_ID`, `GRAPH_SCOPE`.

**Saída** (stdout), uma linha por arquivo: `<status>\t<nome>\t<caminho no volume | motivo>` e `Total: N baixado, N falha`.

**Código de saída**: 0 sem falhas; 1 se qualquer arquivo ou a configuração falhar (stderr: `Erro (<categoria>): <mensagem>`).

**Garantias**: sobrescreve arquivo existente de forma atômica; não grava arquivo parcial; nunca imprime valores secretos; só transfere os caminhos listados.
