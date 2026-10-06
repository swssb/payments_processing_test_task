# Payments processing service

Микросервис принимает платежи, сохраняет их в PostgreSQL, асинхронно обрабатывает через RabbitMQ и отправляет результат на webhook клиента.

## Архитектура

```text
Client
  │
  ▼
FastAPI ── transaction ── PostgreSQL
  │                         │
  │                         └── payments + outbox
  │
  └─────────────── OutboxPublisher ── RabbitMQ ── Consumer
                                                    │
                                                    ├── обработка платежа
                                                    └── webhook с retry
```

Основные компоненты:

- `app/api/v1` — HTTP API;
- `app/payments` — модели, Pydantic-схемы и сервис платежей;
- `app/messaging` — RabbitMQ, outbox publisher, consumer, retry и webhook;
- `app/core` — настройки, подключение к PostgreSQL и API key;
- `alembic` — миграции базы данных.

При создании платежа в одной транзакции сохраняются платеж и outbox-событие. Отдельный publisher публикует outbox-события в RabbitMQ. Это позволяет не потерять событие, если RabbitMQ временно недоступен.

## Запуск через Docker Compose

Требования:

- Docker;
- Docker Compose.

Запуск всех сервисов:

```bash
docker compose up --build
```

Будут запущены:

- API: <http://localhost:8000>;
- PostgreSQL: `localhost:5432`;
- RabbitMQ AMQP: `localhost:5672`;
- RabbitMQ Management UI: <http://localhost:15672>;
- миграции Alembic;
- consumer платежей.



## Конфигурация

Основные переменные находятся в `.env.example`. Для локального запуска без Docker можно создать `.env`:

```bash
cp .env.example .env
```

В Docker Compose значения подключения к PostgreSQL и RabbitMQ передаются сервисам автоматически. API key передаётся через переменную `API_KEY`:

```bash
API_KEY=my-secret-key docker compose -f docker-compose.yaml up --build
```

## API

Все endpoints требуют заголовок:

```text
X-API-Key: api_key_h2Kna3K8Q
```

### Создание платежа

`POST /api/v1/payments`

Обязательные заголовки:

```text
X-API-Key: api_key_h2Kna3K8Q
Idempotency-Key: order-123-payment
```

Пример запроса:

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: api_key_h2Kna3K8Q' \
  -H 'Idempotency-Key: order-123-payment' \
  -d '{
    "amount": "1500.00",
    "currency": "RUB",
    "description": "Оплата заказа 123",
    "metadata": {
      "order_id": "123"
    },
    "webhook_url": "https://example.com/webhooks/payments"
  }'
```

Ответ: `202 Accepted`.

```json
{
  "payment_id": "7f3c1f9b-1d9b-4b6a-a5c4-1a5db6c6d5c8",
  "status": "pending",
  "created_at": "2026-10-06T12:00:00Z"
}
```

Повторный запрос с тем же `Idempotency-Key` возвращает уже существующий платеж и не создаёт второй outbox event.

### Получение платежа

`GET /api/v1/payments/{payment_id}`

```bash
curl http://localhost:8000/api/v1/payments/7f3c1f9b-1d9b-4b6a-a5c4-1a5db6c6d5c8 \
  -H 'X-API-Key: api_key_h2Kna3K8Q'
```

Платёж сначала имеет статус `pending`, затем становится `succeeded` или `failed` после обработки consumer’ом.

После обработки consumer отправляет на `webhook_url` результат:

```json
{
  "event_id": "7f3c1f9b-1d9b-4b6a-a5c4-1a5db6c6d5c8",
  "event_type": "payments.new",
  "payment_id": "7f3c1f9b-1d9b-4b6a-a5c4-1a5db6c6d5c8",
  "amount": "1500.00",
  "currency": "RUB",
  "description": "Оплата заказа 123",
  "metadata": {
    "order_id": "123"
  },
  "webhook_url": "https://example.com/webhooks/payments",
  "status": "succeeded",
  "processed_at": "2026-10-06T12:00:05Z"
}
```

Заголовок `X-Event-ID` содержит идентификатор события. Клиент может использовать его для дедупликации повторных webhook-уведомлений.

## RabbitMQ и retry

Основные сущности RabbitMQ:

- exchange `payments`;
- queue `payments.new`;
- retry exchange `payments.retry`;
- три retry-очереди с задержками `1`, `2` и `4` секунды;
- dead-letter exchange `payments.dlx`;
- dead-letter queue `payments.dlq`.

После трёх неуспешных попыток сообщение отправляется в DLQ. Ошибки доставки webhook повторяются с экспоненциальной задержкой внутри consumer’а.

## Миграции

Применить миграции локально:

```bash
uv run alembic upgrade head
```

Создать новую миграцию после изменения ORM-моделей:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

## Тесты

Установить dev-зависимости:

```bash
uv sync
```

Запустить тесты:

```bash
uv run pytest
```
