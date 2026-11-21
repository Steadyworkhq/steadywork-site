import io, json, re, time
from datetime import date, timedelta
import pytest
from app import db, payments
from app.config import Config
from conftest import sample_bytes

FUTURE = (date.today() + timedelta(days=120)).isoformat()


def csrf(client):
    with client.session_transaction() as s:
        return s["csrf"]


def upload(client, fn="small-numbered-64.csv", pasted=None):
    client.get("/start")
    data = {"csrf": csrf(client)}
    if pasted is not None:
        data["pasted"] = pasted
    else:
        data["file"] = (io.BytesIO(sample_bytes(fn)), fn)
    r = client.post("/start", data=data, content_type="multipart/form-data")
    assert r.status_code == 302, r.data[:500]
    eid = re.search(r"/e/([^/]+)/map", r.headers["Location"]).group(1)
    return eid


def confirm_mapping(client, eid, **kw):
    form = {"csrf": csrf(client), "mode": "full", "full": "0", "table": "1", "has_header": "1", "action": "confirm"}
    form.update(kw)
    r = client.post(f"/e/{eid}/map", data=form)
    assert r.status_code == 302
    return r


def ack_dups(client, eid):
    page = client.get(f"/e/{eid}/review").get_data(as_text=True)
    for sig in re.findall(r'name="sig" value="([^"]+)"', page):
        import html
        client.post(f"/e/{eid}/review", data={"csrf": csrf(client), "action": "keep_both", "sig": html.unescape(sig)})


def set_design(client, eid, **kw):
    form = {"csrf": csrf(client), "design": "botanical", "title": "Ava & Jonah", "event_date": FUTURE, "venue": "Portland",
            "chart_size": "18x24", "chart_layout": "table", "sort_by": "last", "paper": "letter", "card_order": "table", "region": "us"}
    form.update(kw)
    r = client.post(f"/e/{eid}/design", data=form)
    assert r.status_code == 302, r.get_data(as_text=True)[:2000]


def ready_event(client, fn="small-numbered-64.csv"):
    eid = upload(client, fn)
    confirm_mapping(client, eid)
    ack_dups(client, eid)
    set_design(client, eid)
    return eid


def pay(client, eid, retry=False):
    r = client.post(f"/e/{eid}/checkout", data={"csrf": csrf(client)})
    assert r.status_code == 303
    sid = r.headers["Location"].rsplit("/", 1)[-1]
    r = client.post(f"/mock-checkout/{sid}/pay", data={"email": "buyer@example.com", **({"retry": "1"} if retry else {})})
    assert r.status_code == 303
    return sid


def ev(eid):
    return db.q1("SELECT * FROM events WHERE id=?", eid)


def test_full_flow_upload_to_download(client):
    eid = ready_event(client)
    r = client.get(f"/e/{eid}/preview")
    assert r.status_code == 200 and b"Buy the full package" in r.data
    png = client.get(f"/e/{eid}/preview/chart.png")
    assert png.status_code == 200 and png.data[:4] == b"\x89PNG"
    # Unpaid: no print files
    for k in ("chart", "chart-alpha", "cards", "sign", "backup"):
        assert client.get(f"/e/{eid}/download/{k}.pdf").status_code == 402
    assert client.get(f"/e/{eid}/download/all.zip").status_code == 402
    # Unpaid: guest page inactive
    slug = ev(eid)["guest_slug"]
    assert client.get(f"/s/{slug}").status_code == 404
    pay(client, eid)
    assert ev(eid)["status"] == "paid"
    r = client.get(f"/e/{eid}")
    assert r.status_code == 200 and b"/m/" in r.data
    for k in ("chart", "chart-alpha", "cards", "sign", "backup"):
        r = client.get(f"/e/{eid}/download/{k}.pdf")
        assert r.status_code == 200 and r.data[:5] == b"%PDF-", k
        assert b"PREVIEW" not in r.data
    z = client.get(f"/e/{eid}/download/all.zip")
    assert z.status_code == 200 and z.data[:2] == b"PK"


