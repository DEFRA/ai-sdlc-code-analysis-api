"""Error handling utilities for the code analyzer.

This module contains functions for consistent error handling and retry logic across
the code analyzer components.
"""

import logging
import time
from typing import Callable, Optional, TypeVar

# Type variable for generic return type
T = TypeVar("T")


def handle_operation(
    operation: Callable[..., T],
    error_message: str,
    logger: logging.Logger,
    *args,
    **kwargs,
) -> tuple[Optional[T], Optional[Exception]]:
    """Handle an operation with consistent error logging.

    Args:
        operation: Function to execute
        error_message: Message to log on error
        logger: Logger instance to use for logging
        *args: Arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation

    Returns:
        Tuple containing the result (or None on error) and the exception (or None on success)
    """
    try:
        result = operation(*args, **kwargs)
        return result, None
    except Exception as e:
        logger.error("%s: %s", error_message, str(e))
        logger.debug("Exception details:", exc_info=True)
        return None, e


def operation_with_retry(
    operation: Callable[..., T],
    retry_message: str,
    logger: logging.Logger,
    max_retries: int = 3,
    *args,
    **kwargs,
) -> T:
    """Execute an operation with retries.

    Args:
        operation: Function to execute
        retry_message: Message to log on retry
        logger: Logger instance to use for logging
        max_retries: Maximum number of retry attempts
        *args: Arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation

    Returns:
        Result of the operation

    Raises:
        RuntimeError: If all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                logger.warning(
                    "%s (attempt %s/%s): %s",
                    retry_message,
                    attempt + 1,
                    max_retries,
                    str(e),
                )
                time.sleep(2**attempt)  # Exponential backoff
            else:
                logger.error("All retry attempts failed: %s", str(e))

    if last_exception:
        error_msg = (
            f"Operation failed after {max_retries} attempts: {str(last_exception)}"
        )
        raise RuntimeError(error_msg) from last_exception
    # This should never happen, but just in case
    unknown_error_msg = (
        f"Operation failed after {max_retries} attempts for unknown reasons"
    )
    raise RuntimeError(unknown_error_msg)
