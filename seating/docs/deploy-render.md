# Deploying Kindly Seated (Render + Squarespace DNS)

Domain: **kindlyseatedco.com**, registered at Squarespace. The app is hosted on Render.

Nothing here has been done yet. Each step is yours to click, or mine to do once you give me access and approval. Prices are from research notes and may have changed, so check them on Render's pricing page.

## 0. Before you start

- A GitHub repo for the app. Recommended: a new empty repo such as `kindlyseated`, with the Claude GitHub App given access, so I can move `seating/` into it.
  - If it stays in `steadywork-site`, keep `rootDir: seating` in `render.yaml`.
  - Don't merge it to `main` there, because GitHub Pages would publish the internal docs.
- Stripe test keys:
  - the secret key, `sk_test_…`
  - the webhook signing secret, `whsec_…` (you create it in step 3)
- **The app won't start in production without Stripe keys.** That's deliberate: it refuses to run the fake test checkout on the public internet.

## 1. Create the service on Render

1. Sign up at render.com with your GitHub account.
2. Click **New → Blueprint** and pick the repo. Render reads `render.yaml`, which sets up:
   - a Starter web service, about $7/month
   - a 1 GB disk at `/data`, about $0.25/month
   - one instance (SQLite needs that)
   - the start command and a health check
   - `SECRET_KEY` and `ADMIN_TOKEN`, generated for you
3. When it asks, fill in:
   - `STRIPE_SECRET_KEY` = your `sk_test_…` key
   - `SUPPORT_EMAIL` = e.g. `hello@kindlyseatedco.com`
   - `STRIPE_WEBHOOK_SECRET`: leave it empty for now and add it in step 3. Until then the deploy will fail at startup, which is expected.
4. Note the service address Render gives you, e.g. `kindlyseated.onrender.com`.

## 2. Connect kindlyseatedco.com (Squarespace DNS)

1. In Render, open the service, go to **Settings → Custom Domains**, and add both:
   - `kindlyseatedco.com`
   - `www.kindlyseatedco.com`
2. Render shows the DNS records to create. **Use the exact values it shows.** They're usually:

   | Type | Host | Value |
   |---|---|---|
   | A | @ | the IP address Render shows (commonly 216.24.57.1) |
   | CNAME | www | `kindlyseated.onrender.com` (your service address) |

3. In Squarespace, go to **Domains → kindlyseatedco.com → DNS settings**:
   - Remove any default Squarespace records for `@` and `www`.
   - Add the records above.
4. Wait for Render to show the domain as verified, with a certificate issued. This takes minutes to a few hours.
5. Check that both `https://kindlyseatedco.com` and `https://www.kindlyseatedco.com` load with a padlock.

## 3. Stripe webhook (test mode)

1. In the Stripe dashboard, test mode, go to **Developers → Webhooks → Add endpoint**.
2. Set the URL to `https://kindlyseatedco.com/webhooks/stripe`.
3. Choose the events `checkout.session.completed` and `checkout.session.async_payment_succeeded`.
4. Copy the signing secret (`whsec_…`) into Render as `STRIPE_WEBHOOK_SECRET`, then redeploy.

## 4. Test purchase (test mode, no real money)

1. Open `https://kindlyseatedco.com` and upload `samples/small-numbered-64.csv`.
2. Go through to checkout and pay with the card **4242 4242 4242 4242**, any future expiry date and any CVC.
3. You should land on the dashboard with downloads unlocked.
4. In Stripe, open the event and click **Resend**. Then open `/admin?token=…` (the token is in Render's environment settings). There should be one order and no duplicate flag.
5. Print the QR sign and scan it with an iPhone and an Android phone.
6. Delete the test event from the dashboard.

## 5. Going live, after your approval

- Switch the Stripe keys to live ones (`sk_live_…`) and create a live webhook with its own `whsec_…`.
- Back up the database: download `/data/seating.db` from Render's shell, or add a daily backup job. I can add one.
- Set up email for `hello@kindlyseatedco.com`. Squarespace can forward it to your Gmail, or you can use Google Workspace.
- Optionally, add Resend (`RESEND_API_KEY`, `EMAIL_FROM`) so customers get a receipt email.