def test_missing_tables_block_progress(client):
    eid = upload(client, "messy-with-missing.csv")
    confirm_mapping(client, eid)
    page = client.get(f"/e/{eid}/review").get_data(as_text=True)
    assert "3 guests without a table" in page
    # design and preview redirect back to review
    assert client.get(f"/e/{eid}/design").status_code == 302
    assert client.get(f"/e/{eid}/preview").status_code == 302
    r = client.post(f"/e/{eid}/checkout", data={"csrf": csrf(client)})
    assert r.status_code == 302 and "/review" in r.headers["Location"]
    # Assign them
    ids = re.findall(r'name="table_(\d+)"', page)
    client.post(f"/e/{eid}/review", data={"csrf": csrf(client), "action": "assign", **{f"table_{i}": "2" for i in ids}})
    ack_dups(client, eid)
    assert client.get(f"/e/{eid}/design").status_code == 200


def test_duplicates_require_decision_and_are_kept(client):
    eid = upload(client, pasted="Name,Table\nJamie Lee,1\nJamie Lee,4\nAna Ruiz,1\n")
    confirm_mapping(client, eid)
    assert client.get(f"/e/{eid}/design").status_code == 302
    ack_dups(client, eid)
    assert client.get(f"/e/{eid}/design").status_code == 200
    n = db.q1("SELECT COUNT(*) c FROM guests WHERE event_id=? AND name='Jamie Lee'", eid)["c"]
    assert n == 2


def test_other_visitors_cannot_access_event(app, client):
    eid = ready_event(client)
    pay(client, eid)
    other = app.test_client()
    for url in (f"/e/{eid}", f"/e/{eid}/review", f"/e/{eid}/download/chart.pdf", f"/e/{eid}/preview/chart.png", f"/e/{eid}/delete"):
        assert other.get(url).status_code == 403, url
    other.get("/start")
    with other.session_transaction() as s:
        tok = s["csrf"]
    r = other.post(f"/e/{eid}/review", data={"csrf": tok, "action": "add", "new_name": "Intruder", "new_table": "1"})
    assert r.status_code == 403
    r = other.post(f"/e/{eid}/delete", data={"csrf": tok, "confirm": "DELETE"})
    assert r.status_code == 403
    assert ev(eid) is not None


def test_guest_link_is_read_only(app, client):
    eid = ready_event(client)
    pay(client, eid)
    slug = ev(eid)["guest_slug"]
    guest = app.test_client()
    page = guest.get(f"/s/{slug}")
    assert page.status_code == 200
    assert page.headers["X-Robots-Tag"].startswith("noindex")
    body = page.get_data(as_text=True)
    assert 'name="robots" content="noindex' in body
    # No guest names are listed on the page itself
    for r in db.q("SELECT name FROM guests WHERE event_id=?", eid):
        assert r["name"] not in body
    # The guest slug does not grant management access
    assert guest.get(f"/e/{eid}").status_code == 403
    assert guest.get(f"/m/{slug}").status_code == 404
    # Lookup POST only reads
    before = db.q1("SELECT version FROM events WHERE id=?", eid)["version"]
    guest.post(f"/s/{slug}", data={"name": "anything", "table_label": "9", "action": "add"})
    assert db.q1("SELECT version FROM events WHERE id=?", eid)["version"] == before


def test_guest_lookup_exact_name_accent_insensitive(app, client):
    eid = upload(client, pasted="Name,Table\nJosé García,3\nDr. Anastasia Kova,Head Table\nAna Ruiz,1\nJamie Lee,1\nJamie Lee,4\n")
    confirm_mapping(client, eid)
    ack_dups(client, eid)
    set_design(client, eid)
    pay(client, eid)
    slug = ev(eid)["guest_slug"]
    g = app.test_client()
    r = g.post(f"/s/{slug}", data={"name": "  jose GARCIA "}).get_data(as_text=True)
    assert "Table 3" in r and "José García" in r
    r = g.post(f"/s/{slug}", data={"name": "Anastasia Kova"}).get_data(as_text=True)
    assert "Head Table" in r
    r = g.post(f"/s/{slug}", data={"name": "Jamie Lee"}).get_data(as_text=True)
    assert "Table 1" in r and "Table 4" in r
    # Partial names don't browse the list
    r = g.post(f"/s/{slug}", data={"name": "Ana"}).get_data(as_text=True)
    assert "Ana Ruiz" not in r
    r = g.post(f"/s/{slug}", data={"name": "a"}).get_data(as_text=True)
    assert "José" not in r


