# Pesquisa: SharePoint → Volume via bundle

## Estado atual verificado no código

- `download_volume_paths` resolve o lote, rejeita nomes duplicados e grava no volume; a CLI retorna código 1 se houver falha e recusa `--overwrite` em modo volume (sobrescreve por padrão).
- `_download_volume_one` grava com `target.open("wb")`: em falha no meio da escrita sobra arquivo parcial. Contradiz RF-005a/RF-006.
- `_write_atomic` (arquivo temporário `.part` + `os.replace`) já existe para o modo local.
- O Job usa `python_wheel_task` com `download_parameters`, cluster `SINGLE_USER`, `run_as` service principal e o segredo via `{{secrets/...}}` em `spark_env_vars`.

## Decisões

### 1. Gravação atômica no volume
- **Decisão**: reutilizar `_write_atomic` em `_download_volume_one` (temp no mesmo diretório + `os.replace`).
- **Racional**: menor mudança; sobrescreve e evita parcial.
- **Risco**: rename em `/Volumes` (FUSE) pode ter restrições. Validar no workspace (quickstart, passo 4). Se `os.replace` falhar, o erro vira falha do arquivo e o temporário é removido; só então avaliar alternativa.
- **Alternativas**: manter `open("wb")` (viola a spec); gravar em `/tmp` e copiar (mantém não atomicidade na cópia).

### 2. Lista explícita de caminhos por target
- **Decisão**: manter `download_parameters` (JSON) como variável por target, contendo biblioteca, `--volume` e caminhos; nada fora da lista é lido.
- **Alternativas**: pasta recursiva ou delta (rejeitadas na clarificação).

### 3. Segredo
- **Decisão**: manter referência `{{secrets/<scope>/azure-client-secret}}` em variável de ambiente do cluster; scopes separados por target, `READ` só ao service principal.
- **Limite conhecido**: quem executa código no cluster pode ler a variável; mitigado por `SINGLE_USER`. Certificado/federated credentials ficam fora de escopo.

### 4. Remoção do que difere do fluxo
- **Decisão**: remover `resources/volume_smoke_job.yml` e `notebooks/test_volume.py`, e a menção em `tests/unit/test_downloads.py`, se for específica do notebook. O modo local da CLI (`--dest`, `--overwrite`, `DOWNLOAD_DIR`) também foi removido (T016), pois o Job usa apenas o modo volume.

### 5. Sem vazamento de segredo
- **Decisão**: teste unitário que força erro de autenticação e verifica que o valor do segredo não aparece em stdout/stderr.
