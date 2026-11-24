# OneDrive — integração retirada

A integração opcional com OneDrive foi retirada a pedido do usuário em 04/11/2026. Foram removidos os componentes de autorização Microsoft, o leitor de pasta, o envio e o callback OAuth. Nenhuma configuração de segredo ou token era mantida no servidor; os tokens existiam somente na memória da aba. O identificador público salvo no navegador é removido ao carregar a nova versão. Arquivos da Biblioteca própria e dados pessoais não são excluídos. A remoção do site não revoga eventual consentimento concedido diretamente à Microsoft.
