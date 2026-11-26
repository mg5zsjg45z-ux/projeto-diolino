# Redesign visual 2.1 — primeira entrega

A central diária inclui gráficos de estudo, exercício, sono e peso, com períodos de 7, 30 e 90 dias, previsão de vencimentos FSRS de Medicina (7 dias) e calendário de hábitos (30 dias). Células de hábitos têm símbolos, cor e seleção por teclado. O modo demonstração altera somente as quatro séries de atividade/saúde, em memória, sem gravar registros. A previsão FSRS e os hábitos continuam reais.

A arquitetura foi separada em dashboard_data.py (consultas e séries) e dashboard_ui.py (widgets). Não há novas dependências nem migração. Tkinter foi mantido para preservar as funcionalidades existentes; migração Qt, Kanban com arrastar, gráficos de concentração ainda não foram implementados.

A central também apresenta barras de progresso de estudo/exercício e recordação observada em revisões médicas (7 dias, somente avaliações registradas). Quatro testes unitários de dashboard_data.py passaram em ambiente isolado; hashes Git dos dois arquivos testados conferidos. A suíte integral e o teste gráfico Windows permanecem pendentes.

## Homologação
- Executar unittest discover -s tests -v em Python 3.12.
- Abrir a central diária com banco vazio, verificar ausência de registros, ativar demonstração e alternar períodos. Confirmar que nenhum registro é criado.
- Em perfil de teste separado, registrar estudo, exercício, sono, peso e hábito, verificar gráficos e estados. Testar teclado, temas, alto contraste, DPI e resoluções 1366×768 e 1920×1080.
- Capturar screenshots reais e comparar com a proposta. Não aprovar sem validar a janela no Windows.
- Não substituir instalação atual antes de homologação.
