# Diolino 1.7 — Plano de aceitação
32 cenários propostos, nenhum executado. Usar bancos sintéticos, relógios simulados e casos reproduzíveis. Cada cenário deve ter fixture, ação e asserção automatizada; testes de interface Windows complementam testes de motores Windows/Linux.
## FSRS (7)
1. Migração preserva cartões e agendamentos.
2. Cartão pendente recebe agendamento válido.
3. Avaliação antes de revelar resposta bloqueada na interface.
4. Revisão duplicada bloqueada.
5. Edição textual preserva agendamento.
6. Mudança conceitual permite reinício.
7. Otimização inválida preserva parâmetros anteriores.
## Pomodoro (7)
8. Pausa não incrementa estudo.
9. Suspensão Windows não gera tempo fictício.
10. Falha abrupta permite recuperação conservadora.
11. Descarte não cria estudo.
12. Confirmação repetida não duplica.
13. Meia-noite local divide agregação corretamente.
14. Modo livre contabiliza apenas tempo ativo.
## Metas e hábitos (6)
15. Nova meta não altera passado.
16. Dia dispensado não é fracasso.
17. Ausência permanece desconhecida.
18. Alvo quantitativo zero/inválido rejeitado.
19. Plantão respeita configuração.
20. Alterações de hábitos auditáveis.
## Indicadores (5)
21. Denominador zero indefinido.
22. Adesão e completude separadas.
23. Agregação não duplica registros em períodos sobrepostos.
24. Filtros respeitam fuso.
25. Retenção prevista distinta da recordação observada.
## Integração e segurança (7)
26. Backup pré-migração íntegro.
27. Falha preserva banco anterior.
28. Restauração recupera dados e configurações.
29. Recursos anteriores disponíveis.
30. Sincronização não duplica registros.
31. Operação offline.
32. Nenhum envio pessoal sem autorização.

## Gates propostos
100% testes obrigatórios aprovados; cobertura novos motores ≥90% linhas e ≥85% ramificações; zero perda/duplicação nos cenários testados; zero vulnerabilidades bloqueantes conhecidas; Bandit sem alta gravidade não resolvida e revisão dos demais; SBOM gerado/revisado; offline aprovado; nenhuma regressão identificada. Preservar pipeline existente, não enfraquecer verificações. Cobertura não garante ausência de defeitos. Homologação dinâmica e prospectiva pendentes; bloqueio Actions anterior deve ser resolvido antes de consolidar.
