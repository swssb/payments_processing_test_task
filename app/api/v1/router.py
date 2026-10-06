from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import verify_api_key
from app.payments.schemas import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentDetailResponse,
)
from app.payments.services import payments_service

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "", response_model=PaymentCreateResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_payment(
    data: PaymentCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_db_session),
):
    payment = await payments_service.create_payment(
        data=data, idempotency_key=idempotency_key, session=session
    )
    return PaymentCreateResponse(
        payment_id=payment.payment_id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get("/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment(
    payment_id: UUID, session: AsyncSession = Depends(get_db_session)
):
    payment = await payments_service.get_payment(payment_id=payment_id, session=session)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    return payment
