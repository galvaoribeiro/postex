"""Acesso ao object storage (MinIO em dev, S3 em producao).

Regras que este modulo concentra:

* o binario nunca passa pela API - o browser faz PUT direto usando URL assinada;
* URLs de leitura sao sempre assinadas e de curta duracao, e o bucket permanece
  privado;
* as URLs entregues ao browser usam `S3_PUBLIC_ENDPOINT_URL`, que pode ser
  diferente do endpoint interno usado pelo backend (dentro do Docker o host
  `minio` nao existe para o navegador).
"""

from __future__ import annotations

import asyncio
import mimetypes
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Environment, Settings, settings as default_settings
from app.core.exceptions import StorageError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_IMAGE_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
)

_SAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    method: str
    headers: dict[str, str]
    storage_key: str
    expires_in: int


def _slugify_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode()
    cleaned = _SAFE_FILENAME.sub("-", normalized).strip("-._")
    return (cleaned or "arquivo")[:120]


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings
        self._internal = self._build_client(self.settings.S3_ENDPOINT_URL)
        self._public = (
            self._internal
            if self.settings.S3_PUBLIC_ENDPOINT_URL == self.settings.S3_ENDPOINT_URL
            else self._build_client(self.settings.S3_PUBLIC_ENDPOINT_URL)
        )
        #: Nos testes o still gerado nao depende do MinIO.
        self._memory: dict[str, bytes] = {}
        self._use_memory = self.settings.ENVIRONMENT is Environment.TEST

    # ------------------------------------------------------------- clientes
    def _build_client(self, endpoint_url: str) -> Any:
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.settings.S3_ACCESS_KEY,
            aws_secret_access_key=self.settings.S3_SECRET_KEY,
            region_name=self.settings.S3_REGION,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path" if self.settings.S3_FORCE_PATH_STYLE else "auto"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    @property
    def bucket(self) -> str:
        return self.settings.S3_BUCKET

    # ---------------------------------------------------------------- setup
    async def ensure_bucket(self, *, attempts: int = 10, delay: float = 1.5) -> bool:
        """Cria o bucket se ainda nao existir. Idempotente.

        Roda no startup da API, que pode subir antes do MinIO aceitar conexoes -
        daí as tentativas. Uma falha final nao derruba a aplicacao: apenas os
        endpoints de asset ficam indisponiveis, e o log diz o motivo.
        """

        def _ensure() -> None:
            try:
                self._internal.head_bucket(Bucket=self.bucket)
                return
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code")
                if code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
            try:
                self._internal.create_bucket(Bucket=self.bucket)
            except ClientError as exc:  # pragma: no cover - corrida entre replicas
                if exc.response.get("Error", {}).get("Code") not in {
                    "BucketAlreadyOwnedByYou",
                    "BucketAlreadyExists",
                }:
                    raise

        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                await asyncio.to_thread(_ensure)
                logger.info("storage_bucket_ready", bucket=self.bucket)
                return True
            except (BotoCoreError, ClientError) as exc:
                last_error = exc
                if attempt < attempts:
                    await asyncio.sleep(delay)

        logger.warning(
            "storage_bucket_unavailable",
            bucket=self.bucket,
            endpoint=self.settings.S3_ENDPOINT_URL,
            error=str(last_error),
        )
        return False

    # ----------------------------------------------------------------- keys
    def build_key(self, business_id: uuid.UUID, filename: str) -> str:
        """Chave com o negocio no caminho: facilita auditoria e lifecycle rules."""
        today = date.today()
        return (
            f"businesses/{business_id}/{today:%Y/%m}/"
            f"{uuid.uuid4().hex}-{_slugify_filename(filename)}"
        )

    def validate_upload(self, *, filename: str, mime_type: str, size_bytes: int | None) -> str:
        """Valida o upload solicitado e devolve o mime type normalizado."""
        resolved = (mime_type or "").strip().lower()
        if not resolved:
            resolved = mimetypes.guess_type(filename)[0] or ""

        if resolved not in ALLOWED_IMAGE_MIME_TYPES:
            raise ValidationError(
                "Formato de arquivo nao suportado.",
                details={"received": resolved, "allowed": sorted(ALLOWED_IMAGE_MIME_TYPES)},
            )

        if size_bytes is not None and size_bytes > self.settings.max_upload_size_bytes:
            raise ValidationError(
                f"Arquivo maior que o limite de {self.settings.MAX_UPLOAD_SIZE_MB} MB.",
                details={"size_bytes": size_bytes},
            )

        return resolved

    # ------------------------------------------------------------ presigned
    def create_presigned_upload(
        self, *, storage_key: str, mime_type: str, expires_in: int | None = None
    ) -> PresignedUpload:
        expires = expires_in or self.settings.S3_PRESIGN_EXPIRE_SECONDS
        try:
            url = self._public.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": storage_key,
                    "ContentType": mime_type,
                },
                ExpiresIn=expires,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Nao foi possivel preparar o upload.") from exc

        return PresignedUpload(
            url=url,
            method="PUT",
            # O browser precisa enviar exatamente este Content-Type: ele faz
            # parte da assinatura.
            headers={"Content-Type": mime_type},
            storage_key=storage_key,
            expires_in=expires,
        )

    async def put_object(
        self, storage_key: str, body: bytes, *, mime_type: str
    ) -> None:
        """Grava bytes gerados no backend (stills de IA)."""
        if self._use_memory:
            self._memory[storage_key] = body
            return

        def _put() -> None:
            self._internal.put_object(
                Bucket=self.bucket,
                Key=storage_key,
                Body=body,
                ContentType=mime_type,
            )

        try:
            await asyncio.to_thread(_put)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Nao foi possivel gravar a imagem gerada.") from exc

    def create_presigned_download(
        self, storage_key: str, *, expires_in: int | None = None, internal: bool = False
    ) -> str:
        """URL de leitura assinada.

        `internal=True` gera a URL com o endpoint interno, para quando o
        consumidor e o proprio backend (por exemplo o provedor de IA rodando
        dentro da mesma rede).
        """
        if self._use_memory:
            return f"http://testserver/generated/{storage_key}"
        client = self._internal if internal else self._public
        try:
            return client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": storage_key},
                ExpiresIn=expires_in or self.settings.S3_PRESIGN_EXPIRE_SECONDS,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Nao foi possivel gerar o link do arquivo.") from exc

    # --------------------------------------------------------------- objeto
    async def head_object(self, storage_key: str) -> dict[str, Any] | None:
        if self._use_memory:
            data = self._memory.get(storage_key)
            if data is None:
                return None
            return {"ContentLength": len(data)}

        def _head() -> dict[str, Any] | None:
            try:
                return self._internal.head_object(Bucket=self.bucket, Key=storage_key)
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                    return None
                raise

        try:
            return await asyncio.to_thread(_head)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Falha ao consultar o arquivo no storage.") from exc

    async def delete_object(self, storage_key: str) -> None:
        if self._use_memory:
            self._memory.pop(storage_key, None)
            return

        def _delete() -> None:
            self._internal.delete_object(Bucket=self.bucket, Key=storage_key)

        try:
            await asyncio.to_thread(_delete)
        except (BotoCoreError, ClientError) as exc:
            # A remocao do metadado nao deve falhar por causa do storage; o
            # objeto orfao pode ser limpo por lifecycle rule.
            logger.warning("storage_delete_failed", key=storage_key, error=str(exc))


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Instancia unica: criar clientes boto3 por request e caro."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
