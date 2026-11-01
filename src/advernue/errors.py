from __future__ import annotations

from typing import Any, Optional


class AdvernueError(Exception):
    """Raised for any non-2xx response, built from the `{error:{code,message,details}}` envelope."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: str = "unknown",
        details: Any = None,
    ) -> None:
        super().__init__(f"{code}: {message}" + (f" (HTTP {status_code})" if status_code else ""))
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details

    @classmethod
    def from_response(cls, status_code: int, payload: Any) -> "AdvernueError":
        err = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(err, dict):
            return cls(
                str(err.get("message", "request failed")),
                status_code=status_code,
                code=str(err.get("code", f"http_{status_code}")),
                details=err.get("details"),
            )
        return cls("request failed", status_code=status_code, code=f"http_{status_code}", details=payload)
