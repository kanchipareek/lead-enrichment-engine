"""Retry transient failures with bounded backoff, and a simple rate limiter."""
import time
import urllib.error

TRANSIENT = (urllib.error.URLError, TimeoutError, ConnectionError)


def with_retry(fn, tries=3, base=1.0):
    """Call fn(); on a transient error, retry with 1s, 2s, 4s... then raise."""
    last = None
    for i in range(tries):
        try:
            return fn()
        except TRANSIENT as e:
            last = e
            if i < tries - 1:
                time.sleep(base * (2 ** i))
    raise last


class RateLimiter:
    """Keep requests at least `delay` seconds apart."""

    def __init__(self, delay):
        self.delay = delay
        self._last = 0.0

    def wait(self):
        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.monotonic()
