from faststream.rabbit import RabbitQueue

from app.core.config import settings
from app.messaging.broker import broker
from app.messaging.schemas import PaymentEvent
from app.messaging.topology import (
    dead_letter_exchange,
    retry_exchange,
    retry_queues,
)


class MessageRetryPublisher:
    async def publish_retry_or_dead_letter(
        self,
        event: PaymentEvent,
        retry_count: int,
    ) -> None:
        next_retry_count = retry_count + 1
        headers = {"x-retry-count": next_retry_count}

        if next_retry_count >= settings.rabbitmq_max_attempts:
            await broker.publish(
                event.model_dump(mode="json"),
                exchange=dead_letter_exchange,
                routing_key=settings.rabbitmq_dlq,
                headers=headers,
                message_id=str(event.event_id),
                persist=True,
            )
            return

        retry_queue = self._get_retry_queue(retry_count)
        await broker.publish(
            event.model_dump(mode="json"),
            exchange=retry_exchange,
            routing_key=retry_queue.name,
            headers=headers,
            message_id=str(event.event_id),
            persist=True,
        )

    @staticmethod
    def _get_retry_queue(retry_count: int) -> RabbitQueue:
        try:
            return retry_queues[retry_count]
        except IndexError as error:
            raise RuntimeError(
                f"No retry queue configured for retry count {retry_count}"
            ) from error
