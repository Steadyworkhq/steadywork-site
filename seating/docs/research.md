# Seating Package Launch: Channel, Fee and Infrastructure Research

Product: $99 self-service wedding seating package. The customer uploads a guest list and table assignments. We deliver a seating chart PDF, place cards PDF, QR sign PDF and a hosted mobile "find your seat" page with exact-name lookup. The customer can edit and regenerate before the event.

Prepared: 2026-11-03. All sources accessed 2026-11-03.

## Method and limits (read first)

- **WebFetch could not reach any page in this session.** `www.etsy.com` and `stripe.com` both failed DNS resolution because they are outside the session's allowed network domains, and I made no further fetch attempts. **Every claim below therefore comes from WebSearch result summaries and snippets, not from reading the pages directly.** Where I could, I limited searches to the official domain (etsy.com, help.etsy.com, stripe.com, docs.stripe.com, render.com, postmarkapp.com, resend.com, aws.amazon.com).
- **Before acting on anything here, re-check it on the live page,** especially the Etsy policy wording and the prices. To fetch pages directly, add `etsy.com` and `stripe.com` to the session's allowed network domains.
- **The search tool does not show paid ads.** Section 3 lists organic results only. I cannot say who is bidding on these queries.
- "Unverified" means I could not confirm the claim from an official source.

---

## 1. Etsy rules

### (a) Digital and personalized (made-to-order) digital items

| Rule | Source |
|---|---|
| Digital items must be made or designed by the seller ("Designed by a seller" under the Creativity Standards). | https://www.etsy.com/legal/creativity , https://help.etsy.com/hc/en-us/articles/360024112614-What-Can-I-Sell-on-Etsy |
| There are two digital types. Instant downloads are files uploaded with the listing. Made-to-order downloads are custom files the seller uploads when completing the order. | https://help.etsy.com/hc/en-us/articles/115015628347-How-to-Manage-Your-Digital-Listings , https://community.etsy.com/forum/announcements-290/topic/weve-improved-our-made-to-order-digital-listing-experience-22506/ |
| Variations are not allowed on digital listings. | same help article (per search summary) |
| Limit of 5 files per digital listing, 20 MB each. | third-party guide only: https://www.listingloom.app/blog/etsy-digital-download-listing-rules (unverified officially) |
| AI-assisted creations must disclose the AI use. | https://www.etsy.com/legal/creativity (per search summary) |
| **Services are generally not allowed.** The exception is a service that produces a new item. Custom design work sold as digital files is allowed, and the finished item should be sent "as an attachment via email or Etsy Messages". **Software and streaming memberships or subscriptions are prohibited.** | https://www.etsy.com/legal/policy/services/242665313101 |

Implication: personalized PDFs (chart, place cards, QR sign) clearly fit a **made-to-order digital listing**. An ongoing hosted webpage with an edit/regenerate dashboard looks more like a service or software access. The Services policy does not clearly allow that as the thing being sold (my interpretation; Etsy has not ruled on it).

### (b) External websites, off-Etsy accounts, fee avoidance

| Rule | Source |
|---|---|
| The **Off-Platform Transactions Policy** bans steering buyers to buy through outside venues such as a personal website, social shop or other marketplace. It also bans making offers to buy or sell off Etsy and offering off-platform discounts or incentives. | https://www.etsy.com/legal/policy/off-platform-transactions-policy/1254654515806 |
| The same policy says **"using a QR code to direct members off Etsy" is not allowed.** | same page (per search summary) |
| The Buyer Policy also prohibits sharing QR codes for an off-platform transaction. | https://www.etsy.com/legal/buyers/ |
| The Seller Policy bars moving transactions off-platform by exchanging contact or financial details, including phone, email, social handles, **external URLs** and money-transfer instructions. | https://www.etsy.com/legal/sellers/ |
| Extra payment for bespoke orders must go through Etsy's "Create Custom Order" feature. | https://www.etsy.com/legal/sellers/ |
| The older Fees & Payments Policy called encouraging off-Etsy purchase "fee avoidance". | https://www.etsy.com/legal/policy/fees-payments-policy-effective-until/569917133857 (historical) |
| I found **no official Etsy rule** saying whether a listing may require the buyer to create an off-Etsy account or deliver part of the product as a seller-hosted webpage. | **Unverified.** A third-party claim that sellers may share links to their own website as long as no purchase happens there could not be confirmed: https://listingsafe.app/blog/etsy-off-platform-violation |

