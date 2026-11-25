# Projeto Diolino

Aplicativo de desktop para Windows, em português, com dados locais. A branch development/2.0 contém a versão 2.0.0 em homologação.

## Desenvolvimento 2.0 para Windows

Consulte o [guia de uso e compilação da versão 2.0](docs/DESENVOLVIMENTO-2.0.md) para a central diária, planejamento, revisão, foco, hábitos e atualização local.


## Estabilização 1.4.1

A versão 1.4.0 acrescentou o cliente de sincronização com o site por dispositivo, com tratamento de conflitos. A versão 1.4.1 prepara testes Windows, cobertura, auditoria de dependências e análise estática. Consulte `docs/STABILIZATION-1.4.1.md`. A aprovação depende dos resultados do GitHub Actions.


## Ferramentas locais — 1.3.0

No cabeçalho do Windows há **Buscar em tudo · Ctrl+K**, **Cartões de revisão** e
**PDF e OCR**. Os componentes são carregados ao abrir cada ferramenta, evitando
importações desnecessárias na abertura do aplicativo. Estas funções são do Windows;
não foram adicionadas ao site nesta entrega.

**Busca unificada:** índice FTS5 temporário em memória e correspondência aproximada
com RapidFuzz. Pesquisa registros ativos, planos, estudos, agenda e anotações, com
acentos ignorados. Resultados aproximados são identificados. É possível abrir o
registro ou preparar um cartão a partir do conteúdo. Não há envio dos textos à internet.
O índice é atualizado após alterações locais, gravações de outra conexão e restaurações.

**Cartões:** crie pergunta, resposta, área e referência; revise pendentes, revele a
resposta e avalie como Esqueci/Difícil/Bom/Fácil. Py-FSRS 6.3.2 calcula a próxima
revisão; o horário mostrado é local, e o agendamento é salvo em UTC. Editar preserva
o agendamento; arquivar retira da fila e preserva histórico. Revisões não criam minutos
de estudo nem confirmam pilares. Cartões e histórico estão no SQLite existente,
sem migração de esquema, e entram nos backups completos. Não entram na troca JSON
manual com o site nem no resumo para o chat. São cartões elaborados por você;
o aplicativo não fornece um banco de questões clínicas.

**Backups protegidos:** em Dados e backup, criar/restaurar arquivos `.diolinobak`.
Senha nova de pelo menos 12 caracteres, Argon2id (64 MiB, 3 iterações, 4 lanes) e
AES-256-GCM com sal e nonce aleatórios. A senha não é salva nem recuperável pelo aplicativo.
Senha incorreta ou arquivo alterado impedem a restauração. A confirmação de restauração
substitui o banco após validar e criar uma cópia anterior. Limite de 256 MiB.
O backup protegido contém o SQLite, incluindo cartões e notas; credenciais guardadas
fora do banco não entram. O banco em uso, os backups automáticos e as exportações
JSON/CSV continuam sem criptografia própria. Durante a restauração, arquivos temporários
descriptografados são criados na pasta local e removidos no fluxo normal; não é apagamento forense.

**PDF:** extração de texto, combinação com ordem conferida e extração de páginas
como `1,3-5`, usando pypdf. Até 20 MiB por PDF e até 200 páginas no resultado.
Arquivos protegidos por senha não são abertos neste painel. PDFs de imagens podem
não ter texto extraível; este painel não rasteriza páginas para OCR. Novos arquivos
não sobrescrevem os originais nem arquivos existentes.

**OCR offline:** Tesseract 5.5.3.20260724 com português e inglês incluídos. Aceita PNG,
JPEG, TIFF e BMP de até 20 MiB e 40 MP. Limite de 60 segundos por imagem.
O texto fica em uma área editável e só é gravado em anotação após sua ação de salvar
e escolha do título. Também pode ser salvo em TXT ou usado para preparar um cartão.
Reconhecimento pode conter erros e deve ser conferido antes do uso. Documentos não
são enviados à internet. PDFs, OCR e derivação da chave criptográfica trabalham
em segundo plano. Avisos dos componentes ficam em `_internal/licenses` e `_internal/ocr/doc`.
Origens e hashes do mecanismo: `assets/ocr/SOURCES.md`.

## Desinstalação com remoção dos dados — 1.2.1

