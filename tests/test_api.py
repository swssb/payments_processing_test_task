from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.payments.models import CurrencyChoices, Payment, StatusChoices
from app.payments.services import payments_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def build_payment(*, status: StatusChoices = StatusChoices.pending) -> Payment:
    return Payment(
        payment_id=uuid4(),
        amount=Decimal("125.50"),
        currency=CurrencyChoices.RUB,
        description="Test payment",
        payment_metadata={"order_id": "order-123"},
        status=status,
        idempotency_key="idem-123",
        webhook_url="https://example.com/webhook",
        created_at=datetime.now(UTC),
    )


def test_create_payment_requires_api_key(client: TestClient) -> None:
    response = client.post(
        "/api/v1/payments",
        json={
            "amount": "125.50",
            "currency": "RUB",
            "description": "Test payment",
            "metadata": {},
            "webhook_url": "https://example.com/webhook",
        },
        headers={"Idempotency-Key": "idem-123"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid API key"}


def test_create_payment_returns_accepted_payment(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment = build_payment()

    async def create_payment(*args, **kwargs) -> Payment:
        return payment

    monkeypatch.setattr(payments_service, "create_payment", create_payment)

    response = client.post(
        "/api/v1/payments",
        json={
            "amount": "125.50",
            "currency": "RUB",
            "description": "Test payment",
            "metadata": {"order_id": "order-123"},
            "webhook_url": "https://example.com/webhook",
        },
        headers={
            "X-API-Key": "test-api-key",
            "Idempotency-Key": "idem-123",
        },
    )

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["payment_id"] == str(payment.payment_id)
    assert response_data["status"] == "pending"
    assert datetime.fromisoformat(response_data["created_at"]) == payment.created_at


def test_get_payment_returns_payment(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment = build_payment(status=StatusChoices.succeeded)

    async def get_payment(*args, **kwargs) -> Payment:
        return payment

    monkeypatch.setattr(payments_service, "get_payment", get_payment)

    response = client.get(
        f"/api/v1/payments/{payment.payment_id}",
        headers={"X-API-Key": "test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["payment_id"] == str(payment.payment_id)
    assert response.json()["metadata"] == {"order_id": "order-123"}
    assert response.json()["status"] == "succeeded"


def test_get_payment_returns_404_when_payment_does_not_exist(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def get_payment(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(payments_service, "get_payment", get_payment)

    response = client.get(
        f"/api/v1/payments/{uuid4()}",
        headers={"X-API-Key": "test-api-key"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Payment not found"}
