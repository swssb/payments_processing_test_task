from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/payments",
        validation_alias="DATABASE_URL",
    )
    echo_sql: bool = Field(default=False, validation_alias="ECHO_SQL")
    api_key: SecretStr = Field(
        validation_alias="API_KEY",
    )
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        validation_alias="RABBITMQ_URL",
    )
    rabbitmq_exchange: str = Field(
        default="payments",
        validation_alias="RABBITMQ_EXCHANGE",
    )
    rabbitmq_queue: str = Field(
        default="payments.new",
        validation_alias="RABBITMQ_QUEUE",
    )
    rabbitmq_routing_key: str = Field(
        default="payments.new",
        validation_alias="RABBITMQ_ROUTING_KEY",
    )
    rabbitmq_dlx: str = Field(
        default="payments.dlx",
        validation_alias="RABBITMQ_DLX",
    )
    rabbitmq_retry_exchange: str = Field(
        default="payments.retry",
        validation_alias="RABBITMQ_RETRY_EXCHANGE",
    )
    rabbitmq_dlq: str = Field(
        default="payments.dlq",
        validation_alias="RABBITMQ_DLQ",
    )
    rabbitmq_max_attempts: int = Field(
        default=3,
        ge=1,
        validation_alias="RABBITMQ_MAX_ATTEMPTS",
    )
    outbox_poll_interval_seconds: float = Field(
        default=1.0,
        gt=0,
        validation_alias="OUTBOX_POLL_INTERVAL_SECONDS",
    )
    outbox_batch_size: int = Field(
        default=100,
        ge=1,
        validation_alias="OUTBOX_BATCH_SIZE",
    )
    webhook_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        validation_alias="WEBHOOK_TIMEOUT_SECONDS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