def test_guest_lookup_rate_limited(app, client):
    eid = ready_event(client)
    pay(client, eid)
    slug = ev(eid)["guest_slug"]
    g = app.test_client()
    codes = [g.post(f"/s/{slug}", data={"name": f"x{i} y"}).status_code for i in range(45)]
    assert codes[0] == 200 and codes[-1] == 429


def test_webhook_retry_does_not_double_fulfil(client):
    eid = ready_event(client)
    pay(client, eid, retry=True)
    assert db.q1("SELECT COUNT(*) c FROM payments WHERE event_id=?", eid)["c"] == 1
    assert db.q1("SELECT COUNT(*) c FROM funnel WHERE name='paid' AND event_id=?", eid)["c"] == 1


def test_second_paid_session_flagged_not_refulfilled(client):
    eid = ready_event(client)
    # Two checkout sessions opened in two tabs; both get paid.
    r1 = client.post(f"/e/{eid}/checkout", data={"csrf": csrf(client)})
    r2 = client.post(f"/e/{eid}/checkout", data={"csrf": csrf(client)})
    s1, s2 = (r.headers["Location"].rsplit("/", 1)[-1] for r in (r1, r2))
    client.post(f"/mock-checkout/{s1}/pay", data={"email": "a@example.com"})
    # After paid, checkout redirects to dashboard instead of charging again
    assert "/checkout" not in client.post(f"/e/{eid}/checkout", data={"csrf": csrf(client)}).headers["Location"]
    client.post(f"/mock-checkout/{s2}/pay", data={"email": "a@example.com"})
    rows = db.q("SELECT duplicate FROM payments WHERE event_id=? ORDER BY id", eid)
    assert [r["duplicate"] for r in rows] == [0, 1]
    assert db.q1("SELECT COUNT(*) c FROM funnel WHERE name='paid' AND event_id=?", eid)["c"] == 1


def test_webhook_rejects_bad_or_stale_signature(client):
    eid = ready_event(client)
    r = client.post(f"/e/{eid}/checkout", data={"csrf": csrf(client)})
    sid = r.headers["Location"].rsplit("/", 1)[-1]
    payload = payments.mock_completed_event(sid, eid, Config.PRICE_CENTS, "usd", "x@example.com")
    assert client.post("/webhooks/stripe", data=payload, headers={"Stripe-Signature": "t=1,v1=deadbeef"}).status_code == 400
    assert client.post("/webhooks/stripe", data=payload).status_code == 400
    wrong = payments.sign(payload, "whsec_wrong")
    assert client.post("/webhooks/stripe", data=payload, headers={"Stripe-Signature": wrong}).status_code == 400
    stale = payments.sign(payload, Config.MOCK_WEBHOOK_SECRET, ts=int(time.time()) - 3600)
    assert client.post("/webhooks/stripe", data=payload, headers={"Stripe-Signature": stale}).status_code == 400
    tampered = payments.sign(payload, Config.MOCK_WEBHOOK_SECRET)
    assert client.post("/webhooks/stripe", data=payload.replace(b"paid", b"PAID"), headers={"Stripe-Signature": tampered}).status_code == 400
    assert ev(eid)["status"] == "draft"
    # Success URL alone does not unlock
    client.get(f"/e/{eid}/paid?session_id={sid}")
    assert ev(eid)["status"] == "draft"
    assert client.get(f"/e/{eid}/download/chart.pdf").status_code == 402
    # Valid signature works
    good = payments.sign(payload, Config.MOCK_WEBHOOK_SECRET)
    assert client.post("/webhooks/stripe", data=payload, headers={"Stripe-Signature": good}).status_code == 200
    assert ev(eid)["status"] == "paid"


def test_webhook_for_unknown_session_does_not_unlock(client):
    eid = ready_event(client)
    payload = payments.mock_completed_event("cs_forged", eid, Config.PRICE_CENTS, "usd", "x@example.com")
    good = payments.sign(payload, Config.MOCK_WEBHOOK_SECRET)
    client.post("/webhooks/stripe", data=payload, headers={"Stripe-Signature": good})
    assert ev(eid)["status"] == "draft"


