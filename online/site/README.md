# Diolino online

## Tema Matrix e Pomodoro — 04/11/2026

Tema padrão Matrix com fundos pretos e verdes, fontes locais, menu recolhível no
desktop e navegação inferior no celular. Os temas anteriores continuam disponíveis.
A visão geral distingue ausência de registro, metas, agenda e etapas. Planner,
Biblioteca, documentos, Bíblia, anotações e formulários usam o mesmo sistema visual.
Em Mais, a chuva de código é opcional, desativada inicialmente, limitada ao
cabeçalho e pausada com aba oculta ou movimento reduzido do sistema.

Pomodoro no cabeçalho: foco/descanso de 1 a 180 minutos, iniciar, pausar, retomar
e encerrar. Usa tempo decorrido por relógio, incluindo aba em segundo plano, sem
iniciar ciclos automaticamente. Após foco, abre o formulário de estudo com os
minutos completos; nenhum estudo é salvo sem revisão e confirmação. O cronômetro
fica em memória nesta aba e é perdido ao sair/recarregar. Cartões FSRS permanecem
no Windows, e a busca do cabeçalho pesquisa telas e ações, não todos os textos.

Verificação local em Edge isolado: dashboard em 320, 390, 768 e 1440 px; Planner
dia/semana/mês, Biblioteca grade/lista e anotações sem overflow horizontal geral
nas larguras verificadas; menu expandido/recolhido, Ctrl+K, Escape, foco e
movimento reduzido. Pomodoro exercitado com relógio simulado, incluindo pausa,
retomada, término e formulário com minutos preenchidos. Os 22 testes do site
passaram. Contrastes calculados sobre #0D1711: texto 16,22:1, texto secundário
9,37:1 e cores de estado entre 7,15:1 e 13,80:1. Esses testes não constituem
certificação completa de WCAG; leitores de tela e todos os navegadores não foram
auditados. Capturas locais usam somente os dados fictícios da base de testes.

Site privado, com autenticação do ChatGPT e banco D1. O aplicativo Windows original permanece separado.

## Troca manual com Windows — 1.2.0

Em Mais → Seus dados → Troca manual com o Windows, exporte/importe arquivos JSON
`diolino-sync-1`. O Windows 1.2.0 oferece os botões correspondentes em Dados e backup.
A importação funciona com conta já preenchida, mantém itens ausentes e apresenta
prévia das diferenças. O destino prevalece por padrão; cada diferença permite usar
a versão do arquivo. Possíveis correspondências sem vínculo podem ser criadas separadamente.
IDs e relações são remapeados, e os vínculos retornam no próximo arquivo exportado.
Antes de aplicar, o site inicia um download do backup JSON; confira o download.
A revisão da conta impede aplicar prévias desatualizadas. Autenticação, origem,
limite de corpo e atualização concorrente continuam obrigatórios.

Inclui registros ativos e anotações em texto simples. Não inclui exclusões, anexos,
credenciais, preferências nem o relógio do Pomodoro. Itens excluídos já vinculados
no destino não são recriados. Exclusões devem ser repetidas nos dois lados.
Arquivos contêm dados pessoais e de saúde. O histórico permanece nos backups de cada lado.
O limite de 1,8 MB da conta e dos arquivos é mantido. A importação inicial antiga
continua disponível e ainda exige uma conta vazia; ela não é o botão de troca manual.

## Biblioteca de arquivos e Planner — 04/11/2026

Menu próprio Biblioteca, separado de Mais. Armazenamento privado em R2/BUCKET;
metadados e partes em tabelas D1 aditivas. Nenhum anexo é gravado no JSON da conta.
Limites operacionais definidos no código: 500 MiB/arquivo, 10 GiB/conta (arquivos
prontos e reservas pendentes), três envios pendentes e até mil arquivos ativos.
Esses números são limites do aplicativo, não garantia de franquia ou gratuidade
da plataforma de hospedagem. Não foi contratado ou alterado plano de cobrança.

Envio em partes de 8 MiB, pausa, tentativas de reconexão e retomada ao escolher
novamente o mesmo arquivo. Nome/tamanho/fingerprint são comparados na retomada;
fingerprint não substitui checksum criptográfico completo. Campos e caminhos
são validados; formatos executáveis, HTML e SVG não são aceitos. A verificação
de cabeçalho do formato não é um antivírus nem valida todo o conteúdo do arquivo.

