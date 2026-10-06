from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.payments.models import StatusChoices, CurrencyChoices


class PaymentCreateRequest(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=2)
    currency: CurrencyChoices
    description: str = Field(max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: HttpUrl


class PaymentResponseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaymentCreateResponse(PaymentResponseBase):
    payment_id: UUID
    status: StatusChoices
    created_at: datetime


class PaymentDetailResponse(PaymentResponseBase):
    payment_id: UUID
    amount: Decimal
    currency: CurrencyChoices
    description: str
    metadata: dict[str, Any] = Field(
        validation_alias="payment_metadata",
        serialization_alias="metadata",
    )
    status: StatusChoices
    idempotency_key: str
    webhook_url: HttpUrl
    created_at: datetime
    processed_at: datetime | None
