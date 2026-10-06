from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.payments.models import CurrencyChoices


class PaymentEvent(BaseModel):
    event_id: UUID
    event_type: str
    payment_id: UUID
    amount: Decimal
    currency: CurrencyChoices
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: HttpUrl
