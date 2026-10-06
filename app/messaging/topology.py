from faststream.rabbit import (
    ExchangeType,
    RabbitExchange,
    RabbitQueue,
)

from app.core.config import settings
from app.messaging.broker import broker

payments_exchange = RabbitExchange(
    name=settings.rabbitmq_exchange,
    type=ExchangeType.DIRECT,
    durable=True,
)

dead_letter_exchange = RabbitExchange(
    name=settings.rabbitmq_dlx,
    type=ExchangeType.DIRECT,
    durable=True,
)

retry_exchange = RabbitExchange(
    name=settings.rabbitmq_retry_exchange,
    type=ExchangeType.DIRECT,
    durable=True,
)

payments_queue = RabbitQueue(
    name=settings.rabbitmq_queue,
    durable=True,
    arguments={
        "x-dead-letter-exchange": settings.rabbitmq_dlx,
        "x-dead-letter-routing-key": settings.rabbitmq_dlq,
    },
    routing_key=settings.rabbitmq_routing_key,
)

dead_letter_queue = RabbitQueue(
    name=settings.rabbitmq_dlq,
    durable=True,
    routing_key=settings.rabbitmq_dlq,
)

retry_delays_seconds = (1, 2, 4)
retry_queues = tuple(
    RabbitQueue(
        name=f"{settings.rabbitmq_queue}.retry.{delay}s",
        durable=True,
        arguments={
            "x-message-ttl": delay * 1000,
            "x-dead-letter-exchange": settings.rabbitmq_exchange,
            "x-dead-letter-routing-key": settings.rabbitmq_routing_key,
        },
        routing_key=f"{settings.rabbitmq_queue}.retry.{delay}s",
    )
    for delay in retry_delays_seconds
)


async def declare_topology() -> None:
    await broker.declare_exchange(payments_exchange)

    dead_letter_exchange_channel = await broker.declare_exchange(dead_letter_exchange)
    dead_letter_queue_channel = await broker.declare_queue(dead_letter_queue)
    await dead_letter_queue_channel.bind(
        exchange=dead_letter_exchange_channel,
        routing_key=settings.rabbitmq_dlq,
    )

    retry_exchange_channel = await broker.declare_exchange(retry_exchange)
    for retry_queue in retry_queues:
        retry_queue_channel = await broker.declare_queue(retry_queue)
        await retry_queue_channel.bind(
            exchange=retry_exchange_channel,
            routing_key=retry_queue.name,
        )