### (c) A QR-code guest webpage we host, as part of an Etsy order

- **No official Etsy statement covers this specific case.** Unverified.
- **Arguments that it is acceptable** (my interpretation):
  - The QR code sends wedding guests to view a seating lookup. It does not send Etsy members to buy anything.
  - Similar listings exist on Etsy now, which shows the practice is present but not that Etsy allows it:
    - "Digital Seating Chart With QR Code Sign Template ... Table Guest Seating Website": https://www.etsy.com/listing/1727402672/digital-seating-chart-with-qr-code-sign
    - "Digital Wedding Seating Chart Website Template, QR Code Sign": https://www.etsy.com/listing/1843099682/digital-seating-chart-canva-website
    - A custom listing that includes "a seating chart web link and a custom QR code" (per search snippet; listing not identified)
  - Most of these are Canva website templates that the buyer edits and hosts in their own Canva account. They are not seller-hosted dashboards.
- **Risks:**
  - The policy wording bans using QR codes to direct members off Etsy.
  - A management link to our site, with editing, regeneration or any upsell, could look like moving the customer relationship off-platform.
  - Ongoing hosted access resembles a prohibited software or subscription service.
  - Any payment, tip or upgrade taken on our site would clearly break the Off-Platform Transactions Policy.

### (d) Etsy fees (US sellers)

| Fee | Amount | Source |
|---|---|---|
| Listing fee | $0.20 per listing; renews every 4 months or on each sale | https://www.etsy.com/legal/fees/ |
| Transaction fee | 6.5% of the display price plus shipping and gift wrap; not charged on sales tax for US sellers | https://www.etsy.com/legal/fees/ |
| Payment processing (US) | 3% + $0.25 per order, on the gross amount including tax | https://www.etsy.com/legal/etsy-payments/ , https://help.etsy.com/hc/en-us/articles/115015628847-What-are-Payment-Processing-Fees-for-Selling-on-Etsy |
| Offsite Ads | 15% of attributed orders, or 12% once the shop passes $10,000 in sales in a 365-day period; **capped at $100 per order** | https://help.etsy.com/hc/en-us/articles/360000338367-How-Etsy-s-Offsite-Ads-Work , https://www.etsy.com/legal/fees/ |
| Offsite Ads opt-out | Allowed only while the shop has never reached $10,000 in any 365-day period. After that, Offsite Ads are mandatory at 12%. | same |
| Etsy Ads minimum | $1.00/day minimum; new advertisers are capped at $25/day max. Etsy's Seller Handbook suggests $3–5/day for a useful test. | https://help.etsy.com/hc/articles/360033701174 , https://www.etsy.com/seller-handbook/article/667698209245 |
| Shop set-up fee | "may apply" (one-time; amount not shown) | https://www.etsy.com/legal/fees/ (per summary). Unverified amount. |

Worked example for one $99 sale with no tax (my arithmetic):
- Etsy fees: $0.20 + $6.44 + $3.22 = **about $9.86, or 10.0%**.
- If the sale is attributed to Offsite Ads, add $14.85 (15%), for **about $24.71 total**.

### (e) Collecting guest lists: Etsy Messages vs external forms

