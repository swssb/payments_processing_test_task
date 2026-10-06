import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import settings
from app.core.database import session_factory
from app.messaging.broker import broker
from app.messaging.topology import payments_exchange
from app.payments.models import PaymentOutbox

logger = logging.getLogger(__name__)


class OutboxPublisher:
    async def publish_pending(self) -> None:
        async with session_factory() as session:
            result = await session.execute(
                select(PaymentOutbox)
                .where(PaymentOutbox.published_at.is_(None))
                .order_by(PaymentOutbox.created_at)
                .limit(settings.outbox_batch_size)
                .with_for_update(skip_locked=True)
            )
            events = result.scalars().all()

            for event in events:
                payload = {
                    **event.payload,
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                }
                await broker.publish(
                    payload,
                    exchange=payments_exchange,
                    routing_key=event.event_type,
                    message_id=str(event.id),
                    persist=True,
                )
                event.published_at = datetime.now(UTC)

            if events:
                await session.commit()

    async def run(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                await self.publish_pending()
            except Exception:
                logger.exception("Failed to publish outbox events")

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=settings.outbox_poll_interval_seconds,
                )
            except TimeoutError:
                continue
