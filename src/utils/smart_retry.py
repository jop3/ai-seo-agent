"""
Smart Retry with Jitter - Prevents thundering herd during retries.

When multiple requests fail and retry simultaneously, they can overwhelm
the server. Jitter adds random delays to spread out retry attempts.

Impact: Prevents overwhelming servers during recovery, smoother retries.
"""

import asyncio
import random
from typing import Any, Callable, Optional, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar('T')


async def retry_with_jitter(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter_factor: float = 0.3,
    exponential: bool = True,
    retryable_exceptions: Optional[tuple] = None,
) -> T:
    """
    Retry async function with exponential backoff and jitter.

    Args:
        func: Async function to retry
        max_attempts: Maximum retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter_factor: Jitter range (0.0-1.0, default 0.3 = ±30%)
        exponential: Use exponential backoff (2^n)
        retryable_exceptions: Tuple of exceptions to retry on (None = all)

    Returns:
        Result from func

    Example:
        result = await retry_with_jitter(
            lambda: fetch_url(url),
            max_attempts=3,
            base_delay=2.0,
            jitter_factor=0.3
        )

        # Retry delays with jitter:
        # Attempt 1 fails: wait 2.0 * (1 ± 0.3) = 1.4-2.6s
        # Attempt 2 fails: wait 4.0 * (1 ± 0.3) = 2.8-5.2s
        # Attempt 3 fails: wait 8.0 * (1 ± 0.3) = 5.6-10.4s
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            # Check if exception is retryable
            if retryable_exceptions and not isinstance(e, retryable_exceptions):
                logger.error(
                    "Non-retryable exception, not retrying",
                    exception=str(e),
                    exception_type=type(e).__name__,
                )
                raise

            # Don't retry on last attempt
            if attempt >= max_attempts:
                logger.error(
                    "Max retry attempts reached",
                    attempts=attempt,
                    exception=str(e),
                )
                raise

            # Calculate delay with jitter
            if exponential:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            else:
                delay = base_delay

            # Add jitter (random variation)
            jitter = delay * jitter_factor * (2 * random.random() - 1)
            final_delay = max(0, delay + jitter)

            logger.warning(
                "Retry attempt with jitter",
                attempt=attempt,
                max_attempts=max_attempts,
                delay_seconds=round(final_delay, 2),
                exception=str(e),
            )

            await asyncio.sleep(final_delay)

    # Should not reach here, but just in case
    raise last_exception


class SmartRetryPolicy:
    """
    Configurable retry policy with jitter.

    Usage:
        policy = SmartRetryPolicy(
            max_attempts=5,
            base_delay=1.0,
            jitter_factor=0.3
        )

        result = await policy.execute(fetch_url, url)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter_factor: float = 0.3,
        exponential: bool = True,
        retryable_exceptions: Optional[tuple] = None,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor
        self.exponential = exponential
        self.retryable_exceptions = retryable_exceptions

        self._stats = {
            "total_attempts": 0,
            "successful_first_try": 0,
            "retries_needed": 0,
            "total_failures": 0,
        }

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry policy.

        Args:
            func: Async function to execute
            *args: Positional arguments to func
            **kwargs: Keyword arguments to func

        Returns:
            Result from func
        """
        self._stats["total_attempts"] += 1

        attempt = 0
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)

                if attempt == 1:
                    self._stats["successful_first_try"] += 1
                else:
                    self._stats["retries_needed"] += 1

                return result

            except Exception as e:
                last_exception = e

                # Check if retryable
                if self.retryable_exceptions and not isinstance(e, self.retryable_exceptions):
                    self._stats["total_failures"] += 1
                    raise

                # Last attempt
                if attempt >= self.max_attempts:
                    self._stats["total_failures"] += 1
                    logger.error(
                        "Smart retry policy exhausted",
                        attempts=attempt,
                        exception=str(e),
                    )
                    raise

                # Calculate jittered delay
                delay = self._calculate_delay(attempt)

                logger.warning(
                    "Smart retry policy retrying",
                    attempt=attempt,
                    max_attempts=self.max_attempts,
                    delay_seconds=round(delay, 2),
                    exception=str(e),
                )

                await asyncio.sleep(delay)

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with jitter for given attempt."""
        if self.exponential:
            delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        else:
            delay = self.base_delay

        # Add jitter
        jitter = delay * self.jitter_factor * (2 * random.random() - 1)
        return max(0, delay + jitter)

    def get_stats(self) -> dict[str, Any]:
        """Get retry statistics."""
        total = self._stats["total_attempts"]

        return {
            "total_attempts": total,
            "successful_first_try": self._stats["successful_first_try"],
            "retries_needed": self._stats["retries_needed"],
            "total_failures": self._stats["total_failures"],
            "success_rate_percent": round(
                (total - self._stats["total_failures"]) / total * 100, 1
            ) if total > 0 else 0,
            "retry_rate_percent": round(
                self._stats["retries_needed"] / total * 100, 1
            ) if total > 0 else 0,
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = {
            "total_attempts": 0,
            "successful_first_try": 0,
            "retries_needed": 0,
            "total_failures": 0,
        }


# Global retry policy for common use
_global_retry_policy: Optional[SmartRetryPolicy] = None


def get_retry_policy() -> SmartRetryPolicy:
    """Get global retry policy instance."""
    global _global_retry_policy

    if _global_retry_policy is None:
        _global_retry_policy = SmartRetryPolicy(
            max_attempts=3,
            base_delay=2.0,
            jitter_factor=0.3,
        )

    return _global_retry_policy


# Convenience function
async def smart_retry(func: Callable, *args, **kwargs) -> Any:
    """
    Quick retry with global policy.

    Usage:
        result = await smart_retry(fetch_url, "https://example.com")
    """
    policy = get_retry_policy()
    return await policy.execute(func, *args, **kwargs)
