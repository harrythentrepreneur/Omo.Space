# core/utils/retry.py
import time
import random
from functools import wraps
from typing import Callable, Type, Tuple
from app.core.config.logger import logger
import asyncio

class RetryExhaustedError(Exception):
    pass

def retry(
    exceptions: Tuple[Type[Exception]] = (Exception,),
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    log_retries: bool = True,
    exclude: Tuple[Type[Exception], ...] = (),
):
    """
    Decorator for retrying a function with exponential backoff and jitter.

    Args:
        exceptions: Exception types to catch (default: Exception)
        max_retries: Maximum number of retries (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 10.0)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter to delays (default: True)
        log_retries: Whether to log retry attempts (default: True)
        exclude: Exception types to NOT retry — re-raised immediately (default: ())
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            retry_count = 0
            delay = initial_delay

            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if exclude and isinstance(e, exclude):
                        raise  # Non-retryable — bubble up immediately
                    retry_count += 1
                    
                    if retry_count > max_retries:
                        error_msg = f"Max retries ({max_retries}) exceeded for {func.__name__}"
                        if log_retries:
                            logger.error(error_msg)
                        raise RetryExhaustedError(error_msg) from e
                    
                    # Calculate next delay with backoff and jitter
                    next_delay = min(delay * (backoff_factor ** (retry_count - 1)), max_delay)
                    if jitter:
                        next_delay = random.uniform(0.5 * next_delay, 1.5 * next_delay)
                    
                    if log_retries:
                        logger.warning(
                            f"Retry {retry_count}/{max_retries} for {func.__name__} "
                            f"after exception: {str(e)}. Waiting {next_delay:.2f}s"
                        )
                    
                    await asyncio.sleep(next_delay)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            retry_count = 0
            delay = initial_delay

            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if exclude and isinstance(e, exclude):
                        raise  # Non-retryable — bubble up immediately
                    retry_count += 1
                    
                    if retry_count > max_retries:
                        error_msg = f"Max retries ({max_retries}) exceeded for {func.__name__}"
                        if log_retries:
                            logger.error(error_msg)
                        raise RetryExhaustedError(error_msg) from e
                    
                    # Calculate next delay with backoff and jitter
                    next_delay = min(delay * (backoff_factor ** (retry_count - 1)), max_delay)
                    if jitter:
                        next_delay = random.uniform(0.5 * next_delay, 1.5 * next_delay)
                    
                    if log_retries:
                        logger.warning(
                            f"Retry {retry_count}/{max_retries} for {func.__name__} "
                            f"after exception: {str(e)}. Waiting {next_delay:.2f}s"
                        )
                    
                    time.sleep(next_delay)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator