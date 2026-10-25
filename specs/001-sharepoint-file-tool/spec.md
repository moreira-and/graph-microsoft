# Especificação da Funcionalidade: Ferramenta de arquivos do SharePoint

**Branch da funcionalidade**: `001-sharepoint-file-tool`

**Criado em**: 2026-10-24

**Status**: Rascunho

**Entrada**: Ferramenta Python para listar, localizar e baixar arquivos de sites do SharePoint usando Microsoft Graph, com autenticação app-only no Microsoft Entra ID e acesso somente leitura via Sites.Selected.

## Objetivo e motivação

Equipes precisam consultar e obter uma pequena quantidade de arquivos de um site específico do SharePoint sem acesso interativo e sem permissões amplas no tenant. A ferramenta oferece acesso somente leitura, restrito aos sites explicitamente autorizados, com resultados previsíveis e sem expor credenciais.

## Clarificações

### Sessão 2026-10-24

- Q: Qual o limite de arquivos por lote e de tamanho por arquivo? → A: 20 arquivos por lote, 100 MB por arquivo.
- Q: A autenticação aceita só segredo de cliente ou também certificado? → A: Somente segredo de cliente.
- Q: Funções Python ou também interface de linha de comando? → A: Funções Python mais uma CLI mínima.

## Cenários de Usuário e Testes *(obrigatório)*

### História 1 - Resolver site e listar bibliotecas e arquivos (Prioridade: P1)

O operador informa o site (por ID ou por hostname e caminho) e obtém as bibliotecas de documentos e os arquivos e pastas de uma biblioteca ou pasta.

**Por que esta prioridade**: sem identificar o site e enxergar seu conteúdo, nenhuma outra operação é possível; é o MVP.

**Teste independente**: com o site de teste autorizado, resolver o site, listar bibliotecas e listar o conteúdo de uma pasta retorna os itens esperados, inclusive quando o resultado ocupa mais de uma página.

**Cenários de aceitação**:

1. **Dado** um ID de site válido e autorizado, **Quando** o operador resolve o site, **Então** recebe o identificador e o nome do site.
2. **Dado** hostname e caminho válidos de um site autorizado, **Quando** o operador resolve o site, **Então** recebe o mesmo site que seria obtido pelo ID.
3. **Dado** um site com várias bibliotecas, **Quando** o operador lista as bibliotecas, **Então** todas são retornadas, com nome e identificador.
4. **Dado** uma pasta cujo conteúdo excede uma página de resultados, **Quando** o operador lista os itens, **Então** todos os itens de todas as páginas são retornados, seguindo `@odata.nextLink` até não haver mais páginas.
5. **Dado** uma lista de itens, **Quando** exibida, **Então** cada item indica nome, caminho, tipo (arquivo ou pasta) e tamanho (para arquivos).

---

### História 2 - Localizar arquivos por nome ou caminho (Prioridade: P2)

O operador localiza arquivos por nome ou caminho dentro de uma biblioteca ou pasta autorizada.

**Por que esta prioridade**: permite chegar ao arquivo desejado sem navegar manualmente, mas depende da listagem.

**Teste independente**: informar um trecho de nome ou um caminho dentro de uma pasta e verificar que somente os itens correspondentes são retornados.

**Cenários de aceitação**:

1. **Dado** uma biblioteca ou pasta de origem, **Quando** o operador informa um nome (ou parte dele), **Então** recebe apenas os arquivos cujo nome corresponde, sem diferenciar maiúsculas de minúsculas.
2. **Dado** um caminho relativo exato dentro da biblioteca, **Quando** o operador o informa, **Então** recebe o arquivo naquele caminho ou resultado vazio se não existir.
3. **Dado** nenhuma correspondência, **Quando** a localização termina, **Então** o resultado é vazio e informado como "nenhum arquivo encontrado", não como erro.
4. **Dado** uma localização, **Quando** executada, **Então** ela percorre apenas o escopo informado (biblioteca ou pasta) e nunca realiza busca ampla entre sites ou bibliotecas.

