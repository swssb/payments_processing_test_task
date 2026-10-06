from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.payments.models import Payment, PaymentOutbox, StatusChoices
from app.payments.schemas import PaymentCreateRequest
from app.payments.services import PaymentsService


class FakeResult:
    def __init__(self, value: Payment | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> Payment | None:
        return self.value


class FakeSession:
    def __init__(
        self,
        results: list[Payment | None],
        *,
        flush_error: Exception | None = None,
    ) -> None:
        self.results = iter(results)
        self.added: list[Payment | PaymentOutbox] = []
        self.flush_error = flush_error
        self.commit_count = 0
        self.rollback_count = 0

    async def execute(self, statement) -> FakeResult:
        return FakeResult(next(self.results))

    def add(self, instance: Payment | PaymentOutbox) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        if self.flush_error is not None:
            raise self.flush_error

        for instance in self.added:
            if isinstance(instance, Payment) and instance.payment_id is None:
                instance.payment_id = uuid4()

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1

    async def refresh(self, instance: Payment) -> None:
        return None


def create_request() -> PaymentCreateRequest:
    return PaymentCreateRequest(
        amount=Decimal("100.00"),
        currency="RUB",
        description="Test payment",
        metadata={"order_id": "order-1"},
        webhook_url="https://example.com/webhook",
    )


@pytest.mark.asyncio
async def test_create_payment_creates_payment_and_outbox_event() -> None:
    session = FakeSession([None])

    payment = await PaymentsService().create_payment(
        idempotency_key="idem-1",
        data=create_request(),
        session=session,
    )

    assert isinstance(payment.payment_id, UUID)
    assert payment.status is StatusChoices.pending
    assert session.commit_count == 1
    assert session.rollback_count == 0

    outbox_events = [
        instance
        for instance in session.added
        if isinstance(instance, PaymentOutbox)
    ]
    assert len(outbox_events) == 1
    assert outbox_events[0].payment_id == payment.payment_id
    assert outbox_events[0].payload["payment_id"] == str(payment.payment_id)


@pytest.mark.asyncio
async def test_create_payment_returns_existing_payment_for_same_idempotency_key() -> None:
    existing_payment = Payment(payment_id=uuid4(), status=StatusChoices.pending)
    session = FakeSession([existing_payment])

    payment = await PaymentsService().create_payment(
        idempotency_key="idem-1",
        data=create_request(),
        session=session,
    )

    assert payment is existing_payment
    assert session.added == []
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_create_payment_handles_idempotency_race() -> None:
    existing_payment = Payment(payment_id=uuid4(), status=StatusChoices.pending)
    session = FakeSession(
        [None, existing_payment],
        flush_error=IntegrityError("insert", {}, RuntimeError("duplicate key")),
    )

    payment = await PaymentsService().create_payment(
        idempotency_key="idem-1",
        data=create_request(),
        session=session,
    )

    assert payment is existing_payment
    assert session.rollback_count == 1
    assert session.commit_count == 0
