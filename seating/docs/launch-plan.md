# Launch plan: $99 self-service wedding seating package

Status as of 2026-11-03.

- **Done:** working local product (see the README).
- **Proposed:** everything else in this file. Nothing below has been published, posted, deployed or paid for.

## 1. Riskiest assumptions, in order

| # | Assumption | Why it's risky | Cheapest test |
|---|---|---|---|
| 1 | We can reach couples with seating already decided, cheaply and **within about 1–8 weeks of their wedding** | The buying window is narrow and late. Free tools (Planseats, SeatPlan, Canva) dominate organic search for the target phrases (see `research.md` §3). A new site will get no organic traffic for weeks or months. | A small paid search test on purchase-intent phrases (§4), measured to checkout. |
| 2 | $99 is acceptable | Canva QR templates sell for about $4–15 and hosted QR tools for about $49–100 (Wedibox $79; one Etsy hosted listing at $100). These prices come from search snippets and are unverified. Our bundle is broader, but buyers may compare us with the cheap end. | Watch preview→checkout drop-off. If previews are healthy and checkouts are near zero, test $59–79 with a Stripe promotion code before changing the list price. |
| 3 | Self-service is easy enough for people who aren't technical | Messy spreadsheets: merged cells, "Mr & Mrs Smith" on one row, plus-ones. | Watch upload→mapping→preview completion in `/admin` and read support emails. |
| 4 | Support and revisions stay manageable | Late changes are common in the final week. | Log minutes per order (§5). |
| 5 | Venue signal or QR fallback | Mitigated: the package includes a printed chart and backup list. | — |

**Not yet risky enough to build for:** accounts, seat-level assignment, automatic seating, RSVP, printing fulfilment.

## 2. Offer (as built)

- $99 one-time per event. Up to 250 guests.
- Three designs: Minimal, Classic Serif, Botanical.
- Chart at an exact size (16×20, 18×24 or 24×36 in, A2, A1), in both a by-table and an alphabetical layout.
- Place cards on US Letter or A4 with a printing and folding guide.
- QR sign, a hosted guest lookup page, and a printable backup list.
- Corrections until the event.
- Instant download. Written support only.

### Hosting duration proposal (needs your approval)

- **The guest page stays live until 30 days after the event date, then all data is deleted automatically.**
- Drafts are deleted after 14 days of inactivity.
- The customer can delete at any time.
- Event dates are limited to about 18 months ahead.

The guest page is read only on the wedding day and in the days just before and after. Thirty days covers late thank-you checks without holding guest names long. The infrastructure costs a few dollars a month for every event combined (§3), so a longer window is cheap. The main reason to keep it short is privacy.

## 3. Unit economics: labelled scenarios, not forecasts

Fixed costs (proposals; see `research.md` §5–6):

- Hosting about $2–7/month: Fly.io about $2–3 with a 1 GB volume, Render about $7.25.
- Domain: kindlyseatedco.com, about $10–22/year at Squarespace.
- Email: $0 on Resend's free tier.
- **Call it $10/month all-in for planning.**

Per-order variable costs at a $99 list price:

| Item | Own site (Stripe) | Etsy (PDF-only listing) |
|---|---|---|
| Payment / marketplace fees | 2.9% + $0.30 = **$3.17** (+1.5% for international cards) | $0.20 listing + 6.5% + 3% + $0.25 ≈ **$9.86** |
| Etsy Offsite Ads, if a sale is attributed | — | +15% = $14.85 (can opt out while the shop is under $10k in sales) |
| Refund reserve, scenario A / B | 3% / 10% of revenue = $2.97 / $9.90 | same |
| Support time, scenario A / B | 15 / 45 min per order | Etsy is more manual: 30 / 60 min |

Net per order before advertising and your time:

| Scenario | Own site | Etsy (no Offsite Ads) |
|---|---|---|
| Low refunds (3%) | $99 − 3.17 − 2.97 = **$92.86** | $99 − 9.86 − 2.97 = **$86.17** |
| High refunds (10%) | $99 − 3.17 − 9.90 = **$85.93** | **$79.24** |

**Break-even advertising cost per purchase (CAC)** is the net figure above minus what you value your support time at.

Example: with 45 minutes of support valued at $30/hour ($22.50) and high refunds, the own-site break-even CAC is about **$63**.

Illustrative paid-search arithmetic. Neither number below is a measurement; replace them with real data after the test.

| Assumed cost per click | Assumed visit→purchase | Implied CAC | vs $63 break-even |
|---|---|---|---|
| $0.80 | 2.0% | $40 | profitable |
| $1.50 | 2.0% | $75 | loss |
| $1.50 | 4.0% | $37.50 | profitable |
| $2.50 | 1.0% | $250 | heavy loss |

**What the $10k stretch goal implies:** $10,000 ÷ $99 ≈ **102 orders in 30 days**. With ads at a $40 CAC, that's about $4,000 of ad spend. With support at 15–45 minutes per order, it's 25–75 hours of support. Treat it as a stretch.

The first milestone is **5 paid orders**. Hitting it would show the funnel works at all.

## 4. Acquisition experiment for your approval

**Nothing here has been started.** Each item needs an explicit "yes". You set the limits; these are proposals.

