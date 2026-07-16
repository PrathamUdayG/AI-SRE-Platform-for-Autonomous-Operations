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
        error_dict = {
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


"""
Code summary
This file defines a family of custom exceptions. All of them inherit from DomainError, which adds a details field and a to_dict() method. 
The to_dict() method is used by the API to return structured JSON errors. It also automatically includes the stack trace only when settings.
debug=True – so in production, we don't leak internals.

Why this folder?
Because errors that represent business rules (e.g., "this action violates a policy") or domain concepts (e.g., "incident not found")
belong in the Domain layer. Infrastructure exceptions (e.g., "can't connect to Redis") also inherit from our base domain error so they're handled uniformly, but the root definitions live here.

Which module owns it?
The Domain module – it's a core part of the business logic.

 Future files that depend on it
All Application services – they raise these exceptions.
All API endpoints – they catch these exceptions and map them to HTTP responses.
All Infrastructure connectors – they raise InfrastructureError or ConnectionError when something external fails.

"""