Vídeo e áudio usam leitura HTTP Range autenticada. PDFs usam PDF.js local,
licença Apache-2.0 em public/pdfjs/LICENSE, sem CDN. Documentos Office são baixados;
não há conversão nem edição. Reprodução depende do codec e do navegador. Arquivos
não são públicos e todas as operações verificam o proprietário. Respostas são
private/no-store. Exclusão de arquivo é definitiva e exige confirmação explícita.
O backup JSON dos registros NÃO inclui os anexos. Baixe cópias separadamente.
Uploads incompletos reservam a cota até serem cancelados; uploads antigos podem
expirar no provedor. Não há promessa de retomada após expiração do upload R2.

Planner Diário substitui a entrada principal Planos, com modos Diário, Semanal
e Mensal. Reaproveita Agenda e etapas de planos ativos, preservando todos os IDs.
Permite criar tarefas, editar, checar e navegar datas. Checagem não confirma pilares.
Planos e objetivos continuam em Mais. Imprimir modelo usa os planners em branco
existentes, e não imprime uma cópia preenchida da tela. No celular, navegação em
duas linhas; no desktop, itens separados na coluna esquerda.

Testes: mídia multipart privada, retorno 401 sem sessão, rejeição de origem externa,
assinaturas, limites, pausa/retomada por partes, cancelamento, download/ranges,
200 MiB sintéticos (transferência, não vídeo reproduzível), períodos semanais,
anos bissextos e navegação de mês a partir do dia 31. Interface local: PDF fictício
renderizado e vídeo MP4 fictício com metadados carregados (2 s, 320x180).
Nenhum documento pessoal foi usado nos testes. Dados locais e produção separados.

## Módulos e relógio — 26/10/2026

Relógio com segundos no fuso America/Sao_Paulo (Brasília), calculado pelo relógio
do dispositivo; a data inicial usa esse fuso. O relógio preserva a data escolhida.

Em Mais: Agenda mensal com navegação e edição; Anotações com salvamento automático,
busca, favoritas, etiquetas e exportação Markdown. Exclusão tem confirmação interna,
é lógica e preserva a nota no histórico exportável. Conflitos de edição são recusados.
Salvamentos automáticos registram metadados de edição sem guardar o texto inteiro
de cada versão intermediária. Campos têm limite de 20.000 caracteres e compartilham
o limite de 1,8 MB da conta.

Configurações permite ocultar/reativar Planos, Agenda, Bíblia e Anotações, preservando
dados; preferências de módulos são salvas na conta. Oito temas além do monocromático.
Tema, acabamento e preferências de leitura ficam no navegador.

Leitor BPM, em domínio público, com aviso de tradução em revisão e licença em
public/bible. Texto carregado permanece na aba; o site não tem suporte completo
a uso offline. Favoritos bíblicos e última posição são locais ao navegador.
Acesso privado e estrutura D1 existentes preservados. Backup JSON online inclui
notas e preferências. O exportador desktop ainda não migra as anotações locais.

## Atualização visual de 26/10/2026

Acabamento Gravura ou Discreto, monograma e ícones Lucide distribuídos localmente com
licença em public/art/icons/LICENSE. Os detalhes visuais seguem os temas claro e escuro;
cores forçadas ocultam os ornamentos. O menu inferior foi ajustado à largura de celular.
Preferências de tema e ornamentos são locais ao navegador e não alteram o banco de registros.

O botão Buscar e Ctrl+K abrem uma lista filtrável de telas e ações. Os formulários mantêm
campos obrigatórios visíveis e agrupam campos opcionais em uma seção expansível, aberta
automaticamente quando há valores preenchidos. Estudos e treinos incluem atalhos editáveis
de duração (15, 30, 40 e 60 minutos). Nenhum atalho salva dados ou confirma pilares.

Recursos: checagem dos três pilares e cuidados secundários; todas as categorias de registros; nutrição TACO; planos com etapas; calculadora; links para sete versões bíblicas; relatórios por área/período; planners diário, semanal, mensal e combinado; exportação e importação inicial JSON.

