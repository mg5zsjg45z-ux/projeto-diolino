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

## Auditoria e verificação local de 25/11/2026

O ponto de partida foi o commit 238c8e5. O projeto já usava Tkinter, SQLite, Py-FSRS, Pomodoro, exportação protegida e Inno Setup. As novas funções reutilizam os registros de planejamento, a agenda e a tabela de preferências. Nenhuma migração de dados foi necessária.

Ambiente Windows com Python 3.12.10. Para reproduzir a suíte a partir da raiz:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-ci.txt -r requirements-build.txt
New-Item -ItemType Directory -Force test-output | Out-Null
.venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -v
```

Resultado final: 154 de 155 testes Python passaram. O teste de integração de desinstalação compilou o instalador sintético com Inno Setup 6.7.4, mas o Windows recusou iniciá-lo com WinError 5. A instalação, atualização e desinstalação completas permanecem pendentes de homologação. O teste continua ativo.

O executável empacotado passou pelo smoke test com banco sintético, incluindo FSRS, busca, backup protegido, PDF e OCR. Um relato sintético processado pelo Ollama local retornou um rascunho com o peso e a data esperados. Os 19 testes do site independentes do preview passaram. As suítes HTTP dependem do preview com autenticação e D1 local; o checkout não contém a configuração .openai/hosting.json exigida pelo Vite.

A auditoria pip-audit das dependências de build e runtime terminou sem vulnerabilidades conhecidas reportadas. Bandit não encontrou achados de severidade alta nos arquivos Python de aplicação analisados. Relatórios locais em test-output/audit.json, test-output/bandit.json e test-output/sbom.json. O SBOM foi gerado a partir do ambiente de desenvolvimento e abrange seus pacotes Python.

O workflow de qualidade inclui pushes em development/2.0. No runner Windows, a etapa de preparação exige o compilador Inno Setup 6 e informa seu caminho ao teste via DIOLINO_ISCC. A ausência do compilador interrompe o job para que o teste de distribuição não passe despercebido como ignorado.

## Etapas com foco e revisão médica

No Kanban ou na matriz, selecione uma etapa e use Pomodoro ou Flowtime na própria coluna. O temporizador usa o título da etapa. Ao confirmar, o quadro mostra o total acumulado de minutos. Para planos de Medicina ou Bíblia, a confirmação também grava o estudo na área correspondente. Nas outras áreas, o tempo pertence apenas à etapa.

A central mostra cartões de Medicina cujo agendamento atual vence hoje, cartões distintos revisados hoje e recordação observada nos últimos sete dias locais. Cada avaliação Difícil, Bom ou Fácil conta como recordação; Esqueci entra apenas no denominador. Dias sem avaliações aparecem com um traço. Os indicadores usam o relógio local mesmo quando o usuário navega em outra data.

O teste de compatibilidade cria um perfil temporário com o código 1.4.1 do commit 7f30ea4, grava estudo, agenda e cartão revisado, abre o perfil na 2.0 e restaura o backup criptografado em outra pasta. Compara conteúdo, identificadores, agendamento e auditoria nos dois percursos. O teste requer histórico Git que inclua o commit de origem.

Nesta rodada, 156 dos 157 testes Python passaram. A execução do instalador sintético continuou bloqueada no Windows local com WinError 5. O GitHub Actions registrou o push, mas os jobs ficaram bloqueados antes de iniciar por uma restrição de faturamento ou limite da conta. A atualização nativa de ponta a ponta permanece pendente.
