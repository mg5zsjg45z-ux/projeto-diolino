# Desenvolvimento 2.0

Na central diária, **Histórico de atividade** soma os minutos de estudo e exercício dos últimos 7, 30 ou 90 dias, até a data selecionada inclusive. O total vem acompanhado da quantidade de dias registrados. Dias sem lançamentos ficam desconhecidos. A consulta lê o SQLite local.

Na janela Pomodoro, marque **Flowtime** antes de iniciar para contar o tempo de foco até escolher **Encerrar foco**. A sessão pode ser pausada e retomada. Confirme a gravação para incluir os minutos ativos no histórico.

Em **Planos e etapas**, abra o Kanban para consultar os três estados das etapas de planos ativos. A matriz de Eisenhower considera urgente um prazo vencido ou no dia consultado e importante uma etapa de prioridade alta. Selecione a etapa e use Enter para editar ou Ctrl+B para abrir uma reserva de tempo na agenda. Ajuste horário e duração antes de salvar.

Em **Assistente offline**, marque **Usar Ollama (qwen2.5:7b)** para interpretar texto com o modelo instalado no PC. O assistente consulta o modelo no serviço local, em 127.0.0.1:11434. Os rascunhos passam pela validação de evidências e pela revisão manual antes de salvar.

Em **Cartões de revisão**, selecione uma área e importe um arquivo UTF-8 de duas colunas tabuladas (frente e verso). Uma linha inválida cancela a importação inteira. Reimportar o mesmo par de textos na mesma área preserva o cartão existente. A exportação inclui os textos da área filtrada. O agendamento continua no Diolino. **Retenção FSRS** define o alvo para avaliações futuras, com padrão de 90%.

Em **Hábitos e metas**, crie um hábito com frequência de 1 a 7 dias por semana. Uma alteração de meta vale desde a data selecionada. A semana começa na segunda-feira. O quadro conta separadamente dias cumpridos e dias registrados e preserva os dias sem informação.

## Distribuição Windows

Para compilar, instale requirements-build.txt no ambiente .venv e execute build.ps1 e scripts/build_distribution.ps1. O instalador, o ZIP portátil e o manifesto SHA256.csv ficam em releases/2.0.0-distribuicao.

No checkout de desenvolvimento, scripts/update-windows.ps1 aceita -Installer e -ExpectedSha256. Obtenha o hash de uma referência confiável. Use -VerifyOnly para conferir o arquivo. Na atualização, com o aplicativo fechado, o script pede a senha no terminal, copia o SQLite por conexão somente leitura, verifica a integridade e confere a recuperação do arquivo .diolinobak antes de abrir o instalador interativo. O menu Dados permite restaurar a cópia. Ela contém o banco SQLite. Arquivos externos e modelos locais têm armazenamento separado.