O instalador inclui desinstalador, disponível em **Configurações do Windows →
Aplicativos → Aplicativos instalados → Diolino → Desinstalar**, ou pelo
`unins000.exe` da versão instalada. A partir de 1.2.1, a confirmação informa
que serão excluídos os dados de `%LOCALAPPDATA%\ProjetoDiolino` do usuário atual:
banco SQLite, backups internos, anotações, registros de saúde, preferências,
credenciais locais, diagnósticos, impressos e recursos auxiliares nessa pasta.
Essa confirmação permite cancelar antes de apagar. Feche o Diolino usando
**Sair completamente**; a desinstalação é recusada enquanto uma versão instalada
está aberta. O desinstalador encerra o companion local identificado pelo atalho
de inicialização, incluindo os processos Python correspondentes, e remove seus atalhos.
Sem o atalho de identificação, serviços iniciados manualmente devem ser encerrados por você.

A limpeza fica restrita à pasta de dados do aplicativo e aos atalhos conhecidos.
Não procura nem apaga exportações, backups externos, cópias do projeto, snapshots
para o chat fora dessa pasta, arquivos copiados manualmente ou dados de outros usuários.
Também não exclui a conta ou os dados do site e não cancela eventos já enviados
ao iCloud. Reinstalar neste PC começa com um banco vazio se a limpeza terminou;
instalar em outro PC cria outro banco local, até você importar seus dados.
Arquivos ligados por junctions não têm seus destinos externos percorridos na limpeza.
A exclusão comum de arquivos não equivale a apagamento forense ou revogação de credenciais
no provedor. Instalar uma atualização não apaga dados. Desinstalação silenciosa com
limpeza exige `/PURGEDATA=1`, além das opções silenciosas do Inno Setup.

## Troca manual com o site — 1.2.0

Em **Dados e backup**, use **Exportar troca com o site…** para gerar um JSON novo
`diolino-sync-1`. No site, abra **Mais → Seus dados → Troca manual com o Windows**,
selecione o arquivo e clique em **Conferir arquivo**. A prévia informa novos, iguais,
diferenças e bloqueados. Diferenças mantêm o destino por padrão; confira as versões
e escolha usar o arquivo somente quando desejar substituir aquele registro.
Registros semelhantes sem vínculo podem ser mantidos separados explicitamente.
O site permite a troca mesmo quando já há dados, sem exigir limpar a conta.

Depois, use **Exportar troca para o Windows** no site e **Importar troca do site…**
no aplicativo. Esse retorno traz as alterações e os vínculos reconhecidos. Repita
o percurso sempre que quiser atualizar ambos os lados. Não é sincronização automática.
IDs locais são remapeados, preservando relações de planos/etapas e treinos/séries.
Reimportações reconhecem os vínculos; conflitos não são resolvidos por horário do relógio.
Alterações posteriores à prévia exigem gerar outra prévia. Importações no Windows
usam uma transação e backup SQLite anterior. O site inicia o download do backup JSON
antes da confirmação; confira o download no navegador.

São incluídos registros ativos de todas as categorias e anotações pessoais. O arquivo
contém dados de saúde e não tem criptografia própria. Guarde-o em pasta privada e
envie somente à sua conta. Não são incluídos anexos, exclusões, credenciais iCloud,
preferências, favoritos/posição da Bíblia nem o relógio ativo do Pomodoro. Estudos
já confirmados pelo Pomodoro são registros normais e entram na troca.
Itens ausentes no arquivo não são apagados; exclusões precisam ser feitas nos dois lados.
Um vínculo já excluído no destino bloqueia a recriação automática e seus dependentes.
Notas são trocadas em texto simples: a formatação local é preservada se o texto não mudou,
mas é removida quando o texto importado substitui o anterior. Limites: arquivo de
1,8 MB e textos de até 20.000 caracteres. O histórico completo permanece nos backups
de cada lado; o arquivo de troca não substitui esses backups.

## Pomodoro 1.1.0 — Windows

O botão **Pomodoro** no cabeçalho abre uma janela independente; há também um atalho
no resumo de Estudos. Foco de 25 minutos, descanso de 5 e descanso longo de 15 após
quatro focos completos. As três durações aceitam de 1 a 180 minutos. Cada etapa
começa manualmente; é possível pausar, retomar, encerrar o foco antes ou pular o descanso.

Escolha Medicina ou Bíblia e informe o tema/passagem. Na medicina, escolha também
o formato de estudo. Ao terminar, **Confirmar e salvar estudo** cria um registro normal;
**Descartar sessão** não cria estudo. Descansos não contam como foco. A duração médica
é truncada para décimos de minuto; sessões menores que 6 segundos não são registradas.
A Bíblia mantém sua estrutura existente, com duração na reflexão, sem meta mínima.
A data e a hora são as reais do início do foco, não o dia selecionado para consulta.

