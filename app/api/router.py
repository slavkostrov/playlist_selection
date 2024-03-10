"""Main /api router."""
from fastapi import APIRouter

from app.api import predict

router = APIRouter(prefix="/api")
router.include_router(predict.router)
