"""Package with auth handler."""
from app.web.auth.handlers import setup_handlers
from app.web.auth.router import router

__all__ = ["router", "setup_handlers"]
