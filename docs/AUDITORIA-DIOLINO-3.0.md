# Auditoria de prontidão do Diolino 3.0

**Data:** 26/11/2026. **Escopo:** aplicativo desktop 3.0 React + Tauri e site online. Esta revisão acompanha o candidato da branch `fix/alpha5-final-review`, em análise pelo PR #15. A 3.0 mantém armazenamento independente; por decisão do mantenedor, não lê nem migra dados da 2.x. Os ensaios usam dados sintéticos.

## Decisão de lançamento

**Aprovar como beta privada; não aprovar como versão definitiva.** O site beta está publicado com acesso apenas do mantenedor. O aplicativo desktop continua Alpha 5 sem instalador assinado. Os critérios restantes incluem ensaio de instalação limpa, verificação do iPhone e revisão de acessibilidade.

## P0 — bloqueadores da versão definitiva

| Área | Evidência atual | Critério de aprovação |
| --- | --- | --- |
| Persistência da 3.0 | Agenda, Planos, Estudos, Hábitos, Saúde e Tarefas usam armazenamento local próprio; concorrência entre janelas é detectada e os testes verificam recuperação. | Continuar validando em Windows limpo e perfis sintéticos; importação da 2.x não faz parte do escopo aprovado. |
| Migração e mudança de perfil | A 3.0 não abre, lê ou migra a base 2.x. Chaves de demonstração da 3.0 são removidas sem tocar no banco antigo. | Manter explícita a separação entre as versões e garantir que backups 3.0 não tragam dados de demonstração antigos. |
| Backup, restauração e falhas de gravação | Backup JSON versionado, validação por seção e cópia preventiva antes da restauração foram implementados; os testes cobrem perfil vazio, marcações WebView de versões alfa anteriores e corrupção. Anexos originais não são copiados. | Fazer ensaio adicional de recuperação em Windows limpo e documentar a limitação de que arquivos originais da Biblioteca exigem backup separado. |
| Distribuição Windows | O CI compila o executável sem bundle. Nesta continuação, o Tauri também gerou localmente o instalador NSIS da Alpha 5 (5,95 MiB); `Get-AuthenticodeSignature` confirmou `NotSigned`, SHA-256 `472809770B4B4522B4040311333012641325C4626EB02DBC76A715BAFB1AEBDF`. O instalador não foi executado. | Assinar o instalador e ensaiar instalação limpa com WebView2, atualização preservando dados, desinstalação e retorno à versão anterior. Só distribuir um pacote depois desses ensaios. |
| Qualidade e cadeia de entrega | No PR #15, a revisão Windows, Node, Rust, auditorias do site e build Tauri passaram para o candidato de integração `4e936b2a94ed33cecc113fee7be3517d3a2cad95`, gerado a partir do head `7c240fc0a4ccde476b76809e48d9506b99ec1bea`. O executável desse mesmo candidato foi identificado com SHA-256 `3e64693cda24cdbae52414df3919cad4e08dbfcec93dcc839cb91d04fc40274c`. O repositório usa MIT com avisos de terceiros. | Repetir a validação caso o código mude antes da integração; não publicar release estável sem assinatura e instalação limpa. |

## P1 — decisões de paridade com a versão 2.x

| Área | O que falta decidir ou concluir |
| --- | --- |
| Revisão de estudos | A 3.0 lê vencimentos e recordação e agenda releituras próprias. Para substituir o fluxo de revisão da 2.x, falta cadastrar, estudar e avaliar cartões, persistir a atualização FSRS e verificar importação e exportação de cartões, incluindo Anki se mantido no escopo. |
| Saúde e alimentação | A 3.0 tem exercício, sono, peso, diário TACO, metas e planejamento de musculação. Avaliar outros nutrientes, hidratação e cafeína, antropometria, sintomas, medicamentos, consultas e exames, sem migrar registros da 2.x. |
| Biblioteca | Confirmar comportamento de arquivos movidos, caminhos quebrados e ausência das CLIs ArtCraft. Decidir se atalhos, anexos e preferências entram no backup e como recuperar os documentos originais. |
| Integrações pessoais | O companion mantém pareamento e pode ficar em loopback atrás do Tailscale Serve/HTTPS documentado. A conexão real e a validação do certificado no iPhone não foram feitas; notificações/iCloud e paridade com 2.x continuam decisões do produto. OCR, Ollama e atualização automática podem ficar fora da primeira versão. |
| Acessibilidade | A homologação atual cobre os três temas, mas ainda falta uma matriz de teclado, leitor de tela, contraste e DPI em 100%, 110% e 125%, com foco nos formulários, modais e gráficos. |

## Ordem proposta de fechamento

1. Concluir a revisão do PR #15 e repetir a validação no SHA resultante.
2. Assinar o instalador e ensaiar instalação, atualização e retorno em Windows limpo com perfil sintético.
3. Validar Tailscale Serve, certificado HTTPS e pareamento no iPhone real.
4. Concluir a matriz de acessibilidade e registrar a decisão de escopo para FSRS antes da versão estável.

## Evidências históricas da Alpha 4

As notas abaixo registram o estado de uma revisão anterior e não descrevem o candidato atual. Consulte as seções “Itens revisados” e “Validação desta revisão” acima para o estado vigente.

