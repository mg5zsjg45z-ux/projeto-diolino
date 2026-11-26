# Diolino 3.0 — prévia alfa

Esta pasta contém uma prévia alfa da interface desktop React + Tauri, desenvolvida ao lado do aplicativo Windows 2.x. Ela ainda não substitui a versão de uso diário nem é uma versão de produção pronta para distribuição.

## O que está incluído

- **Hoje**: indicadores demonstrativos e consulta ao painel local em modo somente leitura durante o desenvolvimento.
- **Agenda**: visualizações mensal, semanal, diária e anual. Alterações da prévia ficam na demonstração.
- **Planos**: quadro Kanban demonstrativo; alterações não são gravadas no banco pessoal.
- **Estudos**: sessões de estudo e agendamento de revisões na demonstração.
- **Biblioteca**: atalhos locais a documentos e planilhas, abertura do arquivo original no aplicativo padrão do sistema e execução dos CLIs WordCraft, PdfCraft e GridCraft instalados separadamente.
- **Saúde**: registros e metas de exercício, sono e peso, com histórico, gráficos e edição. Esses dados ficam no armazenamento local da prévia, separados do banco SQLite pessoal.
- **Foco e Hábitos**: visualizações demonstrativas.

Os arquivos adicionados à Biblioteca não são copiados para dentro do projeto; a prévia salva o caminho local do arquivo. Os executáveis ArtCraft não são incluídos no repositório nem no aplicativo.

## Dados e privacidade

A demonstração começa ativa e usa dados fictícios. O modo Banco local consulta o banco 2.x existente com SQLite em modo somente leitura; o bridge não cria bancos ausentes nem executa migrações ou gravações. No modo release, o bridge Python ainda está desabilitado. Biblioteca, metas e registros de Saúde usam armazenamento local do WebView e não sincronizam com o banco SQLite, nuvem ou outros dispositivos.

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

Antes de distribuir uma versão de produção, ainda será necessário decidir e concluir: integração de release para o bridge, armazenamento durável e backup dos registros da prévia, validação visual e de acessibilidade em tamanhos e temas suportados, política de dados, empacotamento/assinatura, instalação/atualização/rollback e revisão de licenças e dependências. O banco 2.x deve continuar preservado durante essas etapas. O repositório está privado e não há uma licença de projeto na raiz; escolha a licença e revise o histórico completo de segredos antes de torná-lo público.

## Dependências

`package-lock.json` e `src-tauri/Cargo.lock` fixam as dependências usadas nesta prévia. O CI usa `npm ci` para respeitar o lockfile; a compilação Rust usa `--locked` quando validada localmente.
