# Fonte nutricional TACO

NEPA/UNICAMP. **Tabela Brasileira de Composição de Alimentos (TACO), 4ª edição revisada e ampliada. Campinas, 2011.**

- Página institucional: https://nepa.unicamp.br/tabela-brasileira-de-composicao-de-alimentos-4a-edicao/
- Planilha oficial: https://nepa.unicamp.br/wp-content/uploads/sites/27/2023/10/Taco-4a-Edicao.xlsx
- Livro: https://nepa.unicamp.br/wp-content/uploads/sites/27/2023/10/taco_4_edicao_ampliada_e_revisada.pdf
- Edição mais recente localizada no site do NEPA em **16/10/2026**. A notícia de 2023 disponibiliza a edição de 2011.
- Permissão no livro: reprodução parcial ou total permitida, desde que citada a fonte.

`taco-oficial.xlsx` é o arquivo original, preservado. `catalogue.json` é uma derivação local para uso offline. O JSON registra o hash SHA-256 do original, a edição e a data da conferência. Não são enviados dados pessoais ao NEPA.

Foram importados os 597 alimentos da primeira aba (26 nutrientes/medidas), 423 perfis da aba de ácidos graxos (22 medidas) e 26 perfis de aminoácidos (18 medidas). A junção usa o código TACO; nomes/preparações e as 15 categorias vêm da primeira aba. Os nomes internos das abas contêm “taco3”, mas pertencem ao arquivo de 4ª edição distribuído oficialmente. As colunas repetidas de códigos são verificadas durante a importação.

Todos os valores são por 100 g de parte comestível. O aplicativo multiplica apenas valores numéricos válidos pela massa consumida/100 e salva seis casas decimais. Não converte mL, colher ou unidade em gramas e não calcula energia a partir de macronutrientes, pois a fonte já informa a energia. As casas adicionais presentes na planilha são preservadas, por isso pode haver pequenas diferenças em relação ao livro impresso arredondado.

Valores `Tr`, `NA`, `*` e vazios permanecem distintos: traço, não aplicável, análise em reavaliação e não informado (conforme notas da publicação). Eles não são convertidos em zero. Os campos numéricos do registro ficam vazios nesses casos, e o snapshot guarda o marcador original. Não se aplica correção silenciosa a inconsistências do arquivo:

| Código | Campo | Célula oficial | Valor original |
| --- | --- | --- | --- |
| 288 | Carboidratos | CMVCol taco3!I328 | -0,026666666666666172 |
| 322 | Carboidratos | CMVCol taco3!I365 | -0,04500000000000792 |
| 337 | Carboidratos | CMVCol taco3!I382 | -0,006666666666674814 |
| 373 | Piridoxina | CMVCol taco3!AA424 | `,0,02` |
| 400 | Carboidratos | CMVCol taco3!I451 | -0,02333333333333809 |

Esses valores são mostrados como “Inconsistência na fonte” e ficam indisponíveis para o cálculo; o original permanece no catálogo e no snapshot.

Para reconstruir: execute `scripts/import_taco.py` com o Python empacotado do Codex e a biblioteca openpyxl. `--download` baixa novamente a planilha oficial. Depois revise diferenças, integridade e edição antes de empacotar com `build.ps1`. O aplicativo não substitui seus registros antigos ao atualizar o catálogo: cada lançamento TACO guarda uma cópia da composição, dos metadados e da massa utilizada.
