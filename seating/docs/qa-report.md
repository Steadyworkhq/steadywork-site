# QA report

Run on 2026-11-03 in a Linux container with Python 3.13, ReportLab 5.0.1 and Chromium through Playwright. All data is synthetic.

`python -m pytest -q` → **65 passed**.

## Requirement → evidence

| Requirement | How it was verified | Result |
|---|---|---|
| Long names and accented characters render correctly | `test_long_names_and_single_long_word` covers a 70-character name, a 35-letter single word, Þ/Ó/ú/Ș/ễ, all 3 designs, chart/cards (Letter + A4)/backup. `test_chart_every_guest_no_clipping` extracts text from the PDFs and finds every word of all 250 names. **Visually inspected** rasterised charts, cards and signs for all three designs. | Pass. Vietnamese letters missing from Jost (e.g. "ễ") print in the DejaVu fallback in the Minimal design. The customer is told which names use the fallback. A character no font has blocks purchase instead of printing a box. |
| Two guests can share a name | `test_two_guests_same_name_both_appear_everywhere`, `test_duplicates_require_decision_and_are_kept`, and the guest lookup returning both tables | Pass |
| Missing table assignments flagged | `test_missing_tables_flagged_not_invented`, `test_missing_tables_block_progress` (design, preview and checkout are all blocked) | Pass |
| Every confirmed guest appears in the correct outputs | `check_all_placed` compares the multiset of (name, table) drawn against the input for chart (both layouts), place cards and backup list | Pass |
| No names clipped or silently omitted | Every placed name's drawn width ≤ the space it was given (manifest). `test_chart_names_never_below_minimum_size`: never below 11 pt on posters; long lists split across posters instead. | Pass |
| Large lists paginate sensibly | 250 guests: place cards 63 sheets plus a guide, backup list several pages. On a 16×20 poster, 250 guests split into 2 posters labelled "Table 1 – Table 12" / "Table 13 – Table 25", with a warning in the preview. **Visually inspected.** | Pass |
| PDFs have correct physical dimensions | `test_chart_physical_dimensions` (all 5 sizes, e.g. 18×24 in = 1296×1728 pt), `test_card_and_backup_page_sizes` (Letter 612×792, A4 595.28×841.89), and sign sizes | Pass |
| Fonts embedded | `test_fonts_embedded` plus a manual check: every font is a TrueType subset with FontFile2, and there's no unembedded Helvetica (the initial font was fixed during QA) | Pass |
| QR codes scan | `test_qr_decodes_to_guest_url` decodes the rendered sign images with zxing-cpp for all designs and both paper sizes | Pass with a decoder library. **Not yet scanned with a real phone camera** (no phone available here). Print a sign and scan it with iOS and Android before launch. |
| Guest links cannot modify events | `test_guest_link_is_read_only`: the guest page has no forms besides lookup, the guest slug gives 403/404 on management routes, and a lookup POST doesn't change the version. `test_other_visitors_cannot_access_event` and `test_csrf_required` also cover this. | Pass |
| Unpaid users cannot download paid files | `test_full_flow_upload_to_download`: all 5 PDFs and the zip return 402 before payment, the guest page is inactive before payment, and previews are watermarked PNGs only. `test_webhook_rejects_bad_or_stale_signature`: visiting the success URL alone doesn't unlock anything. | Pass |
| Payment retries don't duplicate fulfilment | `test_webhook_retry_does_not_double_fulfil` (same event delivered twice), `test_second_paid_session_flagged_not_refulfilled` (two tabs both paid → second flagged for refund), `test_webhook_for_unknown_session_does_not_unlock` | Pass **in mock mode**. The mock sends a signed payload through the same verification and fulfilment code. |
| Corrections update outputs consistently | `test_corrections_regenerate_outputs_consistently`: after an edit, all four PDFs contain the new name and not the old one, and the guest lookup returns the new table | Pass |
| Mobile-friendly checkout and editing | Full flow in headless Chromium emulating an iPhone 13 (upload → map → fix missing tables → confirm duplicates → design → preview → mock checkout with a retried webhook → dashboard → download). Guest lookup done on Pixel 7 emulation. Screenshots inspected. | Pass in emulation. Not yet tried on physical devices. |
| Deletion and retention | `test_delete_event_removes_everything`, `test_retention_purge` | Pass |

## Not tested yet (be explicit)

- **Stripe test mode end to end.** api.stripe.com was unreachable from this environment. The Stripe request code (`payments.create_checkout`) has **never been executed against Stripe**. Signature verification follows Stripe's documented scheme and is tested with locally signed payloads only.
- **Email sending** through Resend. It has never been executed; without a key it only logs.
- **A real phone scanning a printed QR sign.**
- **Physical printing:** poster colour and weight, cardstock folding, home-printer margins. Cards keep marks at least 0.2 in from the edge on Letter, but some printers can't print near the edge.
- Very old spreadsheet formats (.xls), and multi-sheet workbooks: only the first non-empty sheet is read.
- Screen readers and accessibility beyond semantic HTML and labels.
- Load or concurrency. The app runs single-process SQLite, which is fine at launch volume.

## Known limits and decisions

- **Last-name sort uses the last word** ("van der Berg" sorts under B, "de la Cruz" under C) unless the customer uploads a separate last-name column. The customer can switch to first-name order.
- **Table labels are normalised:** "Table 5" / "5" / "05" → 5. Named tables are kept as typed.
- **Guest lookup:** exact full name, ignoring case, accents, punctuation and a leading honorific. Partial names don't match, so the list can't be browsed. Guests who type a nickname won't be found; the page tells them to ask at the welcome table.
- **Lost management link:** the customer can replace it while signed in. If they're signed out, it currently needs a support email. A magic-link login by email is the next improvement once email is configured.
- **Abuse risk:** someone could reuse one purchase for a second event by replacing every name. That's accepted for the MVP.
