# `hilt-sdk`

Official Python SDK for Hilt Pay Workspace and Hilt Pay API.

Source: `https://github.com/Hiltpay/hilt-sdk-python`

Agent discovery contract:

- Agent manifest: `https://www.hilt.so/.well-known/hilt-agent.json`
- Agent Discovery Standard: `https://docs.hilt.so/developers/agent-discovery-standard`
- OpenAPI: `https://api.hilt.so/v1/openapi.json`

This SDK wraps the same public merchant routes documented on `docs.hilt.so`:

- products
- hosted checkout
- payments
- memberships
- receipts
- support
- webhooks
- Hilt Pay API apps, products, entitlements, setup manifests, and agent bootstrap
- native subscription state and cancellation helpers

## Install

```bash
pip install hilt-sdk
```

Source and release history: `https://github.com/Hiltpay/hilt-sdk-python`

## Example

### Agent-first Hilt Pay API bootstrap

Current public live settlement is Solana USDC. The `payment_protocol: "x402"` field describes the protected-resource HTTP 402 flow.

```python
from hilt_sdk import HiltClient

public_client = HiltClient()

setup = public_client.pay_api.agent_bootstrap(
    {
        "agent_name": "Acme API Builder",
        "agent_platform": "cursor",
        "requested_use_case": "Protect /ai/pro with Hilt Pay API",
        "contact_email": "founder@acme.test",
        "requested_permissions": ["access:read", "access:write", "access:webhooks"],
    }
)

manifest = public_client.pay_api.submit_agent_setup_manifest(
    setup["setup_intent_id"],
    {
        "setup_token": setup["setup_token"],
        "manifest": {
            "app": {"name": "Acme AI"},
            "product": {
                "external_product_id": "pro-api",
                "title": "Pro API access",
                "amount_minor_units": 79000000,
                "default_rail": "solana_usdc",
                "billing_model": "recurring",
                "renewal_mode": "solana_native_subscription",
                "billing_interval_days": 30,
                "cancel_at_period_end": True,
                "expected_monthly_payments": 120,
                "expected_monthly_volume_usd": 9480,
            },
            "payment_protocol": "x402",
            "settlement_rail": "solana_usdc",
            "protected_resource": {
                "url": "https://api.acme.test/ai/pro",
                "method": "POST",
                "customer_identity": "external_customer_id",
            },
            "webhook": {
                "url": "https://api.acme.test/webhooks/hilt",
                "subscribed_events": ["access.entitlement.activated", "payment.confirmed"],
            },
        },
    },
)

print(manifest["pricing_recommendation"]["recommended_plan"])  # starter, growth, or scale
print(setup["owner_approval_url"])  # send the owner here for the one-minute approval step
```

### Check access before serving a resource

Use this in every API route, middleware, worker, or tool call that needs to know whether a customer has access right now.

```python
import os

from fastapi import FastAPI, Header, HTTPException
from hilt_sdk import HiltClient

app = FastAPI()
client = HiltClient(api_key=os.environ["HILT_API_KEY"])


@app.post("/ai/pro")
async def pro_ai(x_customer_id: str = Header(...)):
    access = client.pay_api.check_entitlement(
        {
            "external_product_id": "pro-api",
            "external_customer_id": x_customer_id,
        }
    )

    if not access["has_access"]:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "payment_required",
                "status": access["status"],
                "reason": access["reason"],
                "external_product_id": access["external_product_id"],
            },
        )

    return {"ok": True}
```

### Merchant workspace product

```python
from hilt_sdk import HiltClient

client = HiltClient(api_key="hk_live_...")

product = client.products.create(
    {
        "product_type": "PAYMENT_LINK",
        "title": "30-day members lounge",
        "amount_minor_units": 200000,
        "token_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "merchant_wallet": "So1anaMerchantWallet1111111111111111111111111",
        "delivery_type": "REDIRECT",
        "delivery_value": "https://example.com/welcome",
        "membership_config": {
            "enabled": True,
            "platform": "CUSTOM",
            "identity_type": "WALLET",
            "identity_required": False,
            "renewal_mode": "ONE_OFF",
            "billing_interval_days": 30,
            "grace_period_days": 3,
        },
    }
)

print(product["id"], product["slug"])
```

### Native subscription state and cancellation

