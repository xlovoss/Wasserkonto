"""A deliberately polite HTTP client.

These services are public infrastructure with no rate limit and no API key.
That is an invitation to be careful, not to hammer them: one impolite scraper
is how open endpoints end up behind a login. Hence a per-host minimum interval,
bounded retries with exponential backoff, and an honest User-Agent.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import requests

from .config import HttpConfig

log = logging.getLogger(__name__)

# Worth retrying: the server is busy or briefly broken, not refusing us.
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class FetchError(RuntimeError):
    """A fetch that failed in a way the caller should log and move past.

    One unreachable station must never abort a collection run -- the archive's
    whole point is to capture what it can, every day, unattended.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(slots=True)
class Response:
    url: str
    status: int
    body: bytes


class PoliteSession:
    def __init__(self, config: HttpConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers["User-Agent"] = config.user_agent
        self._session.headers["Accept-Encoding"] = "gzip, deflate"
        self._last_request: dict[str, float] = {}

    def _wait_for_host(self, url: str) -> None:
        host = urlsplit(url).netloc
        last = self._last_request.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            remaining = self._config.min_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_request[host] = time.monotonic()

    def get(self, url: str, params: dict[str, Any] | None = None) -> Response:
        last_error: Exception | None = None

        for attempt in range(1, self._config.max_retries + 1):
            self._wait_for_host(url)
            try:
                resp = self._session.get(
                    url, params=params, timeout=self._config.timeout_seconds
                )
            except requests.RequestException as exc:
                last_error = exc
                log.warning("attempt %d/%d failed for %s: %s",
                            attempt, self._config.max_retries, url, exc)
            else:
                if resp.status_code in RETRY_STATUS:
                    last_error = FetchError(
                        f"HTTP {resp.status_code} from {resp.url}",
                        status=resp.status_code,
                    )
                    log.warning("attempt %d/%d got HTTP %d for %s",
                                attempt, self._config.max_retries,
                                resp.status_code, resp.url)
                elif not resp.ok:
                    # 4xx other than 429: retrying will not help.
                    raise FetchError(
                        f"HTTP {resp.status_code} from {resp.url}",
                        status=resp.status_code,
                    )
                else:
                    return Response(
                        url=resp.url, status=resp.status_code, body=resp.content
                    )

            if attempt < self._config.max_retries:
                time.sleep(min(2.0 ** attempt, 30.0))

        raise FetchError(f"giving up on {url} after "
                         f"{self._config.max_retries} attempts: {last_error}")

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> PoliteSession:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
