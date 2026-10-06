from fastapi import FastAPI
from app.api.v1.router import router as payments_router

app = FastAPI()

app.include_router(payments_router)
