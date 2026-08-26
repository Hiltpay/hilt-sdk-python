import unittest

from hilt_sdk import (
    HiltApiError,
    PAYMENT_REQUIRED_HEADER,
    PAYMENT_RESPONSE_HEADER,
    encode_x402_header,
    protect_request,
)


class FakePayApi:
    def __init__(self, *, consume=None):
        self.consume = consume
        self.calls = []

    def consume_entitlement(self, body, *, idempotency_key):
        self.calls.append(("consume", body, idempotency_key))
        if isinstance(self.consume, Exception):
            raise self.consume
        return self.consume or {
            "consumed": True,
            "units": 1,
            "usage": {"unit": "request", "granted": 10, "consumed": 1, "remaining": 9},
            "entitlement": {"id": "ent-1"},
        }

    def create_payment_session(self, body, *, idempotency_key):
        self.calls.append(("session", body, idempotency_key))
        return {
            "payment_session": {
                "payment_requirement": {
                    "headers": {PAYMENT_REQUIRED_HEADER: "encoded-requirement"}
                }
            }
        }

    def settle_x402(self, body, *, idempotency_key):
        self.calls.append(("settle", body, idempotency_key))
        return {"headers": {PAYMENT_RESPONSE_HEADER: "encoded-response"}}


class FakeClient:
    def __init__(self, pay_api):
        self.pay_api = pay_api


def payment_signature():
    return encode_x402_header(
        {
            "x402Version": 2,
            "resource": {"url": "https://merchant.test/research"},
            "accepted": {"extra": {"hilt": {"paymentSessionId": "session-1"}}},
            "payload": {"transaction": "signed"},
        }
    )


class ProtectRequestTests(unittest.TestCase):
    def test_allows_only_after_atomic_consumption(self):
        pay_api = FakePayApi()
        result = protect_request(
            client=FakeClient(pay_api),
            external_product_id="research-calls",
            customer_id="agent-42",
            request_id="request-0001",
            resource_url="https://merchant.test/research",
        )

        self.assertTrue(result.allowed)
        self.assertEqual([call[0] for call in pay_api.calls], ["consume"])

    def test_returns_payment_requirement_without_allowing_work(self):
        pay_api = FakePayApi(
            consume=HiltApiError(409, "Payment required", "usage_balance_insufficient")
        )
        result = protect_request(
            client=FakeClient(pay_api),
            external_product_id="research-calls",
            customer_id="agent-42",
            request_id="request-0001",
            resource_url="https://merchant.test/research",
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.status_code, 402)
        self.assertEqual(result.headers[PAYMENT_REQUIRED_HEADER], "encoded-requirement")
        self.assertEqual([call[0] for call in pay_api.calls], ["consume", "session"])

    def test_never_creates_second_payment_after_settlement(self):
        pay_api = FakePayApi(
            consume=HiltApiError(409, "Retry", "entitlement_not_active")
        )
        result = protect_request(
            client=FakeClient(pay_api),
            external_product_id="research-calls",
            customer_id="agent-42",
            request_id="request-0001",
            resource_url="https://merchant.test/research",
            payment_signature=payment_signature(),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.status_code, 409)
        self.assertEqual([call[0] for call in pay_api.calls], ["settle", "consume"])
        self.assertEqual(result.headers[PAYMENT_RESPONSE_HEADER], "encoded-response")


if __name__ == "__main__":
    unittest.main()
