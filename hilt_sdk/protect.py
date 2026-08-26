"""Framework-neutral Hilt Pay API metered request protection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .client import HiltClient
from .errors import HiltApiError
from .x402 import (
    PAYMENT_REQUIRED_HEADER,
    PAYMENT_RESPONSE_HEADER,
    get_hilt_payment_session_id,
)


_PAYMENT_REQUIRED_CODES = {
    "entitlement_not_found",
    "entitlement_not_active",
    "usage_balance_insufficient",
}


@dataclass(frozen=True)
class ProtectedRequestResult:
    allowed: bool
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] = field(default_factory=dict)
    usage: Optional[dict[str, Any]] = None
    settlement: Optional[dict[str, Any]] = None


def _requires_payment(error: Exception) -> bool:
    return (
        isinstance(error, HiltApiError)
        and error.status_code in {404, 409}
        and error.error_code in _PAYMENT_REQUIRED_CODES
    )


def _payment_required_header(payment_requirement: Any) -> str:
    if not isinstance(payment_requirement, dict):
        raise RuntimeError("Hilt did not return an x402 payment requirement")
    headers = payment_requirement.get("headers")
    value = headers.get(PAYMENT_REQUIRED_HEADER) if isinstance(headers, dict) else None
    if not isinstance(value, str) or not value:
        raise RuntimeError("Hilt payment requirement did not contain PAYMENT-REQUIRED")
    return value


def protect_request(
    *,
    client: HiltClient,
    external_product_id: str,
    customer_id: str,
    request_id: str,
    resource_url: str,
    payment_signature: Optional[str] = None,
    units: int = 1,
    resource_description: str = "Paid endpoint request",
    resource_mime_type: str = "application/json",
    metadata: Optional[Mapping[str, Any]] = None,
) -> ProtectedRequestResult:
    """Authorize one metered request before the application serves billable work."""

    product = external_product_id.strip()
    customer = customer_id.strip()
    attempt = request_id.strip()
    if not product or not customer:
        return ProtectedRequestResult(
            allowed=False,
            status_code=400,
            body={"error": "request_identity_required"},
        )
    if len(attempt) < 8 or len(attempt) > 240:
        return ProtectedRequestResult(
            allowed=False,
            status_code=400,
            body={
                "error": "request_id_invalid",
                "message": "The request ID must contain 8 to 240 characters for retry-safe processing.",
            },
        )
    if not isinstance(units, int) or units < 1:
        raise ValueError("units must be a positive integer")

    settlement: Optional[dict[str, Any]] = None
    if payment_signature:
        try:
            payment_session_id = get_hilt_payment_session_id(payment_signature)
        except ValueError:
            return ProtectedRequestResult(
                allowed=False,
                status_code=400,
                body={
                    "error": "payment_signature_invalid",
                    "message": "PAYMENT-SIGNATURE is not a Hilt-bound x402 payment payload.",
                },
            )
        settlement = client.pay_api.settle_x402(
            {
                "payment_session_id": payment_session_id,
                "payment_signature": payment_signature,
            },
            idempotency_key=f"settle-{attempt}",
        )

    try:
        usage = client.pay_api.consume_entitlement(
            {
                "external_product_id": product,
                "external_customer_id": customer,
                "units": units,
                "metadata": {"request_id": attempt},
            },
            idempotency_key=f"consume-{attempt}",
        )
    except HiltApiError as error:
        if not _requires_payment(error):
            raise
        if settlement is not None:
            payment_response = settlement.get("headers", {}).get(PAYMENT_RESPONSE_HEADER)
            headers = {"X-Hilt-Request-Id": attempt}
            if isinstance(payment_response, str) and payment_response:
                headers[PAYMENT_RESPONSE_HEADER] = payment_response
            return ProtectedRequestResult(
                allowed=False,
                status_code=409,
                headers=headers,
                body={
                    "error": "usage_not_ready",
                    "message": "Payment settled, but usage is not ready. Retry with the same request ID and PAYMENT-SIGNATURE.",
                    "request_id": attempt,
                },
                settlement=settlement,
            )

        configured_metadata = dict(metadata or {})
        configured_metadata.update(
            {
                "resource": resource_url,
                "description": resource_description,
                "mime_type": resource_mime_type,
            }
        )
        session = client.pay_api.create_payment_session(
            {
                "external_product_id": product,
                "external_customer_id": customer,
                "payment_protocol": "x402",
                "settlement_rail": "solana_usdc",
                "metadata": configured_metadata,
            },
            idempotency_key=f"payment-{attempt}",
        )
        payment_session = session.get("payment_session") or {}
        return ProtectedRequestResult(
            allowed=False,
            status_code=402,
            headers={
                PAYMENT_REQUIRED_HEADER: _payment_required_header(
                    payment_session.get("payment_requirement")
                ),
                "X-Hilt-Request-Id": attempt,
            },
            body={
                "error": "payment_required",
                "external_product_id": product,
                "request_id": attempt,
            },
        )

    if usage.get("consumed") is not True:
        raise RuntimeError("Hilt did not confirm atomic usage consumption")

    response_headers: dict[str, str] = {}
    if settlement is not None:
        payment_response = settlement.get("headers", {}).get(PAYMENT_RESPONSE_HEADER)
        if isinstance(payment_response, str) and payment_response:
            response_headers[PAYMENT_RESPONSE_HEADER] = payment_response
    return ProtectedRequestResult(
        allowed=True,
        status_code=200,
        headers=response_headers,
        body={"ok": True, "request_id": attempt},
        usage=usage,
        settlement=settlement,
    )
