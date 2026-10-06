import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import session_factory
from app.messaging.schemas import PaymentEvent
from app.payments.models import Payment, StatusChoices


class PaymentNotFoundError(RuntimeError):
    """Raised when an event references a missing payment."""


@dataclass(frozen=True)
class PaymentProcessingResult:
    status: StatusChoices
    processed_at: datetime | None


class PaymentProcessor:
    async def process(self, event: PaymentEvent) -> PaymentProcessingResult:
        async with session_factory() as session, session.begin():
            result = await session.execute(
                select(Payment)
                .where(Payment.payment_id == event.payment_id)
                .with_for_update()
            )
            payment = result.scalar_one_or_none()

            if payment is None:
                raise PaymentNotFoundError(f"Payment {event.payment_id} was not found")

            if payment.processed_at is not None:
                return PaymentProcessingResult(
                    status=payment.status,
                    processed_at=payment.processed_at,
                )

        await asyncio.sleep(random.uniform(2, 5))
        new_status = (
            StatusChoices.succeeded if random.random() < 0.9 else StatusChoices.failed
        )

        async with session_factory() as session, session.begin():
            result = await session.execute(
                select(Payment)
                .where(Payment.payment_id == event.payment_id)
                .with_for_update()
            )
            payment = result.scalar_one_or_none()

            if payment is None:
                raise PaymentNotFoundError(f"Payment {event.payment_id} was not found")

            if payment.processed_at is not None:
                return PaymentProcessingResult(
                    status=payment.status,
                    processed_at=payment.processed_at,
                )

            payment.status = new_status
            payment.processed_at = datetime.now(UTC)

            return PaymentProcessingResult(
                status=payment.status,
                processed_at=payment.processed_at,
            )
