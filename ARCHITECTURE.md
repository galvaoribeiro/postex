# Arquitetura do POSTEX

## Por que campanha no lugar de post

O produto antigo gerava um post de Instagram a partir de um objetivo editorial
(`SELL` / `ATTRACT` / `BRAND`) e formatos (Reel, carrossel, story). O usuario
precisava saber o que postar.

O fluxo diario agora e um pedido de **campanha**:

1. produto (cadastrar ou selecionar, com foto)
2. destino (`INSTAGRAM` / `TIKTOK` / `TIKTOK_SHOP`)
3. saidas (`IMAGE` / `VIDEO` / `COPY`), com recomendacao por destino
4. ate tres perguntas comerciais
5. um job `CAMPAIGN_GENERATION` com stages `analise` → `copy` → `imagem`/`video` → `finalizando`
6. preview para Aprovar, Regenerar uma saida ou Exportar

A geracao de ideias **nao foi apagada**. O worker ainda chama o motor de ideias
por baixo, persiste uma ideia, produz o copy, gera imagem e/ou video e marca a
ideia como usada. A tela de Ideias e o calendario saem do menu principal.
Servicos deixam de aparecer no fluxo diario.

Video real passa por `VideoProvider` (`mock` ou `fal`), separado do provedor de
texto e de imagem. TikTok Shop, neste ciclo, e conteudo comercial exportavel —
sem OAuth, catalogo ou publicacao automatica.

## Mapa de telas

| Rota | Papel |
| --- | --- |
| `/inicio` | Atalho. Monta `/criar?product=&destination=`. |
| `/criar` | Cadastro ou selecao do produto, destino e saidas. Unica maquina do pedido. |
| `/settings/negocio/produtos` | Editar, trocar foto e excluir produtos ja cadastrados. |
| `/contents` | Biblioteca de campanhas (em criacao, para revisar, aprovadas). |
| `/contents/[id]` | Preview da campanha com abas Imagem / Video / Copy. |
| `/calendar` | Preservado, fora do menu. |
| `/settings/*` | Negocio, imagens, conta. Conexoes (IG/TikTok) ainda sao placeholder. |

Rotas antigas (`/dashboard`, `/business`, `/products`, `/services`, `/assets`,
`/ideas`) redirecionam para o lugar novo para nao quebrar bookmarks e o login.
