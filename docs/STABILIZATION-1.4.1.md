# Estabilização 1.4.1

Sem alteração de esquema, interface ou funcionalidades. A versão 1.4.0 já contém o cliente de sincronização com o site; a documentação histórica 1.3.0 permanece como histórico.

## Qualidade
O workflow Diolino quality executa unittest no Windows com cobertura de linhas e ramos, verifica os recursos OCR, audita dependências de execução e build com pip-audit, gera SBOM CycloneDX JSON e executa Bandit. Achados Bandit de severidade alta bloqueiam o job; severidades inferiores devem ser examinadas separadamente. Não há limiar de cobertura até estabelecer uma linha de base. O SBOM Python não inclui DLLs ou Tesseract; consulte assets/ocr/SOURCES.md.

Não usar dados reais ou credenciais nos testes. Não fazer merge antes de todos os jobs concluírem com sucesso e revisão dos relatórios. A proteção obrigatória da branch depende da configuração administrativa do GitHub. Nenhuma release é criada automaticamente.

A auditoria não comprova segurança do servidor remoto nem assinatura digital do instalador.
