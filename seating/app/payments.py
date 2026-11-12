"""Hosted checkout (Stripe Checkout) and webhook verification.

We call Stripe's REST API directly with urllib (no SDK needed) and verify
webhook signatures with the documented scheme:
    Stripe-Signature: t=<unix>,v1=<hex hmac_sha256(secret, f"{t}.{payload}")>

PAYMENTS_MODE=mock replaces the hosted page with a local stand-in that sends a
webhook signed with MOCK_WEBHOOK_SECRET through the *same* verification code.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import Config

TOLERANCE_SECONDS = 300


class SignatureError(Exception):
    pass


def webhook_secret() -> str:
    return Config.STRIPE_WEBHOOK_SECRET if Config.PAYMENTS_MODE == "stripe" else Config.MOCK_WEBHOOK_SECRET


def sign(payload: bytes, secret: str, ts: int | None = None) -> str:
    ts = int(ts if ts is not None else time.time())
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def verify(payload: bytes, header: str | None, secret: str, now: float | None = None) -> dict:
    if not header or not secret:
        raise SignatureError("missing signature")
    parts = {}
    sigs = []
    for item in header.split(","):
        k, _, v = item.strip().partition("=")
        if k == "v1":
            sigs.append(v)
        else:
            parts[k] = v
    try:
        ts = int(parts.get("t", ""))
    except ValueError:
        raise SignatureError("bad timestamp")
    now = time.time() if now is None else now
    if abs(now - ts) > TOLERANCE_SECONDS:
        raise SignatureError("timestamp outside tolerance")
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in sigs):
        raise SignatureError("signature mismatch")
    try:
        return json.loads(payload)
    except ValueError:
        raise SignatureError("bad json")


def _stripe_post(path: str, fields: dict, idempotency_key: str) -> dict:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request("https://api.stripe.com" + path, data=data, method="POST")
    token = base64.b64encode((Config.STRIPE_SECRET_KEY + ":").encode()).decode()
    req.add_header("Authorization", "Basic " + token)
    req.add_header("Idempotency-Key", idempotency_key)
    req.add_header("Stripe-Version", "2024-06-20")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Stripe error {e.code}: {body[:400]}")


def create_checkout(event_id: str, title: str, attempt_key: str) -> tuple[str, str]:
    """Returns (session_id, url to redirect the customer to)."""
    success = f"{Config.BASE_URL}/e/{event_id}/paid?session_id={{CHECKOUT_SESSION_ID}}"
    cancel = f"{Config.BASE_URL}/e/{event_id}/preview?cancelled=1"
    if Config.PAYMENTS_MODE != "stripe":
        sid = "cs_mock_" + secrets.token_urlsafe(18)
        return sid, f"{Config.BASE_URL}/mock-checkout/{sid}"
    fields = {
        "mode": "payment",
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": Config.CURRENCY,
        "line_items[0][price_data][unit_amount]": str(Config.PRICE_CENTS),
        "line_items[0][price_data][product_data][name]": "Wedding seating package",
        "line_items[0][price_data][product_data][description]": "Seating chart, place cards, QR sign and find-your-seat page"[:250],
        "success_url": success,
        "cancel_url": cancel,
        "client_reference_id": event_id,
        "metadata[event_id]": event_id,
        "payment_intent_data[metadata][event_id]": event_id,
        "allow_promotion_codes": "true",
    }
    s = _stripe_post("/v1/checkout/sessions", fields, idempotency_key=attempt_key)
    return s["id"], s["url"]


def mock_completed_event(session_id: str, event_id: str, amount: int, currency: str, email: str) -> bytes:
    """A payload shaped like Stripe's checkout.session.completed event."""
    return json.dumps(
        {
            "id": "evt_mock_" + secrets.token_hex(10),
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": session_id,
                    "object": "checkout.session",
                    "client_reference_id": event_id,
                    "metadata": {"event_id": event_id},
                    "payment_status": "paid",
                    "amount_total": amount,
                    "currency": currency,
                    "customer_details": {"email": email},
                }
            },
        }
    ).encode()
