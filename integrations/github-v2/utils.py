import asyncio
import logging
import random
from typing import Any, AsyncGenerator, Callable, Optional

from .exceptions import GitHubRateLimitError, GitHubNotModified

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    **kwargs,
) -> Any:
    """Retries a function with exponential backoff on GitHubRateLimitError.

    Args:
        func: The async function to be retried.
        max_retries: Maximum number of retries before giving up.
        initial_delay: Initial delay between retries in seconds.
        backoff_factor: Factor by which the delay increases after each retry.
        jitter: Whether to add randomness to the delay to avoid thundering herd problem.
        *args, **kwargs: Arguments to pass to the function.

    Returns:
        The result of the function if successful.

    Raises:
        The last exception raised by the function if all retries fail.
    """
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except GitHubRateLimitError as e:
            wait_for = e.retry_after if e.retry_after is not None else delay

            if attempt == max_retries - 1:
                logger.error("Max retries reached. Giving up")
                raise

            logger.warning(f"Rate limit hit. Retrying in {wait_for:.2f} seconds...")

            await asyncio.sleep(delay + (random.uniform(0, 1) if jitter else 0))
            delay *= backoff_factor
        except GitHubNotModified:
            # No need to retry on 304 Not Modified, we would catch this in the invoker
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise


async def paginate(
    fetch_page: Callable[..., Any],
    *args,
    start_page: int = 1,
    per_page: int = 40,
    **kwargs,
) -> AsyncGenerator[Any, None]:
    """Asynchronously paginates through API results.

    Args:
        fetch_page: An async function that takes a page number and returns the page data.
        start_page: The page number to start from.
        end_page: The page number to end at (inclusive). If None, will continue until no more data.

    Yields:
        Each item from the paginated results.
    """
    page = start_page
    while True:
        data = await fetch_page(*args, per_page=per_page, page=page, **kwargs)

        if not data or getattr(data, "_not_modified", False):
            break

        if isinstance(data, list):
            for item in data:
                yield item

            if len(data) < per_page:
                break
        else:
            yield data
            break

        page += 1
