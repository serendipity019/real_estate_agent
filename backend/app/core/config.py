import secrets
import warnings
from typing import Annotated, Any, Literal
from functools import lru_cache

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.main import DotEnvSettingsSource
from typing_extensions import Self

def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_file_override=True,
        env_ignore_empty=True,
        extra="ignore",
    )

    # ── Core / Security ─────────────────────────────────────────────────────────
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    FRONTEND_HOST: str = "http://127.0.0.1:8000/ui"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    PROJECT_NAME: str = "Smart Real Estate Assistant"
    SENTRY_DSN: HttpUrl | None = None

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]
    
    # ── Postgres  ─────────────────────────────────────────────────────────
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
    
    #  Email (SMTP)  ─────────────────────────────────────────────────────────
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 1

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self


    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    #  First superuser  ─────────────────────────────────────────────────────────
    EMAIL_TEST_USER: EmailStr = "super@gmail.com"
    FIRST_SUPERUSER: EmailStr = "super@gmail.com"
    FIRST_SUPERUSER_PASSWORD: str = "super147963"

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)
    
    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self
    
    # API Keys  ─────────────────────────────────────────────────────────
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    TAVILY_API_KEY: str

    # Model config  ─────────────────────────────────────────────────────────
    PRIMARY_MODEL: str = "claude-sonnet-4-6"
    FALLBACK_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ChromaDB  ─────────────────────────────────────────────────────────
    CHROMA_COLLECTION_NAME: str = "greek_real_estate"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_db"

    # RAG  ─────────────────────────────────────────────────────────
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.5

    # App  ─────────────────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    #  Chat / Memory  ─────────────────────────────────────────────────────────
    MAX_MEMORY_TURNS: int = 20  # how many past turns to keep in SearchSession.memory

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()