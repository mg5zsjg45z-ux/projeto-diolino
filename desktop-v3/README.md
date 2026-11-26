# Diolino 3.0 — prévia alfa

Esta pasta contém uma prévia alfa da interface desktop React + Tauri, desenvolvida ao lado do aplicativo Windows 2.x. Ela ainda não substitui a versão de uso diário nem é uma versão de produção pronta para distribuição.

## O que está incluído

- **Hoje**: indicadores demonstrativos e consulta ao painel local em modo somente leitura no aplicativo Windows.
- **Agenda**: visualizações mensal, semanal, diária e anual. Eventos e releituras próprios persistem no SQLite da 3.0.
- **Planos**: quadro Kanban com tarefas próprias e modo de demonstração.
- **Estudos**: sessões próprias e agendamento de releituras.
- **Biblioteca**: atalhos locais a documentos e planilhas, abertura do arquivo original no aplicativo padrão do sistema e execução dos CLIs WordCraft, PdfCraft e GridCraft instalados separadamente.
- **Saúde**: registros e metas de exercício, sono e peso, com histórico, gráficos e edição. Esses dados ficam no armazenamento local da prévia, separados do banco SQLite pessoal.
- **Foco**: temporizador configurável de concentração, pausas curtas e longas, sessões diárias e histórico local neste dispositivo.
- **Hábitos**: cadastro de rotinas diárias, dias úteis ou fins de semana; marcação de cumprimento, pausa ou não realização, sequência atual e histórico visual de 30 dias, salvos localmente neste dispositivo.

Os arquivos adicionados à Biblioteca não são copiados para dentro do projeto; a prévia salva o caminho local do arquivo. Os executáveis ArtCraft não são incluídos no repositório nem no aplicativo.

## Dados e privacidade

A fonte padrão **Meus registros (3.0)** abre os dados próprios. **Demonstração** usa dados fictícios e preserva suas alterações apenas na sessão. No aplicativo Windows, escolha **Base 2.x (somente leitura)** para consultar o Diolino 2.x. A consulta usa SQLite nativo, sem Python no executável, e abre somente a base de esquema 8 em `%LOCALAPPDATA%/ProjetoDiolino/diolino.sqlite3`. O leitor não cria a base ausente nem altera tabelas, registros ou versão do esquema. O arquivo `bridge.py` permanece como referência de desenvolvimento e para os testes existentes.

| Área | Leitura da versão 2.x | Escrita da versão 3.0 |
| --- | --- | --- |
| Agenda | Eventos no período visível e próximos compromissos em Hoje | Eventos e novas releituras em Meus registros são gravados no SQLite da 3.0. |
| Planos | Etapas dos planos ativos | Criação, edição, mudança de coluna e remoção em Meus registros são gravadas no SQLite da 3.0. |
| Estudos | Sessões, vencimentos FSRS e recordação observada de Medicina | Sessões em Meus registros são gravadas no SQLite da 3.0. O algoritmo FSRS e novas avaliações de cartões continuam na 2.x. |
| Hábitos | Histórico de 30 dias | Rotinas e marcações próprias da 3.0 são gravadas no banco 3.0. |
| Saúde | Séries de exercício, sono e peso | Registros e metas próprios são gravados no banco 3.0. |
| Estudo bíblico | Os registros do módulo Bíblia pertencem ao perfil 3.0 | Marcações no banco 3.0. |

O banco independente é `desktop-v3.sqlite3` na pasta de dados do aplicativo Tauri (`%APPDATA%/br.diolino.preview` no Windows). Ele guarda seções JSON e importa os valores existentes do WebView quando a seção ainda não existe. A interface mantém uma cópia local e informa falhas de gravação SQLite. Na prévia web, as seções continuam usando o armazenamento do navegador. Biblioteca, Foco e tema continuam no armazenamento da interface.

**Backup manual:** com o Diolino 3.0 fechado, copie `desktop-v3.sqlite3` para uma pasta de backup (inclua eventuais arquivos auxiliares SQLite do mesmo nome). Para restaurar, preserve uma cópia do banco atual antes de substituir o arquivo com o aplicativo fechado. Para o perfil completo, arquive a pasta inteira `br.diolino.preview`, que inclui as preferências e outros dados do WebView. Os documentos originais da Biblioteca precisam de backup próprio. O banco e as rotinas de backup 2.x continuam separados.

**Distribuição:** o instalador e a assinatura ficam para a etapa de empacotamento Windows. OCR e Ollama ainda precisam de integração própria na 3.0. A atualização automática depende do empacotamento, assinatura e publicação de um manifesto de atualização.

Não use dados reais de pacientes nesta prévia. A versão 3.0 ainda não possui o modelo de segurança, persistência e validação clínica de uma versão de produção.

## Requisitos e compilação Windows

Use Windows com Node.js/npm, Rust stable MSVC, Visual Studio C++ Build Tools, WebView2 e o ambiente `.venv` da raiz preparado com `requirements-runtime.txt`.

