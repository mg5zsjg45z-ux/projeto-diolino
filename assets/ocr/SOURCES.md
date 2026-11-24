# OCR offline

Mecanismo: Tesseract v5.5.3.20260724, build Windows da Universidade de Mannheim,
referenciado pela documentação do projeto Tesseract. O instalador foi extraído
sem executar seu instalador nem alterar o PATH ou instalar serviços.

Origem: https://github.com/tesseract-ocr/tesseract/releases/tag/5.5.3
Arquivo: tesseract-ocr-w64-setup-5.5.3.20260724.exe
SHA256: bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4
Foram preservados tesseract.exe, DLLs e os avisos originais de doc/.
Código-fonte e instruções de compilação do mecanismo e dependências:
https://github.com/tesseract-ocr/tesseract/tree/5.5.3
https://github.com/msys2/MINGW-packages/tree/master/mingw-w64-tesseract-ocr

Idiomas português e inglês: tesseract-ocr/tessdata_fast, commit
87416418657359cb625c412a48b6e1d6d41c29bd, com licença original em tessdata/LICENSE.
https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd

Para preparar novamente, obtenha o instalador dessa release, confira o SHA256,
extraia seu conteúdo com 7-Zip em uma pasta vazia de teste e copie apenas
tesseract.exe, *.dll e doc/ para esta pasta. Baixe os dois .traineddata e a
licença do commit acima para tessdata/. O empacotador inclui esta pasta no
aplicativo; o uso normal do OCR não baixa arquivos nem envia imagens.
