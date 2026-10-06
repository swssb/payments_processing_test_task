from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.messaging import retry as retry_module
from app.messaging.retry import MessageRetryPublisher
from app.messaging.schemas import PaymentEvent


def create_event() -> PaymentEvent:
    return PaymentEvent(
        event_id=uuid4(),
        event_type="payments.new",
        payment_id=uuid4(),
        amount="100.00",
        currency="RUB",
        description="Test payment",
        metadata={},
        webhook_url="https://example.com/webhook",
    )


@pytest.mark.asyncio
async def test_retry_publisher_sends_event_to_next_retry_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publish = AsyncMock()
    monkeypatch.setattr(retry_module.broker, "publish", publish)
    event = create_event()

    await MessageRetryPublisher().publish_retry_or_dead_letter(
        event=event,
        retry_count=0,
    )

    publish.assert_awaited_once()
    kwargs = publish.await_args.kwargs
    assert kwargs["exchange"] is retry_module.retry_exchange
    assert kwargs["routing_key"] == retry_module.retry_queues[0].name
    assert kwargs["headers"] == {"x-retry-count": 1}
    assert kwargs["message_id"] == str(event.event_id)


@pytest.mark.asyncio
async def test_retry_publisher_sends_third_failure_to_dlq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publish = AsyncMock()
    monkeypatch.setattr(retry_module.broker, "publish", publish)
    event = create_event()

    await MessageRetryPublisher().publish_retry_or_dead_letter(
        event=event,
        retry_count=2,
    )

    publish.assert_awaited_once()
    kwargs = publish.await_args.kwargs
    assert kwargs["exchange"] is retry_module.dead_letter_exchange
    assert kwargs["routing_key"] == retry_module.settings.rabbitmq_dlq
    assert kwargs["headers"] == {"x-retry-count": 3}
