"""Order email. Uses Resend's HTTP API if RESEND_API_KEY is set; otherwise logs.

The management link can't be emailed from here because we only store its hash.
Instead the email links to the event dashboard sign-in help, and the customer
sees and bookmarks the private link right after checkout. (See README: a
magic-link sign-in is the next step once email is configured.)
"""
import json
import logging
import urllib.request

from .config import Config

log = logging.getLogger("seating.email")


def send(to: str, subject: str, text: str) -> bool:
    if not to:
        return False
    if not (Config.RESEND_API_KEY and Config.EMAIL_FROM):
        log.info("EMAIL (not sent, no provider configured) to=%s subject=%s\n%s", to, subject, text)
        return False
    body = json.dumps({"from": Config.EMAIL_FROM, "to": [to], "subject": subject, "text": text}).encode()
    req = urllib.request.Request("https://api.resend.com/emails", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {Config.RESEND_API_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:  # noqa: BLE001
        log.error("email send failed: %s", e)
        return False


def send_receipt(ev, to: str) -> bool:
    text = f"""Thank you — your seating package for {ev['title']} is ready.

Your files and your private management link are on the page you were taken to
after checkout. Please bookmark that management link: it is how you edit names
and tables and re-download your files.

Guest page (the QR code opens this): {Config.BASE_URL}/s/{ev['guest_slug']}
Anyone with that link can look up a guest's table by typing their full name.

Your guest page and data are deleted automatically {Config.RETENTION_DAYS_AFTER_EVENT} days after your event date,
or sooner if you delete the event yourself.

Questions or a lost link? Reply to {Config.SUPPORT_EMAIL}.
"""
    return send(to, f"Your seating package — {ev['title']}", text)
