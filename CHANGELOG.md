# Changelog

## 1.1.9 — 2026-08-20

- Loja/balcao volta a abrir: o jogo usa uma SEGUNDA acao nativa (tecla E,
  `m_actionBKey`) que nao tinha botao nenhum no port. Agora **L2** publica esse
  slot. L1 continua no inventario e o D-pad para baixo continua usando itens
  (pocao).
- L2 tambem responde como eixo de gatilho, entao vale em pad que mapeia L2 como
  botao e em pad que mapeia como eixo.
- Corrigido o fluxo dos menus: **A** confirma (e continua pulando no gameplay)
  e **B** publica `Esc` para voltar/fechar a tela. SELECT permanece como volta
  secundaria e SELECT+START continua fechando o port.

## 1.1.8 — 2026-08-19

- Launcher regenerado com nxbootstrap 0.6.26: validador do resultado do
  NXExtract compativel com engines futuros (classe dos updates hibridos do
  muOS). Sem mudanca de gameplay.
- Quem vem de versao anterior: instalacao LIMPA (apagar a pasta magicrampage
  E o "Magic Rampage.sh" antes de extrair).
