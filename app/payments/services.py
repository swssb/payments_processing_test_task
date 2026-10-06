from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.payments.models import Payment, StatusChoices, PaymentOutbox
from app.payments.schemas import PaymentCreateRequest


class PaymentsService:
    async def get_payment(
        self, payment_id: UUID, session: AsyncSession
    ) -> Payment | None:
        result = await session.execute(
            select(Payment).where(Payment.payment_id == payment_id)
        )
        return result.scalar_one_or_none()

    async def create_payment(
        self, idempotency_key: str, data: PaymentCreateRequest, session: AsyncSession
    ) -> Payment:
        result = await session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        payment = result.scalar_one_or_none()

        if payment is not None:
            return payment

        try:
            payment = Payment(
                amount=data.amount,
                currency=data.currency,
                description=data.description,
                payment_metadata=data.metadata,
                webhook_url=str(data.webhook_url),
                status=StatusChoices.pending,
                idempotency_key=idempotency_key,
            )
            session.add(payment)
            await session.flush()

            outbox = PaymentOutbox(
                payment_id=payment.payment_id,
                payload={
                    "payment_id": str(payment.payment_id),
                    "amount": str(payment.amount),
                    "currency": payment.currency.value,
                    "description": payment.description,
                    "metadata": payment.payment_metadata,
                    "webhook_url": str(payment.webhook_url),
                },
            )
            session.add(outbox)

            await session.commit()
        except IntegrityError:
            await session.rollback()

            result = await session.execute(
                select(Payment).where(Payment.idempotency_key == idempotency_key)
            )
            existing_payment = result.scalar_one_or_none()

            if existing_payment is None:
                raise

            return existing_payment

        await session.refresh(payment)
        return payment


payments_service = PaymentsService()