def test_corrections_regenerate_outputs_consistently(app, client):
    import pypdfium2 as pdfium
    eid = upload(client, pasted="Name,Table\nAna Ruiz,1\nBen Okafor,2\n")
    confirm_mapping(client, eid)
    set_design(client, eid, design="minimal")
    pay(client, eid)
    old = client.get(f"/e/{eid}/download/chart.pdf").data
    gid = db.q1("SELECT id FROM guests WHERE event_id=? AND name='Ana Ruiz'", eid)["id"]
    bid = db.q1("SELECT id FROM guests WHERE event_id=? AND name='Ben Okafor'", eid)["id"]
    client.post(f"/e/{eid}/review", data={"csrf": csrf(client), "action": "save_all", f"name_{gid}": "Ana Ruíz-Peña", f"tbl_{gid}": "5", f"name_{bid}": "Ben Okafor", f"tbl_{bid}": "2"})
    def txt(pdf):
        d = pdfium.PdfDocument(pdf); return "".join(d[i].get_textpage().get_text_range() for i in range(len(d)))
    for k in ("chart", "chart-alpha", "cards", "backup"):
        t = txt(client.get(f"/e/{eid}/download/{k}.pdf").data)
        assert "Ana Ruíz-Peña" in t, k
        assert "Ana Ruiz\n" not in t and "Ana Ruiz " not in t
    assert "Ana Ruiz" in txt(old)
    slug = ev(eid)["guest_slug"]
    r = app.test_client().post(f"/s/{slug}", data={"name": "ana ruiz-pena"}).get_data(as_text=True)
    assert "Table 5" in r


def test_management_link_signs_in_on_new_device(app, client):
    eid = ready_event(client)
    pay(client, eid)
    page = client.get(f"/e/{eid}").get_data(as_text=True)
    link = re.search(r'value="(http://localhost:5000/m/[^"]+)"', page).group(1)
    phone = app.test_client()
    r = phone.get(link.replace("http://localhost:5000", ""))
    assert r.status_code == 302
    assert phone.get(f"/e/{eid}").status_code == 200
    # Replacing the link invalidates the old one
    client.post(f"/e/{eid}/new-link", data={"csrf": csrf(client)})
    assert app.test_client().get(link.replace("http://localhost:5000", "")).status_code == 404


def test_csrf_required(client):
    eid = ready_event(client)
    r = client.post(f"/e/{eid}/review", data={"action": "add", "new_name": "X", "new_table": "1"})
    assert r.status_code == 400


def test_delete_event_removes_everything(app, client):
    eid = ready_event(client)
    pay(client, eid)
    slug = ev(eid)["guest_slug"]
    client.get(f"/e/{eid}/download/chart.pdf")
    r = client.post(f"/e/{eid}/delete", data={"csrf": csrf(client), "confirm": "DELETE"})
    assert r.status_code == 200
    assert ev(eid) is None
    assert db.q1("SELECT COUNT(*) c FROM guests WHERE event_id=?", eid)["c"] == 0
    assert app.test_client().get(f"/s/{slug}").status_code == 404
    import os
    assert not os.path.exists(os.path.join(Config.DATA_DIR, "cache", eid))


def test_retention_purge(client):
    from app.server import purge
    eid = ready_event(client)
    pay(client, eid)
    past = (date.today() - timedelta(days=Config.RETENTION_DAYS_AFTER_EVENT + 1)).isoformat()
    db.x("UPDATE events SET event_date=? WHERE id=?", past, eid)
    d2 = upload(client)
    db.x("UPDATE events SET updated_at=? WHERE id=?", time.time() - (Config.DRAFT_RETENTION_DAYS + 1) * 86400, d2)
    d3 = upload(client)
    purge()
    assert ev(eid) is None and ev(d2) is None and ev(d3) is not None


def test_guest_limit_enforced(client):
    rows = "\n".join(f"Guest {i} Person,{i % 20 + 1}" for i in range(260))
    eid = upload(client, pasted="Name,Table\n" + rows)
    r = client.post(f"/e/{eid}/map", data={"csrf": csrf(client), "mode": "full", "full": "0", "table": "1", "has_header": "1", "action": "confirm"})
    assert r.status_code == 200 and b"up to 250" in r.data


def test_mobile_viewport_on_customer_and_guest_pages(app, client):
    eid = ready_event(client)
    pay(client, eid)
    for url in ("/", "/start", f"/e/{eid}", f"/e/{eid}/review", f"/e/{eid}/design", f"/e/{eid}/preview", f"/s/{ev(eid)['guest_slug']}"):
        assert b'name="viewport"' in client.get(url).data, url
