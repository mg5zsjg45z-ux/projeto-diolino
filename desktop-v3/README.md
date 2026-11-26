# Diolino 3.0 — alfa experimental

Nova camada de interface, independente da janela Tkinter existente. Este é um incremento **somente leitura**, não uma substituição pronta do aplicativo. Sem instalação de produção, sem migração e sem alterações nos registros.

## Arquitetura

React 19 + TypeScript + Vite, Apache ECharts, Lucide e CSS responsivo. Tauri 2 oferece a janela desktop e um comando Rust estritamente definido. Durante desenvolvimento, esse comando invoca o Python do .venv do repositório, sem shell, caminhos ou comandos fornecidos pelo frontend. O bridge utiliza consultas existentes de Store, FSRS, hábitos e planejamento; conexão SQLite mode=ro + query_only, sem executar construtor/migrações. O banco deve ter a versão de esquema atual. Não há servidor HTTP Python nem APIs externas. A demonstração é gerada em memória, começa habilitada e não requer acesso a dados pessoais.

## Windows: prévia visual

No checkout deste mesmo repositório, a partir da raiz:

```powershell
cd desktop-v3
npm install
npm run build
npm run dev
```

Abra http://127.0.0.1:1420. No navegador só a demonstração funciona; a consulta real requer Tauri.

## Prévia desktop e dados reais

Instale Rust stable MSVC, Visual Studio Build Tools com Desktop development with C++ e WebView2 conforme https://v2.tauri.app/start/prerequisites/. Prepare o .venv da raiz com requirements-runtime.txt. A partir de desktop-v3:

```powershell
npm run tauri -- dev
```

Selecione Banco local (leitura). O bridge busca o banco no diretório padrão da versão 2.x; se não existir, retorna erro sem criá-lo. O modo release deliberadamente não habilita a ponte até ser empacotado e validado o sidecar. A prévia não deve substituir o instalador atual.

## Verificação

Na raiz, com .venv preparado:
```powershell
.venv/Scripts/python.exe -m unittest discover -s desktop-v3/tests -v
```

No diretório desktop-v3, npm run build; npm run tauri -- dev. Capturar telas em 1366x768 e 1920x1080, tema claro/escuro, teclado, dados vazios, demo, comparação com versão 2.x em perfil isolado. Gerar e versionar lockfiles de npm e Cargo após compilação verificada. Não considerar os testes adicionados como executados.

## Limites e próximas etapas

- Dashboard, estudo/FSRS, saúde, foco, hábitos, planejamento e agenda em visualização.
- Kanban e agenda ainda são somente leitura (sem arraste, edição ou timeboxing).
- Portar ações de escrita validadas, auditoria, notas, Bíblia, OCR/PDF, backups, integração Ollama, lembretes e sincronização progressivamente. Manter as funções originais até paridade demonstrada.
- CSS próprio nesta primeira etapa; Tailwind/shadcn e componentes especializados poderão ser adotados após validar a base. Não há biblioteca de animação nem calendário externo ainda.
- Empacotar Python sidecar, ícone e instalador, testar integridade e atualização/rollback; limitar privilégios Tauri, fixar dependências, auditar licenças e vulnerabilidades.
- Não há confirmação de compilação/execução Windows ou validação visual nesta entrega.

Referências: https://v2.tauri.app/develop/calling-rust/ e https://v2.tauri.app/develop/sidecar/.

## Temas Diolino XP

XP Luna azul (padrão), Clássico 95/98 e Royale escuro são temas originais inspirados no Windows. Selecione no cabeçalho; a preferência visual fica em localStorage, não no SQLite. Os gráficos e estados de hábitos acompanham o tema. Nenhum ativo gráfico proprietário foi incorporado. Homologar os três temas, contraste, zoom, foco de teclado e persistência após recarregar. Compilação e screenshots ainda pendentes.

## Validação automatizada

Workflow .github/workflows/desktop-v3.yml: primeira execução (45732718964) terminou com falha nos dois jobs, sem passos e sem logs disponíveis (HTTP 404 BlobNotFound). A causa não foi confirmada; não equivale a um erro de compilação demonstrado. 18 combinações de cor de texto/superfície, texto/fundo, destaque/superfície e seleção (6 por tema) foram calculadas a partir dos tokens publicados e passaram no limiar 4,5:1. Isso não certifica toda a interface. Para repetir a compilação no Windows, execute desktop-v3/validate-windows.ps1 a partir do checkout oficial, após instalar os pré-requisitos e preparar .venv. O script não instala o aplicativo nem usa o banco pessoal. A homologação visual continua necessária.