Fechar a janela do Pomodoro mantém a contagem. Sair completamente pausa e preserva
a sessão. Ao abrir novamente, ela aguarda retomada/confirmação. Interrupções superiores
a 10 segundos entre atualizações pausam a contagem sem acrescentar esse intervalo.
Enquanto ativo, o estado é salvo a cada 10 atualizações e nas mudanças de etapa;
um encerramento abrupto pode perder até cerca de 10 segundos recentes. A confirmação
é protegida contra duplicação após falhas. O estado fica no banco local existente,
incluído nos backups SQLite, sem migração de esquema. Esta adição é do Windows;
o site ainda não inclui o Pomodoro.

## Correção 1.0.2

Anotações: botão Excluir selecionada na lista e confirmação dentro da janela.
A exclusão cancela o salvamento automático pendente e preserva o histórico.
Ações do editor permanecem visíveis em janelas menores. Relógio de Brasília
no cabeçalho, com segundos e fuso America/Sao_Paulo. Instalador padrão Inno Setup;
o instalador Python 1.0.0 foi retirado após detecção comportamental do Kaspersky.
Versão 1.0.2 instalada por usuário, sem desligar proteções ou criar exclusões.

## Atualização 1.0.0 — aplicativo Windows offline

- Agenda mensal com navegação por mês/ano, marcação de hoje e dias com eventos,
  filtro por dia e atualização ao cadastrar, editar ou excluir compromissos.
- Configurações → Gerenciamento de Módulos: ocultar/reativar áreas preservando
  todos os registros. Visão geral, checagem, dados/backup e configurações são fixos.
  Ocultar a Agenda não desliga seus lembretes ou uma sincronização já habilitada.
- Aparência e Temas: oito estilos solicitados, além do monocromático anterior.
  Prévia, aplicação e persistência local. A referência conceitual continua sendo
  a prancha Canva https://canva.link/l8gtsneb6hk6kns; nenhuma fonte remota é exigida.
- Anotações diárias: títulos, data editável, pesquisa por conteúdo/etiquetas/data,
  filtros dia/mês/ano, favoritas, formatação de trechos, listas, links textuais,
  navegação entre notas e salvamento automático após 900 ms sem digitação.
  Erros de salvamento ficam visíveis e impedem o fechamento normal com perda
  silenciosa. Edição é armazenada em texto + intervalos de formatação no SQLite.
  A exportação TXT/Markdown e o HTML para imprimir/PDF são em texto simples;
  os backups SQLite preservam a formatação e o histórico. Exclusões são lógicas.
  Ainda não há pauta de linhas desenhadas no editor nem abertura de links ao clicar.
- Bíblia offline: BPM em domínio público, com aviso de tradução em revisão,
  pesquisa, favoritos, fonte/espaçamento e última posição salvos. Inclui as 81
  seções/livros da fonte oficial, com deuterocanônicos e variantes. Detalhes,
  licença, formato de importação e limitações: data/bibles/README.md.
- Migração 7 → 8 aditiva com backup anterior; registros existentes preservados.
  Notas privadas não entram no resumo do chat nem na sincronização iCloud.
- Pacote portátil: releases/1.0.0-distribuicao/Diolino-portatil.zip. Extraia toda
  a pasta antes de abrir Diolino/Diolino.exe; não copie apenas o executável.
- Instalador por usuário: releases/1.0.0-distribuicao/Diolino-Instalador.exe,
  sem necessidade de administrador, com atalhos e desinstalação no Windows.
  O instalador requer uma pasta de destino vazia; atualizações devem usar outra
  pasta de versão. A desinstalação mantém os dados em LOCALAPPDATA/ProjetoDiolino.
  Pacotes sem assinatura digital; não houve certificação por terceiros.
- Reproduzir: build.ps1 e depois scripts/build_distribution.ps1.

Essas adições pertencem ao executável Windows. O site privado continua com a
atualização visual já publicada e seu banco independente; estes módulos novos
não são sincronizados automaticamente com o site.

## Abrir

Execute `Diolino.exe` na pasta de distribuição ou use o atalho criado na área de trabalho.
O uso local não precisa de navegador, servidor, conta online nem chave de API.
A integração opcional com o iCloud requer internet e autenticação da sua Conta Apple.
Ele pode continuar aberto quando o GPT for fechado. Para abri-lo por ferramentas de automação,
use `scripts/start_diolino.ps1` (`-Background` para iniciar na bandeja): o lançador cria o processo
fora do grupo de processos da ferramenta. A abertura comum pelo atalho da área de trabalho
ou pela inicialização do Windows usa diretamente o executável.

## Gravura e revisão visual 0.9.4

O estilo Gravura acrescenta monograma, filetes e cantoneiras discretas, inspirados em cadernos
impressos. Em Aparência, Acabamento gráfico permite alternar para Discreto, sem ornamentos.
O Alto Contraste oculta os detalhes decorativos. O espaço interno dos cartões acompanha
imediatamente as mudanças de densidade, e a prévia também respeita o Alto Contraste.

