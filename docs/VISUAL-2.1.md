# Redesign visual 2.1 — prévia integrada

A central diária apresenta gráficos de estudo, exercício, sono, peso e tempo médico confirmado por Pomodoro/Flowtime, com períodos de 7, 30 e 90 dias. Os filtros mostram todos os indicadores ou apenas a categoria escolhida. FSRS: vencimentos futuros e recordação observada de Medicina nos últimos sete dias locais. Habit calendar: 30 dias, símbolos e seleção pelo teclado. O modo demonstração gera gráficos e hábitos sintéticos em memória, sem gravar no SQLite. Os cartões externos ao painel continuam reais.

A área de planejamento abre um Kanban de cartões com prioridade, prazo e mudança de estado por arraste ou seletor, com acesso ao quadro anterior para foco por etapa. A semana visual oferece cartões por dia, navegação semanal e criação/edição de reservas de tempo utilizando a agenda existente. Alterações passam pela validação e auditoria do Store.

Não há novas dependências nem migração. Tkinter permanece. Gráficos de foco estão limitados ao estudo médico com origem Pomodoro/Flowtime; sessões de outras áreas e pausas não são inferidas. Não há timeline horária proporcional, redimensionamento de blocos, persistência dos filtros, migração Qt ou validação visual completa.

Cinco testes unitários de dashboard_data.py foram executados em ambiente isolado com os blobs Git 62e2cee36cd16cea02ce7ed24ba2d75b2675d0cd e 6e62dd1a254eb062666468a7348eda61866fa2b8 conferidos: todos aprovados. Testes de planejamento e interface adicionados, ainda não executados.

## Homologação
- Executar unittest discover -s tests -v em Python 3.12.
- Abrir central diária com banco vazio, ativar demonstração, alternar períodos e filtros; conferir que não há novos registros.
- Com perfil de teste separado, criar estudo, exercício, sono, peso, hábito, cartão de revisão, plano e compromisso; conferir gráficos e dados.
- Testar arrastar etapas e alternativa por teclado, auditoria, edição de blocos e transição de ano.
- Verificar temas claro/escuro, alto contraste, resoluções 1366×768 e 1920×1080, DPI 100–200%.
- Capturar screenshots reais e comparar com referência. Não aprovar antes da execução no Windows.


## Tokens e estados na interface Tkinter

| Papel | Valores |
| --- | --- |
| Espaçamento | 4, 8, 12, 16, 24 e 32 unidades lógicas |
| Raios | 8 para controles, 12 para cartões e 16 para superfícies maiores |
| Tipografia | Segoe UI 10 para corpo, Semibold 10 para rótulos, 13 para seções, 20 para métricas e 25 para títulos |
| Tamanho de texto | 100%, 110% ou 125%, calculados sobre a fonte original |
| Densidade | Confortável em 100% e compacta em 80% para espaçamentos adaptados |

A paleta clara vem de `theme.py`. Os temas alternativos preservam os mesmos papéis semânticos para fundo, superfície, texto, texto secundário, contorno, seleção e navegação. O modo Automático relê a preferência de tema do Windows ao receber foco. O modo de alto contraste aplica as cores do sistema e desativa os ornamentos.

Botões comuns, ações principais e seletores de semana têm estados de repouso, hover, pressionado, desabilitado e foco. O contorno de foco acompanha o contraste da superfície do botão. Campos têm fundo próprio para leitura e desabilitado, com contorno reforçado ao receber foco. Cartões informativos mantêm aparência estática e o foco fica nos controles internos.

O grid recalcula colunas de acordo com a largura em tela, o DPI, o tamanho do texto e a densidade. Os controles existentes são reposicionados no mesmo grid. A sidebar encurta rótulos quando o espaço diminui. A central separa o resumo e as revisões das ações rápidas.

O estilo Gravura usa um losango no divisor e traços curtos nos cantos dos cartões. `RoundedSurface(..., ornaments=False)` permite ocultar os traços em uma superfície específica. As preferências existentes de tema, texto, densidade, títulos, sombras e ornamentos continuam no mesmo arquivo `appearance.json`.