As operações exigem identidade fornecida pela plataforma. Cada conta possui seus próprios registros. Gravações verificam a revisão do banco para impedir que dois dispositivos sobrescrevam alterações concorrentes. Exclusões são lógicas, com histórico exportável. O site não usa armazenamento do navegador para os registros; somente preferências visuais.

## Limitações desta versão

- O assistente offline foi removido. A sincronização iCloud e as notificações nativas continuam no Windows. O ditado do teclado pode preencher campos.
- Não há sincronização automática com o banco local. A importação inicial requer uma conta online vazia. Faça exportações periódicas pelo botão de backup.
- Registros e histórico por conta têm limite conjunto de 1,8 MB nesta primeira estrutura. Ao atingir o limite, a gravação é recusada sem substituir os dados anteriores. Não é adequado para anexos ou grandes prontuários.
- Importação do desktop inclui registros ativos e referências nutricionais; histórico de exclusões e credenciais iCloud permanecem no PC. JSON de backup pode conter dados de saúde: guarde-o em local privado.
- Disponibilidade depende da hospedagem e da internet, não do computador local. Não há garantia de disponibilidade ininterrupta.

## Desenvolvimento

Use os scripts do plugin Sites. `npm run db:generate` gera migrações; a publicação aplica o esquema na hospedagem. Testes `node --test tests/domain.test.mjs`; `tests/http.test.mjs` exige preview local na porta 5173 com migração aplicada. Nenhum teste grava no banco de produção.

O arquivo de migração pode ser preparado pelo script externo `online/export_desktop.py --output <arquivo.json>`, usando o Python do aplicativo. Não copie bancos, credenciais, arquivos de saúde ou estado local para o repositório deste site.

## Tema Terminal
Novo padrão visual escuro com destaques ciano, verde-limão, amarelo e vermelho. A migração visual acontece uma vez por navegador; os temas anteriores continuam disponíveis em Mais → Aparência. Alteração de apresentação, sem migração de registros. CSS do próprio aplicativo para contornos, controles e sombras; preferências de alto contraste do sistema e impressão permanecem tratadas separadamente. Validado em prévia desktop, viewport de 390 px, editor de registros e alternância claro/Terminal. Não houve instalação de skills adicionais: as oficiais já presentes cobrem o trabalho.


## Leitura interna e capacidade
Limite operacional ampliado para 10 GiB por conta; 500 MiB por arquivo. A franquia e cobrança efetiva da hospedagem Sites não foram expostas nem alteradas. Vídeo com controles nativos, velocidade e tela cheia; PDF com página e zoom; TXT até 2 MiB. DOCX até 20 MiB em modo de leitura local com Mammoth, DOMPurify e iframe isolado sem scripts/rede; imagens e paginação não reproduzidas. Arquivos DOC antigos aceitos para guardar/baixar, com orientação de conversão para DOCX/PDF. Não há conversor DOC binário hospedado. ZIP com metadados limitados antes de descompressão, worker cancelável com timeout; nenhum documento pessoal foi usado nos testes. Arquivos originais permanecem privados e intactos. 


## Biblioteca visual e Planner por horários
Biblioteca com grade/lista, busca, filtros, ordenação e painel de detalhes. Miniaturas privadas de imagens até 20 MiB, primeira página de PDF e vídeo compatível, carregadas por visibilidade; DOCX e demais formatos usam capa identificada pelo tipo. Sem criar cópias persistentes das miniaturas.  Envio recolhível; exclusão exige confirmação explícita no painel. Planner diário/semanal com faixas horárias e área sem horário; cadastro pela faixa preenche a hora. Faixa 06–22h inclui compromissos fora do intervalo para evitar ocultação; opção 24h. A altura das faixas não representa duração e não há arrastar para reagendar nesta versão. Visão mensal e registros preservados, sem migração de banco.

## Retirada da integração OneDrive
Conexão Microsoft, callback, listagem e envio ao OneDrive removidos por solicitação do usuário. Biblioteca própria, leitores e limite operacional de 10 GiB preservados. Nenhuma alteração na integração iCloud ou em arquivos da conta Microsoft.
