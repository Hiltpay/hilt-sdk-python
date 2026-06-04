from __future__ import annotations

from typing import Any, Optional

HILT_ERROR_CODES = {
    "payment_failed": "payment_failed",
    "subscription_expired": "subscription_expired",
    "invalid_authorization": "invalid_authorization",
    "webhook_signature_failed": "webhook_signature_failed",
    "invalid_idempotency_key": "invalid_idempotency_key",
    "idempotency_key_required": "idempotency_key_required",
    "idempotency_key_too_long": "idempotency_key_too_long",
    "idempotency_key_invalid": "idempotency_key_invalid",
    "idempotency_in_progress": "idempotency_in_progress",
    "idempotency_conflict": "idempotency_conflict",
    "idempotency_race": "idempotency_race",
    "rate_limited": "rate_limited",
    "setup_not_ready": "setup_not_ready",
    "entitlement_missing": "entitlement_missing",
    "subscription_cancelled": "subscription_cancelled",
    "subscription_requires_reapproval": "subscription_requires_reapproval",
    "request_timeout": "request_timeout",
}


class HiltError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        retryable: bool = False,
        docs_url: Optional[str] = None,
        body: Any = None,
        raw_response: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        self.retryable = retryable
        self.docs_url = docs_url
        self.body = body
        self.raw_response = raw_response


class HiltApiError(HiltError):
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Any = None,
        *,
        request_id: Optional[str] = None,
        retryable: bool = False,
        docs_url: Optional[str] = None,
        raw_response: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message,
            code=error_code,
            status_code=status_code,
            request_id=request_id,
            retryable=retryable,
            docs_url=docs_url,
            body=details,
            raw_response=raw_response,
        )
        self.error_code = error_code
        self.details = details
