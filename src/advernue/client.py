from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from ._base import RETRY_STATUS, BaseClient
from ._generated.async_api import AsyncNamespaces
from ._generated.sync_api import Namespaces
from .errors import AdvernueError


class Advernue(BaseClient, Namespaces):
    """Synchronous client. `Advernue(api_key=...).campaigns.list()`."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        BaseClient.__init__(self, api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)
        Namespaces.__init__(self)
        self._http = httpx.Client(timeout=timeout, transport=transport)

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Dict[str, Any]] = None,
        body: Any = None,
        idempotency_key: Optional[str] = None,
        dry_run: bool = False,
    ) -> Any:
        kwargs = self._prepare(method, path, query, body, idempotency_key, dry_run)
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            try:
                resp = self._http.request(**kwargs)
            except httpx.TransportError as e:
                if last:
                    raise AdvernueError(str(e) or type(e).__name__, code="connection_error") from e
                time.sleep(self._delay(attempt, None))
                continue
            if resp.status_code in RETRY_STATUS and not last:
                time.sleep(self._delay(attempt, resp))
                continue
            return self._parse(resp)
        raise AssertionError("unreachable")

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Advernue":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncAdvernue(BaseClient, AsyncNamespaces):
    """Asynchronous client. `await AsyncAdvernue(api_key=...).campaigns.list()`."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        BaseClient.__init__(self, api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)
        AsyncNamespaces.__init__(self)
        self._http = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Dict[str, Any]] = None,
        body: Any = None,
        idempotency_key: Optional[str] = None,
        dry_run: bool = False,
    ) -> Any:
        kwargs = self._prepare(method, path, query, body, idempotency_key, dry_run)
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            try:
                resp = await self._http.request(**kwargs)
            except httpx.TransportError as e:
                if last:
                    raise AdvernueError(str(e) or type(e).__name__, code="connection_error") from e
                await asyncio.sleep(self._delay(attempt, None))
                continue
            if resp.status_code in RETRY_STATUS and not last:
                await asyncio.sleep(self._delay(attempt, resp))
                continue
            return self._parse(resp)
        raise AssertionError("unreachable")

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncAdvernue":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
