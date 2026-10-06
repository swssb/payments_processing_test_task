import asyncio

import httpx

from app.core.config import settings
from app.messaging.processor import PaymentProcessingResult
from app.messaging.schemas import PaymentEvent


class WebhookDeliveryError(RuntimeError):
    """Raised when all webhook delivery attempts fail."""


class WebhookSender:
    async def send(
        self,
        event: PaymentEvent,
        result: PaymentProcessingResult,
    ) -> None:
        payload = {
            **event.model_dump(mode="json"),
            "status": result.status.value,
            "processed_at": (
                result.processed_at.isoformat()
                if result.processed_at is not None
                else None
            ),
        }
        headers = {"X-Event-ID": str(event.event_id)}

        async with httpx.AsyncClient(
            timeout=settings.webhook_timeout_seconds,
        ) as client:
            last_error: Exception | None = None

            for attempt in range(3):
                try:
                    response = await client.post(
                        str(event.webhook_url),
                        json=payload,
                        headers=headers,
                    )
                    response.raise_for_status()
                    return
                except httpx.HTTPError as error:
                    last_error = error
                    if attempt < 2:
                        await self._sleep_before_retry(attempt)

            raise WebhookDeliveryError(
                f"Webhook delivery failed for event {event.event_id}"
            ) from last_error

    async def _sleep_before_retry(self, attempt: int) -> None:
        delay_seconds = 2**attempt
        await asyncio.sleep(delay_seconds)
