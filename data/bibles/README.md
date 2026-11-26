# Bíblia offline — BPM

Fonte oficial: https://ebible.org/details.php?id=porbrbsl
Arquivo: https://ebible.org/Scriptures/porbrbsl_usfx.zip
Consulta e obtenção: 26/10/2026. Fonte indica revisão de 08/10/2026.
Idioma: português brasileiro. Licença declarada pelo editor: Public Domain.
Armazenamento e redistribuição permitidos por essa dedicação ao domínio público.
Aviso do editor: tradução em revisão. Esse aviso permanece visível no leitor.

Conversão reproduzível: scripts/prepare_bible.py. Inclui os 81 livros/seções
presentes no arquivo-fonte (também deuterocanônicos e variantes textuais),
38.029 entradas de versículos com texto. Foram omitidos 29 marcadores vazios
presentes no USFX; nenhuma lacuna foi preenchida artificialmente. Notas de
rodapé, remissões e títulos editoriais não integram o texto convertido.
Identificadores originais de livros/capítulos/versículos preservados.
SHA-256 do ZIP original consta em BPM.json. O aviso original está em
BPM-copyright.html. Importações do usuário não são adicionadas à distribuição.

Formato de importação: JSON UTF-8 com id (letras, números, _ ou -), name,
language, license, source e books. books é um objeto de códigos de livro;
cada livro contém name e chapters, cujas chaves são números positivos em texto.
Cada capítulo contém pares número de versículo/texto. Veja BPM.json como exemplo.
Limite: 20 MB, 100 livros, 50.000 versículos. Importação não concede licença:
o usuário precisa possuir autorização para armazenar o arquivo escolhido.

NAA, ARA, ARC, NVI, NVT, NTLH e ACF permanecem como links opcionais aos
leitores existentes. Não foi verificada autorização para redistribuir essas
edições; por isso seus textos não acompanham o executável.

## Edições adicionais da prévia 3.0

- **Bíblia Livre (BLIVRE)**, edição de fevereiro de 2018, 66 livros e 31.102 versículos. © 2018 Diego Santos, Mario Sérgio e Marco Teles. [Fonte](https://ebible.org/details.php?id=porbr2018) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Bíblia Livre Para Todos (BLT)**, edição de março de 2022, Novo Testamento, 27 livros e 7.942 versículos. © 2022 Free Bible Ministry, Inc. [Fonte](https://ebible.org/details.php?id=porblt) · [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

As duas edições foram convertidas das distribuições USFX do eBible.org pelo mesmo conversor usado para a BPM, com formato JSON, seleção do texto de versículos e normalização de whitespace. Os avisos originais do editor acompanham os catálogos em `desktop-v3/`. O JSON da BLT é redistribuído sob CC BY-SA 4.0.