### Experiment 1: Google Search ads on purchase intent (primary)

- **Budget cap: $300 total, at most $30/day, for 10 days.** Pause automatically at $300.
- **Keywords**, phrase and exact match, in the US only:
  - "done for you wedding seating chart"
  - "custom wedding seating chart digital"
  - "wedding seating chart and place cards"
  - "QR wedding seating chart"
  - "seating chart with qr code wedding"
  - "find your seat qr code"
- **Negative keywords:** free, template, canva, printable free, diy, app.
- **Ads** state the price ($99) and say "upload your list". Stating the price filters out people looking for something free.
- **Landing page:** `/?utm_source=google&utm_campaign=seat1`.
- **Stop rules:**
  - If $150 has been spent with zero checkout starts, pause and review the search terms report.
  - If $300 has been spent with zero purchases, stop and rethink the offer or channel rather than adding features.
- **Continue rule:** at least 2 purchases at a CAC under $63 → ask you about a second $300 tranche.
- Caveats: Google's minimum budgets and current CPCs are unverified (`research.md` §2). We have not seen who else bids on these terms.

### Experiment 2: Etsy, PDF-only listing ($0 fixed, optional ads)

Sell a policy-compliant variant on Etsy; see `marketplace-listing.md`.

- It's the made-to-order personalised digital files only: chart, place cards and backup list.
- We run the buyer's list through our own tool and send the PDFs via Etsy.
- No external links, and no QR page pointing off Etsy, unless Etsy Support confirms in writing that it's allowed.
- **Cost:** $0.20 to list.
- **Optional Etsy Ads: $3/day capped at $45 total** — needs your yes.
- **Opt out of Offsite Ads** while it's allowed.
- **Why run it:** it uses Etsy's existing buyer traffic, which tests demand separately from our ability to drive traffic.
- **Downside:** manual work per order.

### Free, approval-light: Pinterest organic

Pin the three samples (marked fictional) linking to the landing page with a `utm_source=pinterest` tag. This needs a Pinterest business account in your name. We don't post until you approve.

**Not recommended:** posting in Reddit or Facebook groups. Self-promotion is generally banned there (`research.md` §2), and you asked for no unsolicited messages.

## 5. Funnel measurement plan

The app records these steps in the `funnel` table, viewable at `/admin?token=…`:

```
visit (with utm_source) → start_view → upload → mapping_confirmed → preview → checkout_start → paid → download
correction (after purchase), guest_lookup_hit / guest_lookup_miss (wedding-day usage)
```

Track these every day in a simple sheet:

| Metric | Where | Watch for |
|---|---|---|
| Visits by source | /admin sources | Ad clicks vs. visits mismatch (tracking or bounce issue) |
| Upload rate (upload / visit) | /admin | < 5% → landing page isn't convincing |
| Mapping completion (mapping_confirmed / upload) | /admin | Low → file parsing problems; check support |
| Preview rate (preview / mapping_confirmed) | /admin | Low → missing-table/duplicate step is too hard |
| Checkout start / preview | /admin | Low → price or trust |
| Paid / checkout start | Stripe + /admin | Low → checkout friction |
| Corrections per order | /admin | High → expected; check support load |
| Support minutes per order | Manual log (date, order, minutes, issue) | > 45 min average → fix the top cause |
| Refunds / duplicate payments | Stripe + /admin flag | Any duplicate → refund same day |
| Ad spend, CPC, CAC | Google Ads / Etsy | vs $63 break-even |
| Guest lookup misses vs hits | /admin | Many misses → lookup matching too strict |

There is no third-party analytics script. That's deliberate for privacy. Add one only if you decide to, and update the privacy page if you do.

## 6. 30-day sequence: where we are

| Days | Plan | Status |
|---|---|---|
| 1–3 | Confirm offer, competitor and channel rules, samples, core guest-list→PDF prototype | **Done** (prototype is a working local app). Competitor scan is limited to search snippets (`research.md`). |
| 4–7 | Local flow, test-mode checkout, guest lookup, QA, reviewable launch | **Mostly done locally.** Stripe test mode **not yet exercised** (no network access to Stripe here). Hosting not deployed. |
| 8–14 | One acquisition experiment, seek 5 orders | Waiting on your approvals (§7) |
| 15–21 | Fix actual causes of drop-off and complaints | — |
| 22–30 | Expand only if economics justify; otherwise change offer, price or channel | — |

## 7. Approvals and decisions I need from you

1. ~~Brand and domain~~ **Decided:** Kindly Seated, kindlyseatedco.com.
2. **Stripe account** in test mode, plus the two keys described in the README. I'll then run the real test-mode purchase and re-send the webhook.
3. **Hosting:** Render (decided). Still needs your approval to make the site public.
4. **Retention:** 30 days after the event (§2). Approve it or change it.
5. **Support email address** for the site and receipts.
6. **Acquisition:**
   - Experiment 1 (up to $300)
   - Experiment 2 (Etsy listing, plus up to $45 of Etsy Ads)
   - Pinterest organic
   - Answer yes or no for each.
7. **Legal review** of the draft `/privacy` and `/terms`, especially the refund wording and your business details.
