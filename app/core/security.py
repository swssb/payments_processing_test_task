from secrets import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_api_key(
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if api_key is None or not compare_digest(
        api_key,
        settings.api_key.get_secret_value(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
