"""Video deterministico, sem custo e sem rede.

Devolve um MP4 placeholder e um thumbnail PNG. Suficiente para o fluxo
completo em desenvolvimento e nos testes.
"""

from __future__ import annotations

import asyncio
import io
import time
from typing import ClassVar

from PIL import Image, ImageDraw, ImageFont

from app.ai.video.base import GeneratedVideo, VideoPrompt, VideoProvider

MOCK_VIDEO_LATENCY_SECONDS = 0.05


def _thumbnail(request: VideoPrompt) -> bytes:
    width, height = 432, 768
    image = Image.new("RGB", (width, height), (15, 15, 23))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, height // 2, width, height), fill=(124, 58, 237))
    font = ImageFont.load_default()
    draw.text((28, 36), "Video gerado", fill=(255, 255, 255), font=font)
    subtitle = "COM REFERENCIA" if request.references else "preview local"
    draw.text((28, 58), subtitle, fill=(220, 220, 230), font=font)
    draw.text((28, height - 48), "MOCK · 9:16", fill=(180, 180, 190), font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _placeholder_mp4(payload: bytes) -> bytes:
    """ISO BMFF minimo com mdat. Nao e um clipe reproduzivel em todos os players."""
    ftyp = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x01isommp41"
    mdat = (8 + len(payload)).to_bytes(4, "big") + b"mdat" + payload
    return ftyp + mdat


class MockVideoProvider(VideoProvider):
    name: ClassVar[str] = "mock"

    @property
    def default_model(self) -> str:
        return "mock-video"

    async def generate(self, request: VideoPrompt) -> GeneratedVideo:
        started = time.perf_counter()
        await asyncio.sleep(MOCK_VIDEO_LATENCY_SECONDS)
        thumb = _thumbnail(request)
        data = _placeholder_mp4(thumb[:1200])
        return GeneratedVideo(
            data=data,
            mime_type="video/mp4",
            width=432,
            height=768,
            duration_seconds=request.duration_seconds,
            provider=self.name,
            model=self.default_model,
            prompt=request.prompt,
            latency_ms=int((time.perf_counter() - started) * 1000),
            thumbnail_data=thumb,
            used_reference=bool(request.references),
        )
