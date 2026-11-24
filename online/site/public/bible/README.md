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
