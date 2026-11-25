# Matriz de integração
Escala qualitativa: 1 baixo, 2 moderado, 3 alto; não são resultados de testes.
| Área | Super Productivity | Anki | Loop | ActivityWatch | OpenHabitTracker |
|---|---:|---:|---:|---:|---:|
| Interface |3|2|3|2|3|
| Planejamento |3|1|2|1|3|
| FSRS |1|3|1|1|1|
| Concentração |3|1|1|2|2|
| Hábitos |2|1|3|1|3|
| Indicadores |3|3|3|3|3|
| Compatibilidade Python |1|3|1|3|1|
| Reuso de código |3|1|1|2|1|
| Móvel |2|2|2|1|3|

| Motor | Referência | Estratégia | Validação |
|---|---|---|---|
| Learning | Anki/Py-FSRS | manter biblioteca, intercâmbio documentado | agendamentos, importação, retenção |
| Focus | Super Productivity | regras independentes e adaptação MIT seletiva | relógio, pausas, idempotência |
| Goal | OpenHabitTracker/SP | implementação própria | perfis e vigência |
| Habit | Loop | implementação própria | frequência, ausentes, calendário |
| Analytics | ActivityWatch | adaptador local opcional | agregação, privacidade, indisponibilidade |
| UI | SP/OHT | padrões Tkinter | acessibilidade e regressões |

Arquitetura: Tkinter → serviços Learning/Focus/Goal/Habit/Analytics → repositórios/adaptadores → SQLite/backups. Integrações externas opcionais, sem dependência obrigatória de serviços ou novas stacks. Priorizar retenção configurável, atalhos, central diária e calendário; planejar importação, analytics, ActivityWatch e mobile; Rust experimental; evitar migração integral de stack. Benefício/esforço são estimativas qualitativas.
