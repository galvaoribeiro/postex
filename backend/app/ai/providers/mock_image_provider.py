"""Still deterministico, sem custo e sem rede.

Gera um PNG com o prompt resumido e o negocio. Serve para o fluxo inteiro
funcionar em desenvolvimento e nos testes.
"""

from __future__ import annotations

import asyncio
import io
import time
from typing import ClassVar

from PIL import Image, ImageDraw, ImageFont

from app.ai.image.base import GeneratedImage, ImagePrompt, ImageProvider
from app.ai.image.prompt import parse_size

MOCK_IMAGE_LATENCY_SECONDS = 0.05


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    words = text.split()
    if not words:
        return ""
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines[:8])


class MockImageProvider(ImageProvider):
    name: ClassVar[str] = "mock"

    @property
    def default_model(self) -> str:
        return "mock-still"

    async def generate(self, request: ImagePrompt) -> GeneratedImage:
        started = time.perf_counter()
        await asyncio.sleep(MOCK_IMAGE_LATENCY_SECONDS)
        data, width, height = self._render(request)
        return GeneratedImage(
            data=data,
            mime_type="image/png",
            width=width,
            height=height,
            provider=self.name,
            model=self.default_model,
            prompt=request.prompt,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _render(self, request: ImagePrompt) -> tuple[bytes, int, int]:
        width, height = parse_size(request.size)
        # Dall-e portrait e grande demais para o mock; reduz proporcionalmente.
        scale = 768 / max(width, 1)
        if width > 768:
            width = int(width * scale)
            height = int(height * scale)

        accent = (124, 58, 237)
        image = Image.new("RGB", (width, height), accent)
        draw = ImageDraw.Draw(image)
        # Vinheta simples no terco inferior.
        overlay = Image.new("RGB", (width, height // 2), (15, 15, 23))
        image.paste(overlay, (0, height // 2))

        font = ImageFont.load_default()
        draw.text((36, height // 2 + 28), "Still gerado", fill=(255, 255, 255), font=font)
        draw.text(
            (36, height // 2 + 52),
            "Preview local · adulta ficticia",
            fill=(220, 220, 230),
            font=font,
        )

        body = _wrap(draw, request.prompt[:280], font, width - 72)
        draw.multiline_text(
            (36, height // 2 + 80),
            body,
            fill=(200, 200, 210),
            font=font,
            spacing=4,
        )
        draw.text(
            (36, height - 48),
            "MOCK · still gerado localmente",
            fill=(180, 180, 190),
            font=font,
        )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue(), width, height
