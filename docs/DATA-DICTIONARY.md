# Diolino 1.7 — Modelo de dados proposto
Não constitui migração executável. IDs únicos, chaves estrangeiras, índices de consulta, transações e auditoria. Eventos UTC e fuso/contexto local para agregação. Preservar dados ausentes.
| Entidade | Campos principais |
|---|---|
| learning_cards | id, pergunta, resposta, especialidade, fonte, estado FSRS, revision, archived |
| learning_reviews | id, card_id, profile_id, rating, UTC, duração, estado anterior/posterior |
| scheduler_profiles | id, versão FSRS, parâmetros, retenção desejada, vigência |
| focus_sessions | id, task_id opcional, início, término, segundos efetivos, status |
| focus_events | id, session_id, evento, horário, duração |
| goals | id, nome, categoria, unidade |
| goal_versions | id, goal_id, alvo, vigência, perfil diário |
| habits | id, nome, contexto, frequência, status |
| habit_observations | id, habit_id, data, resultado, contexto, observação |
| tasks | id, descrição, prioridade, prazo, conclusão |
| daily_context | data, perfil, exceções autorizadas |
| learning_sources | id, DOI, PMID, título, referência, vínculo documental |

Relações 1:N cartão/revisões, perfil/revisões, sessão/eventos, meta/versões, hábito/observações, tarefa/sessões. Reutilizar entidades existentes quando possível; não duplicar tarefas. Etiquetas e fontes podem exigir relações adicionais. Restrições: revisão otimista; identificador idempotente de confirmação; alvo quantitativo positivo; estados explícitos; vigências não sobrepostas; observação única por hábito/data quando frequência diária. Índices por vencimento, cartão/data, sessão/data, hábito/data e meta/vigência.

## Migração
Backup prévio verificado, inventário de registros JSON legados e histórico, importação transacional preservando IDs e agendamentos, comparação de contagens e conteúdo, integridade SQLite e chaves estrangeiras. Não inventar histórico ausente. Em falha rollback e recuperação do backup; manter compatibilidade durante transição. Testar repetição idempotente, restauração e sincronização antes de ativar.

## Indicadores
Tempo efetivo: soma de segundos confirmados, sem pausas ou sobreposição. Progresso: realizado/alvo vigente. Execução: tarefas concluídas entre programadas no período. Recordação observada: avaliações bem-sucedidas (Hard/Good/Easy) / revisões avaliáveis, estratificar aprendizagem e reaprendizagem. Retenção prevista: probabilidade FSRS, não resultado observado. Carga: vencimentos no período. Interrupções: eventos/sessões. Adesão: realizados/(realizados+não realizados). Completude: (realizados+não realizados)/dias aplicáveis. Excluir não aplicáveis; desconhecidos não são zeros; denominador zero = indefinido. Exibir denominadores e período. Limites de adesão no total aplicável: realizados/aplicáveis até (realizados+desconhecidos)/aplicáveis. Indicadores calculados dos registros primários, sem escore composto.
