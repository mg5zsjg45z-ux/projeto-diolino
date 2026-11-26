# Modelo de melhoria do Diolino

Copie este roteiro para cada mudança que afete um fluxo de uso ou prepare uma versão para distribuição.

## Resultado esperado

- **Fluxo e versão:** onde começa, qual versão é afetada e como a pessoa chega ao resultado.
- **Problema observado:** descreva o comportamento atual e indique como reproduzi-lo.
- **Critério de aceite:** escreva o que deve acontecer na interface e o que deve permanecer salvo ao reabrir o aplicativo.

## Implementação

- Reaproveite os componentes, termos e padrões de navegação do Diolino.
- Declare onde cada dado é salvo, como os dados existentes serão lidos e como desfazer uma mudança quando houver edição de registros.
- Use dados fictícios durante a validação. Se a mudança exigir migração, planeje backup e recuperação.

## Evidência de entrega

| Verificação | Resultado e evidência |
| --- | --- |
| Fluxo principal e estados vazio, erro e recuperação | |
| Teclado, foco visível e mensagens de estado | |
| Persistência ao fechar e reabrir | |
| Compilação e execução no Windows | |
| Instalador e validação do commit de distribuição, quando aplicável | |

Identifique o ambiente usado em cada verificação. Marque verificações que não se aplicam e registre as que ficaram pendentes.

## Aplicação ao Diolino 3.0

1. **Agenda, Planos e Estudos.** Validar a gravação e a recuperação dos registros. Em Estudos, confirmar que a revisão aparece na Agenda ao reabrir o aplicativo.
2. **Biblioteca, Saúde, Foco e Hábitos.** Validar os controles na janela nativa e documentar quais dados podem ser recuperados ou exportados. Para Hábitos, o aceite inicial é marcar e desfazer pelo teclado, com atualização do contador e persistência da marcação.
3. **Distribuição Windows.** Definir o escopo da versão, gerar o instalador e verificar instalação, abertura e comportamento dos dados em um perfil isolado. Relacionar esses resultados ao commit candidato.