- Windows local, compilação otimizada com identificador Tauri de teste e base 2.x sintética. Mantive a instância de uso aberta. Usei um perfil separado para o ensaio.
- Registros verificados no aplicativo: sintéticos. As três paletas foram selecionadas e a preferência foi recuperada após reiniciar. O teste de leitura do Estudo na base 2.x confirmou que o SHA-256 do banco de teste permaneceu igual.
- Agenda diária, Bíblia nas três edições, TACO e pizza de macronutrientes foram exercitadas na janela do aplicativo com acesso externo bloqueado. Treino, entrada alimentar, meta específica e comentário bíblico foram recuperados do SQLite após remover as cópias do WebView do perfil de teste.
- **Bloqueador reproduzido:** um evento avulso criado na demonstração aparece na Agenda e desaparece ao reiniciar.
- Três testes da ponte Python e um teste do leitor Rust passaram. `cargo fmt --check` e `cargo check --locked` passaram. A compilação manteve o aviso do Vite sobre tamanho de arquivos.
- `npm audit` retornou zero avisos no momento da consulta. A auditoria RustSec ficou pendente porque o comando `cargo audit` não está instalado. Esta foi uma revisão de prontidão, com checagem de dependências npm.
- O [GitHub Actions da Alpha 4 publicada](https://github.com/mg5zsjg45z-ux/projeto-diolino/actions/runs/45770252742) concluiu com sucesso. A homologação das alterações posteriores foi local.
- A primeira execução dos testes da 2.x detectou que as novas traduções mudavam a edição padrão do leitor legado. Os catálogos adicionais foram isolados em `data/bibles/desktop-v3/`. Na repetição, os **165 testes da 2.x passaram**. O Tkinter emitiu um aviso de callback de autosave após encerramento de uma janela de teste, sem reprovar a suíte.

## Atualização após a primeira entrega

O bloqueador de persistência de Agenda, Planos e Estudos foi implementado e homologado na compilação local. **Meus registros (3.0)** abre por padrão e grava eventos, tarefas, sessões e novas releituras no SQLite. **Demonstração** é uma sessão separada; **Base 2.x** é apenas leitura.

No Windows, foram verificados criação, edição, remoção após recarregar e persistência em duas reinicializações. O teste também confirmou isolamento das fontes, recuperação das releituras, rejeição de uma edição desatualizada após outra gravação e preservação do hash da base sintética 2.x. A migração integrada e o backup/restauração continuam como próximos bloqueadores.

## Atualização após a entrega de backup

A migração da 2.x é opcional para o caso de uso iniciado sem registros antigos. O menu **Backup** exporta os registros SQLite e as preferências do perfil 3.0 em JSON versionado. A restauração valida o arquivo, salva uma cópia preventiva e substitui as seções em uma transação. Na validação com dados fictícios, os comandos nativos restauraram um compromisso e conservaram sua edição anterior na cópia preventiva. Os testes Rust também verificaram a restauração em uma base vazia, a rejeição de backup inválido e a preservação dos dados se a cópia preventiva não puder ser criada.

Os anexos originais permanecem fora do arquivo de backup. O backup desta compilação é sem criptografia. A instalação assinada, a definição da paridade funcional e os testes em Windows limpo continuam na lista da versão definitiva.

O ensaio adicional na janela nativa do Windows também passou pelos diálogos de salvar e selecionar arquivo, rejeição de JSON danificado, confirmação explícita e reabertura. O compromisso e o tema originais voltaram, e a cópia preventiva preservou o compromisso editado e o tema anterior à restauração.

## Homologação Alpha 5 — 26/11/2026

A candidata Alpha 5 reúne persistência nativa, backup, Tarefas, Bíblia offline, alimentação, treino e o visual minimalista. Nesta rodada passaram os 3 testes da ponte, os 165 testes de regressão Python, os 2 testes Rust (backup e leitura legada), TypeScript, Vite, formatação Rust, cargo check e compilação Windows de depuração. Os testes nativos passam a integrar também o CI. O aviso de tamanho dos bundles permanece. A suíte legada emitiu aviso de callback de autosave após encerramento, sem falha nos testes. A homologação é de prévia portátil; instalador assinado e ensaio em Windows limpo seguem pendentes.

O teste adicional do frontend de produção no Edge passou por 13 módulos, criação e recuperação de tarefa após recarga, micro-passos, abertura do Foco, seleção dos três temas e 24 faixas horárias na Agenda. Não houve erro JavaScript nesse percurso. Esse ensaio usa armazenamento isolado do navegador; não substitui a matriz nativa descrita acima.

## Ajustes incluídos no candidato do PR #15 — 26/11/2026

O aplicativo deixou de oferecer dados demonstrativos e leitura da base antiga. A inicialização remove apenas as chaves de demonstração identificadas dentro do armazenamento da 3.0 e os registros de saúde marcados como demonstração. A base pessoal das versões anteriores não é aberta, migrada ou apagada. Backups antigos são limpos desses mesmos dados durante a leitura. O teste Rust usa um banco sintético.

Em **Tarefas**, foram adicionadas ações para editar e apagar tarefa e apagar micro-passo, além de reorganizar os controles em telas estreitas. O fluxo foi conferido visualmente no navegador local com texto sintético; a tarefa de teste foi apagada ao concluir. `npm test` (5 testes), build Vite/TypeScript, `cargo test --locked` (8 testes) e `cargo fmt -- --check` passaram. O Vite ainda avisa sobre chunks grandes. A base pessoal anterior não foi consultada.
