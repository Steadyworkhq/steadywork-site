"""Flask web app: customer flow, paid downloads, guest lookup, webhooks."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import date, timedelta
from functools import wraps

from flask import (
    Flask,
    Response,
    abort,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from . import db, emailer, outputs, payments
from . import designs as D
from .config import Config
from .guestlist import (
    MAX_GUESTS,
    Guest,
    RawTable,
    apply_mapping,
    clean_name,
    clean_table,
    match_key,
    parse_upload,
    suggest_mapping,
    table_display,
    validate,
)
from .render import CHART_SIZES, PAPERS

from werkzeug.exceptions import HTTPException

log = logging.getLogger("seating")


class PaymentRequired(HTTPException):
    code = 402
    description = "Payment required"


HONORIFICS = {"mr", "mrs", "ms", "miss", "mx", "dr", "prof", "sir", "dame", "rev", "fr"}


def lookup_key(name: str) -> str:
    parts = match_key(name).split(" ")
    while parts and parts[0] in HONORIFICS and len(parts) > 1:
        parts = parts[1:]
    return " ".join(parts)


def hash_token(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    if test_config:
        for k, v in test_config.items():
            setattr(Config, k, v)
    app.config.update(
        SECRET_KEY=Config.SECRET_KEY,
        MAX_CONTENT_LENGTH=Config.MAX_UPLOAD_BYTES,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=Config.PRODUCTION,
        PERMANENT_SESSION_LIFETIME=timedelta(days=60),
    )
    for p in Config.check():
        if Config.PRODUCTION:
            raise RuntimeError(p)
        log.warning("config: %s", p)
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    db.init(os.path.join(Config.DATA_DIR, "seating.db"))
    purge()

    # ------------------------------------------------------------------
    # Request plumbing
    # ------------------------------------------------------------------

    @app.before_request
    def _before():
        session.permanent = True
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(24)
        if request.method == "POST" and request.endpoint not in ("stripe_webhook", "guest_lookup", "mock_checkout_pay", "demo_guest"):
            tok = request.form.get("csrf") or request.headers.get("X-CSRF")
            if not tok or not hmac.compare_digest(tok, session["csrf"]):
                abort(400, "Your session expired. Please go back and try again.")
        _maybe_purge()

    @app.after_request
    def _headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Frame-Options"] = "DENY"
        if request.path.startswith(("/s/", "/e/", "/m/", "/mock-checkout", "/demo/")):
            resp.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.context_processor
    def _ctx():
        return {
            "brand": Config.BRAND_NAME,
            "support_email": Config.SUPPORT_EMAIL,
            "price": f"${Config.PRICE_CENTS / 100:.0f}" if Config.PRICE_CENTS % 100 == 0 else f"${Config.PRICE_CENTS / 100:.2f}",
            "csrf": session.get("csrf", ""),
            "retention_days": Config.RETENTION_DAYS_AFTER_EVENT,
            "draft_days": Config.DRAFT_RETENTION_DAYS,
            "mock_mode": Config.PAYMENTS_MODE != "stripe",
            "max_guests": MAX_GUESTS,
            "table_display": table_display,
        }

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def authorize(event_id):
        ids = set(session.get("events", []))
        ids.add(event_id)
        session["events"] = sorted(ids)[-20:]

    def owner_required(f):
        @wraps(f)
        def inner(event_id, *a, **kw):
            if event_id not in session.get("events", []):
                abort(403)
            ev = db.q1("SELECT * FROM events WHERE id=?", event_id)
            if not ev:
                abort(404)
            g.ev = ev
            return f(event_id, *a, **kw)

        return inner

    def touch(event_id, bump=True):
        if bump:
            db.x("UPDATE events SET version=version+1, updated_at=? WHERE id=?", time.time(), event_id)
            outputs.clear_cache(event_id)
        else:
            db.x("UPDATE events SET updated_at=? WHERE id=?", time.time(), event_id)

    def is_paid(ev):
        return ev["status"] == "paid"

    # ------------------------------------------------------------------
    # Public pages
    # ------------------------------------------------------------------

    @app.route("/")
    def landing():
        db.track("visit", source=(request.args.get("utm_source") or request.args.get("ref") or "")[:40] or None)
        return render_template("landing.html", designs=D.DESIGNS, sizes=CHART_SIZES)

    @app.route("/healthz")
    def healthz():
        db.q1("SELECT 1")
        return "ok"

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/samples/<path:fn>")
    def samples(fn):
        return send_from_directory(os.path.join(os.path.dirname(__file__), "static", "samples"), fn)

    @app.route("/robots.txt")
    def robots():
        return Response("User-agent: *\nDisallow: /s/\nDisallow: /e/\nDisallow: /m/\n", mimetype="text/plain")

    # ------------------------------------------------------------------
    # Step 1: upload
    # ------------------------------------------------------------------

    @app.route("/start", methods=["GET", "POST"])
    def start():
        if request.method == "GET":
            db.track("start_view")
            return render_template("start.html", error=None)
        f = request.files.get("file")
        pasted = request.form.get("pasted", "")
        try:
            if f and f.filename:
                raw = parse_upload(f.filename, f.read())
            elif pasted.strip():
                raw = parse_upload(None, pasted=pasted)
            else:
                return render_template("start.html", error="Choose a file or paste your list.")
        except Exception as e:  # noqa: BLE001 - show a friendly message
            log.info("upload parse failed: %s", e)
            msg = str(e) if isinstance(e, ValueError) else "We couldn't read that file. Try saving it as CSV UTF-8 or .xlsx, or paste the list instead."
            return render_template("start.html", error=msg)
        if not raw.rows:
            return render_template("start.html", error="We couldn't find any rows in that list.")
        if len(raw.rows) > MAX_GUESTS + 50:
            return render_template("start.html", error=f"This package supports up to {MAX_GUESTS} guests. Your list has {len(raw.rows)} rows.")
        eid = secrets.token_urlsafe(12)
        manage = secrets.token_urlsafe(24)
        slug = secrets.token_urlsafe(12)
        now = time.time()
        db.x(
            "INSERT INTO events(id, manage_hash, guest_slug, raw_json, mapping_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            eid,
            hash_token(manage),
            slug,
            json.dumps({"headers": raw.headers, "rows": raw.rows, "has_header": raw.has_header, "warnings": raw.warnings}),
            json.dumps(suggest_mapping(raw)),
            now,
            now,
        )
        authorize(eid)
        session[f"mt_{eid}"] = manage  # shown to the customer so they can bookmark it
        db.track("upload", eid)
        return redirect(url_for("map_columns", event_id=eid))

    # ------------------------------------------------------------------
    # Step 2: confirm column mapping
    # ------------------------------------------------------------------

    def _raw(ev) -> RawTable | None:
        j = db.jload(ev["raw_json"], None)
        if not j:
            return None
        return RawTable(j["headers"], j["rows"], j["has_header"], j.get("warnings", []))

    @app.route("/e/<event_id>/map", methods=["GET", "POST"])
    @owner_required
    def map_columns(event_id):
        ev = g.ev
        raw = _raw(ev)
        if raw is None:
            return redirect(url_for("review", event_id=event_id))
        mapping = db.jload(ev["mapping_json"], {})
        if request.method == "POST":
            def ix(k):
                v = request.form.get(k, "")
                return int(v) if v.isdigit() and int(v) < len(raw.headers) else None

            mapping = {"mode": request.form.get("mode", "full"), "full": ix("full"), "first": ix("first"), "last": ix("last"), "table": ix("table")}
            if request.form.get("has_header") in ("0", "1"):
                want = request.form.get("has_header") == "1"
                if want != raw.has_header:
                    if want:
                        raw = RawTable([c or f"Column {i+1}" for i, c in enumerate(raw.rows[0])], raw.rows[1:], True, raw.warnings)
                    else:
                        raw = RawTable([f"Column {i+1}" for i in range(len(raw.headers))], [raw.headers] + raw.rows, False, raw.warnings)
            if request.form.get("action") == "refresh":
                return render_template("map.html", ev=ev, raw=raw, mapping=mapping, error=None, preview_rows=_map_preview(raw, mapping))
            err = None
            if mapping["mode"] == "split" and (mapping["first"] is None or mapping["last"] is None):
                err = "Choose both the first-name and last-name columns."
            if mapping["mode"] != "split" and mapping["full"] is None:
                err = "Choose the column that holds guest names."
            if mapping["table"] is None:
                err = "Choose the column that holds table assignments."
            if err:
                return render_template("map.html", ev=ev, raw=raw, mapping=mapping, error=err, preview_rows=_map_preview(raw, mapping))
            guests, problems = apply_mapping(raw, mapping)
            if len(guests) > MAX_GUESTS:
                return render_template("map.html", ev=ev, raw=raw, mapping=mapping, error=f"That's {len(guests)} guests; this package supports up to {MAX_GUESTS}.", preview_rows=_map_preview(raw, mapping))
            db.x("DELETE FROM guests WHERE event_id=?", event_id)
            for i, gu in enumerate(guests):
                db.x("INSERT INTO guests(event_id, name, table_label, last, position) VALUES (?,?,?,?,?)", event_id, gu.name, gu.table, gu.last, i)
            # Raw upload is no longer needed; don't keep extra columns the customer may have had.
            db.x("UPDATE events SET raw_json=NULL, mapping_json=?, step='review' WHERE id=?", json.dumps(mapping), event_id)
            touch(event_id)
            session[f"import_notes_{event_id}"] = problems[:20]
            db.track("mapping_confirmed", event_id)
            return redirect(url_for("review", event_id=event_id))
        return render_template("map.html", ev=ev, raw=raw, mapping=mapping, error=None, preview_rows=_map_preview(raw, mapping))

    def _map_preview(raw, mapping):
        guests, _ = apply_mapping(RawTable(raw.headers, raw.rows[:8], raw.has_header), mapping)
        return guests

    @app.route("/e/<event_id>/remap", methods=["POST"])
    @owner_required
    def remap(event_id):
        # Start over with a new file without losing the event links.
        return redirect(url_for("start"))

    # ------------------------------------------------------------------
    # Step 3: review — missing tables, duplicates, edits
    # ------------------------------------------------------------------

    def _guest_rows(event_id):
        return db.q("SELECT id, name, table_label, last FROM guests WHERE event_id=? ORDER BY position", event_id)

    def _state(ev):
        rows = _guest_rows(ev["id"])
        guests = [Guest(r["name"], r["table_label"], r["last"]) for r in rows]
        rep = validate(guests)
        acks = set(db.jload(ev["dup_ack_json"], []))
        dup_groups = []
        for grp in rep.duplicate_groups:
            key = match_key(guests[grp[0]].name)
            ids = sorted(rows[i]["id"] for i in grp)
            sig = key + "|" + ",".join(map(str, ids))
            dup_groups.append({"key": key, "sig": sig, "rows": [rows[i] for i in grp], "acked": sig in acks})
        unresolved_dups = [d for d in dup_groups if not d["acked"]]
        fallback, missing_glyph = outputs.coverage_issues(guests, ev["design"])
        ready = bool(guests) and not rep.blocking and not unresolved_dups and not missing_glyph
        return {
            "rows": rows,
            "guests": guests,
            "report": rep,
            "missing_rows": [rows[i] for i in rep.missing_table],
            "too_long_rows": [rows[i] for i in rep.too_long],
            "dup_groups": dup_groups,
            "unresolved_dups": unresolved_dups,
            "fallback": fallback,
            "missing_glyph": missing_glyph,
            "ready": ready,
        }

    @app.route("/e/<event_id>/review", methods=["GET", "POST"])
    @owner_required
    def review(event_id):
        ev = g.ev
        if request.method == "POST":
            action = request.form.get("action")
            changed = False
            if action == "assign":
                for k, v in request.form.items():
                    if k.startswith("table_") and v.strip():
                        gid = int(k[6:])
                        db.x("UPDATE guests SET table_label=? WHERE id=? AND event_id=?", clean_table(v), gid, event_id)
                        changed = True
            elif action == "remove":
                gid = int(request.form.get("guest_id", "0"))
                db.x("DELETE FROM guests WHERE id=? AND event_id=?", gid, event_id)
                changed = True
            elif action == "keep_both":
                sig = request.form.get("sig", "")
                acks = set(db.jload(ev["dup_ack_json"], []))
                acks.add(sig)
                db.x("UPDATE events SET dup_ack_json=? WHERE id=?", json.dumps(sorted(acks)), event_id)
            elif action == "save_all":
                changed = _save_editor(event_id)
            elif action == "add":
                name = clean_name(request.form.get("new_name", ""))
                table = clean_table(request.form.get("new_table", ""))
                if name:
                    n = db.q1("SELECT COUNT(*) c FROM guests WHERE event_id=?", event_id)["c"]
                    if n >= MAX_GUESTS:
                        session["flash"] = f"This package supports up to {MAX_GUESTS} guests."
                    else:
                        pos = db.q1("SELECT COALESCE(MAX(position),0)+1 p FROM guests WHERE event_id=?", event_id)["p"]
                        db.x("INSERT INTO guests(event_id, name, table_label, last, position) VALUES (?,?,?,?,?)", event_id, name, table, "", pos)
                        changed = True
            if changed:
                touch(event_id)
                if is_paid(ev):
                    db.track("correction", event_id)
            anchor = request.form.get("anchor", "")
            return redirect(url_for("review", event_id=event_id) + (f"#{anchor}" if anchor else ""))
        st = _state(ev)
        notes = session.pop(f"import_notes_{event_id}", [])
        flash = session.pop("flash", None)
        return render_template("review.html", ev=ev, st=st, notes=notes, flash=flash, manage_token=session.get(f"mt_{event_id}"))

    def _save_editor(event_id):
        changed = False
        rows = {r["id"]: r for r in _guest_rows(event_id)}
        for k, v in request.form.items():
            m = re.fullmatch(r"name_(\d+)", k)
            if m:
                gid = int(m.group(1))
                if gid not in rows:
                    continue
                name = clean_name(v)
                table = clean_table(request.form.get(f"tbl_{gid}", rows[gid]["table_label"]))
                if not name:
                    continue  # empty name: ignore rather than delete silently
                if name != rows[gid]["name"] or table != rows[gid]["table_label"]:
                    # Last-name sort column no longer matches an edited name.
                    last = rows[gid]["last"] if name == rows[gid]["name"] else ""
                    db.x("UPDATE guests SET name=?, table_label=?, last=? WHERE id=? AND event_id=?", name, table, last, gid, event_id)
                    changed = True
        return changed

    # ------------------------------------------------------------------
    # Step 4: design + event details
    # ------------------------------------------------------------------

    @app.route("/e/<event_id>/design", methods=["GET", "POST"])
    @owner_required
    def design(event_id):
        ev = g.ev
        error = None
        if request.method == "POST":
            f = request.form
            title = clean_name(f.get("title", ""))[:80]
            d = f.get("event_date", "").strip()
            try:
                dd = date.fromisoformat(d)
            except ValueError:
                dd = None
            if not title:
                error = "Add the names to show on your chart (for example “Ava & Jonah”)."
            elif not dd:
                error = "Add your event date. We use it to decide how long your guest page stays online."
            elif dd < date.today() - timedelta(days=1) and not is_paid(ev):
                error = "That date is in the past."
            elif dd > date.today() + timedelta(days=Config.MAX_DAYS_AHEAD):
                error = "That date is more than 18 months away. Please contact support."
            vals = {
                "design": f.get("design") if f.get("design") in D.DESIGNS else "minimal",
                "chart_size": f.get("chart_size") if f.get("chart_size") in CHART_SIZES else "18x24",
                "chart_layout": "alpha" if f.get("chart_layout") == "alpha" else "table",
                "sort_by": "first" if f.get("sort_by") == "first" else "last",
                "paper": "a4" if f.get("paper") == "a4" else "letter",
                "card_order": "alpha" if f.get("card_order") == "alpha" else "table",
                "region": "intl" if f.get("region") == "intl" else "us",
            }
            if not error:
                db.x(
                    "UPDATE events SET title=?, event_date=?, venue=?, design=?, chart_size=?, chart_layout=?, sort_by=?, paper=?, card_order=?, region=?, step='preview' WHERE id=?",
                    title, dd.isoformat(), clean_name(f.get("venue", ""))[:80], vals["design"], vals["chart_size"], vals["chart_layout"],
                    vals["sort_by"], vals["paper"], vals["card_order"], vals["region"], event_id,
                )
                touch(event_id)
                return redirect(url_for("preview", event_id=event_id))
            ev = dict(ev)
            ev.update(vals, title=title, event_date=d, venue=f.get("venue", ""))
        st = _state(g.ev)
        if not st["ready"] and not is_paid(g.ev):
            return redirect(url_for("review", event_id=event_id))
        return render_template("design.html", ev=ev, designs=D.DESIGNS, sizes=CHART_SIZES, papers=PAPERS, error=error, n=len(st["guests"]))

    # ------------------------------------------------------------------
    # Step 5: watermarked preview (raster images only — no printable file)
    # ------------------------------------------------------------------

    @app.route("/e/<event_id>/preview")
    @owner_required
    def preview(event_id):
        ev = g.ev
        st = _state(ev)
        if not st["ready"]:
            return redirect(url_for("review", event_id=event_id))
        if not ev["title"] or not ev["event_date"]:
            return redirect(url_for("design", event_id=event_id))
        _, man = outputs.render_kind(ev, "chart", preview=True)
        pages = {k: outputs.page_count(ev, k) for k in ("chart", "cards")}
        db.track("preview", event_id)
        return render_template(
            "preview.html", ev=ev, st=st, man=man, pages=pages, sizes=CHART_SIZES, papers=PAPERS,
            cancelled=request.args.get("cancelled"), paid=is_paid(ev),
        )

    @app.route("/e/<event_id>/preview/<kind>.png")
    @owner_required
    def preview_image(event_id, kind):
        if kind not in outputs.KINDS:
            abort(404)
        page = request.args.get("page", "0")
        page = int(page) if page.isdigit() else 0
        png = outputs.preview_png(g.ev, kind, page)
        resp = make_response(png)
        resp.headers["Content-Type"] = "image/png"
        return resp

    # ------------------------------------------------------------------
    # Step 6: hosted checkout
    # ------------------------------------------------------------------

    @app.route("/e/<event_id>/checkout", methods=["POST"])
    @owner_required
    def checkout(event_id):
        ev = g.ev
        if is_paid(ev):
            return redirect(url_for("manage", event_id=event_id))
        st = _state(ev)
        if not st["ready"] or not ev["title"] or not ev["event_date"]:
            return redirect(url_for("review", event_id=event_id))
        attempt = f"{event_id}-{ev['version']}-{int(time.time() // 600)}"
        try:
            sid, url = payments.create_checkout(event_id, ev["title"], attempt)
        except Exception as e:  # noqa: BLE001
            log.error("checkout create failed: %s", e)
            abort(502, "We couldn't reach the payment provider. Please try again in a minute.")
        db.x("INSERT OR IGNORE INTO checkout_sessions(session_id, event_id, created_at) VALUES (?,?,?)", sid, event_id, time.time())
        db.track("checkout_start", event_id)
        return redirect(url, code=303)

    @app.route("/e/<event_id>/paid")
    @owner_required
    def paid_landing(event_id):
        # The success URL grants nothing by itself; we wait for the verified webhook.
        if is_paid(g.ev):
            return redirect(url_for("manage", event_id=event_id, welcome=1))
        return render_template("confirming.html", ev=g.ev)

    @app.route("/e/<event_id>/status")
    @owner_required
    def status(event_id):
        return jsonify({"paid": is_paid(g.ev)})

    # Local stand-in for the hosted checkout page (PAYMENTS_MODE=mock only).
    @app.route("/mock-checkout/<sid>", methods=["GET"])
    def mock_checkout(sid):
        if Config.PAYMENTS_MODE == "stripe":
            abort(404)
        row = db.q1("SELECT * FROM checkout_sessions WHERE session_id=?", sid)
        if not row:
            abort(404)
        return render_template("mock_checkout.html", sid=sid, event_id=row["event_id"])

    @app.route("/mock-checkout/<sid>/pay", methods=["POST"])
    def mock_checkout_pay(sid):
        if Config.PAYMENTS_MODE == "stripe":
            abort(404)
        row = db.q1("SELECT * FROM checkout_sessions WHERE session_id=?", sid)
        if not row:
            abort(404)
        email = request.form.get("email", "test@example.com")[:200]
        payload = payments.mock_completed_event(sid, row["event_id"], Config.PRICE_CENTS, Config.CURRENCY, email)
        header = payments.sign(payload, Config.MOCK_WEBHOOK_SECRET)
        # Deliver through the real webhook handler (same signature checks).
        with app.test_client() as c:
            r = c.post("/webhooks/stripe", data=payload, headers={"Stripe-Signature": header, "Content-Type": "application/json"})
            if r.status_code != 200:
                abort(500)
            if request.form.get("retry") == "1":  # simulate the provider retrying delivery
                c.post("/webhooks/stripe", data=payload, headers={"Stripe-Signature": header, "Content-Type": "application/json"})
        return redirect(f"/e/{row['event_id']}/paid?session_id={sid}", code=303)

    @app.route("/webhooks/stripe", methods=["POST"])
    def stripe_webhook():
        payload = request.get_data()
        try:
            evt = payments.verify(payload, request.headers.get("Stripe-Signature"), payments.webhook_secret())
        except payments.SignatureError as e:
            log.warning("webhook rejected: %s", e)
            return "bad signature", 400
        handle_event(evt)
        return "ok", 200

    # ------------------------------------------------------------------
    # Management dashboard
    # ------------------------------------------------------------------

    @app.route("/m/<token>")
    def manage_login(token):
        ev = db.q1("SELECT id FROM events WHERE manage_hash=?", hash_token(token))
        if not ev:
            time.sleep(0.3)
            abort(404)
        authorize(ev["id"])
        session[f"mt_{ev['id']}"] = token
        return redirect(url_for("manage", event_id=ev["id"]))

    @app.route("/e/<event_id>")
    @owner_required
    def manage(event_id):
        ev = g.ev
        if not is_paid(ev):
            return redirect(url_for(ev["step"] if ev["step"] in ("review", "design", "preview") else "map_columns", event_id=event_id))
        st = _state(ev)
        token = session.get(f"mt_{event_id}")
        return render_template(
            "manage.html", ev=ev, st=st, guest_url=outputs.guest_url(ev),
            manage_url=f"{Config.BASE_URL}/m/{token}" if token else None,
            delete_on=delete_after(ev), welcome=request.args.get("welcome"), sizes=CHART_SIZES, papers=PAPERS,
        )

    @app.route("/e/<event_id>/new-link", methods=["POST"])
    @owner_required
    def new_manage_link(event_id):
        tok = secrets.token_urlsafe(24)
        db.x("UPDATE events SET manage_hash=? WHERE id=?", hash_token(tok), event_id)
        session[f"mt_{event_id}"] = tok
        session["flash"] = "A new private management link was created. The old one no longer works."
        return redirect(url_for("manage", event_id=event_id))

    @app.route("/e/<event_id>/download/<kind>.pdf")
    @owner_required
    def download(event_id, kind):
        ev = g.ev
        if not is_paid(ev):
            raise PaymentRequired()
        if kind not in outputs.KINDS:
            abort(404)
        pdf = outputs.get_pdf(ev, kind, preview=False)
        db.track("download", event_id)
        resp = make_response(pdf)
        resp.headers["Content-Type"] = "application/pdf"
        resp.headers["Content-Disposition"] = f'attachment; filename="{outputs.KINDS[kind]}.pdf"'
        return resp

    @app.route("/e/<event_id>/download/all.zip")
    @owner_required
    def download_zip(event_id):
        if not is_paid(g.ev):
            raise PaymentRequired()
        data = outputs.zip_all(g.ev)
        db.track("download", event_id)
        resp = make_response(data)
        resp.headers["Content-Type"] = "application/zip"
        resp.headers["Content-Disposition"] = 'attachment; filename="seating-package.zip"'
        return resp

    @app.route("/e/<event_id>/delete", methods=["GET", "POST"])
    @owner_required
    def delete_event(event_id):
        if request.method == "GET":
            return render_template("delete.html", ev=g.ev)
        if request.form.get("confirm", "").strip().upper() != "DELETE":
            return render_template("delete.html", ev=g.ev, error="Type DELETE to confirm.")
        _delete(event_id)
        session["events"] = [e for e in session.get("events", []) if e != event_id]
        session.pop(f"mt_{event_id}", None)
        return render_template("deleted.html")

    # ------------------------------------------------------------------
    # Guest-facing lookup (read-only)
    # ------------------------------------------------------------------

    rate = defaultdict(deque)
    rate_lock = threading.Lock()

    def limited(key, n=40, window=600):
        now = time.time()
        with rate_lock:
            dq = rate[key]
            while dq and now - dq[0] > window:
                dq.popleft()
            if len(dq) >= n:
                return True
            dq.append(now)
            return False

    def _guest_event(slug):
        ev = db.q1("SELECT * FROM events WHERE guest_slug=?", slug)
        if not ev or not is_paid(ev):
            return None
        return ev

    @app.route("/s/<slug>", methods=["GET"])
    def guest_page(slug):
        ev = _guest_event(slug)
        if not ev:
            return render_template("guest_missing.html"), 404
        return render_template("guest.html", ev=ev, info=outputs.event_info(ev), results=None, query="")

    @app.route("/s/<slug>", methods=["POST"])
    def guest_lookup(slug):
        ev = _guest_event(slug)
        if not ev:
            return render_template("guest_missing.html"), 404
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
        if limited((slug, ip)):
            return render_template("guest.html", ev=ev, info=outputs.event_info(ev), results=None, query="", error="Too many searches. Please wait a few minutes or ask at the welcome table."), 429
        query = request.form.get("name", "")[:120]
        key = lookup_key(query)
        results = []
        if len(key) >= 3:
            for r in db.q("SELECT name, table_label FROM guests WHERE event_id=? ORDER BY position", ev["id"]):
                if lookup_key(r["name"]) == key:
                    results.append(r)
        db.track("guest_lookup_hit" if results else "guest_lookup_miss", ev["id"])
        return render_template("guest.html", ev=ev, info=outputs.event_info(ev), results=results, query=query)

    # Demo guest pages for the fictional sample packages on the landing page.
    @app.route("/demo/<key>", methods=["GET", "POST"])
    def demo_guest(key):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_samples", os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "build_samples.py"))
        bs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bs)
        if key not in bs.SAMPLES:
            abort(404)
        title, d, venue, fn, *_ = bs.SAMPLES[key]
        guests = bs.guests_for(fn)
        ev = {"title": title + " (sample)"}
        results, query = None, ""
        if request.method == "POST":
            query = request.form.get("name", "")[:120]
            k = lookup_key(query)
            results = [{"name": gu.name, "table_label": gu.table} for gu in guests if len(k) >= 3 and lookup_key(gu.name) == k]
        sample_names = [guests[i].name for i in (0, 1, 2)]
        return render_template("guest.html", ev=ev, info=None, results=results, query=query, demo=True, sample_names=sample_names)

    # ------------------------------------------------------------------
    # Admin (owner) — funnel and orders. Requires ADMIN_TOKEN.
    # ------------------------------------------------------------------

    @app.route("/admin")
    def admin():
        tok = request.args.get("token", "")
        if not Config.ADMIN_TOKEN or not hmac.compare_digest(tok, Config.ADMIN_TOKEN):
            abort(404)
        names = ["visit", "start_view", "upload", "mapping_confirmed", "preview", "checkout_start", "paid", "download", "correction", "guest_lookup_hit", "guest_lookup_miss"]
        counts = {n: db.q1("SELECT COUNT(*) c, COUNT(DISTINCT event_id) e FROM funnel WHERE name=?", n) for n in names}
        sources = db.q("SELECT COALESCE(source,'(direct)') s, COUNT(*) c FROM funnel WHERE name='visit' GROUP BY s ORDER BY c DESC LIMIT 20")
        orders = db.q("SELECT e.id, e.title, e.event_date, e.paid_at, e.version, p.amount, p.duplicate FROM payments p JOIN events e ON e.id=p.event_id ORDER BY p.created_at DESC LIMIT 100")
        return render_template("admin.html", counts=counts, sources=sources, orders=orders)

    @app.errorhandler(PaymentRequired)
    def _402(e):
        return render_template("error.html", title="Payment required", msg="Print files unlock after checkout. Your watermarked preview is still available."), 402

    @app.errorhandler(403)
    def _403(e):
        return render_template("error.html", title="Private page", msg="Open your private management link to access this event."), 403

    @app.errorhandler(404)
    def _404(e):
        return render_template("error.html", title="Not found", msg="This page doesn't exist or has been deleted."), 404

    return app


# ----------------------------------------------------------------------
# Payment fulfilment (idempotent)
# ----------------------------------------------------------------------

def handle_event(evt: dict) -> str:
    eid_provider = evt.get("id", "")
    typ = evt.get("type", "")
    try:
        db.x("INSERT INTO webhook_events(provider_event_id, type, received_at) VALUES (?,?,?)", eid_provider, typ, time.time())
    except Exception:  # sqlite3.IntegrityError: already processed (provider retry)
        return "duplicate-event"
    if typ not in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        return "ignored"
    obj = evt.get("data", {}).get("object", {})
    sid = obj.get("id", "")
    if obj.get("payment_status") != "paid":
        return "not-paid"
    cs = db.q1("SELECT * FROM checkout_sessions WHERE session_id=?", sid)
    event_id = (obj.get("metadata") or {}).get("event_id") or obj.get("client_reference_id")
    if not cs or cs["event_id"] != event_id:
        log.error("webhook for unknown session %s / event %s", sid, event_id)
        return "unknown-session"
    if obj.get("amount_total") != Config.PRICE_CENTS or (obj.get("currency") or "").lower() != Config.CURRENCY:
        # Promotion codes change amount_total; accept but record it for review.
        log.warning("amount differs for %s: %s %s", sid, obj.get("amount_total"), obj.get("currency"))
    email = ((obj.get("customer_details") or {}).get("email") or "")[:200]
    try:
        db.x(
            "INSERT INTO payments(event_id, session_id, amount, currency, created_at) VALUES (?,?,?,?,?)",
            event_id, sid, int(obj.get("amount_total") or 0), (obj.get("currency") or "").lower(), time.time(),
        )
    except Exception:
        return "duplicate-session"
    db.x("UPDATE checkout_sessions SET status='complete' WHERE session_id=?", sid)
    cur = db.x("UPDATE events SET status='paid', paid_at=?, customer_email=? WHERE id=? AND status='draft'", time.time(), email, event_id)
    if cur.rowcount != 1:
        # Already paid via another session: flag for a refund, don't fulfil twice.
        db.x("UPDATE payments SET duplicate=1 WHERE session_id=?", sid)
        log.error("DUPLICATE PAYMENT for event %s session %s — refund needed", event_id, sid)
        return "duplicate-payment"
    db.track("paid", event_id)
    ev = db.q1("SELECT * FROM events WHERE id=?", event_id)
    emailer.send_receipt(ev, email)
    return "fulfilled"


# ----------------------------------------------------------------------
# Retention
# ----------------------------------------------------------------------

def delete_after(ev) -> date | None:
    if not ev["event_date"]:
        return None
    return date.fromisoformat(ev["event_date"]) + timedelta(days=Config.RETENTION_DAYS_AFTER_EVENT)


def _delete(event_id):
    db.x("DELETE FROM guests WHERE event_id=?", event_id)
    db.x("DELETE FROM checkout_sessions WHERE event_id=?", event_id)
    db.x("DELETE FROM events WHERE id=?", event_id)
    db.x("UPDATE funnel SET event_id=NULL WHERE event_id=?", event_id)
    # Payment rows keep amount/date for bookkeeping but not names or guest data.
    outputs.clear_cache(event_id)


_last_purge = [0.0]


def _maybe_purge():
    if time.time() - _last_purge[0] > 3600:
        purge()


def purge() -> int:
    _last_purge[0] = time.time()
    n = 0
    today = date.today()
    for ev in db.q("SELECT * FROM events"):
        if ev["status"] == "paid":
            d = delete_after(ev)
            if d and d < today:
                _delete(ev["id"]); n += 1
        elif time.time() - ev["updated_at"] > Config.DRAFT_RETENTION_DAYS * 86400:
            _delete(ev["id"]); n += 1
    return n
