# Modelo de Dados

Sem persistência nova. Entidades em memória já existentes em `downloads.py`:

| Entidade | Campos | Regras |
|---|---|---|
| `DownloadRequest` | `drive_id`, `item_id`, `name`, `size`, `source_path` | `size` obrigatório e ≤ 100 MB; nome único no lote |
| `DownloadResult` | `name`, `status`, `path`, `reason` | `status` ∈ baixado, falha |
| `DownloadReport` | `results` | exit code 1 se houver falha |

**Configuração por target (bundle)**: `azure_tenant_id`, `azure_client_id`, `client_secret_reference` (referência, não valor), `sharepoint_site_id`, `volume_catalog`, `volume_schema`, `volume_name`, `job_service_principal_name`, `download_parameters` (lista explícita de caminhos).

**Transição de um arquivo no volume**: ausente/antigo → (temporário `.part` escrito) → substituído atomicamente; em falha, o temporário é removido e o conteúdo anterior permanece.
