import os

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/payments",
)
os.environ.setdefault(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/",
)
