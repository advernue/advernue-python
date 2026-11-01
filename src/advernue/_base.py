from __future__ import annotations

import os
import random
import uuid
from typing import Any, Dict, Optional

import httpx

from .errors import AdvernueError

DEFAULT_BASE_URL = "https://api.advernue.com"
RETRY_STATUS = {429, 500, 502, 503, 504}
__version__ = "0.1.0"


class BaseClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        key = api_key or os.environ.get("ADVERNUE_API_KEY")
        if not key:
            raise ValueError("api_key is required (or set ADVERNUE_API_KEY)")
        self.api_key = key
        self.base_url = (base_url or os.environ.get("ADVERNUE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _prepare(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]],
        body: Any,
        idempotency_key: Optional[str],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Build httpx request kwargs. Writes always carry an idempotency key, reused on every retry."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": f"advernue-python/{__version__}",
        }
        params = {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in (query or {}).items() if v is not None}
        write = method != "GET"
        if write:
            headers["Idempotency-Key"] = idempotency_key or str(uuid.uuid4())
            if dry_run:
                params["dry_run"] = "true"
        kwargs: Dict[str, Any] = {"method": method, "url": self.base_url + path, "headers": headers, "params": params}
        if body is not None:
            kwargs["json"] = body
        return kwargs

    def _delay(self, attempt: int, response: Optional[httpx.Response]) -> float:
        if response is not None:
            try:
                return min(max(float(response.headers["retry-after"]), 0.0), 30.0)
            except (KeyError, ValueError):
                pass
        return min(0.5 * 2.0**attempt, 8.0) * (0.5 + random.random() / 2)

    @staticmethod
    def _parse(response: httpx.Response) -> Any:
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            raise AdvernueError.from_response(response.status_code, payload)
        if response.status_code == 204 or not response.content:
            return None
        ct = response.headers.get("content-type", "")
        if "json" in ct:
            return response.json()
        if ct.startswith("text/") or "javascript" in ct:
            return response.text
        return response.content
