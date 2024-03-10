"""Custom exceptions of playlist selection web-app."""

class RequiresLoginException(Exception):
    """Raises when user try to open page with login dependecy without login."""
    pass


class UnknownCookieException(Exception):
    """Raises when user's cookie is unknown."""
