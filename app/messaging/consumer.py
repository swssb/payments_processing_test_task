import asyncio
import logging

from faststream import FastStream, Header

from app.messaging.broker import broker
from app.messaging.processor import PaymentProcessor
from app.messaging.publisher import OutboxPublisher
from app.messaging.retry import MessageRetryPublisher
from app.messaging.schemas import PaymentEvent
from app.messaging.topology import (
    declare_topology,
    payments_exchange,
    payments_queue,
)
from app.messaging.webhook import WebhookSender

logger = logging.getLogger(__name__)
app = FastStream(broker)
payment_processor = PaymentProcessor()
outbox_publisher = OutboxPublisher()
webhook_sender = WebhookSender()
retry_publisher = MessageRetryPublisher()
publisher_stop_event: asyncio.Event | None = None
publisher_task: asyncio.Task[None] | None = None


@app.after_startup
async def start_background_tasks() -> None:
    global publisher_stop_event, publisher_task

    await declare_topology()
    publisher_stop_event = asyncio.Event()
    publisher_task = asyncio.create_task(outbox_publisher.run(publisher_stop_event))


@app.on_shutdown
async def stop_background_tasks() -> None:
    if publisher_stop_event is not None:
        publisher_stop_event.set()

    if publisher_task is not None:
        await publisher_task


@broker.subscriber(
    queue=payments_queue,
    exchange=payments_exchange,
)
async def process_payment(
    event: PaymentEvent,
    retry_count: int = Header("x-retry-count", default=0),
) -> None:
    try:
        result = await payment_processor.process(event)
        await webhook_sender.send(event, result)
    except Exception:
        logger.exception(
            "Payment event processing failed",
            extra={
                "event_id": str(event.event_id),
                "payment_id": str(event.payment_id),
                "retry_count": retry_count,
            },
        )
        await retry_publisher.publish_retry_or_dead_letter(
            event=event,
            retry_count=retry_count,
        )
