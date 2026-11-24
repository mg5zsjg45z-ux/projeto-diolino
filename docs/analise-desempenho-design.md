# Diolino: desempenho, fluidez e opções de interface

Análise de 04/11/2026, sobre a versão Windows 1.3.0. As integrações de busca,
FSRS, backup protegido, PDF e OCR foram implementadas nesta versão. As mudanças
de arquitetura e bibliotecas de interface abaixo são propostas, não migrações executadas.

## Evidência local

Medições reproduzíveis com `scripts/benchmark_ui.py`, em uma pasta isolada:
3.650 medições, 730 estudos e 1.000 notas fictícias. Cinco aberturas por tela;
mediana do tempo de navegação mais `update_idletasks`, com janela de código-fonte
oculta. Não mede a inicialização do executável, animação, tempo até o primeiro
quadro visível, uso real nem desempenho de outro computador. A construção de
App, após os imports do processo, levou 416 ms neste cenário.

| Tela | Mediana | Consultas SELECT por navegação |
|---|---:|---:|
| Visão geral | 209 ms | 17 |
| Estudos | 62 ms | 211 |
| Saúde | 184 ms | 222 |
| Gráficos | 80 ms | 2 |
| Planos | 44 ms | 3 |
| Anotações | 43 ms | 2 |
| Dados e backup | 117 ms | 1 |

A primeira busca, incluindo indexação dos dados fictícios, levou 41 ms. A mediana
de dez buscas aproximadas seguintes foi 28 ms. São resultados locais, sem comparação
antes/depois: não demonstram que a versão inteira ficou mais rápida.

O perfil instrumentado de uma abertura de Saúde registrou aproximadamente 207 ms.
Chamadas ao Tk acumularam 163 ms; a aplicação de aparência acumulou 78 ms, incluindo
251 visitas de `apply_tree` e callbacks de mapeamento. Esses tempos se sobrepõem;
não devem ser somados. A medição aponta trabalho de interface e consultas repetidas,
não demonstra que o banco sozinho seja o maior gargalo.

## Mudanças prioritárias na estrutura atual

1. **Atualizar somente a região que mudou.** `App.render` destrói os widgets da área
   de conteúdo e recria a tela. Preservar a estrutura e atualizar textos, linhas e
   pontos dos gráficos pode reduzir criação, destruição e novos eventos de mapeamento.
   Validar foco, rolagem, data selecionada e temas após a mudança.
2. **Aplicar aparência quando necessário.** `appearance.apply_tree` percorre a árvore,
   e `on_map` também aplica aparência. Marcar widgets já estilizados pela geração do
   tema e reaplicar somente quando o tema, fonte ou acessibilidade mudar. Não remover
   a reaplicação indiscriminadamente: ela mantém contraste e preferências atuais.
3. **Consultar um período de uma vez.** `metric_points` calcula resumos diários em um
   laço. Uma consulta agrupada por data pode substituir centenas de SELECTs. Preservar
   a distinção entre ausência de registro, zero e confirmação manual dos pilares.
4. **Limitar tabelas e filtros.** Paginação ou carregamento incremental de registros,
   evitando reconstruir todas as linhas a cada tecla. A busca nova já usa atraso de
   180 ms, índice em memória e invalidação após alterações/restaurações.
5. **Medir tarefas demoradas separadamente.** PDF, OCR e derivação da chave já usam
   workers nesta entrega. Escritas no SQLite e atualizações do Tk continuam na thread
   principal. Futuras tarefas de rede devem retornar resultados por fila, sem tocar
   diretamente nos widgets de outra thread.

## Ferramentas verificadas no GitHub

| Projeto | Aplicação possível | Limite / decisão |
|---|---|---|
| [py-spy](https://github.com/benfred/py-spy) | Amostragem de processos Python no Windows, para investigar travamentos durante uso representativo. | Ferramenta de desenvolvimento; não precisa ir no instalador. Usar em ambiente autorizado e verificar permissões e compatibilidade do processo empacotado. |
| [pyperf](https://github.com/psf/pyperf) | Executar comparações repetidas e guardar resultados de desempenho. | Não substitui medição de resposta visual ou teste de interface. Priorizar operações do banco e busca. |
| [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) | Controles e temas sobre o ttk existente, com uma camada de estilos reutilizável. | Melhor candidato a um protótipo pequeno. Conflita potencialmente com a aparência própria, botões desenhados e temas atuais; não instalar como substituição global sem teste. |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Controles próprios com aparência consistente e suporte a escala/DPI. | Exige substituir controles e retestar teclado, foco, contraste e tabelas. Não é garantia de velocidade e não deve ser misturado indiscriminadamente ao sistema atual. |
| [Windows App SDK / WinUI 3](https://github.com/microsoft/WindowsAppSDK) | Alternativa para uma interface Windows baseada em Fluent Design e APIs nativas. | Migrar a interface Python/Tkinter para WinUI seria um projeto maior. A disponibilidade dessas APIs não torna a interface existente automaticamente compatível ou mais rápida. |
| [Nuitka](https://github.com/Nuitka/Nuitka) | Construir uma distribuição nativa comparável ao pacote PyInstaller. | Não instalado nesta entrega. Só adotar após comparar abertura, memória, navegação, arquivos e recursos em PCs-alvo. A [exceção de runtime](https://github.com/Nuitka/Nuitka/blob/develop/LICENSE-RUNTIME.txt) trata a saída compilada proprietária; a licença do compilador e das dependências continua aplicável. |

Os cinco primeiros projetos estavam sem marcação de arquivamento na consulta atual;
os metadados identificavam MIT como licença. Foram lidos os respectivos READMEs.
Isso não equivale a auditoria de segurança, teste de integração ou validação de
todas as dependências. Fixar versões e preservar os avisos ao incorporar componentes.

## Direção de design proposta

Manter a identidade do Diolino e padronizar os controles existentes antes de trocar
o framework. Organizar as ferramentas numa área própria com três entradas principais:
buscar, estudar e documentos. Nos formulários, deixar uma ação principal por etapa,
usar larguras proporcionais e manter os comandos próximos do conteúdo. A biblioteca
de cartões deve distinguir pendentes, próximos e arquivados, com restauração de
arquivamento acessível. Mensagens de erro devem permanecer junto à operação que falhou.

Validar em 100%, 125%, 150% e 200% de escala, com janela menor, teclado, texto maior,
tema escuro e alto contraste. São critérios de aceitação para o próximo trabalho de
interface, não conformidade já demonstrada. Esta pesquisa não é uma auditoria visual
formal e não comprova acessibilidade por leitor de tela.

Recomendação: primeiro reduzir reconstrução, aparência repetida e consultas por dia;
depois comparar um formulário ttkbootstrap com o formulário atual. Uma migração
completa para outro framework deve depender dessa comparação e de necessidades
funcionais, não apenas da disponibilidade de um projeto no GitHub.
