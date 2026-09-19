"""Configuracao central da aplicacao.

Todas as variaveis sensiveis vem exclusivamente do ambiente. Nenhum segredo
possui valor padrao utilizavel em producao: `Settings.validate_production`
falha explicitamente se a aplicacao subir em producao com valores de exemplo.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_PREFIX = "troque-esta-chave"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class AIProviderName(str, Enum):
    MOCK = "mock"
    OPENAI = "openai"


class AIExecutionMode(str, Enum):
    """Como as tarefas de IA sao executadas.

    - ``celery``: enfileira no Redis e o worker processa (producao).
    - ``inline``: executa no proprio processo da API, ainda de forma assincrona
      via ``BackgroundTasks``. Permite rodar o produto sem worker e em testes.
    """

    CELERY = "celery"
    INLINE = "inline"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ app
    PROJECT_NAME: str = "Motor de Conteudo"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True

    # O valor padrao existe apenas para nao travar o ambiente local. Ele e
    # rejeitado por `validate_runtime` quando ENVIRONMENT e staging/producao.
    SECRET_KEY: str = Field(
        default=f"{INSECURE_SECRET_PREFIX}-em-producao-com-no-minimo-32-caracteres",
        min_length=32,
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # ----------------------------------------------------------------- cors
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    COOKIE_DOMAIN: str | None = None

    # ------------------------------------------------------------- database
    DATABASE_URL: str = "postgresql+asyncpg://postex:postex@localhost:5432/postex"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ---------------------------------------------------------------- redis
    REDIS_URL: str = "redis://localhost:6379/0"
    AI_EXECUTION_MODE: AIExecutionMode = AIExecutionMode.INLINE

    # -------------------------------------------------------------- storage
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_PUBLIC_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "motor-conteudo-assets"
    S3_REGION: str = "us-east-1"
    S3_FORCE_PATH_STYLE: bool = True
    S3_PRESIGN_EXPIRE_SECONDS: int = 900
    MAX_UPLOAD_SIZE_MB: int = 15

    # ------------------------------------------------------------------- ia
    AI_PROVIDER: AIProviderName = AIProviderName.MOCK
    AI_TEMPERATURE: float = 0.8
    AI_MAX_RETRIES: int = 3
    AI_DEFAULT_IDEA_COUNT: int = 5

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: int = 90
    OPENAI_BASE_URL: str | None = None

    @field_validator("COOKIE_DOMAIN", "OPENAI_API_KEY", "OPENAI_BASE_URL", mode="before")
    @classmethod
    def _empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT in {Environment.PRODUCTION, Environment.STAGING}

    @property
    def sync_database_url(self) -> str:
        """URL sincrona, usada por ferramentas que nao falam asyncpg."""
        return self.DATABASE_URL.replace("+asyncpg", "")

    def validate_runtime(self) -> None:
        """Checagens que devem falhar o boot, nao virar warning silencioso."""
        problems: list[str] = []

        if self.is_production:
            if self.SECRET_KEY.startswith(INSECURE_SECRET_PREFIX):
                problems.append("SECRET_KEY ainda contem o valor de exemplo")
            if not self.COOKIE_SECURE:
                problems.append("COOKIE_SECURE deve ser true fora de desenvolvimento")
            if self.DEBUG:
                problems.append("DEBUG deve ser false em producao")

        if self.AI_PROVIDER is AIProviderName.OPENAI and not self.OPENAI_API_KEY:
            problems.append("AI_PROVIDER=openai exige OPENAI_API_KEY")

        if problems:
            raise RuntimeError(
                "Configuracao invalida:\n  - " + "\n  - ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