A navegação usa um subconjunto dos ícones Lucide, obtido pelo GitHub e distribuído localmente
com licença e atribuição em assets/visual/lucide. Os contornos são renderizados antes da
compilação e coloridos pelo aplicativo, sem depender de uma fonte de símbolos do Windows.
Fonte e revisão: https://github.com/lucide-icons/lucide/tree/03f11e2d6adc319ea21e9a1d5820a99cd3767257.
O uso do GitHub nesta atualização foi pesquisa e incorporação de recursos visuais licenciados;
não houve publicação do projeto ou dos dados pessoais em um repositório.

## Acabamento visual 0.9.3

Direção visual criada no Canva: https://canva.link/l8gtsneb6hk6kns.
O aplicativo usa cartões com cantos arredondados e contornos suavizados, botões com bordas
próprias para estados normal, foco, pressionado e desabilitado, além de espaçamento interno
padronizado nos campos. A suavização dos contornos é desenhada localmente com Pillow,
sem depender das sombras ou animações do Windows. Tema escuro, Alto Contraste e fontes
personalizadas continuam disponíveis. A referência do Canva é conceitual; os textos e
componentes funcionais são definidos no código do aplicativo.

## Bíblia, relatórios e planners 0.9

No Windows, **Bíblia** permite escolher NAA, ARA, ARC, NVI, NVT, NTLH ou ACF, livro e capítulo.
O capítulo abre no leitor online YouVersion/Bible.com (ACF: Bíblia Online). A integração usa links
para as versões disponibilizadas pelos leitores; requer internet, sem copiar suas traduções para o PC
ou sincronizar contas. **Registrar estudo** abre um formulário com a referência e versão, que só
confirma um registro após Salvar. Também há ficha imprimível e planos de João (21 dias) e Provérbios
(31 dias), com etapas e datas. Criar ou checar um plano não registra estudo bíblico automaticamente.
Fontes do catálogo: https://www.bible.com/pt/versions e https://www.bibliaonline.com.br/acf/jo/3.

**Relatórios / Imprimir** inclui todas as áreas do banco: pilares, hábitos, antropometria, alimentação,
hidratação, treinos e séries, sono, medicação, saúde, exames, medicina, Bíblia, agenda, planos,
perfil e simulações. Escolha áreas, período (até 366 dias), anotações e seções vazias. São impressos
registros ativos; o histórico de alterações e exclusões continua disponível na exportação completa.
Registros datados são filtrados pelo período; séries seguem a data do treino. Planos são incluídos
quando seus intervalos se sobrepõem, etapas pelo prazo (incluindo etapas sem prazo), e perfil sem filtro.
Ausência de dados aparece como “–”, e não como zero ou falha de execução.

Planners A4: diário (1 página), semanal (programação + hábitos), mensal (calendário + hábitos),
fichas de estudo médico/bíblico e plano de ação. O caderno integrado reúne semana, sete páginas
diárias, duas fichas de estudo e plano de ação (12 páginas no modelo em branco). É possível incluir
registros existentes; conteúdo extenso pode gerar páginas adicionais. Mensal preenchido inclui
uma agenda detalhada em página separada. A semana começa na segunda, com os pilares também no domingo.

**Visualizar / Imprimir** cria um HTML autossuficiente na pasta local `impressos` e o abre no navegador.
Use o botão **Imprimir / Salvar PDF**, com papel A4, retrato e escala 100%. Desative os cabeçalhos e
rodapés automáticos do navegador. **Salvar em arquivo** permite escolher outra pasta. Não há
impressão automática nem envio a serviço externo. Cópias geradas permanecem locais até você removê-las;
anotações em papel não são importadas automaticamente. Estes recursos estão na versão Windows.

A interface Windows e a página móvel usam textos objetivos, sem frases motivacionais. O aplicativo
define cores, fontes, espaçamento e sombras próprios, e resolve cores padrão do sistema para sua
paleta. Efeitos de animação/transparência do Windows não são necessários. A moldura nativa da janela,
diálogos do sistema e suavização das fontes ainda dependem do Windows/Tk; não há promessa de renderização
idêntica ao desativar a suavização de fontes. Nenhuma configuração global do Windows é alterada.