- Buyer data may be used **only for Etsy-related communications and transactions**. No marketing or mailing-list sign-up without the buyer's consent. https://www.etsy.com/legal/sellers/
- **Sellers are responsible for protecting the personal information they receive**, including unintended breaches. https://www.etsy.com/legal/sellers/
- Sellers serving EU buyers must have a GDPR-compliant privacy policy, and Etsy recommends every seller have one. https://help.etsy.com/hc/en-us/articles/360001027628-How-to-Comply-with-General-Data-Protection-Regulation
- A guest list is third-party personal data (guests' names). Collecting it through Etsy Messages keeps the exchange on-platform. An external upload form means sending an external URL, which the Seller Policy restricts when used to move the transaction off Etsy. I found no explicit rule either allowing or banning external forms used only to collect order details. Unverified.

### Verdict

**Do not list the exact bundle on Etsy as-is.** These parts are unverified or likely non-compliant:
1. A seller-hosted page plus a management dashboard reached by an off-Etsy link or account.
2. Edit/regenerate "access", which reads as a service or subscription.
3. Guest-list upload through an external form.
4. A QR code that leads off Etsy. It leads guests, not buyers, but the policy text is broad.

**A compliant Etsy listing would look like this** (lowest risk first):
1. **Etsy for PDFs only.** Sell a "made-to-order personalized digital file" listing: seating chart, place cards and QR sign, delivered as Etsy digital files.
   - Collect the guest list as a CSV attachment or personalization text in Etsy Messages.
   - Handle edits through Etsy Messages, with a stated number of revisions included.
   - Sell the full package with the hosted page and self-serve editing only on our own site. Never link to it or mention it in Etsy listings or messages.
2. **Bonus page included, nothing to buy off Etsy.** Same as option 1, plus the QR sign points to a guest lookup page we host. Present the page as a free part of the delivered file, not as software access.
   - No account, sign-up or payment off Etsy.
   - No upsell or marketing on the page.
   - Edits are requested through Etsy Messages and we regenerate.
   - **Ask Etsy Support in writing first.** This option is an interpretation, not confirmed policy.

---

## 2. Other channels

| Channel | Relevant rules and minimum spend | Source |
|---|---|---|
| Zola vendor marketplace | Listing reportedly free; no published ad rates for stationery found. **Unverified.** | secondary only: https://d3.harvard.edu/platform-digit/wp-json/wp/v2/hck-submission/14196 |
| The Knot / WeddingWire | **No official rate card found.** Third-party estimates run $0 to $700+/month, and one aggregator says from $50/month billed annually. **Unverified.** The Knot forums ban vendors soliciting business. | https://curate.co/blog/the-knot-advertising-cost/ , https://forums.theknot.com/discussion/752727/new-here-faqs-and-welcome |
| Pinterest Ads | Sources conflict: "no official minimum" vs a "$5/day per campaign" minimum. Pinterest's help page found does not state one. **Unverified.** | https://help.pinterest.com/business/article/set-up-campaign-budgets , https://www.tailwindapp.com/blog/how-much-does-pinterest-advertising-cost |
| Google Search Ads | No enforced minimum budget, per secondary sources; official confirmation not retrieved. | https://opascope.com/insights/google-ads-budget/ |
| Reddit r/weddingplanning | Official subreddit rules **not retrieved**. Secondary sources say it is heavily moderated and vendors who promote get banned. r/weddit allows vendor replies only on "ISO" flaired posts. Treat as **no self-promotion**. | https://www.conbersa.ai/learn/what-is-reddit-wedding , https://reddit.sudovanilla.org/r/weddit |
| Facebook groups | Each group sets its own promotion rules. Meta prohibits selling admin roles or group space for ads (Community Standards, spam). Commerce Policies apply to selling. Get admin permission before posting. | https://www.socialmediatoday.com/news/facebook-clarifies-that-its-against-its-terms-to-sell-group-admin-rights/543571 , https://www.socialmediatoday.com/news/meta-outlines-policy-requirements-for-businesses-looking-to-advertise-and-s/617152/ |

---

## 3. Purchase-intent search scan

**Ads:** WebSearch shows organic results only, so no paid ads (Google Ads, Shopping or Etsy Ads) are visible. **I cannot report who is bidding on these queries.** The results below are organic, as returned by the tool on 2026-11-03, in its order.

**Prices:** I could not open any page to confirm prices or review counts. Prices below are as quoted in search snippets or summaries and are marked accordingly.

### "done for you wedding seating chart"
| Result | What they sell | Price seen | Place cards / QR / webpage |
|---|---|---|---|
| planning.wedding/seating-chart | Free drag-and-drop tool | free | webpage tool |
| 101planners.com | Free templates | free | no |
| wedibox.com (blog) | Guide; Wedibox sells QR charts | see below | QR + webpage |
| planseats.com | Free online maker | free | tool |
| seatplan.io | Free template + designer | free | tool |
| wedding-seating-chart.com | Free maker, no signup | free | tool |
| amodernwedding.com/products/blase-seating-chart-1 | Printed chart; you supply names; proof in 2 days | $235.99 regular, 24x40 (snippet) | chart only |
| templatelab.com, adobe.com | Templates | free | no |

Finding: no clear "done-for-you" digital competitor ranks for this query. It is mostly free tools.

### "custom wedding seating chart digital"
| Result | What they sell | Price seen | Bundles |
|---|---|---|---|
| etsy.com/market/custom_seating_chart | Etsy category page | "$3–$20 typical" (search summary, unverified) | varies |
| planning.wedding, weddingwire.com, wedding.studio, seatplan.io | Free makers | free (wedding.studio charges for printing) | tools |
| canva.com seating-chart templates | Free templates | free | no |
| wedibox.com/features/wedding-seating-chart | QR seating chart linked to wedding site | see Wedibox below | QR + webpage |
| digiseats.com | QR seating chart; editable after sharing QR; paid tiers | not found | QR + webpage |
| serendipitydesigns.gumroad.com | Canva template | not shown | no |

### "wedding seating chart and place cards"
| Result | What they sell | Price seen | Bundles |
|---|---|---|---|
| paperlust.co (3 blog posts) | Stationery retailer content | not shown | chart + place cards (printed) |
| etsy.com/market/wedding_seating_chart_cards_individual, /market/seating_cards | Etsy categories | not shown | varies |
| papier.com/us place cards | Printed place cards | not shown | place cards |
| womangettingmarried.com, morningside-inn.com, thepemberleycreative.com | Editorial | n/a | n/a |

Finding: this query is mostly informational and editorial. Printed-stationery retailers (Paperlust, Papier) rank. I saw no digital chart + place cards + QR bundle.

### "QR wedding seating chart"
| Result | What they sell | Price seen | Bundles |
|---|---|---|---|
| etsy.com/listing/4310878634 | QR seating chart sign, digital download | not shown | QR sign |
| etsy.com/listing/1727402672 | QR sign template + alphabetical "guest seating website" (Canva) | $9.00, (1.3k) per search snippet | QR + webpage template |
| wedibox.com | Hosted QR chart | Capterra: free tier excludes seating; $49 one-time Wedding plan; **$79 one-time All-In-One (includes seating chart)** | QR + webpage |
| zazzle.com (2 listings) | Printed QR seating signs / foam board | not shown | QR sign |
| pinterest (pin) | Etsy-style QR sign | n/a | n/a |
| svenstudios.com SeatScan | Free QR seating plan | free | QR + webpage |
| goimagine.com | Canva QR sign template | not shown | QR sign |
| pleasefindyourseat.com | Browser QR chart; works until 1 week after event | not found | QR + webpage |
| digiseats.com | Hosted QR chart, paid tiers | not found | QR + webpage |

Wedibox pricing source: https://www.capterra.com/p/10043467/Wedibox/ (third-party).

### Etsy price points seen (search snippets only, unverified on page)
- Requested listing https://www.etsy.com/listing/1782181243/wedding-seating-chart-custom-seating:
  - Could not fetch it.
  - The search index shows it as the Etsy AU page by shop **ReinaBorealis**: "Printed or Digital File, Find your seat sign".
  - Structured data shows a range of **AUD 32.08–193.96**. The snapshot is about 800 days old.
  - **Review count not visible.**
- From an Etsy-limited search on QR / digital seating listings (https://www.etsy.com/market/qr_code_seating , https://www.etsy.com/market/digital_seat_chart):
  - DIY Canva templates mostly about **$4–$15**.
  - One Canva listing at about **$87.49** with 4.9 (276 reviews), 3.3k sales.
  - One **$100 hosted QR seating chart listing** with 5.0 (24 reviews). Reviewers mention 300- and 350-person weddings. Listing URL not identified.
  - Printed QR acrylic or foam signs about **$46–$106**, and one foam board at $199.75.
  - All of these are from search summaries and unverified.

Takeaways:
- Hosted QR "find your seat" pages already sell at roughly $49–$100 (Wedibox $79; an Etsy hosted listing at $100). That makes $99 plausible but not cheap.
- None of the competitors seen clearly bundle chart PDF, place cards, QR sign and a hosted name-lookup page in one product. That is unverified, since I could not inspect the listings.

---

## 4. Stripe

| Item | Finding | Source |
|---|---|---|
| Standard US online card pricing | **2.9% + 30¢** per successful domestic card charge | https://stripe.com/pricing |
| International cards | +1.5% | https://stripe.com/pricing |
| Currency conversion | +1% | https://stripe.com/pricing |
| Promotion codes in Checkout | **Yes.** Set `allow_promotion_codes=true` on the Checkout Session. Codes are built on coupons and can be restricted, for example to first-time orders. Limit of one code per session. A 100%-off code allows a free checkout. | https://docs.stripe.com/payments/checkout/discounts , https://docs.stripe.com/payments/checkout/no-cost-orders , https://docs.stripe.com/billing/subscriptions/coupons |
| Test mode | **Yes.** Sandbox with test API keys; test card 4242 4242 4242 4242; `pm_card_visa` for code | https://docs.stripe.com/testing |

Caveat: stripe.com/pricing could not be fetched, and the cached snippets vary in age.

On a $99 sale, Stripe takes $3.17 (3.2%), compared with about $9.86 (10%) on Etsy before Offsite Ads (my arithmetic).

---

## 5. Hosting (Flask + SQLite with a persistent disk)

| Option | Smallest suitable plan | Persistent storage | Source |
|---|---|---|---|
| Fly.io | shared-cpu-1x 256 MB: $1.94/mo on Fly's cached official page. Third-party reports say $2.19/mo after an Oct 1, 2026 RAM price rise; that change is **unverified**. | Volumes $0.15/GB-mo | https://fly.io/docs/about/pricing/ , https://www.buildmvpfast.com/blog/fly-io-pricing-2026-ram-increase-vs-hetzner |
| Render | Starter web service (0.5 CPU / 512 MB): $7/mo. Free instances cannot attach disks. | Disk $0.25/GB-mo | https://render.com/pricing , https://render.com/docs/compute-plans |
| Railway | Hobby plan: $5/mo, including $5 of usage. Volumes max 5 GB on Hobby. | Volume rate about $0.15–0.16/GB-mo per most sources (some say $0.25). **Unverified.** | https://docs.railway.com/pricing/plans , https://docs.railway.com/reference/volumes |
| DigitalOcean Droplet | Basic $4/mo (512 MB, 10 GB SSD) or $6/mo (1 GB, 25 GB SSD) | local SSD included | https://betterstack.com/community/guides/web-servers/digitalocean-vs-hetzner/ (secondary; official page not retrieved) |
| Hetzner Cloud | CX23 (2 vCPU / 4 GB / 40 GB) about €3.99/mo after the April 1, 2026 price rise. Sources conflict (€3.99–€4.51), and prices vary by region. **Unverified.** | local SSD included | https://findstack.com/resources/hetzner-price-increase-2026 , https://agentdeals.dev/hetzner-pricing-2026 |

Expected monthly cost for a 1 GB volume (my arithmetic; excludes bandwidth and backups):

| Option | Approx. monthly cost |
|---|---|
| Fly.io | about $2.10–2.35 |
| Render | about $7.25 |
| Railway | about $5 (inside the plan credit at low load) |
| DigitalOcean | $4–6 |
| Hetzner | about €4 |

A VPS gives the most for the money but means managing the OS, TLS and backups yourself.

---

## 6. Transactional email (management link)

| Provider | Free tier | Entry paid | Source |
|---|---|---|---|
| Postmark | Developer plan: 100 emails/mo, never expires, no overages, no card needed | $15/mo for 10,000 emails (Basic); Pro $16.50, Platform $18. Nothing between 100 and 10k. | https://postmarkapp.com/pricing , https://postmarkapp.com/support/article/1285-pricing-billing-faq |
| Resend | 3,000 emails/mo, **100/day cap** (resets at UTC midnight), no overages | Pro $20/mo for 50,000, no daily cap; overage $0.90 per 1,000 | https://resend.com/pricing , https://resend.com/docs/knowledge-base/account-quotas-and-limits |
| Amazon SES | Old SES free tier (3,000 messages/mo for 12 months) **ended for new customers on July 21, 2026**. New AWS accounts get up to $200 in Free Tier credits for 6 months. | À la carte $0.10 per 1,000. New accounts start on the "Essentials" plan at about $0.16 per 1,000, with no monthly fee. You handle bounces and reputation yourself. | https://aws.amazon.com/ses/pricing/ , https://aws.amazon.com/blogs/messaging-and-targeting/introducing-amazon-simple-email-service-ses-pricing-plans/ |

At this product's volume (a few emails per order), the **Resend free tier** covers launch, as long as fewer than 100 emails go out per day.
