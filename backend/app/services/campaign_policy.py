"""Politica de destinos e saidas da campanha.

Centraliza combinacoes padrao, formato editorial interno e rotulos usados
pela API e pelos prompts. A UI nao precisa conhecer ContentFormat.
"""

from __future__ import annotations

from app.models.enums import CampaignDestination, CampaignOutput, ContentFormat

DEFAULT_OUTPUTS: dict[CampaignDestination, tuple[CampaignOutput, ...]] = {
    CampaignDestination.INSTAGRAM: (CampaignOutput.IMAGE, CampaignOutput.COPY),
    CampaignDestination.TIKTOK: (CampaignOutput.VIDEO, CampaignOutput.COPY),
    CampaignDestination.TIKTOK_SHOP: (CampaignOutput.VIDEO, CampaignOutput.COPY),
}

DESTINATION_LABELS: dict[CampaignDestination, str] = {
    CampaignDestination.INSTAGRAM: "Instagram",
    CampaignDestination.TIKTOK: "TikTok",
    CampaignDestination.TIKTOK_SHOP: "TikTok Shop",
}


def normalize_outputs(
    destination: CampaignDestination,
    requested: list[CampaignOutput] | None,
) -> list[CampaignOutput]:
    if requested:
        unique: list[CampaignOutput] = []
        for item in requested:
            if item not in unique:
                unique.append(item)
        if CampaignOutput.COPY not in unique:
            unique.append(CampaignOutput.COPY)
        return unique
    return list(DEFAULT_OUTPUTS[destination])


def content_format_for(
    destination: CampaignDestination, outputs: list[CampaignOutput]
) -> ContentFormat:
    if CampaignOutput.VIDEO in outputs:
        return ContentFormat.REEL
    if destination is CampaignDestination.INSTAGRAM:
        return ContentFormat.IMAGE_POST
    return ContentFormat.REEL


def wants(outputs: list[CampaignOutput] | list[str], output: CampaignOutput) -> bool:
    values = {item.value if isinstance(item, CampaignOutput) else str(item) for item in outputs}
    return output.value in values
