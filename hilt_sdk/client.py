from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlencode

import requests

JSONDict = Dict[str, Any]


class HiltApiError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


def _normalize_base_url(value: Optional[str]) -> str:
    candidate = (value or "https://api.hilt.so").strip().rstrip("/")
    return candidate or "https://api.hilt.so"


def _append_query(path: str, query: Optional[Mapping[str, Any]]) -> str:
    if not query:
        return path
    items: list[tuple[str, str]] = []
    for key, raw_value in query.items():
        if raw_value is None or raw_value == "":
            continue
        if isinstance(raw_value, (list, tuple)):
            for value in raw_value:
                items.append((key, str(value)))
            continue
        items.append((key, str(raw_value)))
    if not items:
        return path
    return f"{path}?{urlencode(items)}"


@dataclass(frozen=True)
class _AuthHeader:
    name: str
    value: str


class _ResourceBase:
    def __init__(self, client: "HiltClient") -> None:
        self._client = client


class ProductsResource(_ResourceBase):
    def create(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request("/v1/products", method="POST", body=body)

    def list(self) -> list[JSONDict]:
        return self._client.request("/v1/products")

    def get(self, product_id: str) -> JSONDict:
        return self._client.request(f"/v1/products/{product_id}")

    def update(self, product_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(f"/v1/products/{product_id}", method="PATCH", body=body)

    def archive(self, product_id: str) -> JSONDict:
        return self._client.request(f"/v1/products/{product_id}", method="DELETE")

    def list_payments(self, product_id: str, query: Optional[Mapping[str, Any]] = None) -> list[JSONDict]:
        return self._client.request(f"/v1/products/{product_id}/payments", query=query)

    def get_analytics(self, product_id: str) -> JSONDict:
        return self._client.request(f"/v1/products/{product_id}/analytics")

    def create_handoff_link(self, product_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(f"/v1/products/{product_id}/handoff-link", method="POST", body=body)


class CheckoutResource(_ResourceBase):
    def get_product(self, slug: str) -> JSONDict:
        return self._client.request(f"/v1/products/p/{slug}", auth="none")

    def connect(self, slug: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(f"/v1/products/p/{slug}/connect", method="POST", body=body, auth="none")

    def resolve_handoff(self, slug: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            f"/v1/products/p/{slug}/resolve-handoff",
            method="POST",
            body=body,
            auth="none",
        )

    def broadcast_payment(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request("/v1/pay/broadcast", method="POST", body=body, auth="none")

    def confirm_payment(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request("/v1/pay/confirm", method="POST", body=body, auth="none")


class PaymentsResource(_ResourceBase):
    def get(self, payment_id: str) -> JSONDict:
        return self._client.request(f"/v1/payments/{payment_id}", auth="none")


class MembershipsResource(_ResourceBase):
    def list(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/memberships", query=query)

    def lookup(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/memberships/lookup", query=query)

    def get_renewal_intelligence(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/memberships/renewal-intelligence", query=query)

    def get(self, membership_id: str) -> JSONDict:
        return self._client.request(f"/v1/memberships/{membership_id}")

    def update_notes(self, membership_id: str, notes: str) -> JSONDict:
        return self._client.request(
            f"/v1/memberships/{membership_id}/notes",
            method="PATCH",
            body={"notes": notes},
        )

    def update_profile(self, membership_id: str, platform_display: str) -> JSONDict:
        return self._client.request(
            f"/v1/memberships/{membership_id}/profile",
            method="PATCH",
            body={"platform_display": platform_display},
        )

    def gift(self, membership_id: str, days: int, note: str = "") -> JSONDict:
        return self._client.request(
            f"/v1/memberships/{membership_id}/gift",
            method="POST",
            body={"days": days, "note": note},
        )

    def retry_delivery(self, membership_id: str) -> JSONDict:
        return self._client.request(f"/v1/memberships/{membership_id}/retry-delivery", method="POST")

    def get_delivery_diagnostics(self, membership_id: str) -> JSONDict:
        return self._client.request(f"/v1/memberships/{membership_id}/delivery-diagnostics")

    def open_delivery_support_ticket(self, membership_id: str) -> JSONDict:
        return self._client.request(
            f"/v1/memberships/{membership_id}/delivery-support-ticket",
            method="POST",
        )

    def get_reactivation(self, membership_id: str) -> JSONDict:
        return self._client.request(f"/v1/memberships/{membership_id}/reactivation")


class ReceiptsResource(_ResourceBase):
    def create(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request("/v1/receipt", method="POST", body=body)

    def list(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/receipts", query=query)

    def get(self, receipt_id: str) -> JSONDict:
        return self._client.request(f"/v1/receipt/{receipt_id}")

    def get_public(self, receipt_id: str) -> JSONDict:
        return self._client.request(f"/v1/receipt/{receipt_id}/public", auth="none")

    def verify(self, receipt_id: str) -> JSONDict:
        return self._client.request(f"/v1/receipt/{receipt_id}/verify", auth="none")

    def get_pdf(self, receipt_id: str) -> bytes:
        return self._client.request(
            f"/v1/receipt/{receipt_id}/pdf",
            auth="none",
            response_type="content",
        )

    def update_invoice_metadata(self, receipt_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            f"/v1/receipt/{receipt_id}/invoice-metadata",
            method="PATCH",
            body=body,
        )

    def send_proof(self, receipt_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            f"/v1/receipt/{receipt_id}/send-proof",
            method="POST",
            body=body,
        )


class SupportResource(_ResourceBase):
    def create_ticket(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request("/v1/support/tickets", method="POST", body=body)

    def list_tickets(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/support/tickets", query=query)

    def get_ticket(self, ticket_id: str) -> JSONDict:
        return self._client.request(f"/v1/support/tickets/{ticket_id}")

    def add_message(self, ticket_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(f"/v1/support/tickets/{ticket_id}/message", method="POST", body=body)


class AccessResource(_ResourceBase):
    @staticmethod
    def _idempotency_headers(idempotency_key: str) -> dict[str, str]:
        normalized = str(idempotency_key or "").strip()
        if not normalized:
            raise ValueError("Hilt Pay API write calls require an idempotency key.")
        return {"Idempotency-Key": normalized}

    def list_rails(self) -> JSONDict:
        return self._client.request("/v1/access/rails")

    def agent_bootstrap(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            "/v1/access/agent-bootstrap",
            method="POST",
            body=body,
            auth="none",
        )

    def get_agent_setup_status(self, setup_intent_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            f"/v1/access/agent-bootstrap/{setup_intent_id}/status",
            method="POST",
            body=body,
            auth="none",
        )

    def submit_agent_setup_manifest(self, setup_intent_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            f"/v1/access/agent-bootstrap/{setup_intent_id}/manifest",
            method="POST",
            body=body,
            auth="none",
        )

    def approve_agent_setup(self, setup_intent_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            f"/v1/access/agent-bootstrap/{setup_intent_id}/approve",
            method="POST",
            body=body,
            auth="bearer",
        )

    def list_rail_settings(self) -> JSONDict:
        return self._client.request("/v1/access/rail-settings")

    def update_rail_setting(
        self,
        rail_id: str,
        body: Mapping[str, Any],
        *,
        idempotency_key: str,
    ) -> JSONDict:
        return self._client.request(
            f"/v1/access/rail-settings/{rail_id}",
            method="PUT",
            body=body,
            headers=self._idempotency_headers(idempotency_key),
        )

    def get_setup_readiness(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/access/setup/readiness", query=query)

    def get_product_available_rails(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/access/products/available-rails", query=query)

    def get_product_available_rails_by_id(
        self,
        product_id: str,
        query: Optional[Mapping[str, Any]] = None,
    ) -> JSONDict:
        return self._client.request(f"/v1/access/products/{product_id}/available-rails", query=query)

    def get_native_subscription(self, authorization_id: str) -> JSONDict:
        return self._client.request(f"/v1/access/native-subscriptions/{authorization_id}")

    def create_native_subscription_cancel_intent(
        self,
        authorization_id: str,
        body: Optional[Mapping[str, Any]] = None,
    ) -> JSONDict:
        return self._client.request(
            f"/v1/access/native-subscriptions/{authorization_id}/cancel-intent",
            method="POST",
            body=body or {},
        )

    def confirm_native_subscription_cancel(
        self,
        authorization_id: str,
        body: Mapping[str, Any],
        *,
        idempotency_key: str,
    ) -> JSONDict:
        return self._client.request(
            f"/v1/access/native-subscriptions/{authorization_id}/cancel-confirm",
            method="POST",
            body=body,
            headers=self._idempotency_headers(idempotency_key),
        )

    def create_app(self, body: Mapping[str, Any], *, idempotency_key: str) -> JSONDict:
        return self._client.request(
            "/v1/access/apps",
            method="POST",
            body=body,
            headers=self._idempotency_headers(idempotency_key),
        )

    def create_product(self, body: Mapping[str, Any], *, idempotency_key: str) -> JSONDict:
        return self._client.request(
            "/v1/access/products",
            method="POST",
            body=body,
            headers=self._idempotency_headers(idempotency_key),
        )

    def create_payment_session(self, body: Mapping[str, Any], *, idempotency_key: str) -> JSONDict:
        return self._client.request(
            "/v1/access/payment-sessions",
            method="POST",
            body=body,
            headers=self._idempotency_headers(idempotency_key),
        )

    def submit_payment_proof(self, body: Mapping[str, Any], *, idempotency_key: str) -> JSONDict:
        return self._client.request(
            "/v1/access/payment-proofs",
            method="POST",
            body=body,
            headers=self._idempotency_headers(idempotency_key),
        )

    def check_entitlement(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            "/v1/access/entitlements/check",
            method="POST",
            body=body,
        )

    def get_entitlement(self, entitlement_id: str) -> JSONDict:
        return self._client.request(f"/v1/access/entitlements/{entitlement_id}")

    def create_webhook(self, body: Mapping[str, Any], *, idempotency_key: str) -> JSONDict:
        return self._client.request(
            "/v1/access/webhooks",
            method="POST",
            body=body,
            headers=self._idempotency_headers(idempotency_key),
        )

    def create_stripe_billing_checkout(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            "/v1/access/billing/checkout/stripe",
            method="POST",
            body=body,
            auth="bearer",
        )


class WebhooksResource(_ResourceBase):
    def list_endpoints(self) -> JSONDict:
        return self._client.request("/v1/webhooks/endpoints", auth="bearer")

    def create_endpoint(self, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request("/v1/webhooks/endpoints", method="POST", body=body, auth="bearer")

    def update_endpoint(self, endpoint_id: str, body: Mapping[str, Any]) -> JSONDict:
        return self._client.request(
            f"/v1/webhooks/endpoints/{endpoint_id}",
            method="PATCH",
            body=body,
            auth="bearer",
        )

    def disable_endpoint(self, endpoint_id: str) -> JSONDict:
        return self._client.request(f"/v1/webhooks/endpoints/{endpoint_id}", method="DELETE", auth="bearer")

    def send_test_event(self, endpoint_id: str, event_type: str) -> JSONDict:
        return self._client.request(
            f"/v1/webhooks/endpoints/{endpoint_id}/test",
            method="POST",
            body={"event_type": event_type},
            auth="bearer",
        )

    def list_deliveries(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/webhooks/deliveries", query=query, auth="bearer")

    def replay_delivery(self, delivery_id: int) -> JSONDict:
        return self._client.request(
            f"/v1/webhooks/deliveries/{delivery_id}/replay",
            method="POST",
            auth="bearer",
        )

    def get_timeline(self, query: Mapping[str, Any]) -> JSONDict:
        return self._client.request("/v1/webhooks/timeline", query=query, auth="bearer")

    def list_events(self, query: Optional[Mapping[str, Any]] = None) -> JSONDict:
        return self._client.request("/v1/webhooks/events", query=query, auth="bearer")


class HiltClient:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 20.0,
        user_agent: str = "hilt-python-sdk/1.0.3",
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.bearer_token = bearer_token.strip() if bearer_token else None
        self.base_url = _normalize_base_url(base_url)
        self.timeout = timeout
        self.user_agent = user_agent
        self.session = session or requests.Session()

        self.products = ProductsResource(self)
        self.checkout = CheckoutResource(self)
        self.payments = PaymentsResource(self)
        self.memberships = MembershipsResource(self)
        self.receipts = ReceiptsResource(self)
        self.support = SupportResource(self)
        self.access = AccessResource(self)
        self.pay_api = self.access
        self.webhooks = WebhooksResource(self)

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        auth: str = "merchant",
        query: Optional[Mapping[str, Any]] = None,
        body: Optional[Mapping[str, Any]] = None,
        response_type: str = "json",
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        url = f"{self.base_url}{_append_query(path, query)}"
        request_headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        if headers:
            request_headers.update(headers)

        auth_header = self._resolve_auth_header(auth)
        if auth_header:
            request_headers[auth_header.name] = auth_header.value

        if body is not None:
            request_headers["Content-Type"] = "application/json"

        response = self.session.request(
            method=method,
            url=url,
            json=body,
            headers=request_headers,
            timeout=self.timeout,
        )

        if not response.ok:
            raise self._build_error(response)

        if response_type == "content":
            return response.content
        if response_type == "text":
            return response.text
        if response.status_code == 204:
            return None
        return response.json()

    def _resolve_auth_header(self, auth: str) -> Optional[_AuthHeader]:
        if auth == "none":
            return None
        if auth == "apiKey":
            if not self.api_key:
                raise ValueError("This HiltClient instance does not have an API key configured.")
            return _AuthHeader("X-Hilt-Key", self.api_key)
        if auth == "bearer":
            if not self.bearer_token:
                raise ValueError("This HiltClient instance does not have a bearer token configured.")
            return _AuthHeader("Authorization", f"Bearer {self.bearer_token}")
        if self.api_key:
            return _AuthHeader("X-Hilt-Key", self.api_key)
        if self.bearer_token:
            return _AuthHeader("Authorization", f"Bearer {self.bearer_token}")
        raise ValueError("This HiltClient instance needs either an API key or a bearer token for merchant routes.")

    @staticmethod
    def _build_error(response: requests.Response) -> HiltApiError:
        payload: Any = None
        message = f"HTTP {response.status_code}"
        error_code: Optional[str] = None

        try:
            payload = response.json()
        except ValueError:
            payload = response.text.strip() or None

        if isinstance(payload, str) and payload:
            message = payload
        elif isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("message")
            if isinstance(detail, str) and detail.strip():
                message = detail
            code = payload.get("error") or payload.get("code")
            if isinstance(code, str) and code.strip():
                error_code = code

        return HiltApiError(
            status_code=response.status_code,
            message=message,
            error_code=error_code,
            details=payload,
        )
