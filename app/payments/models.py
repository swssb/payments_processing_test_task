from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Numeric,
    String,
    Text,
    func,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CurrencyChoices(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class StatusChoices(str, Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2),
    )
    currency: Mapped[CurrencyChoices] = mapped_column()
    description: Mapped[str] = mapped_column(String(length=1000))
    payment_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
    )
    status: Mapped[StatusChoices] = mapped_column(
        default=StatusChoices.pending,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(length=255),
        unique=True,
    )
    webhook_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentOutbox(Base):
    __tablename__ = "outbox"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    payment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("payments.payment_id"),
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        default="payments.new",
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    attempts_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
