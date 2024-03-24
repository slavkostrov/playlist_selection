"""Main router fow web endpoints."""
from fastapi import APIRouter

from app.web import auth, generate

router = APIRouter()
router.include_router(auth.router)
router.include_router(generate.router)
