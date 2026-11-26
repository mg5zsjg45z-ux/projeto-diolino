# Diolino online e código aberto: preparação

Estado em 26/11/2026. O repositório GitHub está público e a licença MIT foi
integrada à branch padrão no PR #13 (commit `b83e4a96`). O site não está
implantado como serviço independente.

## Estado confirmado no checkout

- O site em `online/site` é uma aplicação separada, com Cloudflare Workers,
  D1 e R2. A autenticação atual depende dos cabeçalhos de identidade injetados
  pelo ambiente de hospedagem ChatGPT; não é uma autenticação genérica para
  uma implantação pública independente.
- A raiz agora contém `LICENSE` com MIT, escolhida pelo mantenedor em
  26/11/2026. Ela se destina ao código original do Diolino. Conteúdos,
  dependências e componentes de terceiros mantêm os respectivos avisos e
  licenças; a presença da licença raiz não os relicencia.
- O site declara armazenar registros de conta no D1 e anexos privados no R2.
  O ambiente local e as suítes HTTP usam estado sintético/local; nenhuma
  migração ou publicação remota deve ser usada como etapa de teste.
- `hosting.local.json` contém configuração local e fica fora do controle de
  versão. `hosting.local.example.json` é o modelo sem credenciais.

## Separação de licenças

Uma licença do código do Diolino não licencia automaticamente bases de dados,
traduções bíblicas, documentação, ícones, fontes, imagens ou dependências. A
revisão inicial encontrou, entre outros:

- `data/bibles`: BPM está identificada como domínio público no material do
  projeto; BLIVRE informa CC BY 4.0 e BLT informa CC BY-SA 4.0. Preservar os
  créditos e as condições de cada tradução.
- `data/taco`: a cópia informa a TACO/NEPA/UNICAMP, 4ª edição (2011), e pede
  citação da fonte. Manter essa atribuição junto da base.
- O site distribui PDF.js (Apache-2.0), Mammoth, DOMPurify e ícones Lucide,
  com avisos de licença nos respectivos diretórios `public/`.

Este inventário é inicial, não um parecer jurídico nem uma auditoria completa
de proveniência. Antes de anunciar compatibilidade de licenças, revisar todos
os arquivos publicados, créditos, dependências e conteúdo binário. Não juntar
conteúdo de terceiros sob a licença do código do aplicativo.

## Caminho de beta online controlada

1. Criar uma aplicação Cloudflare Workers separada para a beta, com D1 e R2
   próprios. Não reutilizar o banco local, bancos de perfis nem recursos de
   produção de outro serviço.
2. Colocar Cloudflare Access à frente do Worker com política de acesso por
   lista de e-mails/invitados e exigir autenticação. Não habilitar cadastro
   público enquanto não houver política de privacidade, exclusão de conta,
   retenção, limites e resposta a incidentes definidos.
3. Adaptar a aplicação para usar somente uma identidade verificada pelo
   Access no Worker, com identificador estável do provedor. Remover a confiança
   em cabeçalhos `oai-authenticated-user-*` fora do ambiente ChatGPT. Se o
   Worker não receber identidade autenticada, a requisição deve falhar fechada.
4. Manter contas e anexos de beta isolados e rotulados como dados de teste.
   Não importar dados pessoais de desktop. Testar o ciclo de vida, autorização
   por conta, backup/restauração, limites e concorrência apenas com perfis
   sintéticos.
5. Configurar domínio e TLS no provedor, aplicar as migrações D1 na base de
   beta explicitamente, validar R2 privado e só então fazer um deploy de
   candidato. O deploy de produção requer revisão separada.

O código atual ainda não implementa o passo 3. Há também uma limitação concreta:
o build Cloudflare atual gera `assets` na configuração do Worker. A documentação
do Cloudflare informa que o roteador interno de Workers com Static Assets não
encaminha `ctx.access` ao Worker do aplicativo. Portanto, só proteger o Worker
com Access não basta para preencher os cabeçalhos de identidade usados pelo
site. Será necessário validar o `Cf-Access-Jwt-Assertion` no próprio Worker
(issuer, assinatura, audiência e validade) ou mudar o formato de hospedagem;
não confiar em `Cf-Access-Authenticated-User-Email` ou cabeçalhos `oai-*`
recebidos sem validação criptográfica. O modo escolhido precisa de testes
negativos antes de receber dados de conta.

Este documento não ativa Access, não configura domínio, não cria recursos
Cloudflare e não altera dados remotos. O limite do contexto `ctx.access` está
documentado em [Cloudflare Access para Workers](https://developers.cloudflare.com/workers/configuration/cloudflare-access/).

## Conclusão da abertura do código

Antes de anunciar o projeto como open source:

1. A licença escolhida é MIT e o aviso está como `Diolino contributors`.
   O mantenedor autorizou a escolha e a integração. O histórico Git identifica
   os autores dos commits, mas não prova titularidade legal; confirmar que as
   contribuições próprias podem ser licenciadas e preservar as licenças de
   terceiros. MIT permite reutilização inclusive comercial e não exige que
   modificações hospedadas sejam publicadas.
2. Revisar o inventário de conteúdo e avisos acima e o restante dos arquivos
   rastreados. Garantir que nenhum banco pessoal, segredo, token, upload, perfil
   ou arquivo local de configuração esteja incluído.
3. Separar claramente a edição estável desktop da beta online e explicar que
   a beta pode armazenar dados pessoais em serviço hospedado.
4. Revisar `LICENSE` e `THIRD-PARTY-NOTICES.md`, confirmar o titular indicado,
   e preparar política de privacidade e termos compatíveis com a hospedagem.
5. Revisar o diff, executar as verificações pertinentes e publicar primeiro
   uma beta restrita. Tornar o repositório e o serviço públicos são duas ações
   distintas.

## O que falta para avançar

- Auditoria de titularidade/licença de todas as contribuições e de conteúdo
  rastreado antes de uma distribuição mais ampla.
- Domínio, conta Cloudflare e lista de convidados da beta.
- Política de privacidade, retenção e exclusão de contas/anexos para dados
  hospedados.
- Implementação e testes da identidade Access, seguida de revisão de segurança.
- Auditoria completa de licenças e origem dos arquivos rastreados.

