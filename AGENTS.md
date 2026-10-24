# Instruções do repositório

Antes de alterar o projeto, consulte `.specify/memory/constitution.md` e preserve
os padrões e a arquitetura existentes. Mantenha responsabilidades claras,
coesão alta, acoplamento baixo e soluções simples.

## Qualidade e validação

- Use nomes expressivos e fluxo de execução simples; evite duplicação,
  condicionais complexas e abstrações sem justificativa.
- Para cada linguagem de aplicação introduzida, configure um linter e
  formatador adequados, análise estática com limites de complexidade e testes
  automatizados. Execute essas verificações na integração contínua.
- Escreva testes focados no comportamento alterado, execute-os e rode as demais
  verificações disponíveis antes de concluir.
- Não escolha uma stack de aplicação ou ferramentas específicas sem contexto
  suficiente no projeto. Até existir código de aplicação, não há uma linguagem
  ou suíte de testes a presumir.
- Revise as mudanças quanto à legibilidade, responsabilidades, complexidade,
  duplicação e compatibilidade com a arquitetura antes de solicitar revisão.

## Revisão de código

Toda mudança deve explicar o que foi alterado e por quê. A revisão deve
confirmar os critérios de qualidade acima, a validação executada e a ausência
de regressões relevantes. Registre verificações não aplicáveis e o motivo.

## Spec Kit

Mantenha os arquivos do Spec Kit na raiz do repositório. Para detalhes de
instalação e inicialização com GitHub Copilot, consulte `README.md`.
