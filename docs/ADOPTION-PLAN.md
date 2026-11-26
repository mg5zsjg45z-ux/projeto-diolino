# Plano de adoção seletiva
Complementa BENCHMARK-BACKLOG.md. Decisão de planejamento, não implementação. Preservar main, PR 1.4.1, Tkinter, SQLite e dados.
## P0 — uso diário (1.6)
Super Productivity: central Hoje, captura rápida, três prioridades opcionais, agenda com blocos de tempo, subtarefas, atalhos, revisão de fim de dia. OpenHabitTracker: filtros comuns entre notas, tarefas e hábitos, temas e densidade. Reutilizar agenda e entidades existentes. Aceitação: fluxo completo offline, teclado, sem regressões.
## P1 — aprendizagem e foco (1.7.0–1.7.1)
Anki: manter Py-FSRS, retenção configurável, etiquetas/especialidades, previsão, recordação observada, intercâmbio de cartões com validação. Super Productivity: sessão vinculada à tarefa, Pomodoro/Flowtime, pausas opcionais, confirmação idempotente. Não exigir Anki ou Electron. Aceitação: testes FSRS e foco existentes mais cenários de importação e recuperação.
## P1 — metas e hábitos (1.7.2–1.7.3)
Loop: calendário, frequência personalizada, registros quantitativos. OpenHabitTracker: ordenar hábitos por vencimento, sem punir sequência interrompida. Para hábitos de intervalo fixo, urgência = tempo desde última conclusão confirmada / intervalo planejado; sem registro inicial, mostrar desconhecido; não aplicar a metas de calendário ou dias dispensados. Urgência não mede automaticidade. Preservar medicina 60 min, exercício 40 min e Bíblia sem mínimo como padrões atuais. Perfis de plantão opcionais e metas versionadas.
## P2 — indicadores (1.7.4)
ActivityWatch: agregação temporal, categorias e distinção entre atividade e inatividade. Adaptador externo apenas experimental, opt-in, agregado, sem títulos de janelas ou dados clínicos. Painel 7/30/90 dias, adesão, completude, tempo efetivo e recordação distintos. Não criar escore global.
## P3 — evolução
Otimização Rust condicionada a licença, testes e empacotamento. Interface móvel após estabilidade. Não incorporar plataformas completas.
## Gates
Cada entrega em branch própria, testes sintéticos, migração recuperável, revisão de licença por arquivo, SBOM e auditoria; nenhuma cópia externa sem verificação. Sem merge antes de aprovação integral. Bloqueio anterior do CI precisa ser resolvido para homologação.
## Referências
https://github.com/super-productivity/super-productivity
https://www.openhabittracker.net/
https://github.com/ankitects/anki
https://github.com/iSoron/uhabits
https://github.com/ActivityWatch/activitywatch
Classificação de prioridade é proposta de engenharia, não benchmark medido. Nenhuma funcionalidade implementada neste documento.
