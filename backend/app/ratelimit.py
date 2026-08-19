from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("rate limit exceeded")


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> None:
    """Sliding-window limiter.

    In-memory and therefore per-process. For multi-worker/multi-node
    deployments back this with Redis; the interface stays the same.
    Raises RateLimitExceeded when the caller is over the limit.
    """
    if limit <= 0:
        return
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            raise RateLimitExceeded(retry_after)
        bucket.append(now)


def reset() -> None:
    """Testing helper to clear all buckets."""
    with _lock:
        _buckets.clear()
