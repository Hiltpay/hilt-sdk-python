from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import time
from typing import Any, Awaitable, Callable, Optional

from .errors import HILT_ERROR_CODES, HiltError

JSONDict = dict[str, Any]
WebhookHandler = Callable[[JSONDict], Any | Awaitable[Any]]


def _raw_body_text(raw_body: str | bytes | bytearray | memoryview) -> str:
    if isinstance(raw_body, str):
        return raw_body
    return bytes(raw_body).decode("utf-8")


def _parse_signature_header(signature_header: Optional[str]) -> dict[str, str]:
    parts: dict[str, str] = {}
    for chunk in (signature_header or "").split(","):
        item = chunk.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key:
            parts[key] = value
    return parts


def verify_webhook_signature(
    raw_body: str | bytes | bytearray | memoryview,
    signature_header: Optional[str],
    signing_secret: str,
    *,
    tolerance_seconds: int = 300,
    now: Optional[float] = None,
) -> None:
    parts = _parse_signature_header(signature_header)
    received = parts.get("v1")
    try:
        timestamp = int(parts.get("t", ""))
    except ValueError as exc:
        raise HiltError(
            "Malformed Hilt webhook signature header.",
            code=HILT_ERROR_CODES["webhook_signature_failed"],
            status_code=400,
            docs_url="https://docs.hilt.so/developers/webhooks#signature-verification",
        ) from exc

    if not received:
        raise HiltError(
            "Malformed Hilt webhook signature header.",
            code=HILT_ERROR_CODES["webhook_signature_failed"],
            status_code=400,
            docs_url="https://docs.hilt.so/developers/webhooks#signature-verification",
        )

    current_time = int(now if now is not None else time.time())
    if tolerance_seconds > 0 and abs(current_time - timestamp) > tolerance_seconds:
        raise HiltError(
            "Stale Hilt webhook signature timestamp.",
            code=HILT_ERROR_CODES["webhook_signature_failed"],
            status_code=400,
            docs_url="https://docs.hilt.so/developers/webhooks#signature-verification",
        )

    body = _raw_body_text(raw_body)
    expected = hmac.new(
        signing_secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise HiltError(
            "Invalid Hilt webhook signature.",
            code=HILT_ERROR_CODES["webhook_signature_failed"],
            status_code=400,
            docs_url="https://docs.hilt.so/developers/webhooks#signature-verification",
        )


def construct_webhook_event(
    raw_body: str | bytes | bytearray | memoryview,
    signature_header: Optional[str],
    signing_secret: str,
    *,
    tolerance_seconds: int = 300,
    now: Optional[float] = None,
) -> JSONDict:
    verify_webhook_signature(
        raw_body,
        signature_header,
        signing_secret,
        tolerance_seconds=tolerance_seconds,
        now=now,
    )
    try:
        event = json.loads(_raw_body_text(raw_body))
    except json.JSONDecodeError as exc:
        raise HiltError(
            "Hilt webhook payload was not valid JSON.",
            code="invalid_webhook_payload",
            status_code=400,
            docs_url="https://docs.hilt.so/developers/webhooks#payload-shape",
            body=_raw_body_text(raw_body),
        ) from exc
    if not isinstance(event, dict):
        raise HiltError(
            "Hilt webhook payload must be a JSON object.",
            code="invalid_webhook_payload",
            status_code=400,
            docs_url="https://docs.hilt.so/developers/webhooks#payload-shape",
            body=event,
        )
    return event


class HiltWebhookRouter:
    def __init__(self) -> None:
        self._handlers: dict[str, list[WebhookHandler]] = {}

    def on(
        self,
        event_type: str,
        handler: Optional[WebhookHandler] = None,
    ) -> WebhookHandler | Callable[[WebhookHandler], WebhookHandler]:
        def register(inner: WebhookHandler) -> WebhookHandler:
            self._handlers.setdefault(event_type, []).append(inner)
            return inner

        if handler is None:
            return register
        return register(handler)

    async def dispatch(self, event: JSONDict) -> None:
        event_type = str(event.get("type") or event.get("event_type") or "")
        handlers = [*self._handlers.get(event_type, []), *self._handlers.get("*", [])]
        for handler in handlers:
            result = handler(event)
            if inspect.isawaitable(result):
                await result


def create_webhook_router() -> HiltWebhookRouter:
    return HiltWebhookRouter()