---

### História 3 - Baixar poucos arquivos em lote com segurança (Prioridade: P3)

O operador baixa alguns arquivos para um diretório local configurado, um por vez.

**Por que esta prioridade**: entrega o valor final, mas se apoia na resolução e localização.

**Teste independente**: baixar um lote com arquivos novos, existentes e inexistentes e verificar o relatório final e o conteúdo do diretório.

**Cenários de aceitação**:

1. **Dado** um lote de arquivos válidos, **Quando** o operador baixa, **Então** os arquivos são baixados sequencialmente e o relatório lista cada um como baixado.
2. **Dado** um arquivo que já existe no destino, **Quando** o operador baixa sem sobrescrita, **Então** o arquivo local permanece intacto e é informado como ignorado.
3. **Dado** um arquivo existente e sobrescrita explicitamente habilitada, **Quando** o operador baixa, **Então** o arquivo local é substituído pelo conteúdo remoto.
4. **Dado** um lote em que um item falha, **Quando** o download termina, **Então** os itens já concluídos são preservados e o relatório identifica sucesso, ignorados e falhas individuais com o motivo, sem interromper os itens restantes.
5. **Dado** um nome ou caminho remoto que resultaria em gravação fora do diretório configurado (por exemplo, com `..` ou caminho absoluto), **Quando** o download é solicitado, **Então** o item é recusado como falha de segurança e nada é gravado fora do diretório.
6. **Dado** uma falha ou interrupção durante a gravação, **Quando** ocorre, **Então** nenhum arquivo final incompleto permanece no destino; o arquivo final só aparece quando o conteúdo está completo.

---

### História 4 - Autenticar e configurar o ambiente (Prioridade: P1)

O operador configura credenciais e o site de teste por variáveis de ambiente e executa a ferramenta sem interação.

**Por que esta prioridade**: pré-requisito de todas as operações.

**Teste independente**: executar com configuração completa autentica; executar com variável ausente falha com mensagem clara, sem acessar a rede.

**Cenários de aceitação**:

1. **Dado** `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` e `AZURE_CLIENT_SECRET` definidos, **Quando** a ferramenta é executada, **Então** autentica de forma app-only no Microsoft Entra ID.
2. **Dado** uma variável obrigatória ausente ou vazia, **Quando** a ferramenta inicia, **Então** falha antes de qualquer chamada de rede, informando o nome da variável ausente, sem exibir valores.
3. **Dado** um site de teste definido por configuração, **Quando** nenhum site é informado na operação, **Então** o site configurado é usado.

---

### Casos de Borda

- Site, biblioteca, pasta ou arquivo inexistente ou sem concessão de acesso (HTTP 404/403): erro claro identificando o recurso, sem detalhes sensíveis.
- Credenciais inválidas ou expiradas (HTTP 401 ou falha de autenticação): erro de autenticação claro.
- Limitação de requisições (HTTP 429): respeita `Retry-After`; a ferramenta não adiciona uma segunda política de retry se o SDK já trata a limitação.
- Timeout de rede na listagem ou no download: reportado como falha do item/operação, sem travar indefinidamente.
- Erros HTTP 5xx: reportados como falha com código de status.
- Dois itens do lote com o mesmo nome de destino: o segundo é tratado como existente (ignorado ou sobrescrito conforme a opção).
- Nomes de arquivo com caracteres especiais ou separadores: normalizados ou recusados sem escapar do diretório.
- Item solicitado é uma pasta, não um arquivo: falha individual informada.
- Pasta vazia: resultado vazio, não erro.
- URLs pré-autenticadas de download, tokens e segredos nunca aparecem em logs, mensagens de erro ou relatórios.

## Requisitos *(obrigatório)*

### Requisitos Funcionais

