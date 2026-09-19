# Arquitetura do POSTEX

## Por que a ideacao virou etapa interna

O produto antigo pedia dois jobs visiveis: gerar ideias em `/ideas`, escolher um
card e so depois produzir o post. Isso vazava taxonomia (pilares editoriais) e
obrigava o usuario a entender um pipeline de redacao.

O fluxo diario agora e um unico pedido em `/criar`:

1. item (opcional, obrigatorio so para vender) + objetivo (`SELL` / `ATTRACT` / `BRAND`)
2. ate tres perguntas determinísticas
3. um job `CONTENT_CREATION` com stages `ideia` → `roteiro` → `imagem` → `finalizando`
4. preview para Aprovar, Refazer ou Agendar

A geracao de ideias **nao foi apagada**. O worker ainda chama o motor de ideias
por baixo, persiste uma ideia, produz o conteudo, gera um **still de capa**
(apresentadora automatica + produto) e marca a ideia como usada.
Quem quiser controle fino continua em **Configuracoes → Ideias**, sem polimento
e fora do menu principal.

O job `CONTENT_CREATION` expoe os stages `ideia` → `roteiro` → `imagem` →
`finalizando`. A imagem passa por `ImageProvider` (`mock` ou `openai`),
separado do provedor de texto. Personagens (Lara, Camila, Bianca) vivem em
`app/ai/config/presenters.yaml` e sao escolhidas automaticamente — nao ha
seletor no menu.

## Mapa de telas

| Rota | Papel |
| --- | --- |
| `/inicio` | Atalho. Monta `/criar?product=&objective=`. Nao e wizard. |
| `/criar` | Unica maquina de estados do pedido. |
| `/contents` | Biblioteca em abas (em criacao, para aprovar, agendados, publicados). |
| `/contents/[id]` | Preview, Aprovar/Refazer/Agendar; editor em Ajustar; resto no menu `...`. |
| `/calendar` | Semana por padrao, mes opcional. |
| `/settings/*` | Negocio, imagens, ideias, conta. Instagram e plano ainda sao placeholder. |

Rotas antigas (`/dashboard`, `/business`, `/products`, `/services`, `/assets`,
`/ideas`) redirecionam para o lugar novo para nao quebrar bookmarks e o login.