Na versão 0.9.1, os espaçamentos internos e as linhas de tabelas acompanham o DPI informado pelo Tk;
a altura das linhas considera também a altura real da fonte, inclusive no modo compacto.
A janela inicial é limitada ao tamanho disponível da tela. Isso não constitui suporte completo
a troca dinâmica entre monitores com DPIs diferentes: ao mudar a escala, reabra o aplicativo.
O Alto Contraste do Windows tem prioridade temporária sobre o tema, usando suas cores de texto
e fundo e ocultando sombras decorativas. É consultado na abertura e quando a interface recebe foco,
sem sobrescrever as preferências salvas. O navegador respeita cores forçadas e redução de movimento.
Testes simulam escalas de 100%, 125%, 150% e 200% nas métricas das tabelas; não alteram o Windows.

## Aparência 0.8

Abra **Aparência** na barra lateral do Windows. Escolha tema claro ou escuro, tamanho do texto
(100%, 110% ou 125%), espaçamento confortável ou compacto, títulos clássicos (Georgia) ou modernos
(Segoe UI) e sombra sutil ou desativada. A amostra muda antes de aplicar: **Salvar e aplicar**
atualiza a interface imediatamente, sem reiniciar. **Desfazer alterações** recupera as escolhas
salvas; **Restaurar padrão** prepara o preto e branco claro original, e só grava ao salvar.

As preferências ficam em `appearance.json`, junto ao banco local, e são recuperadas ao abrir.
Não alteram registros, metas ou o banco de saúde; a cópia SQLite não inclui esse arquivo de aparência.
Formulários, tabelas, calendário e gráficos acompanham o tema. Símbolos dos pilares mantêm sua
identificação textual e cores de situação. O Safari mantém sua configuração própria por navegador.

## Planos e interface 0.7

A versão Windows inclui uma faixa semanal de segunda a domingo na Visão geral, Checagem,
Planos e Agenda. Clique no dia para alterar a data de referência; as setas avançam/voltam
uma semana, com destaque no dia selecionado e mês em português. Os controles de data e Hoje
continuam disponíveis. Selecionar datas não cria registros ou confirma compromissos.
Títulos e valores grandes têm uma sombra de 1 pixel muito suave; textos de leitura e campos
ficam nítidos. No navegador, a sombra também é discreta e se adapta ao tema claro/escuro.

**Planos** funciona no Safari e no aplicativo Windows. Crie um objetivo, escolha sua área e
adicione etapas com prazos, prioridades e situação (A fazer, Em andamento, Concluído).
A checagem fica salva e pode ser desfeita. O progresso reflete as etapas ativas concluídas;
não altera os pilares diários nem cria minutos de estudo, treinos ou avisos da agenda.
O plano só muda de situação quando você o editar; 100% das etapas não o arquiva automaticamente.

No navegador há visualização em lista/quadro, busca, filtros de Hoje/7 dias/Atrasadas,
arquivamento reversível e duplicação com etapas desmarcadas e prazos limpos. Modelos opcionais
ajudam a organizar a semana e os estudos; escolher um modelo apenas preenche o formulário,
e só Criar plano grava os dados. Uma criação com várias etapas é uma transação única.
Planos e etapas entram no histórico, exportação CSV e backup SQLite. A migração para esquema 7
faz backup automático antes de criar as tabelas e continua restaurando versões 1 a 6.

A interface móvel preserva a tipografia clássica e o preto e branco, com ícones discretos,
modo claro/escuro local ao navegador, navegação semanal e atalhos para água, peso e estudo.
Os pilares têm símbolos individuais: verde ✓ confirmado, vermelho × quando marcado Não realizado,
cinza ◔ em andamento e – quando não informado. Ausência de registro aparece como –.
Não são usados somente sinais de cor: cada símbolo tem identificação textual/acessível.
O gráfico removido de pilares dos últimos 7 dias não foi reintroduzido.
Na visão geral, as etapas com prazo aparecem separadas dos compromissos da agenda.