```python
subscription = client.pay_api.get_native_subscription("AUTHORIZATION_ID")

cancel_intent = client.pay_api.create_native_subscription_cancel_intent(
    "AUTHORIZATION_ID",
    {
        "reason": "buyer_requested",
        "cancel_at_period_end": True,
    },
)

cancelled = client.pay_api.confirm_native_subscription_cancel(
    "AUTHORIZATION_ID",
    {
        "cancel_tx_signature": "SOLANA_CANCEL_TRANSACTION_SIGNATURE",
        "reason": "buyer_requested",
        "immediate_revoke": False,
    },
    idempotency_key="native-cancel-AUTHORIZATION_ID-001",
)

print(subscription["status"], cancel_intent["status"], cancelled["status"])
```

### Sandbox session helpers

```python
sandbox = client.pay_api.create_sandbox_payment_session(
    {
        "external_product_id": "pro-api",
        "external_customer_id": "cust_123",
        "rail": "solana_usdc",
        "confirm_sandbox_mode": True,
    },
    idempotency_key="sandbox-session-cust-123-pro-api-001",
)

confirmed = client.pay_api.confirm_sandbox_payment_session(
    sandbox["payment_session"]["id"],
    {"proof": "sandbox-confirmed-access"},
    idempotency_key="sandbox-confirm-cust-123-pro-api-001",
)

print(confirmed["entitlement"])
```

### Webhook verification and routing

```python
from hilt_sdk import construct_webhook_event, create_webhook_router

router = create_webhook_router()


@router.on("payment.confirmed")
async def grant_access(event):
    await sync_access(event["data"])


async def hilt_webhook(request):
    raw_body = await request.body()
    event = construct_webhook_event(
        raw_body,
        request.headers.get("X-Hilt-Signature"),
        HILT_WEBHOOK_SECRET,
    )
    await router.dispatch(event)
    return {"ok": True}
```

Hilt signs `<timestamp>.<raw_json_body>` and sends the signature as `X-Hilt-Signature: t=<unix_timestamp>,v1=<hex_hmac_sha256>`.

### Error handling

```python
from hilt_sdk import HiltApiError

try:
    client.pay_api.create_payment_session(body, idempotency_key="session-001")
except HiltApiError as exc:
    print(exc.code, exc.status_code, exc.request_id, exc.retryable, exc.docs_url)
```

`HiltApiError` includes the public error code, HTTP status, Hilt request id when available, retryability, docs URL, and safe response details.

The error catalog lives at `https://docs.hilt.so/developers/errors`. SDK `docs_url` values point to anchors such as `#payment-failed`, `#idempotency-in-progress`, and `#request-timeout`.

### Subscription helper boundary

The SDK exposes the current public native subscription routes: read an authorization, create a cancellation intent, and confirm the signed cancellation. Public endpoints for list, pause, resume, or browser-safe customer management sessions are not exposed yet, so the SDK does not fake those methods. Build recurring access today with a recurring product, a payment session, signed webhooks, and entitlement checks.

Proposed backend contract for future high-level subscription helpers:

```text
POST /v1/access/subscriptions
GET  /v1/access/subscriptions/{subscription_id}
GET  /v1/access/subscriptions
POST /v1/access/subscriptions/{subscription_id}/pause
POST /v1/access/subscriptions/{subscription_id}/resume
POST /v1/access/subscriptions/{subscription_id}/cancel
POST /v1/access/customer-sessions
POST /v1/access/sandbox/subscriptions/{subscription_id}/advance-period
```

The browser-facing contract should return only a short-lived customer token or hosted management URL. It must never expose a Hilt API key in browser code.

## Quick start

1. Create or approve a Hilt Pay API setup intent.
2. Use the SDK to create an app, product, payment session, and webhook.
3. Use sandbox sessions to validate object handling without live money.
4. Use entitlement checks before serving paid work.
5. For recurring access, create products with `billing_model: "recurring"` and `renewal_mode: "solana_native_subscription"`.

## Auth surfaces

For most merchant routes, configure either:

- `api_key` for server-to-server merchant automation
- `bearer_token` for dashboard-session tooling

Webhook endpoint management currently requires a dashboard session token, so the webhook resource uses the configured `bearer_token`.

## What the SDK is best at

- products and hosted checkout
- payment confirmation and reads
- membership lookup, renewal intelligence, and recovery
- receipt proof, PDF access, and proof sending
- support tickets and webhook endpoint operations

## Build from source

```bash
python setup.py sdist bdist_wheel
```
