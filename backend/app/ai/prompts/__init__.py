"""Todos os prompts do sistema.

Nenhum texto de prompt e montado fora deste pacote. Isso mantem a engenharia de
prompt versionada em um lugar so e evita variacoes acidentais entre endpoints.
"""

from app.ai.prompts.ideation import build_ideation_prompt
from app.ai.prompts.regeneration import build_regeneration_prompt, output_model_for_scope
from app.ai.prompts.system import base_system_prompt
from app.ai.prompts.vision import build_asset_analysis_prompt

__all__ = [
    "base_system_prompt",
    "build_asset_analysis_prompt",
    "build_ideation_prompt",
    "build_regeneration_prompt",
    "output_model_for_scope",
]
