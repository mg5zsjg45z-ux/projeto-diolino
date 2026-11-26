# Backlog de engenharia comparativa
Propostas, não tarefas implementadas. Dependem da estabilização 1.4.1 e homologação das versões anteriores.
| ID | Melhoria | Referência | Versão | Aceitação resumida |
|---|---|---|---|---|
| BEN-01 | Central diária | Super Productivity |1.6| tarefas/metas em uma visão |
| BEN-02 | Navegação recolhível | Super Productivity |1.6| teclado e estado preservados |
| BEN-03 | Temas/densidade | OpenHabitTracker |1.6| contraste e preferências |
| BEN-04 | Retenção FSRS configurável | Anki |1.7.0| perfil versionado, sem perda |
| BEN-05 | Intercâmbio cartões | Anki |1.7.0| round-trip com fixtures |
| BEN-06 | Previsão revisões | Anki |1.7.0| contagem por vencimento |
| BEN-07 | Otimização Rust | FSRS-RS | experimental | licença, calibração e empacotamento |
| BEN-08 | Foco por tarefa | Super Productivity |1.7.1| vínculo e tempo confirmado |
| BEN-09 | Foco livre | Super Productivity |1.7.1| pausas excluídas |
| BEN-10 | Perfis diários | OpenHabitTracker |1.7.2| histórico preservado |
| BEN-11 | Calendário hábitos | Loop |1.7.3| quatro estados distinguíveis |
| BEN-12 | Frequência personalizada | Loop |1.7.3| denominadores corretos |
| BEN-13 | Agregação temporal | ActivityWatch |1.7.4| sem duplicação |
| BEN-14 | Adaptador local | ActivityWatch |1.7.4| opt-in, agregados, falha tolerada |
| BEN-15 | Interface móvel | OpenHabitTracker |2.0| estudo de viabilidade |

Prioridade inicial: BEN-01/02/04/11; planejar demais conforme dependências. BEN-07/14/15 exigem prova de conceito separada. Não alterar pipeline, dados ou código nesta etapa. Aplicar os 32 cenários e gates de ACCEPTANCE-TESTS.md, acrescentando testes específicos por integração. Nenhuma homologação ou merge autorizado.
