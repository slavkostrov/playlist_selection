"""Package with web handler."""
from app.web.auth import setup_handlers
from app.web.router import router

__all__ = ["router", "setup_handlers"]
