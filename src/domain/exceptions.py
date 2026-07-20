# src/domain/exceptions.py
from typing import Any, Dict, Optional

from src.infrastructure.config.settings import settings


class DomainError(Exception):
    """Base exception for all domain-level errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a serializable dict for API responses."""
        error_dict: Dict[str, Any] = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.details:
            error_dict["details"] = self.details
        # Show internal trace only in debug mode
        if settings.debug and hasattr(self, "__traceback__"):
            import traceback

            error_dict["trace"] = traceback.format_tb(self.__traceback__)
        return error_dict


# ---------- Specific domain exceptions ----------


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""

    pass


class ValidationError(DomainError):
    """Raised when input data fails business validation."""

    pass


class PolicyViolationError(DomainError):
    """Raised when an action violates a defined policy."""

    pass


class UnauthorizedError(DomainError):
    """Raised when authentication fails or permissions are insufficient."""

    pass


class ConflictError(DomainError):
    """Raised when there is a state conflict (e.g., duplicate resource)."""

    pass


# ---------- Infrastructure / external errors ----------


class InfrastructureError(DomainError):
    """Raised when an external system fails (DB, Redis, API)."""

    pass


class ConnectionError(InfrastructureError):
    """Raised when a network connection fails."""

    pass


class LLMError(InfrastructureError):
    """Raised when an LLM service (OpenAI, etc.) fails."""

    pass


class ConnectorError(InfrastructureError):
    """Raised when a specific infrastructure connector (Hostinger, AWS) fails."""

    pass


class ConnectionFailedError(ConnectorError):
    """Raised when connecting to a remote infrastructure element fails."""

    pass


class AuthenticationFailedError(ConnectorError):
    """Raised when authentication with credentials or SSH keys fails."""

    pass


class CommandExecutionFailedError(ConnectorError):
    """Raised when executing a command on a remote host fails or returns non-zero."""

    pass


class ConnectorTimeoutError(ConnectorError):
    """Raised when a connection attempt or execution command times out."""

    pass
