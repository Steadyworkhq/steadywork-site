"""Glue between stored events and the renderers, with a small on-disk cache."""
from __future__ import annotations

import io
import os
import shutil
import zipfile
from datetime import date

import pypdfium2 as pdfium

from . import db
from . import designs as D
from .config import Config
from .guestlist import Guest
from .render import (
    EventInfo,
    render_backup_list,
    render_chart,
    render_place_cards,
    render_qr_sign,
)

KINDS = {
    "chart": "seating-chart",
    "chart-alpha": "seating-chart-alphabetical",
    "cards": "place-cards",
    "sign": "qr-sign",
    "backup": "guest-lookup-list",
}


def guest_url(ev_row) -> str:
    return f"{Config.BASE_URL}/s/{ev_row['guest_slug']}"


def load_guests(event_id) -> list[Guest]:
    rows = db.q("SELECT name, table_label, last FROM guests WHERE event_id=? ORDER BY position", event_id)
    return [Guest(name=r["name"], table=r["table_label"], last=r["last"], row=i + 1) for i, r in enumerate(rows)]


def event_info(ev_row) -> EventInfo:
    d = None
    if ev_row["event_date"]:
        try:
            d = date.fromisoformat(ev_row["event_date"])
        except ValueError:
            d = None
    return EventInfo(title=ev_row["title"] or "Your names", event_date=d, venue=ev_row["venue"] or "", design=ev_row["design"], region=ev_row["region"])


def _cache_dir(event_id):
    return os.path.join(Config.DATA_DIR, "cache", event_id)


def clear_cache(event_id):
    shutil.rmtree(_cache_dir(event_id), ignore_errors=True)


def render_kind(ev_row, kind: str, preview: bool):
    guests = load_guests(ev_row["id"])
    info = event_info(ev_row)
    other_layout = "alpha" if ev_row["chart_layout"] == "table" else "table"
    if kind == "chart":
        return render_chart(info, guests, ev_row["chart_size"], ev_row["chart_layout"], ev_row["sort_by"], preview)
    if kind == "chart-alpha":
        return render_chart(info, guests, ev_row["chart_size"], other_layout, ev_row["sort_by"], preview)
    if kind == "cards":
        return render_place_cards(info, guests, ev_row["paper"], ev_row["sort_by"], ev_row["card_order"], preview)
    if kind == "sign":
        return render_qr_sign(info, guest_url(ev_row), ev_row["paper"], preview)
    if kind == "backup":
        return render_backup_list(info, guests, ev_row["paper"], ev_row["sort_by"], preview)
    raise KeyError(kind)


def get_pdf(ev_row, kind: str, preview: bool) -> bytes:
    d = _cache_dir(ev_row["id"])
    os.makedirs(d, exist_ok=True)
    tag = "preview" if preview else "final"
    p = os.path.join(d, f"v{ev_row['version']}-{kind}-{tag}.pdf")
    if os.path.exists(p):
        with open(p, "rb") as f:
            return f.read()
    pdf, _ = render_kind(ev_row, kind, preview)
    with open(p, "wb") as f:
        f.write(pdf)
    return pdf


def preview_png(ev_row, kind: str, page: int = 0, long_edge: int = 1600) -> bytes:
    d = _cache_dir(ev_row["id"])
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"v{ev_row['version']}-{kind}-p{page}-{long_edge}.png")
    if os.path.exists(p):
        with open(p, "rb") as f:
            return f.read()
    pdf = pdfium.PdfDocument(get_pdf(ev_row, kind, preview=True))
    page = max(0, min(page, len(pdf) - 1))
    pg = pdf[page]
    w, h = pg.get_size()
    img = pg.render(scale=long_edge / max(w, h)).to_pil().convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    data = buf.getvalue()
    with open(p, "wb") as f:
        f.write(data)
    return data


def page_count(ev_row, kind) -> int:
    return len(pdfium.PdfDocument(get_pdf(ev_row, kind, preview=True)))


def zip_all(ev_row) -> bytes:
    buf = io.BytesIO()
    slug = "".join(ch for ch in (ev_row["title"] or "event") if ch.isalnum() or ch in " -").strip().replace(" ", "-")[:40] or "event"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for kind, fname in KINDS.items():
            z.writestr(f"{slug}-{fname}.pdf", get_pdf(ev_row, kind, preview=False))
        z.writestr("README.txt", README_TXT.format(url=guest_url(ev_row)))
    return buf.getvalue()


README_TXT = """Your seating package
====================

seating-chart.pdf              Main chart, exact poster size. Print at 100% ("Actual size").
seating-chart-alphabetical.pdf The same guests in the other layout, if you prefer it.
place-cards.pdf                Page 1 is the printing and folding guide.
qr-sign.pdf                    Opens your find-your-seat page: {url}
guest-lookup-list.pdf          Plain alphabetical list for the welcome table, in case
                               phones can't get a signal at the venue.

Anyone with the QR link can look up a guest by typing their full name.
The page is not listed in search engines and does not show the full guest list.

If you correct names or tables later, download the files again; printed copies
do not update themselves, but the QR page updates immediately.
"""


def coverage_issues(guests: list[Guest], design_key: str) -> tuple[list[str], list[str]]:
    """Names that need the fallback font, and names with characters we can't draw."""
    d = D.DESIGNS[design_key]
    fallback, missing = [], []
    for g in guests:
        if not D.font_has(d.name_font, g.name):
            if D.font_has(d.fallback_font, g.name):
                fallback.append(g.name)
            else:
                missing.append(g.name)
    return fallback, missing
