# `hilt-sdk`

Official Python SDK for Hilt Pay Workspace and Hilt Pay API.

Source: `https://github.com/Hiltpay/hilt-sdk-python`

This SDK wraps the same public merchant routes documented on `docs.hilt.so`:

- products
- hosted checkout
- payments
- memberships
- receipts
- support
- webhooks
- Hilt Pay API apps, products, entitlements, setup manifests, and agent bootstrap

## Install

```bash
pip install hilt-sdk
```

Source and release history: `https://github.com/Hiltpay/hilt-sdk-python`

## Example

### Agent-first Hilt Pay API bootstrap

Public launch settlement is Solana USDC. The `payment_protocol: "x402"` field describes the protected-resource HTTP 402 flow.

```python
from hilt_sdk import HiltClient

public_client = HiltClient()

setup = public_client.pay_api.agent_bootstrap(
    {
        "agent_name": "Acme API Builder",
        "agent_platform": "cursor",
        "requested_use_case": "Protect /ai/pro with Hilt Pay API",
        "requested_permissions": ["access:read", "access:write", "access:webhooks"],
    }
)

public_client.pay_api.submit_agent_setup_manifest(
    setup["setup_intent"]["id"],
    {
        "setup_token": setup["setup_token"],
        "manifest": {
            "app": {"name": "Acme AI"},
            "product": {
                "external_product_id": "pro-api",
                "title": "Pro API access",
                "amount_minor_units": 79000000,
                "default_rail": "solana_usdc",
            },
            "payment_protocol": "x402",
            "settlement_rail": "solana_usdc",
            "protected_resource": {"url": "https://api.acme.test/ai/pro"},
        },
    },
)
```

### Merchant workspace product

```python
from hilt_sdk import HiltClient

client = HiltClient(api_key="hk_live_...")

product = client.products.create(
    {
        "product_type": "PAYMENT_LINK",
        "title": "Members lounge",
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
            "renewal_mode": "MANUAL",
            "billing_interval_days": 30,
            "grace_period_days": 3,
        },
    }
)

print(product["id"], product["slug"])
```

## Quick start

1. Launch one real product in the Hilt app first.
2. Create an API key for backend automation.
3. Use the SDK to read or create the same product from your own system.
4. Switch longer-running automation to Hilt webhooks.
5. Use one tiny live payment before real traffic.

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
