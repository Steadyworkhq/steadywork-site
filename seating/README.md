# Wedding seating package (MVP)

Self-service product: a customer uploads a guest list with table assignments they've already decided, confirms columns, fixes missing tables and possible duplicates, picks one of three designs, sees a watermarked preview with their real names, pays $99 through hosted checkout, and downloads:

1. A print-ready seating chart at the exact size they choose (16×20, 18×24, 24×36 in, A2, A1), in both a by-table layout and an alphabetical layout.
2. Matching tent place cards (US Letter or A4, 4 per sheet, crop marks, fold ticks, a printing guide and a 1 in / 25 mm calibration square).
3. A QR "find your seat" sign (8×10 in or A4).
4. A plain alphabetical backup list for the welcome table, for venues with poor signal.
5. A private management link to correct names and tables and re-download. The guest QR page updates right away.

This lives in `seating/` inside the existing Steadywork site repo. The static site at the repo root is unchanged.

## Stack and why

**Python 3 + Flask + SQLite + ReportLab**, server-rendered HTML, almost no JavaScript.

- ReportLab draws vector PDFs at exact physical sizes and embeds TrueType font subsets. Layout, sorting, validation, QR generation and exports are all deterministic code. There is no AI anywhere in the app, and guest lists are never sent to a third party apart from the payment provider (which only gets the event ID).
- SQLite is a single file: nothing extra to run, easy to back up, plenty for hundreds of orders.
- Flask with templates keeps the code small enough for one person to maintain.
- Stripe Checkout (hosted) is called with plain HTTPS from `urllib` (no SDK). Webhook signatures are checked with Stripe's documented HMAC-SHA256 scheme.

Fonts are open-licence (SIL OFL) fonts from Google Fonts: Jost, EB Garamond, Cormorant Garamond and Lora. DejaVu is the fallback for characters a design font lacks. They're in `app/fonts/`. All artwork, including the botanical sprigs, is drawn in code.

## Run the local demo

```bash
cd seating
pip install -r requirements.txt
python scripts/build_samples.py          # rebuild the 3 sample packages (optional; already committed)
ADMIN_TOKEN=devadmin python run.py       # http://localhost:5000
```

The default is `PAYMENTS_MODE=mock`. "Buy" opens a local stand-in checkout page that sends a signed `checkout.session.completed` webhook through the same verification code real payments use. A banner on every page says it's a demo. To see the funnel counts, open `/admin?token=devadmin`.

Synthetic guest lists are in `samples/` (made by `scripts/make_synthetic.py`). They include long names, many accents, legitimately shared names and missing tables.

## Tests

```bash
cd seating && pip install -r requirements-dev.txt && python -m pytest -q   # 65 tests
```

The QR decode test needs `zxing-cpp` (it's in `requirements-dev.txt`). See `docs/qa-report.md` for what each requirement was tested against, and what has **not** been tested.

## Remaining setup steps (need you)

1. **Stripe test mode.** The test run in this environment could not reach api.stripe.com, so real Stripe test mode has **not been exercised yet**.
   - Create a Stripe account. In test mode, copy the secret key (`sk_test_…`).
   - Add a webhook endpoint at `https://YOUR-DOMAIN/webhooks/stripe` for the events `checkout.session.completed` and `checkout.session.async_payment_succeeded`, then copy its signing secret (`whsec_…`).
   - For local testing, run `stripe listen --forward-to localhost:5000/webhooks/stripe` and use the secret it prints.
   - Set `PAYMENTS_MODE=stripe STRIPE_SECRET_KEY=sk_test_… STRIPE_WEBHOOK_SECRET=whsec_…`.
   - Buy once with the test card 4242 4242 4242 4242, then re-send the event from the Stripe dashboard to confirm it is not fulfilled twice.
2. **Hosting** (proposal: Fly.io with a 1 GB volume, about $2–3/month per `docs/research.md`; a $4–6 VPS also works).
   - Set `PRODUCTION=1`, `SECRET_KEY` (a long random value), `BASE_URL=https://…`, `DATA_DIR=/data`, `ADMIN_TOKEN`, `SUPPORT_EMAIL` and the Stripe variables.
   - Run with `gunicorn -w 2 -b 0.0.0.0:8080 'app.server:create_app()'`.
   - Back up `DATA_DIR/seating.db` daily.
   - In production the app refuses to start with mock payments or a non-https URL.
3. **Domain.** Suggested: a subdomain such as `seating.steadyworkhq.com` (a CNAME at Squarespace). Or pick a separate consumer brand, since Steadywork is a B2B admin-automation brand. Set `BRAND_NAME`.
4. **Email (optional for launch).**
   - Set `RESEND_API_KEY` and `EMAIL_FROM` to send a receipt with the guest link.
   - Without these, the receipt is only logged. Customers still see their links on screen right after paying.
   - A lost management link currently needs a support email. A follow-up is an emailed sign-in link.
5. **Rebuild the samples for the public URL.** Their demo QR codes currently point to localhost. Run `BASE_URL=https://your-domain python scripts/build_samples.py`.
6. **Review the drafts** of `/privacy` and `/terms`, and the refund wording, before going live.

## Environment variables

See `app/config.py`. The important ones are `PAYMENTS_MODE`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `PRICE_CENTS` (default 9900), `BASE_URL`, `SECRET_KEY`, `DATA_DIR`, `RETENTION_DAYS_AFTER_EVENT` (default 30), `DRAFT_RETENTION_DAYS` (default 14), `ADMIN_TOKEN`, `BRAND_NAME` and `SUPPORT_EMAIL`.

## Privacy and access design

- **Guest page `/s/<slug>`**
  - Uses a 96-bit random slug.
  - Lookup is by exact full name, ignoring case, accents, punctuation and a leading title such as "Dr.".
  - No list can be browsed, and lookups are rate-limited to 40 per 10 minutes per IP.
  - Pages carry `noindex` (header and meta) and are excluded in robots.txt.
  - The page is read-only, and it only works for paid events that haven't expired.
  - The page and the dashboard both tell the customer plainly that anyone with the link can look up a guest by full name.
- **Management**
  - A separate 192-bit token link, `/m/<token>`, is stored only as a SHA-256 hash. Opening it signs that browser in with a signed, HttpOnly cookie.
  - Every customer route checks that session. Every form needs a CSRF token.
  - The customer can replace the link, which makes the old one stop working.
- **Paid files**
  - Every download route checks `status='paid'` on the server.
  - That status is set only by a verified webhook for a checkout session we created, for that event.
  - The success URL unlocks nothing by itself.
  - Before payment, previews are watermarked PNG images only. No printable PDF is served.
- **Idempotency**
  - Webhook event IDs are recorded, so retries are ignored.
  - A second paid session for an event that's already paid is flagged `DUPLICATE — refund` in `/admin` and isn't fulfilled again.
  - Checkout on a paid event goes to the dashboard instead.
- **Data minimisation**
  - Only name and table are stored. Extra columns in the upload are dropped, and the raw upload is discarded once columns are confirmed.
- **Retention (proposal)**
  - The guest page and all data are deleted automatically 30 days after the event date.
  - Unpaid drafts are deleted after 14 days of inactivity.
  - The dashboard has an immediate "Delete event" control.
  - Event dates are limited to about 18 months ahead.
  - A payment record (amount and date, no names) is kept for accounting.