- **FR-001**: O sistema DEVE autenticar de forma app-only no Microsoft Entra ID usando somente segredo de cliente (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID` e `AZURE_CLIENT_SECRET`), lidos do ambiente (com `.env` local opcional); certificados não são suportados.
- **FR-002**: O sistema DEVE validar a configuração obrigatória no início e falhar com mensagem que cita apenas o nome das variáveis ausentes.
- **FR-003**: O sistema DEVE identificar o site de teste por configuração.
- **FR-004**: O sistema DEVE resolver um site por ID ou por hostname e caminho.
- **FR-005**: O sistema DEVE listar as bibliotecas de documentos de um site.
- **FR-006**: O sistema DEVE listar arquivos e pastas da raiz de uma biblioteca ou de uma pasta informada.
- **FR-007**: O sistema DEVE seguir a paginação do Graph por `@odata.nextLink` em toda listagem, retornando todos os itens.
- **FR-008**: O sistema DEVE localizar arquivos por nome ou por caminho dentro de uma biblioteca ou pasta autorizada, percorrendo somente esse escopo.
- **FR-009**: O sistema DEVE baixar um lote de até 20 arquivos para um diretório local configurado, de forma sequencial, recusando lotes maiores antes de baixar qualquer item.
- **FR-009a**: O sistema DEVE recusar, como falha individual, arquivos acima de 100 MB sem baixá-los, e também arquivos cujo tamanho não seja informado pelo Graph.
- **FR-010**: O sistema NÃO DEVE sobrescrever arquivos existentes por padrão e DEVE informá-los como ignorados.
- **FR-011**: O sistema DEVE permitir sobrescrita somente mediante opção explícita.
- **FR-012**: O sistema DEVE validar que todo destino resolvido está dentro do diretório configurado e recusar o item caso contrário.
- **FR-013**: O sistema DEVE gravar cada arquivo em um arquivo temporário e renomeá-lo para o nome final somente após a conclusão, removendo temporários em caso de falha.
- **FR-014**: O sistema DEVE produzir, ao fim do lote, um relatório com itens baixados, ignorados e com falha (e motivo), preservando os resultados já concluídos quando houver falhas.
- **FR-015**: O sistema DEVE tratar erros HTTP e timeouts, convertendo-os em erros claros e distinguíveis (autenticação, permissão, não encontrado, limitação, servidor, timeout).
- **FR-016**: Em HTTP 429, o sistema DEVE respeitar `Retry-After` sem implementar uma segunda política de retry quando o SDK já tratar a limitação.
- **FR-017**: O sistema NÃO DEVE registrar segredos, tokens ou URLs pré-autenticadas de download.
- **FR-018**: O sistema DEVE operar apenas com a permissão Sites.Selected com acesso de leitura concedido explicitamente ao site de teste.
- **FR-019**: O sistema NÃO DEVE usar endpoints de busca ampla do Graph (busca de sites ou arquivos), por serem incompatíveis com Sites.Selected.
- **FR-020**: O sistema DEVE usar o SDK oficial `msgraph-sdk` e `azure-identity`, já declarados no projeto.
- **FR-021**: O código DEVE ser organizado em poucos módulos com responsabilidades distintas: autenticação/cliente Graph, operações SharePoint e downloads locais, usando funções simples e sem camadas genéricas sem necessidade concreta.
- **FR-022**: A suíte padrão de testes DEVE rodar sem acesso ao SharePoint e sem credenciais, cobrindo paginação, listagem, localização, erros, arquivos existentes, sobrescrita, falhas parciais e segurança de caminhos.
- **FR-023**: Os testes de integração DEVEM ser opt-in, usar `.env` local e ficar fora da execução padrão.
- **FR-024**: A solução DEVE preservar as ferramentas e hooks existentes (uv, Ruff, mypy, pytest, pre-commit).
- **FR-025**: A ferramenta DEVE oferecer funções Python e uma interface de linha de comando mínima para resolver site, listar, localizar e baixar, com opções explícitas de diretório de destino e sobrescrita.

### Fora de Escopo

- Upload, edição, renomeação, movimentação, exclusão ou qualquer operação de escrita no SharePoint.
- Manipulação de listas de negócio e de seus itens.
- Busca ampla de sites ou arquivos (endpoints de busca do Graph) e descoberta de sites do tenant.
- Autenticação delegada/interativa, login de usuário e fluxos de dispositivo.
- Downloads concorrentes/paralelos, retomada de downloads parciais e sincronização de pastas.
- Downloads em larga escala (milhares de arquivos ou arquivos muito grandes além do limite definido).
- Concessão de permissões (a concessão Sites.Selected ao site é feita fora da ferramenta).
- Interface gráfica, serviço web ou agendamento.
- Políticas próprias de retry/backoff além do comportamento do SDK.
- Repositories, factories, interfaces ou camadas genéricas de abstração.

### Entidades Principais

- **Site**: site do SharePoint, identificado por ID ou hostname e caminho; possui nome.
- **Biblioteca**: biblioteca de documentos de um site, com nome e identificador.
- **Item**: arquivo ou pasta dentro de uma biblioteca, com nome, caminho, tipo e tamanho.
- **Item de download**: arquivo a baixar; um lote é uma lista de itens de download com diretório de destino e opção de sobrescrita.
- **Resultado de download**: status por item (baixado, ignorado, falha) e motivo, agregado em um relatório de lote.

## Decisões Pendentes

Resolvidas no planejamento (ver [research.md](research.md)), sujeitas a revisão:

1. **Configuração**: `SHAREPOINT_SITE_ID` e `GRAPH_SCOPE` de `.env.example` são mantidos; site por hostname e caminho usa `SHAREPOINT_HOSTNAME` e `SHAREPOINT_SITE_PATH`. O destino vem do argumento `--dest`, com `DOWNLOAD_DIR` como padrão.
2. **Timeouts**: 30 s por requisição de listagem e 120 s por download.

Resolvidas em 2026-10-24: tipo de credencial, limites do download e forma de uso (ver Clarificações).

## Critérios de Sucesso *(obrigatório)*

### Resultados Mensuráveis

- **SC-001**: Listagens com mais de uma página retornam 100% dos itens, verificado por teste com no mínimo 3 páginas simuladas.
- **SC-002**: Em 100% dos testes de segurança de caminhos (`..`, caminhos absolutos, separadores), nenhum arquivo é gravado fora do diretório configurado.
- **SC-003**: Em lotes com falhas parciais, 100% dos arquivos concluídos permanecem íntegros e o relatório classifica cada item como baixado, ignorado ou falha.
- **SC-004**: Sem a opção de sobrescrita, 0 arquivos existentes são modificados; com ela, 100% são substituídos.
- **SC-005**: Após falha durante o download, 0 arquivos finais incompletos permanecem no diretório.
- **SC-006**: Nenhum segredo, token ou URL pré-autenticada aparece em logs, erros ou relatórios nos testes.
- **SC-007**: A suíte padrão passa sem credenciais nem rede e as verificações de qualidade (Ruff, mypy, pytest) passam sem violações.
- **SC-008**: O operador resolve um site, lista uma biblioteca e baixa um arquivo do site de teste em menos de 2 minutos de execução, após a configuração.

## Premissas

- O app registrado no Microsoft Entra ID tem Sites.Selected com consentimento de administrador e leitura concedida ao site de teste.
- O ambiente tem acesso à rede ao Microsoft Graph; há um tenant de teste dedicado.
- O uso é por operadores técnicos, em lote pequeno e execução sequencial.
- Os pacotes `msgraph-sdk` e `azure-identity` já estão em `pyproject.toml` e o SDK trata a limitação de requisições (429) por padrão.
- Credenciais ficam em variáveis de ambiente ou `.env` local, nunca versionado.
- Os testes de integração exigem site de teste real e são executados explicitamente.
