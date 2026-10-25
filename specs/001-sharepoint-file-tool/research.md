# Pesquisa: Ferramenta de arquivos do SharePoint

## 1. Resolução do site

- **Decisão**: usar `client.sites.by_site_id(...)` com o ID, ou com `"{hostname}:/{caminho}"` (ex.: `contoso.sharepoint.com:/sites/equipe`) para hostname e caminho. Nenhum endpoint de busca.
- **Justificativa**: ambos são acessos diretos compatíveis com Sites.Selected; o SDK expõe `by_site_id` e a sintaxe de caminho é aceita pelo Graph.
- **Alternativas**: busca de sites (`sites?search=`, `get_all_sites`), rejeitada por ser incompatível com Sites.Selected.

## 2. Bibliotecas, listagem e localização

- **Decisão**: bibliotecas por `sites/{id}/drives`; itens por `drives/{id}/items/{item}/children` (a raiz usa o item `root`). A localização percorre apenas a pasta informada, filtrando o nome (contém, sem diferenciar maiúsculas/minúsculas) e entrando em subpastas de forma recursiva e explícita; localização por caminho exato usa `root:/{caminho}` (acesso direto). Não usa `search(q=...)`.
- **Justificativa**: `children` e acesso por caminho funcionam com Sites.Selected; a recursão limita-se ao escopo pedido.
- **Alternativas**: `search_with_q` (existe em `DriveItemItemRequestBuilder`), rejeitada pela restrição do pedido; `delta`, fora de escopo.

## 3. Paginação

- **Decisão**: laço que lê `value` e segue `odata_next_link` com `request_builder.with_url(next_link).get()` até não haver mais link; retorna lista completa.
- **Justificativa**: é o padrão do SDK e atende a FR-007; a lista final é pequena no escopo previsto.
- **Alternativas**: iterador de páginas do SDK (`PageIterator`), rejeitado por esconder o comportamento que os testes precisam controlar.

## 4. Retry e HTTP 429

- **Decisão**: não implementar retry próprio. O middleware padrão do SDK (`RetryHandler` do kiota) já repete 429/503/504 respeitando `Retry-After`, com 3 tentativas por padrão. A ferramenta apenas traduz o erro final para `GraphToolError` com a categoria "limitação" e, quando presente, o `Retry-After`.
- **Justificativa**: evita uma segunda política (FR-016). Verificado no código instalado: `RetryHandlerOption` com padrão de 3 tentativas e uso de `Retry-After`.
- **Alternativas**: laço próprio de backoff, rejeitado por duplicar o SDK.

## 5. Timeouts

- **Decisão**: criar o cliente HTTP com `httpx.AsyncClient(timeout=...)` via `GraphClientFactory.create_with_default_middleware`, mantendo os middlewares padrão. Padrões: 30 s para chamadas de listagem e 120 s para download, configuráveis por argumento da biblioteca. `httpx.TimeoutException` vira `GraphToolError` (categoria timeout).
- **Justificativa**: preserva o retry do SDK e dá limite explícito a cada chamada. Como o cliente tem um único timeout, serão dois clientes (listagem e download) criados por `client.py`. `httpx` é dependência transitiva do SDK; declará-la em `pyproject.toml` evita depender de um import indireto.
- **Alternativas**: `asyncio.wait_for` por chamada, aceita como reserva se a configuração do `httpx` se mostrar inviável na implementação.

## 6. Download

- **Decisão**: `drives/{id}/items/{item}/content` via SDK (`content.get()`), que devolve bytes. Antes, uma chamada ao item valida tipo arquivo e tamanho (<= 100 MB). Grava-se em arquivo temporário na pasta de destino (`tempfile.NamedTemporaryFile(delete=False, dir=destino)`) e então `os.replace`. Em falha, o temporário é removido. Sobrescrita é `os.replace` apenas quando habilitada; sem sobrescrita, a existência é verificada antes de baixar.
- **Tamanho ausente**: sem `size` no item, o download é recusado em vez de ler o conteúdo sem limite.
- **Justificativa**: o limite de 100 MB torna aceitável manter o conteúdo em memória; a URL pré-autenticada (`@microsoft.graph.downloadUrl`) nunca é lida nem registrada, pois o SDK segue o redirecionamento internamente.
- **Alternativas**: streaming por `httpx` direto na URL pré-autenticada, rejeitado por expor a URL e contornar o SDK.

## 7. Segurança de caminhos

- **Decisão**: o destino é `(diretório_base / nome_ou_caminho_relativo).resolve()` e deve satisfazer `is_relative_to(base.resolve())`. Caminhos absolutos, `..` e nomes vazios são recusados. Por padrão o arquivo é gravado com o nome do item na raiz do diretório, sem recriar a estrutura remota; links simbólicos em direção ao exterior são cobertos por `resolve()`.
- **Nomes duplicados**: dois itens com o mesmo nome (em pastas diferentes) disputam o mesmo destino, pois a estrutura remota não é recriada. A regra é a de arquivo existente: ignorado sem `overwrite`, substituído com ele.
- **Justificativa**: simples e verificável por teste (SC-002).

## 8. Configuração

- **Decisão**: variáveis de ambiente `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` (obrigatórias), `GRAPH_SCOPE` (opcional, padrão `https://graph.microsoft.com/.default`), `SHAREPOINT_SITE_ID` ou o par `SHAREPOINT_HOSTNAME` + `SHAREPOINT_SITE_PATH` (um dos dois), e `DOWNLOAD_DIR` (opcional; argumento `--dest` prevalece). O `.env` é lido pela CLI com um leitor mínimo próprio (sem nova dependência) e nunca sobrescreve variáveis já definidas no ambiente.
- **Justificativa**: reaproveita `.env.example`; evita `python-dotenv`, conforme a constituição (sem dependências sem necessidade). Os testes de integração leem o mesmo `.env`.
- **Alternativas**: `python-dotenv`, aceita se o leitor mínimo ficar complexo.

## 9. Erros

- **Decisão**: `GraphToolError(category, message)` em `client.py`, com categorias: configuração, autenticação (401), permissão (403), não encontrado (404), limitação (429), servidor (5xx), timeout, caminho inválido. As mensagens nunca incluem tokens, segredos nem URLs de download; o SDK gera `ODataError` e `ClientAuthenticationError` (azure), que são traduzidos em um único ponto.

## 10. Testes e CI

- **Decisão**: unitários com fakes simples (classes de teste que imitam os builders usados) para evitar rede; integração marcada `integration`, excluída por `addopts`; workflow de CI executa `uv sync --locked`, `ruff check`, `ruff format --check`, `mypy` e `pytest`.
- **Justificativa**: AGENTS.md exige verificações na CI para cada linguagem introduzida.

## Itens resolvidos

Timeouts (30 s e 120 s), nomes de configuração para site por hostname e caminho (`SHAREPOINT_HOSTNAME`, `SHAREPOINT_SITE_PATH`) e destino padrão (`DOWNLOAD_DIR`) estão decididos acima e refletidos na spec.
