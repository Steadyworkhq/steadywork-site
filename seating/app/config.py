"""All settings come from environment variables. Nothing secret is hard-coded."""
import os
import secrets


def _bool(name, default=False):
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


class Config:
    BRAND_NAME = os.environ.get("BRAND_NAME", "Kindly Seated")
    SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "hello@kindlyseatedco.com")
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000").rstrip("/")
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
    PRODUCTION = _bool("PRODUCTION", False)
    SECRET_KEY = os.environ.get("SECRET_KEY") or ("dev-" + secrets.token_hex(16))

    # Payments: "mock" runs a local stand-in for hosted checkout (development only);
    # "stripe" uses Stripe Checkout. Start with Stripe *test* keys (sk_test_...).
    PAYMENTS_MODE = os.environ.get("PAYMENTS_MODE", "mock")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    MOCK_WEBHOOK_SECRET = os.environ.get("MOCK_WEBHOOK_SECRET") or ("whsec_mock_" + secrets.token_hex(16))
    PRICE_CENTS = int(os.environ.get("PRICE_CENTS", "9900"))
    CURRENCY = os.environ.get("CURRENCY", "usd")

    # Email (optional). Without a key, emails are written to the server log only.
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "")

    # Retention: the guest page stays live and data is kept until this many days
    # after the event date, then everything is deleted automatically.
    RETENTION_DAYS_AFTER_EVENT = int(os.environ.get("RETENTION_DAYS_AFTER_EVENT", "30"))
    # Unpaid drafts are deleted after this many days of inactivity.
    DRAFT_RETENTION_DAYS = int(os.environ.get("DRAFT_RETENTION_DAYS", "14"))
    # Events must be within this many days from today.
    MAX_DAYS_AHEAD = int(os.environ.get("MAX_DAYS_AHEAD", "550"))

    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
    MAX_UPLOAD_BYTES = 2 * 1024 * 1024

    @classmethod
    def check(cls):
        problems = []
        if cls.PRODUCTION:
            if not os.environ.get("SECRET_KEY"):
                problems.append("SECRET_KEY must be set in production.")
            if cls.PAYMENTS_MODE != "stripe":
                problems.append("PAYMENTS_MODE must be 'stripe' in production (mock checkout is for local demos).")
            if not cls.BASE_URL.startswith("https://"):
                problems.append("BASE_URL must be https:// in production.")
        if cls.PAYMENTS_MODE == "stripe" and not (cls.STRIPE_SECRET_KEY and cls.STRIPE_WEBHOOK_SECRET):
            problems.append("STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET are required when PAYMENTS_MODE=stripe.")
        return problems
