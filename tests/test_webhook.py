from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.messaging import webhook as webhook_module
from app.messaging.processor import PaymentProcessingResult
from app.messaging.schemas import PaymentEvent
from app.messaging.webhook import WebhookSender
from app.payments.models import StatusChoices


def create_event() -> PaymentEvent:
    return PaymentEvent(
        event_id=uuid4(),
        event_type="payments.new",
        payment_id=uuid4(),
        amount="100.00",
        currency="RUB",
        description="Test payment",
        metadata={"order_id": "order-1"},
        webhook_url="https://example.com/webhook",
    )


@pytest.mark.asyncio
async def test_webhook_contains_processing_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs) -> None:
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            return None

        async def post(self, url, *, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(webhook_module.httpx, "AsyncClient", FakeAsyncClient)
    processed_at = datetime.now(UTC)

    await WebhookSender().send(
        create_event(),
        PaymentProcessingResult(
            status=StatusChoices.succeeded,
            processed_at=processed_at,
        ),
    )

    payload = captured["json"]
    assert payload["status"] == "succeeded"
    assert payload["processed_at"] == processed_at.isoformat()
    assert captured["headers"]["X-Event-ID"]
