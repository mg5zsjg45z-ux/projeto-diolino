# Licenciamento e compatibilidade
Inventário preliminar da pesquisa anterior; não é parecer jurídico nem verificação de todos os arquivos. O mantenedor escolheu MIT para o código original do Diolino em 26/11/2026 (ver `LICENSE`). Essa licença não relicencia dados, traduções, assets ou dependências de terceiros; preservar os avisos e condições próprios. Antes de distribuir, confirmar a titularidade/direito de licenciar todas as contribuições e completar o inventário de arquivos.
| Componente | Licença identificada | Decisão |
|---|---|---|
| Super Productivity | MIT | adaptação seletiva com avisos |
| Py-FSRS | MIT | manter integração |
| FSRS-RS | BSD-3-Clause | avaliar |
| FSRS-RS-Python | não confirmada | bloquear incorporação até verificar |
| ActivityWatch | MPL-2.0 | integração modular opcional |
| aw-client | MPL-2.0 | avaliar dependência opcional |
| Anki | AGPL-3.0-or-later | interoperabilidade, sem copiar núcleo |
| Loop | GPL-3.0-or-later | referência funcional |
| OpenHabitTracker | GPL-3.0 | referência arquitetural |

MIT/BSD exigem preservação dos avisos e condições aplicáveis. MPL tem copyleft predominantemente por arquivo coberto; GPL/AGPL podem exigir disponibilização de código correspondente na distribuição de obras derivadas; AGPL possui obrigação adicional em condições de interação pela rede com versão modificada. Uso privado não implica automaticamente publicação. Código público sem licença não autoriza reutilização geral.
Antes de incorporar: fixar commit/tag; conferir LICENSE, cabeçalhos, exceções, assets e dependências transitivas; identificar origem e alterações; avaliar compatibilidade com licença e forma de distribuição do Diolino; preservar avisos; atualizar SBOM e inventário de terceiros; revisar obrigações antes de release. Preferir implementação independente de conceitos e interfaces documentadas quando licença incompatível ou incerta. Nenhum código externo copiado nesta etapa.
