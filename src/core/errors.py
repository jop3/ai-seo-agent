"""
Custom exceptions and error handling utilities for SEO Agent.
"""

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Standardized error codes."""

    # Configuration errors
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"

    # API errors
    API_UNAVAILABLE = "API_UNAVAILABLE"
    API_RATE_LIMITED = "API_RATE_LIMITED"
    API_AUTH_FAILED = "API_AUTH_FAILED"
    API_TIMEOUT = "API_TIMEOUT"

    # Data errors
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    DATA_INVALID = "DATA_INVALID"
    DATA_PARSE_ERROR = "DATA_PARSE_ERROR"

    # Agent errors
    AGENT_TASK_FAILED = "AGENT_TASK_FAILED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_CONTEXT_MISSING = "AGENT_CONTEXT_MISSING"

    # External service errors
    GSC_ERROR = "GSC_ERROR"
    SERP_ERROR = "SERP_ERROR"
    OPENAI_ERROR = "OPENAI_ERROR"
    COSMOS_ERROR = "COSMOS_ERROR"

    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class SEOAgentError(Exception):
    """Base exception for SEO Agent."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": True,
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(SEOAgentError):
    """Configuration-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, ErrorCode.CONFIG_MISSING, details)


class APIError(SEOAgentError):
    """External API-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.API_UNAVAILABLE,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message, code, details, cause)


class RateLimitError(APIError):
    """Rate limit exceeded."""

    def __init__(self, service: str, retry_after: int | None = None):
        super().__init__(
            f"Rate limit exceeded for {service}",
            ErrorCode.API_RATE_LIMITED,
            {"service": service, "retry_after": retry_after},
        )
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Authentication failed."""

    def __init__(self, service: str, details: dict[str, Any] | None = None):
        super().__init__(
            f"Authentication failed for {service}",
            ErrorCode.API_AUTH_FAILED,
            {"service": service, **(details or {})},
        )


class DataError(SEOAgentError):
    """Data-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.DATA_INVALID,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, code, details)


class AgentError(SEOAgentError):
    """Agent execution errors."""

    def __init__(
        self,
        message: str,
        agent_type: str,
        task_type: str | None = None,
        code: ErrorCode = ErrorCode.AGENT_TASK_FAILED,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(
            message,
            code,
            {"agent_type": agent_type, "task_type": task_type, **(details or {})},
            cause,
        )
        self.agent_type = agent_type
        self.task_type = task_type


def handle_api_error(func):
    """Decorator to handle common API errors with retry logic."""
    import asyncio
    import functools
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
    )

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except RateLimitError:
            raise  # Let caller handle rate limits
        except AuthenticationError:
            raise  # Let caller handle auth errors
        except Exception as e:
            # Wrap unknown exceptions
            raise APIError(
                f"API call failed: {str(e)}",
                ErrorCode.API_UNAVAILABLE,
                cause=e,
            ) from e

    return wrapper


def safe_execute(default_return: Any = None):
    """Decorator to safely execute functions and return default on error."""
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning(
                    "Safe execute caught exception",
                    function=func.__name__,
                    error=str(e),
                )
                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning(
                    "Safe execute caught exception",
                    function=func.__name__,
                    error=str(e),
                )
                return default_return

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


import asyncio
