"""Small x402 V2 wire helpers for Hilt Pay API clients."""

from __future__ import annotations

import base64
import json
from typing import Any, Mapping


PAYMENT_REQUIRED_HEADER = "PAYMENT-REQUIRED"
PAYMENT_SIGNATURE_HEADER = "PAYMENT-SIGNATURE"
PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"
HILT_EXACT_SCHEME = "hilt-exact"
SOLANA_MAINNET_CAIP2 = "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def encode_x402_header(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def decode_x402_header(value: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(str(value or "").strip() + ("=" * (-len(str(value or "").strip()) % 4)))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("x402 header must contain base64-encoded JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("x402 header JSON must be an object")
    return payload


def get_hilt_payment_session_id(payment_signature: str) -> str:
    payload = decode_x402_header(payment_signature)
    accepted = payload.get("accepted")
    extra = accepted.get("extra") if isinstance(accepted, dict) else None
    hilt = extra.get("hilt") if isinstance(extra, dict) else None
    payment_session_id = hilt.get("paymentSessionId") if isinstance(hilt, dict) else None
    if not isinstance(payment_session_id, str) or not payment_session_id.strip():
        raise ValueError("PAYMENT-SIGNATURE is not bound to a Hilt payment session")
    return payment_session_id.strip()


def _positive_amount(value: Any, field: str) -> int:
    text = str(value or "")
    if not text.isdigit() or text.startswith("0"):
        raise ValueError(f"{field} must be a positive integer string")
    return int(text)


def get_hilt_exact_transfers(acceptance: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected = dict(acceptance)
    if selected.get("scheme") != HILT_EXACT_SCHEME:
        raise ValueError("acceptance must use hilt-exact")
    if selected.get("network") != SOLANA_MAINNET_CAIP2 or selected.get("asset") != SOLANA_USDC_MINT:
        raise ValueError("hilt-exact currently supports Solana USDC on mainnet")
    extra = selected.get("extra")
    hilt = extra.get("hilt") if isinstance(extra, dict) else None
    transfers = hilt.get("atomicTransfers") if isinstance(hilt, dict) else None
    if not isinstance(transfers, list) or len(transfers) != 2 or not all(isinstance(item, dict) for item in transfers):
        raise ValueError("hilt-exact requires one merchant transfer and one Hilt fee transfer")
    roles = {item.get("role") for item in transfers}
    if roles != {"merchant", "hilt_fee"}:
        raise ValueError("hilt-exact transfer roles are invalid")
    total = sum(_positive_amount(item.get("amount"), f"{item.get('role')} amount") for item in transfers)
    if total != _positive_amount(selected.get("amount"), "acceptance amount"):
        raise ValueError("hilt-exact transfer amounts do not equal the advertised amount")
    merchant = next(item for item in transfers if item.get("role") == "merchant")
    if merchant.get("payTo") != selected.get("payTo"):
        raise ValueError("merchant transfer does not match acceptance.payTo")
    if any(item.get("asset") != SOLANA_USDC_MINT for item in transfers):
        raise ValueError("every hilt-exact transfer must use Solana USDC")
    return [dict(item) for item in transfers]


def create_payment_signature(
    payment_required: Mapping[str, Any],
    *,
    signed_transaction_base64: str,
) -> str:
    requirement = dict(payment_required)
    accepts = requirement.get("accepts")
    resource = requirement.get("resource")
    if requirement.get("x402Version") != 2:
        raise ValueError("payment_required must use x402Version 2")
    if not isinstance(accepts, list) or len(accepts) != 1 or not isinstance(accepts[0], dict):
        raise ValueError("payment_required must contain exactly one acceptance")
    if not isinstance(resource, dict) or not resource.get("url"):
        raise ValueError("payment_required must contain resource.url")
    if accepts[0].get("scheme") == HILT_EXACT_SCHEME:
        get_hilt_exact_transfers(accepts[0])
    transaction = str(signed_transaction_base64 or "").strip()
    if not transaction:
        raise ValueError("signed_transaction_base64 is required")
    try:
        base64.b64decode(transaction + ("=" * (-len(transaction) % 4)), validate=True)
    except ValueError as exc:
        raise ValueError("signed_transaction_base64 must be base64 encoded") from exc
    return encode_x402_header(
        {
            "x402Version": 2,
            "resource": resource,
            "accepted": accepts[0],
            "payload": {"transaction": transaction},
        }
    )
