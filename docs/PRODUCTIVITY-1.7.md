# Diolino 1.7 — Learning & Productivity Engine
Status: proposta documental, sem implementação. Base: main; estabilização 1.4.1 independente. Dependências de entrega: homologação 1.4.1, segurança 1.5 e interface 1.6. Preservar Python, Tkinter, SQLite, operação offline, dados históricos e funcionalidades. Sem API paga, telemetria ou IA obrigatória.

## Arquitetura
Interface Tkinter → controladores/serviços → motores Learning, Focus, Goal, Habit e Analytics → repositórios transacionais SQLite, auditoria e backups. Separar lógica pura da interface para testes Windows/Linux. Propor productivity/{learning_engine,focus_engine,goal_engine,habit_engine,analytics_engine,repositories,schemas,validators}.py; ui/productivity/{dashboard,learning_view,focus_view,goals_view,habits_view,analytics_view}.py; migrations/{productivity_v1,legacy_fsrs_import}.py; tests/productivity/test_{learning,focus,goals,habits,analytics,migrations,integration}.py. Adaptadores preservam review_cards.py, pomodoro.py, productivity_ui.py, storage.py e views.py durante transição.

## Learning Engine (1.7.0)
LE-01 FSRS; LE-02 retenção configurável (90% inicial proposto); LE-03 especialidades; LE-04 etiquetas/filtros; LE-05 DOI/PMID; LE-06 histórico; LE-07 reinício após mudança conceitual; LE-08 previsão de carga; LE-09 otimização opcional; LE-10 cartões difíceis; LE-11 importação/exportação; LE-12 integração notas/PDF/OCR/cartões. LE-01–04,06–07 obrigatórios; LE-09 evolutivo; restantes alta prioridade.
Usar Py-FSRS 6.3.2 inicialmente, sem reimplementar fórmula. Selecionar pendentes, apresentar pergunta, recuperar ativamente, revelar resposta/fonte, avaliar Again/Hard/Good/Easy. Validar avaliação, revisão otimista e vencimento dentro de transação; calcular novo estado com perfil vigente e horário UTC; persistir cartão, log e auditoria atomicamente. Edição textual preserva estado; mudança conceitual permite reinício explícito. Otimização somente com histórico suficiente e validação temporal, comparar calibração/desempenho com baseline, preservar parâmetros anteriores. Reagendamento em massa exige simulação e confirmação. Dependências opcionais de otimização devem ser verificadas antes de empacotar.
Interface: pendentes, revisados hoje, recordação observada, previsão de sete dias, especialidades, iniciar revisão. Previsão baseada nos vencimentos atuais não garante carga futura.

## Focus Engine (1.7.1)
FE-01 clássico 25/5; FE-02 personalização; FE-03 modo livre; FE-04 interrupções opcionais; FE-05 vínculo tarefa/especialidade; FE-06 recuperação; FE-07 excluir pausas; FE-08 confirmação explícita; FE-09 idempotência; FE-10 segundos estruturados.
Estados: pronto → foco ↔ pausa → confirmação → registrado ou descartado → descanso → pronto. Relógio monotônico durante execução, persistência periódica, recuperação conservadora após falha/suspensão. Somar segmentos ativos confirmados; excluir tempo não verificável; dividir segmentos na meia-noite local para agregação, sem duplicar sessão. Descarte pode contar ciclo operacional, nunca estudo confirmado. Presets 15/3, 25/5, 50/10 e livre são escolhas operacionais, não protocolos superiores comprovados. Interface compacta com duração, tarefa, iniciar/pausar/encerrar.

## Goal Engine (1.7.2)
Metas iniciais Medicina 60 min/dia, exercício 40 min/dia, Bíblia compromisso binário sem mínimo. Perfis normal, plantão, férias e reduzido, dias programados e exceções explícitas. Configuração pelo usuário, sem inferência clínica. Versionar vigência; não reclassificar passado automaticamente. Progresso quantitativo = realizado/alvo ×100, alvo positivo; barra limitada a 100%, valor real preservado. Binário não usa divisão. Dia dispensado não aplicável. Editor com dias da semana e totais planejados.

## Habit Engine (1.7.3)
HE-01 cadastro; HE-02 frequência; HE-03 contexto; HE-04 histórico; HE-05 quatro estados; HE-06 frequência/completude; HE-07 lembretes opcionais; HE-08 automaticidade somente com instrumento validado. Estados realizado, não realizado, desconhecido, não aplicável. Não converter ausência em falha. Não usar regra de 21 dias, penalizações ou sequências como prova de automaticidade. Interface calendário de 28 dias com legenda textual acessível.

## Analytics Engine (1.7.4)
Painel 7/30/90 dias: tempo efetivo, tarefas concluídas, revisões, recordação observada, retenção prevista, carga futura, interrupções, adesão e completude. Separar esforço de aprendizagem. Estratificar revisões iniciais, reaprendizagem e revisões após intervalos. Não criar escore global arbitrário. Ver dicionário para denominadores.

## Segurança e compatibilidade
Dados locais, minimização, backups protegidos, migração transacional, dependências auditadas, sincronização opcional com conflitos e sem envio não autorizado. Nenhuma alteração de dados reais para testes. Compatibilidade com arquitetura 1.5 a validar.

## Roadmap
1.7.0 fundação/FSRS 3 semanas, 30–45 h; 1.7.1 foco 2 semanas, 15–25 h; 1.7.2 metas 2 semanas, 15–25 h; 1.7.3 hábitos 2 semanas, 15–25 h; 1.7.4 analytics 3 semanas, 25–40 h; 1.7.5 homologação 2 semanas, 26–38 h. Total preliminar 14 semanas, 126–198 h, não medido. Codex pode auxiliar implementação e revisão, sem substituir homologação.
Roadmap geral: 1.4.1 estabilização; 1.5 segurança; 1.6 interface; 1.7 produtividade; 1.8 IA local; 2.0 consolidação.
Ver DATA-DICTIONARY.md, ACCEPTANCE-TESTS.md e EVIDENCE-BASE.md. Protótipos descritos são conceituais, sem dados reais ou interface implementada.