Referências de organização: [Todoist Boards](https://www.todoist.com/inspiration/kanban-board)
e [TickTick](https://ticktick.com/features). Não há integração de dados com esses serviços.

## Acesso pelo iPhone / Safari

O módulo `mobile_server.py` oferece uma interface responsiva local sobre o mesmo banco SQLite
do desktop: visão geral, checagem, consulta/criação/edição dos registros, busca TACO, simulação
calórica e envio de texto/arquivo de áudio para a IA offline do PC, com revisão antes de salvar.
Não é uma cópia separada dos dados. Navegue novamente na tela do desktop para atualizar a listagem.
Configuração de conta iCloud, restauração de backups e instalação de modelos permanecem no PC.

Inicie com `scripts/start_mobile.ps1`; o processo fica independente do GPT. Na rede configurada,
abra **http://192.168.0.6:8765** no Safari e informe o código de `%LOCALAPPDATA%\ProjetoDiolino\mobile-access.json`.
O código é local, não é a senha Apple. O PC deve ficar ligado, acordado e conectado à rede.
O iPhone deve estar no Wi-Fi do mesmo roteador/rede local; o PC pode usar cabo Ethernet.
Não funciona pelo 4G/5G ou fora dessa rede. Redes de convidados com isolamento podem impedir a conexão.
O endereço pode mudar se o roteador atribuir outro IP ao PC; nesse caso atualize a URL e a regra de Firewall.

Execute `scripts/install_mobile_startup.ps1` para iniciar o acesso ao entrar no Windows (já configurado
nesta instalação). Esse serviço é separado do aplicativo desktop: “Sair completamente” no desktop
não encerra o servidor móvel. Não há serviço instalado com acesso de administrador.

O Firewall precisa da regra TCP 8765 limitada ao IP do PC e à rede 192.168.0.0/24. Configure uma vez
executando **scripts/Habilitar-acesso-iPhone.cmd** como administrador, ou execute
`scripts/enable_mobile_network.ps1` em um PowerShell elevado. Não altera o perfil Público/Privado
da rede e não abre portas no roteador. Requer confirmação do próprio Windows.

O acesso usa HTTP local (sem criptografia de transporte); use somente uma rede de confiança.
Há código de 12 dígitos, sessão HttpOnly/SameSite com validade de 12 horas, verificação de origem/Host,
proteção CSRF, limite de tentativas e de uploads. Saúde exige autenticação. Não publique essa porta
diretamente na internet. Para acesso externo ou tráfego cifrado, configure futuramente uma VPN/HTTPS.
No Safari, use Compartilhar → Adicionar à Tela de Início se desejar um ícone.
Arquivos de áudio são enviados ao PC e os temporários são removidos após a transcrição.
O microfone direto do Safari não é usado por esta página HTTP: selecione um áudio em Arquivos.

## Preenchimento

Na versão 0.9.2, o assistente offline foi removido da interface. Use os formulários de registros.
Os modelos baixados anteriormente permanecem no PC; nenhum dado pessoal foi apagado.

## Armazenamento local

Os dados pessoais ficam em `%LOCALAPPDATA%\ProjetoDiolino\diolino.sqlite3`, fora do código e do executável.
Atualizar o programa não exige apagar o banco. Há backup automático diário ao abrir e backup manual
em **Dados e backup**. Faça também cópias para outro dispositivo: um backup no mesmo disco não
protege contra perda física do PC. Os arquivos não têm criptografia própria.

O arquivo `Resumo-para-o-chat.md` na pasta do projeto é atualizado ao abrir, salvar e navegar.
Ele contém um resumo dos últimos sete dias (pilares, checagens, peso, sono, água e calorias) e os próximos
dez títulos da agenda. Doses, diagnósticos, exames e notas privadas não entram nesse arquivo.
O assistente deste projeto pode consultá-lo; não há mensagens automáticas nem sincronização bidirecional.
Confira sempre a data do snapshot. Os lembretes do chat podem usar esse arquivo como contexto quando disponível.

## Organização

- **Visão geral:** resumo do dia, atalhos para a rotina e próximos compromissos.
- **Checagem diária:** três pilares em destaque, hábitos secundários, fechamentos e constância.
- **Saúde:** resumo, medidas, sono, alimentação, água, medicação, sinais, exames, perfil,
  calculadora, simulações salvas e gráficos de 7/30/90/365 dias.
- **Treinos:** atividades e séries/cargas, com gráfico de duração registrada.
- **Estudos:** medicina e Bíblia, com gráfico de minutos de estudo médico.
- **Agenda:** tarefas, compromissos e notas, datas, horários e notificações.
- **Agenda › iCloud e iPhone:** conexão opcional do calendário e roteiro para alarmes do Relógio.
- **Dados e backup:** exportação, restauração e atualização do resumo para o chat.

Ícones da fonte Segoe MDL2 Assets instalada no Windows, conforme o
[catálogo da Microsoft](https://learn.microsoft.com/en-us/windows/apps/design/iconography/segoe-ui-symbol-font).
Interface monocromática, com títulos em Georgia, textos em Segoe UI, bordas finas e gráficos em tons de cinza.
As tabelas ajustam as colunas ao conteúdo e ao tamanho disponível. Colunas numéricas ficam alinhadas
à direita, e uma prévia mostra o texto completo ao passar o mouse sobre uma célula.

## Calendário iCloud e Relógio do iPhone

Configure em **Agenda › iCloud e iPhone**. Digite sua Conta Apple e uma
[senha específica de app](https://support.apple.com/pt-br/102654), gerada por você na Conta Apple.
Use **Conectar e listar calendários**, escolha um calendário (recomendado: **Projeto Diolino**,
que também pode ser criado pelo botão correspondente) e clique em **Ativar sincronização**.
A conexão só fica ativa após esse passo; não basta instalar a atualização.

Apenas a Agenda é sincronizada, nos dois sentidos, a cada 5 minutos enquanto o aplicativo estiver aberto.
Os dados de saúde não entram nessa integração. A senha e a conexão são protegidas com DPAPI para
a conta atual do Windows, no arquivo `icloud-connection.bin` fora do banco e das exportações.
Use **Desconectar** para apagar essa conexão local; os eventos já enviados continuam no iCloud.

São sincronizados título, descrição, data, hora, duração, categoria, situação e aviso de calendário.
O fuso é America/Fortaleza; eventos sem hora são de dia inteiro e eventos com hora sem duração usam
30 minutos. A duração da Apple é preservada ao importar. Concluídos, cancelados e exclusões locais
são enviados como eventos cancelados, sem apagar o histórico. Exclusões no iCloud cancelam o item local.
UIDs estáveis evitam duplicatas, e gravações usam ETag/If-Match. Se o mesmo item mudar nos dois lados,
escolha a versão na tela de integração. Falhas de leitura não são interpretadas como exclusões.

Recorrências sem participantes são importadas como ocorrências para consulta, de 366 dias atrás
até 731 dias à frente; o período avança automaticamente. Regras, exclusões e alterações de ocorrências
são calculadas a partir da série da Apple. Edite/exclua esses itens no Calendário da Apple;
eles nunca são enviados como eventos independentes. Datas antigas fora do período permanecem no histórico.
Convites (eventos com participantes/organizador) continuam sem importação. Não são enviados convites.
Depois de restaurar backups antigos, confira os vínculos antes de reativar uma conexão com a Apple.

Notificações do Calendário **não** são alarmes do app Relógio. O roteiro disponível no aplicativo explica
como criar no iPhone com iOS 26.6 um atalho pessoal que lê os eventos de hoje e cria alarmes no Relógio.
Ele precisa ser montado e conferido no aparelho; não foi instalado automaticamente. Reexecute o atalho
após mudanças de agenda e desative alarmes antigos de horários alterados. Seus outros alarmes são preservados.
O [AlarmKit](https://developer.apple.com/documentation/alarmkit) atende apps nativos de iOS e não expõe
controle remoto do Relógio ao programa de Windows.

Antes da autenticação real, os testes da integração usam um servidor simulado; não comprovam uma
conexão com sua conta. O estado na tela informa conexão pendente, erros ou a última sincronização concluída.

## Agenda e notificações no Windows

O usuário autorizou iniciar minimizado com o Windows. O atalho de inicialização chama o executável com `--background`.
Fechar a janela deixa o aplicativo na bandeja; clique no ícone para abrir. Clique com o botão direito para sair completamente.
O menu lateral também oferece **Sair completamente**. Depois de sair, os lembretes voltam na próxima abertura.
Apenas uma instância usa cada pasta de dados; abrir novamente mostra a janela existente.

Cadastre data, hora, título e **Notificar: Sim**. Lembretes pendentes que vencerem com o PC desligado serão apresentados
quando o aplicativo abrir. Cada horário é notificado uma vez; reagendar permite um novo aviso. Concluir ou cancelar
impede avisos futuros. Notas sem horário podem usar **Notificar: Não**.
Os avisos nativos respeitam as configurações de notificações e Não Perturbe do Windows; o aplicativo não altera essas configurações.

## Calculadora calórica

Usa a equação simplificada de [Mifflin–St Jeor (1990)](https://pubmed.ncbi.nlm.nih.gov/2305711/)
para estimar gasto de repouso (GER), como aproximação do metabolismo basal:
`10 × peso (kg) + 6,25 × altura (cm) − 5 × idade + coeficiente (+5 ou −161)`.
Gasto total = GER × fator de atividade informado. Ingestão simulada = total × (1 − déficit percentual/100).
O fator já inclui a atividade; o aplicativo não adiciona novamente o treino.
O [NIDDK](https://www.niddk.nih.gov/bwp) fornece contexto para os fatores de atividade e limitações de simulações.
Não implementamos o modelo dinâmico de peso do NIDDK, nem prevemos perda de peso.

O coeficiente não é inferido. O cálculo é para adultos, não aplicável à gestação/amamentação.
Uma simulação abaixo de 1.000 kcal/dia não é apresentada como meta. Os valores acima desse limite
também não são garantia de adequação nem prescrição. As simulações salvas preservam os parâmetros utilizados.

## Como começar

1. Preencha **Perfil e saúde** e sua primeira medição em **Peso e medidas**.
2. Escolha a data no topo usando os campos Dia, Mês e Ano. Horários usam campos Hora e Minuto (24 horas).
   Os controles Hoje/Agora facilitam o preenchimento. O banco mantém datas ISO internamente.
3. Em **Saúde › Alimentação**, use **Buscar na TACO** para selecionar o alimento e os gramas consumidos.
   Os nutrientes da porção são calculados automaticamente. Use **Novo manual** para informações de rótulos
   ou outros alimentos; nesse modo, informe os nutrientes da quantidade consumida, não de 100 g.
4. Cadastre um **Treino**, depois vincule suas **Séries de musculação**. A função Duplicar incrementa
   o número da série. Especifique se a carga é total, por halter/lado, da máquina ou peso corporal.
5. Registre o sono com data e hora de início e fim. Use como data do registro o dia em que acordou.
6. Em medicamentos, separe dose prescrita de dose tomada, com unidade e horário. O sistema não recomenda doses.
7. Registre estudo médico e bíblico. A checagem diária soma os minutos de medicina (meta 60) e exercício
   (meta 40). O estudo bíblico não tem tempo mínimo. Você também pode confirmar os pilares diretamente.
   Uma checagem explícita tem prioridade sobre o cálculo automático; os registros detalhados são preservados.

Todos os pilares são diários, inclusive domingo. A exceção de domingo é somente para o lembrete no chat.
Campos vazios significam desconhecido, não zero. A alimentação sinaliza totais com dados faltantes.

## Funcionalidades

- Catálogo offline TACO oficial: 597 alimentos, 15 categorias, 66 medidas nutricionais (composição,
  minerais, vitaminas, ácidos graxos e aminoácidos, quando disponíveis). Busca sem acentos e filtro por categoria.
- Fonte: NEPA/UNICAMP, 4ª edição revisada e ampliada (2011), edição mais recente localizada no site oficial
  em 16/10/2026. A data da notícia de disponibilização não é o ano da edição.
- A TACO usa gramas de parte comestível. Não há conversão presumida de mL ou medidas caseiras.
  Traços, valores ausentes, não aplicáveis, em reavaliação e inconsistências são mantidos em aberto.
- Cada lançamento guarda a fonte e a composição original usada, inclusive nutrientes adicionais.
  Alterar a quantidade recalcula a porção. Registros antigos mantêm seus valores ao atualizar o catálogo.
  Para editar nutrientes manualmente, use **Preenchimento manual** no editor.
- Atualização do banco da versão 4 para 5 com backup preventivo; fontes nutricionais entram nos backups,
  no histórico e no arquivo `food_nutrition.csv` da exportação. Detalhes de origem em `data/taco/README.md`.

- Checagem secundária diária: higiene bucal 3x, banho 2x e duas confirmações da medicação.
- Água: meta pessoal de 50 mL/kg/dia calculada com o último peso até a data selecionada.
  O progresso usa os registros de Água e cafeína marcados como água. Registros antigos com nomes
  exatos como Água, Água mineral e Água filtrada também contam; outros nomes precisam ser classificados.
  Sem peso, o sistema mostra o consumo e pede uma medição, sem inventar uma meta.
- As checagens são salvas a cada clique, separadas dos três pilares, com histórico e exportação.
  As duas checagens de medicação não criam doses no registro detalhado nem definem uma prescrição.
- Atualização automática do banco anterior com backup preventivo. Backups da versão anterior
  continuam podendo ser restaurados e são atualizados em uma cópia antes da restauração.

- Perfil, antropometria, alimentação, hidratação/cafeína, treinos e séries.
- Sono, medicamentos, sinais/sintomas, exames/consultas e estudos.
- Inclusão, edição, duplicação, exclusão lógica e histórico das alterações.
- Busca e filtro por data; gráficos de peso, medidas, sono, calorias, água e constância.
- Backup SQLite, restauração validada com cópia preventiva e exportação ZIP/CSV.

## Limites desta primeira versão

- Sem importação de exames, anexos, catálogo nutricional ou integração com dispositivos.
- Sem medição de gasto calórico, prescrição clínica, recomendação de doses ou inferência causal.
- Sem senha ou criptografia própria; utiliza a proteção da conta Windows.
- O gasto calórico é estimado; calorias dos alimentos continuam sendo informadas pelo usuário.

## Desenvolvimento

Python 3.12+, com Tkinter e SQLite. Execução: `python app.py`.
Testes: `python -m unittest discover -s tests -v`.
Teste de telas: `python app.py --data-dir test-output/ui --smoke-test`.
Build: instalar `requirements-build.txt` e executar
`python -m PyInstaller --noconfirm --clean --windowed --onedir --name Diolino app.py`.

As dependências estão em requirements-runtime.txt e são incluídas no pacote. PyInstaller é usado somente no empacotamento.
