"""Diretrizes de copy e criativo por destino de publicacao."""

from __future__ import annotations

from app.models.enums import CampaignDestination, CampaignOutput, ContentFormat

PLATFORM_PERSONA = """\
Voce transforma produtos reais em conteudo que vende. Trabalha para UM negocio \
especifico, cujo contexto e fornecido em cada solicitacao. O usuario entrega o \
produto; voce decide o angulo, o gancho e a chamada para acao mais eficazes \
para o destino escolhido.

Voce nao gera posts genericos. Cada peca precisa parecer que so aquele produto, \
naquela marca, para aquele publico, poderia existir."""


def production_extra(destination: CampaignDestination) -> str:
    common = """\
NESTA ETAPA voce escreve o conteudo final, pronto para publicar ou exportar. \
Nao devolva sugestoes nem alternativas: devolva a versao definitiva.
A primeira linha da legenda precisa interromper a rolagem. Hashtags devem ser \
especificas do nicho e da regiao - nunca uma lista generica."""
    extras = {
        CampaignDestination.INSTAGRAM: (
            "Destino Instagram: tom de feed comercial brasileiro. Legenda com "
            "quebra de linha real, CTA unico, 8 a 12 hashtags misturando nicho e local."
        ),
        CampaignDestination.TIKTOK: (
            "Destino TikTok: escrita falada, gancho nos 3 primeiros segundos, "
            "legendas curtas na tela, hashtags de busca (3 a 6). Sem jargao de "
            "Instagram (direct, carrossel, story)."
        ),
        CampaignDestination.TIKTOK_SHOP: (
            "Destino TikTok Shop: peca comercial. Mostre o produto, um beneficio "
            "concreto, prova rapida e CTA de compra ('Comprar agora'). Se houver "
            "preco, cite-o. Nao invente desconto, estoque ou selo oficial da loja."
        ),
    }
    return f"{common}\n\n{extras[destination]}"


def still_aspect(destination: CampaignDestination, content_format: ContentFormat) -> str:
    if destination in {CampaignDestination.TIKTOK, CampaignDestination.TIKTOK_SHOP}:
        return "1024x1792"
    if content_format in {ContentFormat.REEL, ContentFormat.STORY}:
        return "1024x1792"
    return "1024x1024"


def video_duration(destination: CampaignDestination) -> int:
    if destination is CampaignDestination.TIKTOK_SHOP:
        return 5
    if destination is CampaignDestination.TIKTOK:
        return 5
    return 4


def output_labels(outputs: list[CampaignOutput]) -> str:
    labels = {
        CampaignOutput.COPY: "copy (legenda, roteiro e CTA)",
        CampaignOutput.IMAGE: "imagem comercial",
        CampaignOutput.VIDEO: "video vertical",
    }
    return ", ".join(labels[item] for item in outputs)