A partir da raiz deste repositório, rode os testes e compile a interface:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s desktop-v3\tests -v
Set-Location desktop-v3
npm ci
npm run build
npm run tauri -- build --debug --no-bundle
```

Volte à raiz e abra `desktop-v3\src-tauri\target\debug\diolino-v3.exe`. O script `desktop-v3\validate-windows.ps1`, executado a partir do checkout oficial, repete os testes e builds. Ele não instala a aplicação nem acessa ou altera o banco pessoal.

## Situação de distribuição

`tauri.conf.json` mantém o empacotamento desativado e a versão identificada como alfa. Não há instalador, assinatura de código, atualização automática, bridge Python sidecar para release ou migração de produção. O build local sem bundle confirma compilação, não certifica instalador ou prontidão para usuários finais.

A [auditoria de prontidão do Diolino 3.0](../docs/AUDITORIA-DIOLINO-3.0.md) registra os bloqueadores e os critérios para a versão definitiva. O repositório é público e a raiz ainda não contém um arquivo de licença do projeto.

## Dependências

`package-lock.json` e `src-tauri/Cargo.lock` fixam as dependências usadas nesta prévia. O CI usa `npm ci` para respeitar o lockfile; a compilação Rust usa `--locked` quando validada localmente.


## Aparência e interações

XP, Clássico e Royale compartilham a escala de espaçamento de 4, 8, 12, 16 e 24 px. Cada tema fornece sua paleta, raio e sombra. O Clássico usa cantos retos e relevo. O Royale usa texto escuro sobre as ações claras. A seleção continua no armazenamento local da interface.

A navegação indica a página ativa e os controles têm estados de ponteiro, foco e desabilitação. As transições curtas de cor e borda são desligadas com a preferência de movimento reduzido. Mensagens temporárias confirmam ações e erros ficam visíveis até serem dispensados ou até a mudança de tela.

Na demonstração dos Planos, arraste o cartão para outra coluna. A coluna de destino aparece contornada e o cartão movido fica destacado. Pelo teclado, use Editar e altere o Estado da tarefa. Essas mudanças continuam na sessão da demonstração.

### Ícones

A interface usa `lucide-react` com imports nomeados para tree shaking no Vite. Os ícones de 16, 18 e 20 px herdam a cor do contexto. Ícones decorativos usam `aria-hidden` e ações sem texto mantêm um nome acessível no botão.

## Atividade Física e Bíblia offline

**Atividade Física**, **Estudos** e **Bíblia** têm atalhos próprios no menu. A tela de atividade usa os mesmos registros e metas de exercício de Saúde. Em um registro combinado, remover a atividade preserva os campos de sono e peso. A data desse registro pode ser alterada em Saúde.

A tela **Bíblia** reúne o registro de leitura por data e o texto da tradução BPM (português brasileiro, domínio público, edição em revisão). O leitor carrega uma cópia incluída na aplicação ao abrir o módulo, com navegação por livro e capítulo e busca textual. Consulte [origem, edição e aviso do editor](../data/bibles/README.md).

## Agenda diária, Alimentação e musculação

- A visão **Dia** mostra 24 faixas de horário. Compromissos sem hora aparecem em uma seção própria.
- **Alimentação** usa os 597 itens do [catálogo TACO](../data/taco/README.md). O diário escala a composição por massa comestível em gramas, guarda os valores usados no lançamento e soma apenas medidas numéricas válidas. Metas diárias são informadas pelo usuário. O gráfico mostra o nutriente escolhido nos dias até a data selecionada.
- A calculadora apresenta gasto em repouso pela equação [Mifflin–St Jeor](https://pubmed.ncbi.nlm.nih.gov/2305711/) e gasto diário pelo fator de atividade fornecido. Trata-se de estimativa para adultos.
- **Atividade Física** inclui planejamento de musculação por data, exibido em semana (segunda a domingo) ou mês civil. A tabela guarda exercício, séries, repetições, carga e observações.
- Diário, metas alimentares e planejamento são gravados no SQLite local da 3.0 no aplicativo Windows. Na interface web usam armazenamento do navegador. A TACO é distribuída dentro da aplicação e a consulta ocorre localmente.

## Comentários bíblicos, traduções e gráficos

O leitor inclui BPM, Bíblia Livre (66 livros) e Bíblia Livre Para Todos (Novo Testamento). Selecione um versículo para salvar um comentário ou marcação. A lista de referências abre a passagem na tradução original da anotação. Os textos acompanham a compilação e os comentários ficam no SQLite 3.0. Consulte [licenças e créditos](../data/bibles/README.md).

Os gráficos temporais permitem linhas ou barras. Em Alimentação, a composição do dia tem barras em gramas e pizza da contribuição energética estimada de proteínas, carboidratos e gorduras. O gráfico semanal ou mensal compara consumo com a meta diária. Uma meta específica da data tem prioridade sobre o padrão; o padrão atual vale para datas sem ajuste específico.

Em **Meus registros (3.0)**, eventos, tarefas, estudos e novas releituras usam uma gravação transacional. A interface confirma a ação após o SQLite aceitar a edição. Se outra janela gravar primeiro, use **Atualizar** e revise suas alterações antes de tentar novamente. Releituras salvas antes desta mudança continuam visíveis em Meus registros. Na interface web, esses registros usam armazenamento local do navegador.

## Backup e restauração no aplicativo

No menu **Backup**, use **Salvar backup…** para criar um arquivo `.diolino-backup.json` em uma pasta escolhida. O arquivo reúne as seções gravadas no SQLite da 3.0 e as preferências do tema, Foco e atalhos da Biblioteca. Guarde-o em local privado. O formato é versionado e os dados ficam em texto simples. Arquivos originais da Biblioteca são preservados em suas pastas e devem ser copiados à parte.

Em um perfil novo ou existente, feche outras janelas da 3.0, escolha **Selecionar backup…**, confira a data e confirme **Restaurar e reabrir**. A versão e a estrutura do arquivo são verificadas. Antes de substituir os registros, o aplicativo grava uma cópia preventiva na subpasta `backups` da pasta de dados 3.0. A conclusão mostra onde essa cópia ficou. Para desfazer, restaure a cópia anterior pelo mesmo menu.

Esse procedimento usa apenas os dados da 3.0. A consulta opcional à base 2.x permanece em modo somente leitura. A versão web precisa do aplicativo Windows para usar os diálogos de exportação e restauração.
