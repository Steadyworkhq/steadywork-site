"""Deterministic PDF rendering: seating chart, place cards, QR sign, backup list.

Every function returns (pdf_bytes, manifest). The manifest lists every guest
name that was drawn, with its page, font size, drawn width and the width it was
allowed. Tests use it to prove no name was clipped or omitted.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from datetime import date

import qrcode
from reportlab.lib.colors import Color, white
from reportlab.lib.units import inch, mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

from . import designs as D
from .guestlist import (
    Guest,
    alpha_sorted,
    grouped_by_table,
    letter_of,
    table_display,
    table_is_numbered,
)

CHART_SIZES = {
    # key: (label, width_pt, height_pt)
    "16x20": ('16 × 20 in', 16 * inch, 20 * inch),
    "18x24": ('18 × 24 in', 18 * inch, 24 * inch),
    "24x36": ('24 × 36 in', 24 * inch, 36 * inch),
    "a2": ("A2 (420 × 594 mm)", 420 * mm, 594 * mm),
    "a1": ("A1 (594 × 841 mm)", 594 * mm, 841 * mm),
}

PAPERS = {
    "letter": ("US Letter (8.5 × 11 in)", 8.5 * inch, 11 * inch),
    "a4": ("A4 (210 × 297 mm)", 210 * mm, 297 * mm),
}

SIGN_SIZES = {
    "letter": ("8 × 10 in", 8 * inch, 10 * inch),
    "a4": ("A4 (210 × 297 mm)", 210 * mm, 297 * mm),
}


# Smallest guest-name size allowed on a poster. If a list can't fit at this size
# we split it across posters instead of printing smaller text.
MIN_NAME_PT = 11.0


@dataclass
class EventInfo:
    title: str  # e.g. "Ava & Jonah"
    event_date: date | None
    venue: str = ""
    design: str = "minimal"
    region: str = "us"  # "us" -> "June 12, 2027"; "intl" -> "12 June 2027"


@dataclass
class Placed:
    name: str
    table: str
    page: int
    size: float
    width: float
    max_width: float
    font: str


@dataclass
class Manifest:
    kind: str
    pages: int = 0
    page_size: tuple[float, float] = (0, 0)
    placed: list[Placed] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    font_size: float = 0


def format_date(d: date | None, region: str) -> str:
    if not d:
        return ""
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    if region == "intl":
        return f"{d.day} {months[d.month - 1]} {d.year}"
    return f"{months[d.month - 1]} {d.day}, {d.year}"


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------

def tracked_width(text, font, size, tracking_em):
    if not text:
        return 0.0
    return stringWidth(text, font, size) + tracking_em * size * (len(text) - 1)


def draw_text(c, x, y, text, font, size, tracking_em=0.0, align="left", color=None):
    w = tracked_width(text, font, size, tracking_em)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    c.saveState()
    if color is not None:
        c.setFillColor(color)
    t = c.beginText(x, y)
    t.setFont(font, size)
    if tracking_em:
        t.setCharSpace(tracking_em * size)
    t.textOut(text)
    c.drawText(t)
    c.restoreState()
    return w


def fit_size(text, font, max_w, start, minimum, tracking=0.0):
    s = start
    while s > minimum and tracked_width(text, font, s, tracking) > max_w:
        s -= 0.25
    return s


def wrap_words(text, font, size, max_w):
    """Greedy word wrap. Returns lines; a single overlong word stays whole."""
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip() if cur else w
        if stringWidth(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def watermark(c, w, h):
    c.saveState()
    c.setFillColor(Color(0.55, 0.1, 0.1, alpha=0.16))
    size = min(w, h) / 9
    c.setFont("Jost-Medium", size)
    c.translate(w / 2, h / 2)
    c.rotate(35)
    step = size * 2.6
    span = int(max(w, h) / step) + 3
    for i in range(-span, span + 1):
        for j in range(-span, span + 1):
            c.drawCentredString(i * size * 7.5 + (j % 2) * size * 3.7, j * step, "PREVIEW")
    c.restoreState()


def new_canvas(w, h, title):
    D.register_fonts()
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(w, h), pageCompression=1, initialFontName="Jost", initialFontSize=10)
    c.setTitle(title)
    c.setAuthor("Kindly Seated")
    c.setCreator("Kindly Seated (kindlyseatedco.com)")
    return c, buf


# --------------------------------------------------------------------------
# Header shared by chart and sign
# --------------------------------------------------------------------------

def draw_header(c, design: D.Design, ev: EventInfo, w, top, scale, kicker=None, page_label=""):
    """Draws kicker, couple title, date. Returns y below header."""
    cx = w / 2
    y = top
    kicker = kicker if kicker is not None else design.kicker_text
    ks = scale * 0.42
    kt = kicker.upper() if design.key == "minimal" else kicker
    kf = design.pick(design.kicker_font, kt)
    draw_text(c, cx, y - ks, kt, kf, ks, 0.22 if design.key == "minimal" else 0.02, "center", design.soft if design.key == "minimal" else design.accent)
    y -= ks * 2.0
    title = ev.title.upper() if design.upper_title else ev.title
    tf = design.pick(design.title_font, title)
    ts = fit_size(title, tf, w * 0.84, scale * (1.0 if design.upper_title else 1.25), scale * 0.35, design.title_tracking)
    draw_text(c, cx, y - ts * 0.8, title, tf, ts, design.title_tracking, "center", design.ink)
    y -= ts * 1.15
    sub = format_date(ev.event_date, ev.region)
    if ev.venue:
        sub = f"{sub}  ·  {ev.venue}" if sub else ev.venue
    if page_label:
        sub = f"{sub}  ·  {page_label}" if sub else page_label
    if sub:
        ss = fit_size(sub, design.pick(design.small_font, sub), w * 0.8, scale * 0.36, scale * 0.2)
        sf = design.pick(design.small_font, sub)
        sub_t = sub.upper() if design.key == "minimal" else sub
        sf = design.pick(design.small_font, sub_t)
        draw_text(c, cx, y - ss, sub_t, sf, ss, 0.14 if design.key == "minimal" else 0.0, "center", design.soft)
        y -= ss * 2.2
    if design.key == "botanical":
        y -= scale * 0.3  # leaves need room above the stem
    D.divider(design, c, cx, y, min(w * 0.28, scale * 6), lw=max(0.5, scale / 60))
    return y - scale * 0.6


# --------------------------------------------------------------------------
# Seating chart
# --------------------------------------------------------------------------

@dataclass
class Line:
    kind: str  # "head" | "name" | "letter" | "gap"
    text: str
    size: float
    font: str
    height: float
    guest: Guest | None = None
    label: str = ""  # alpha layout: table label at right


def _name_lines(design, g: Guest, size, max_w):
    """Lines for one guest name.

    1. Fits as-is.  2. Otherwise shrink this one name down to 75%.
    3. Otherwise wrap by words (each line may shrink to 60%).
    Returns None if it cannot fit, so the layout picks a smaller size —
    names are never clipped.
    """
    font = design.pick(design.name_font, g.name)
    if stringWidth(g.name, font, size) <= max_w:
        return [(g.name, size)], font
    floor = max(size * 0.75, min(size, MIN_NAME_PT))
    s = size
    while s > floor and stringWidth(g.name, font, s) > max_w:
        s -= 0.25
    if stringWidth(g.name, font, s) <= max_w:
        return [(g.name, s)], font
    out = []
    for ln in wrap_words(g.name, font, size * 0.9, max_w):
        s = size * 0.9
        while stringWidth(ln, font, s) > max_w and s > max(size * 0.6, min(size, MIN_NAME_PT)):
            s -= 0.25
        if stringWidth(ln, font, s) > max_w:
            return None, font  # cannot fit at this size
        out.append((ln, s))
    return out, font


def _build_table_blocks(design, groups, size, col_w):
    blocks = []
    hs = size * 1.05
    for label, gs in groups:
        head = table_display(label)
        head_t = head.upper() if design.upper_headings else head
        hf = design.pick(design.heading_font, head_t)
        if tracked_width(head_t, hf, hs, design.heading_tracking) > col_w:
            s2 = fit_size(head_t, hf, col_w, hs, hs * 0.6, design.heading_tracking)
            if tracked_width(head_t, hf, s2, design.heading_tracking) > col_w:
                return None
        else:
            s2 = hs
        lines = [Line("head", head_t, s2, hf, hs * 1.75)]
        for g in gs:
            nl, nf = _name_lines(design, g, size, col_w)
            if nl is None:
                return None
            for k, (t, s) in enumerate(nl):
                lines.append(Line("name", t, s, nf, size * (1.32 if k == 0 else 1.02), guest=g if k == 0 else None))
        blocks.append((label, lines))
    return blocks


def _build_alpha_lines(design, guests, size, col_w, sort_by):
    lines = []
    sorted_g = alpha_sorted(guests, sort_by)
    label_font = design.pick(design.heading_font, "0123456789")
    labels = {g.table: (g.table if table_is_numbered(g.table) else g.table) for g in sorted_g}
    lab_w = max((stringWidth(v, design.pick(design.name_font, v), size) for v in labels.values()), default=0)
    lab_w = min(lab_w, col_w * 0.45)
    name_w = col_w - lab_w - size * 1.2
    if name_w < col_w * 0.4:
        return None
    current = None
    blocks = []
    for g in sorted_g:
        L = letter_of(g, sort_by)
        if L != current:
            current = L
            blocks.append((L, [Line("letter", L, size * 1.1, design.pick(design.heading_font, L), size * 1.9)]))
        nl, nf = _name_lines(design, g, size, name_w)
        if nl is None:
            return None
        lab = labels[g.table]
        lf = design.pick(design.name_font, lab)
        ls = size
        while stringWidth(lab, lf, ls) > lab_w and ls > size * 0.6:
            ls -= 0.25
        if stringWidth(lab, lf, ls) > lab_w:
            return None
        for k, (t, s) in enumerate(nl):
            blocks[-1][1].append(
                Line("name", t, s, nf, size * (1.32 if k == 0 else 1.02), guest=g if k == 0 else None, label=lab if k == len(nl) - 1 else "")
            )
            if k == len(nl) - 1:
                blocks[-1][1][-1].size_label = ls  # type: ignore[attr-defined]
                blocks[-1][1][-1].label_font = lf  # type: ignore[attr-defined]
    return blocks, name_w, lab_w


def _flow(blocks, ncols, col_h, allow_split):
    """Place blocks into columns. Returns list of columns (list of lines) or None."""
    cols = [[]]
    used = 0.0
    for label, lines in blocks:
        bh = sum(l.height for l in lines)
        gap = lines[0].height * 0.55 if cols[-1] else 0
        if used + gap + bh <= col_h:
            if cols[-1]:
                cols[-1].append(Line("gap", "", 0, "", gap))
                used += gap
            cols[-1].extend(lines)
            used += bh
            continue
        if bh <= col_h and not allow_split:
            cols.append(list(lines))
            used = bh
        elif bh <= col_h:
            cols.append(list(lines))
            used = bh
        else:
            # Table/letter longer than a whole column: split with a "continued" head.
            head = lines[0]
            rest = lines[1:]
            if cols[-1]:
                cols.append([])
                used = 0.0
            cols[-1].append(head)
            used = head.height
            for ln in rest:
                if used + ln.height > col_h:
                    cont = Line(head.kind, head.text + (" (cont.)" if head.kind == "head" else ""), head.size, head.font, head.height)
                    cols.append([cont])
                    used = cont.height
                cols[-1].append(ln)
                used += ln.height
        if len(cols) > ncols:
            return None
    if len(cols) > ncols:
        return None
    return cols


def _layout_chart(design, guests, layout, sort_by, w, h, content_top, margin, min_size, max_size, pages):
    """Find the largest font size that fits all guests across `pages` posters."""
    content_h = content_top - margin * 1.3
    content_w = w - 2 * margin
    best = None
    if layout == "table":
        groups = grouped_by_table(guests, sort_by)
        chunks = _split_groups(groups, pages)
    else:
        chunks = _split_alpha(guests, sort_by, pages)
    for ncols in range(1, 11):
        gutter = content_w * 0.035
        col_w = (content_w - gutter * (ncols - 1)) / ncols
        lo, hi = min_size, max_size
        found = None
        for _ in range(22):
            mid = (lo + hi) / 2
            ok = True
            res = []
            for chunk in chunks:
                if layout == "table":
                    blocks = _build_table_blocks(design, chunk, mid, col_w)
                    extra = None
                else:
                    r = _build_alpha_lines(design, chunk, mid, col_w, sort_by)
                    blocks, extra = (r[0], r[1:]) if r else (None, None)
                if blocks is None:
                    ok = False
                    break
                cols = _flow(blocks, ncols, content_h, allow_split=True)
                if cols is None:
                    ok = False
                    break
                res.append((cols, extra))
            if ok:
                found = (mid, res)
                lo = mid
            else:
                hi = mid
            if hi - lo < 0.1:
                break
        if found:
            score = _score(found[0], found[1])
            if best is None or score > best[5] + 0.01:
                best = (found[0], ncols, col_w, gutter, found[1], score)
    return best[:5] if best else None


def _score(size, page_results):
    """Readability score: base size, penalised by shrunken or wrapped names."""
    sizes, wraps = [], 0
    for cols, _ in page_results:
        for col in cols:
            for ln in col:
                if ln.kind == "name":
                    sizes.append(ln.size)
                    if ln.guest is None:
                        wraps += 1
    if not sizes:
        return size
    worst = min(sizes) / size
    return size * (worst ** 0.7) * (0.985 ** wraps)


def _split_groups(groups, pages):
    if pages == 1:
        return [groups]
    total = sum(len(g) + 2 for _, g in groups)
    target = total / pages
    chunks, cur, acc = [], [], 0
    for item in groups:
        if cur and acc + len(item[1]) / 2 > target * (len(chunks) + 1) and len(chunks) < pages - 1:
            chunks.append(cur)
            cur = []
        cur.append(item)
        acc += len(item[1]) + 2
    chunks.append(cur)
    return chunks


def _split_alpha(guests, sort_by, pages):
    s = alpha_sorted(guests, sort_by)
    if pages == 1:
        return [s]
    n = len(s)
    chunks = []
    for p in range(pages):
        chunks.append(s[p * n // pages:(p + 1) * n // pages])
    return chunks


def render_chart(ev: EventInfo, guests: list[Guest], size_key="18x24", layout="table", sort_by="last", preview=False):
    design = D.DESIGNS[ev.design]
    label, w, h = CHART_SIZES[size_key]
    margin = min(w, h) * 0.075
    scale = min(w, h) / 14  # header scale
    man = Manifest(kind=f"chart-{layout}", page_size=(w, h))
    min_size = max(12.0, min(w, h) / 110)
    max_size = min(w, h) / 34
    for pages in range(1, 6):
        # Header height estimate (draw on a scratch canvas to measure).
        scratch, _ = new_canvas(w, h, "scratch")
        header_bottom = draw_header(scratch, design, ev, w, h - margin, scale, page_label="Tables 1–99" if pages > 1 else "")
        if design.key == "botanical":
            header_bottom -= 0
        best = _layout_chart(design, guests, layout, sort_by, w, h, header_bottom, margin, min_size, max_size, pages)
        if best:
            break
    if not best:
        raise ValueError("Guest list is too large for this chart size even across 5 posters.")
    size, ncols, col_w, gutter, page_results = best
    page_results = _balance(design, guests, layout, sort_by, chunks_for(guests, layout, sort_by, pages), size, ncols, col_w, page_results)
    man.font_size = size
    if pages > 1:
        man.warnings.append(
            f"To keep names readable at {label}, your chart is split across {pages} posters. "
            "Choose a larger size if you'd like a single poster."
        )
    c, buf = new_canvas(w, h, f"Seating chart — {ev.title}")
    chunks = _split_groups(grouped_by_table(guests, sort_by), pages) if layout == "table" else _split_alpha(guests, sort_by, pages)
    for p, (cols, extra) in enumerate(page_results):
        page_label = ""
        if pages > 1:
            if layout == "table":
                page_label = f"{table_display(chunks[p][0][0])} – {table_display(chunks[p][-1][0])}"
            else:
                page_label = f"{letter_of(chunks[p][0], sort_by)} – {letter_of(chunks[p][-1], sort_by)}"
        _decorate(c, design, w, h, margin)
        top = draw_header(c, design, ev, w, h - margin, scale, page_label=page_label)
        # Center columns horizontally when fewer than planned are used.
        used = len(cols)
        total_w = used * col_w + (used - 1) * gutter
        x0 = (w - total_w) / 2
        # Vertically: start just below header; balance by centering tallest column.
        tallest = max(sum(l.height for l in col) for col in cols)
        avail = top - margin * 1.3
        y_start = top - max(0, (avail - tallest) * 0.25)
        for ci, col in enumerate(cols):
            x = x0 + ci * (col_w + gutter)
            y = y_start
            for ln in col:
                y -= ln.height
                if ln.kind == "gap":
                    continue
                base = y + ln.height * 0.28
                if layout == "table":
                    cx = x + col_w / 2
                    if ln.kind == "head":
                        draw_text(c, cx, base, ln.text, ln.font, ln.size, design.heading_tracking, "center", design.accent if design.key != "minimal" else design.ink)
                    else:
                        wdt = draw_text(c, cx, base, ln.text, ln.font, ln.size, 0, "center", design.ink)
                        if ln.guest is not None:
                            man.placed.append(Placed(ln.guest.name, ln.guest.table, p + 1, ln.size, wdt, col_w, ln.font))
                        elif man.placed:  # continuation line of a wrapped name
                            last = man.placed[-1]
                            last.size = min(last.size, ln.size)
                            last.width = max(last.width, wdt)
                else:
                    if ln.kind == "letter":
                        draw_text(c, x, base, ln.text, ln.font, ln.size, 0.05, "left", design.accent if design.key != "minimal" else design.ink)
                    else:
                        wdt = draw_text(c, x, base, ln.text, ln.font, ln.size, 0, "left", design.ink)
                        name_w = extra[0]
                        if ln.label:
                            lw = draw_text(c, x + col_w, base, ln.label, ln.label_font, ln.size_label, 0, "right", design.ink)
                            # dotted leader
                            c.saveState()
                            c.setFillColor(design.soft)
                            dot_start = x + wdt + ln.size * 0.5
                            dot_end = x + col_w - lw - ln.size * 0.5
                            step = ln.size * 0.42
                            xx = dot_start
                            while xx < dot_end:
                                c.circle(xx, base + ln.size * 0.12, max(0.35, ln.size * 0.035), stroke=0, fill=1)
                                xx += step
                            c.restoreState()
                        if ln.guest is not None:
                            man.placed.append(Placed(ln.guest.name, ln.guest.table, p + 1, ln.size, wdt, name_w, ln.font))
                        elif man.placed:
                            last = man.placed[-1]
                            last.size = min(last.size, ln.size)
                            last.width = max(last.width, wdt)
        if preview:
            watermark(c, w, h)
        c.showPage()
    c.save()
    man.pages = pages
    return buf.getvalue(), man


def chunks_for(guests, layout, sort_by, pages):
    if layout == "table":
        return _split_groups(grouped_by_table(guests, sort_by), pages)
    return _split_alpha(guests, sort_by, pages)


def _balance(design, guests, layout, sort_by, chunks, size, ncols, col_w, page_results):
    """Re-flow each page with the shortest column height that still fits."""
    out = []
    for chunk, (cols, extra) in zip(chunks, page_results):
        if layout == "table":
            blocks = _build_table_blocks(design, chunk, size, col_w)
        else:
            r = _build_alpha_lines(design, chunk, size, col_w, sort_by)
            blocks = r[0]
        hi = max(sum(l.height for l in col) for col in cols)
        lo = hi / ncols
        if layout == "table":
            # Never split a table just to balance columns.
            lo = max(lo, max(sum(l.height for l in b[1]) for b in blocks) - 0.01)
        best = cols
        for _ in range(25):
            mid = (lo + hi) / 2
            f = _flow(blocks, ncols, mid, allow_split=True)
            if f is not None:
                best, hi = f, mid
            else:
                lo = mid
        out.append((best, extra))
    return out


def minimal_rule_under(c, cx, y, width, design):
    c.saveState()
    c.setStrokeColor(design.soft)
    c.setLineWidth(0.5)
    c.line(cx - width / 2, y, cx + width / 2, y)
    c.restoreState()


def _decorate(c, design, w, h, margin):
    if design.key == "botanical":
        D.corner_greenery(c, w, h, design.accent, min(w, h) * 0.17)
        D.bottom_greenery(c, w / 2, margin * 0.55, design.accent, min(w, h) * 0.12)
    elif design.key == "classic":
        c.saveState()
        c.setStrokeColor(design.accent)
        inset = margin * 0.45
        c.setLineWidth(max(0.8, min(w, h) / 900))
        c.rect(inset, inset, w - 2 * inset, h - 2 * inset)
        c.setLineWidth(max(0.4, min(w, h) / 2400))
        i2 = inset + min(w, h) * 0.006
        c.rect(i2, i2, w - 2 * i2, h - 2 * i2)
        c.restoreState()


# --------------------------------------------------------------------------
# Place cards (tent fold)
# --------------------------------------------------------------------------

CARD_SPECS = {
    # paper: (card width, unfolded height, cols, rows, gutter)
    "letter": (3.75 * inch, 5.0 * inch, 2, 2, 0.25 * inch),
    "a4": (90 * mm, 120 * mm, 2, 2, 6 * mm),
}


def _crop_marks(c, x, y, cw, ch, length, offset):
    c.saveState()
    c.setStrokeColor(Color(0, 0, 0))
    c.setLineWidth(0.4)
    for (px, py, dx, dy) in ((x, y, -1, -1), (x + cw, y, 1, -1), (x, y + ch, -1, 1), (x + cw, y + ch, 1, 1)):
        c.line(px + dx * offset, py, px + dx * (offset + length), py)
        c.line(px, py + dy * offset, px, py + dy * (offset + length))
    c.restoreState()


def _fold_ticks(c, x, y, cw, length, offset):
    c.saveState()
    c.setStrokeColor(Color(0.4, 0.4, 0.4))
    c.setLineWidth(0.4)
    c.setDash(2, 2)
    c.line(x - offset - length, y, x - offset, y)
    c.line(x + cw + offset, y, x + cw + offset + length, y)
    c.restoreState()


def _card_face(c, design, ev, g: Guest, x, y, cw, chh, man, page, preview):
    """Front face (lower half of unfolded card), upright."""
    pad = cw * 0.09
    max_w = cw - 2 * pad
    cx = x + cw / 2
    if design.key == "botanical":
        D.sprig(c, cx - 2, y + chh * 0.80, cw * 0.17, 172, design.accent, leaves=5, mirror=True)
        D.sprig(c, cx + 2, y + chh * 0.80, cw * 0.17, 8, design.accent, leaves=5)
    elif design.key == "classic":
        D.classic_rule(c, cx, y + chh * 0.80, cw * 0.30, design.accent, 0.5)
    else:
        D.minimal_rule(c, cx, y + chh * 0.82, cw * 0.12, design.ink, 0.5)
    font = design.pick(design.name_font if design.key != "botanical" else "Cormorant-MediumItalic", g.name)
    if design.key == "botanical" and font == design.fallback_font:
        font = design.pick(design.name_font, g.name)
    start = chh * 0.20
    size = fit_size(g.name, font, max_w, start, chh * 0.115)
    lines = [(g.name, size)]
    if stringWidth(g.name, font, size) > max_w:
        size = chh * 0.15
        lines = []
        for ln in wrap_words(g.name, font, size, max_w):
            s = fit_size(ln, font, max_w, size, chh * 0.07)
            lines.append((ln, s))
        if len(lines) > 3:
            size = chh * 0.10
            lines = [(ln, fit_size(ln, font, max_w, size, chh * 0.05)) for ln in wrap_words(g.name, font, size, max_w)]
    total = sum(s * 1.15 for _, s in lines)
    yy = y + chh * 0.50 + total / 2
    for k, (ln, s) in enumerate(lines):
        yy -= s * 1.15
        wdt = draw_text(c, cx, yy + s * 0.2, ln, font, s, 0, "center", design.ink)
        if k == 0:
            man.placed.append(Placed(g.name, g.table, page, s, max(wdt, max(stringWidth(l2, font, s2) for l2, s2 in lines)), max_w, font))
    tl = table_display(g.table)
    tl_t = tl.upper() if design.upper_headings else tl
    tf = design.pick(design.small_font if design.key != "minimal" else "Jost", tl_t)
    ts = fit_size(tl_t, tf, max_w, chh * 0.075, chh * 0.04, 0.16 if design.key == "minimal" else 0)
    draw_text(c, cx, y + chh * 0.16, tl_t, tf, ts, 0.16 if design.key == "minimal" else 0, "center", design.soft if design.key == "minimal" else design.accent)


def _card_back(c, design, ev, g, x, y, cw, chh):
    """Back face (upper half), rotated 180° so it reads correctly once folded."""
    c.saveState()
    c.translate(x + cw / 2, y + chh / 2)
    c.rotate(180)
    title = ev.title
    tf = design.pick(design.small_font, title)
    ts = fit_size(title, tf, cw * 0.8, chh * 0.075, chh * 0.04)
    draw_text(c, 0, -chh * 0.05, title, tf, ts, 0, "center", design.soft)
    d = format_date(ev.event_date, ev.region)
    if d:
        df = design.pick(design.small_font, d)
        draw_text(c, 0, -chh * 0.05 - ts * 1.5, d, df, ts * 0.8, 0, "center", design.soft)
    c.restoreState()


def _calibration_page(c, w, h, design, ev, paper, n_cards, sheets):
    c.setFillColor(design.ink)
    m = 0.9 * inch
    y = h - m
    draw_text(c, m, y, "Place cards — printing guide", "Jost-Medium", 20)
    y -= 30
    draw_text(c, m, y, f"{ev.title} · {n_cards} cards on {sheets} sheets · {PAPERS[paper][0]}", "Jost", 10.5, color=design.soft)
    y -= 34
    steps = [
        "1. Print at 100% / “Actual size”. Do not choose “Fit to page” or “Scale to fit”.",
        "2. Check the square below with a ruler before printing every sheet.",
        "3. Use matte cardstock (about 65–110 lb cover / 175–300 gsm) your printer supports.",
        "4. Cut along the corner crop marks. Each card is cut separately.",
        "5. Score lightly along the dashed fold ticks, then fold away from the printed name.",
        "6. Cards are ordered by table so you can bundle them for setup. The back of",
        "    each card shows your names and date, so it reads correctly from either side.",
        "7. Printed 2 × 2 per sheet. Front face finished size:",
    ]
    spec = CARD_SPECS[paper]
    finished = "3.75 × 2.5 in" if paper == "letter" else "90 × 60 mm"
    steps[-1] += f" {finished}."
    for s in steps:
        draw_text(c, m, y, s, "Jost", 11)
        y -= 18
    y -= 26
    side = 1 * inch if paper == "letter" else 25 * mm
    lab = "This square should measure exactly 1 inch" if paper == "letter" else "This square should measure exactly 25 mm"
    c.setStrokeColor(design.ink)
    c.setLineWidth(0.6)
    c.rect(m, y - side, side, side)
    draw_text(c, m + side + 14, y - side / 2 - 4, lab, "Jost", 11)
    y -= side + 40
    draw_text(c, m, y, "Tip: print one test sheet on plain paper and fold it before using cardstock.", "Jost-Light", 11, color=design.soft)


def render_place_cards(ev: EventInfo, guests: list[Guest], paper="letter", sort_by="last", order="table", preview=False):
    design = D.DESIGNS[ev.design]
    plabel, pw, ph = PAPERS[paper]
    cw, ch, cols, rows, gut = CARD_SPECS[paper]
    per = cols * rows
    if order == "table":
        ordered = [g for _, gs in grouped_by_table(guests, sort_by) for g in gs]
    else:
        ordered = alpha_sorted(guests, sort_by)
    sheets = max(1, math.ceil(len(ordered) / per))
    man = Manifest(kind="place-cards", page_size=(pw, ph))
    c, buf = new_canvas(pw, ph, f"Place cards — {ev.title}")
    _calibration_page(c, pw, ph, design, ev, paper, len(ordered), sheets)
    c.showPage()
    grid_w = cols * cw + (cols - 1) * gut
    grid_h = rows * ch + (rows - 1) * gut
    x0 = (pw - grid_w) / 2
    y0 = (ph - grid_h) / 2
    mark_len = min(gut * 0.9, 0.18 * inch)
    for s in range(sheets):
        batch = ordered[s * per:(s + 1) * per]
        page = s + 2
        for i, g in enumerate(batch):
            col = i % cols
            row = i // cols
            x = x0 + col * (cw + gut)
            y = y0 + (rows - 1 - row) * (ch + gut)
            half = ch / 2
            _card_face(c, design, ev, g, x, y, cw, half, man, page, preview)
            _card_back(c, design, ev, g, x, y + half, cw, half)
            _crop_marks(c, x, y, cw, ch, mark_len, 0.04 * inch)
            _fold_ticks(c, x, y + half, cw, mark_len, 0.04 * inch)
        tables = sorted({table_display(g.table) for g in batch}, key=lambda t: [g.table for g in batch].index(next(g.table for g in batch if table_display(g.table) == t)))
        foot = f"Sheet {s + 1} of {sheets}  ·  {', '.join(tables)}"
        ff = "DejaVuSans" if not D.font_has("Jost", foot) else "Jost"
        # Centred under the first card, clear of the crop marks at card corners.
        draw_text(c, x0 + cw / 2, y0 * 0.42, foot, ff, 7, 0, "center", Color(0.45, 0.45, 0.45))
        if preview:
            watermark(c, pw, ph)
        c.showPage()
    c.save()
    man.pages = sheets + 1
    return buf.getvalue(), man


# --------------------------------------------------------------------------
# QR sign
# --------------------------------------------------------------------------

def qr_matrix(url: str):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=0, box_size=1)
    q.add_data(url)
    q.make(fit=True)
    return q.get_matrix()


def draw_qr(c, url, x, y, size, color):
    m = qr_matrix(url)
    n = len(m)
    quiet = 4
    cell = size / (n + 2 * quiet)
    c.saveState()
    c.setFillColor(white)
    c.rect(x, y, size, size, stroke=0, fill=1)
    c.setFillColor(color)
    p = c.beginPath()
    for r, row in enumerate(m):
        for k, on in enumerate(row):
            if on:
                px = x + (quiet + k) * cell
                py = y + size - (quiet + r + 1) * cell
                p.rect(px, py, cell + 0.01, cell + 0.01)
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()
    return n


def render_qr_sign(ev: EventInfo, url: str, paper="letter", preview=False):
    design = D.DESIGNS[ev.design]
    label, w, h = SIGN_SIZES[paper]
    man = Manifest(kind="qr-sign", page_size=(w, h))
    c, buf = new_canvas(w, h, f"Find your seat sign — {ev.title}")
    margin = min(w, h) * 0.08
    _decorate(c, design, w, h, margin)
    scale = min(w, h) / 13
    y = draw_header(c, design, ev, w, h - margin * 1.1, scale, kicker="Welcome")
    head = "Find your seat"
    head_t = head.upper() if design.key == "minimal" else head
    hf = design.pick(design.title_font if design.key != "minimal" else "Jost", head_t)
    hs = scale * (0.62 if design.key == "minimal" else 0.85)
    draw_text(c, w / 2, y - hs, head_t, hf, hs, 0.18 if design.key == "minimal" else 0, "center", design.ink)
    y -= hs * 1.9
    qs = min(w * 0.44, 3.6 * inch)
    # Dark QR on white for reliable scanning (no low-contrast tints).
    from reportlab.lib.colors import HexColor
    draw_qr(c, url, w / 2 - qs / 2, y - qs, qs, HexColor("#111111"))
    y -= qs + scale * 0.55
    lines = [
        "Scan with your phone camera,",
        "then type your full name to see your table.",
    ]
    for ln in lines:
        draw_text(c, w / 2, y, ln, design.pick(design.name_font, ln), scale * 0.34, 0, "center", design.ink)
        y -= scale * 0.48
    y -= scale * 0.15
    short = url.split("://", 1)[-1]
    sf = "Jost"
    ss = fit_size(short, sf, w * 0.8, scale * 0.24, 6)
    draw_text(c, w / 2, y, short, sf, ss, 0, "center", design.soft)
    y -= scale * 0.55
    fb = "No signal? Every name is also on the seating chart."
    draw_text(c, w / 2, y, fb, design.pick(design.small_font, fb), scale * 0.28, 0, "center", design.soft)
    if preview:
        watermark(c, w, h)
    c.showPage()
    c.save()
    man.pages = 1
    return buf.getvalue(), man


# --------------------------------------------------------------------------
# Backup list (printable alternative when the venue has poor connectivity)
# --------------------------------------------------------------------------

def render_backup_list(ev: EventInfo, guests: list[Guest], paper="letter", sort_by="last", preview=False):
    """Plain, compact alphabetical lookup list for the welcome table / staff."""
    design = D.DESIGNS[ev.design]
    plabel, w, h = PAPERS[paper]
    man = Manifest(kind="backup-list", page_size=(w, h))
    c, buf = new_canvas(w, h, f"Guest lookup list — {ev.title}")
    m = 0.6 * inch
    size = 10.5
    line_h = size * 1.45
    cols = 2
    gutter = 0.35 * inch
    col_w = (w - 2 * m - gutter) / cols
    tab_w = 0.9 * inch
    name_w = col_w - tab_w
    items = alpha_sorted(guests, sort_by)
    rows_per_col = int((h - 2 * m - 46) // line_h)
    per_page = rows_per_col * cols
    # Wrap names that are too long rather than clipping them.
    entries = []
    for g in items:
        f = design.pick("EBGaramond" if design.key != "minimal" else "Jost", g.name)
        lines = wrap_words(g.name, f, size, name_w - 6) if stringWidth(g.name, f, size) > name_w - 6 else [g.name]
        s = size
        while any(stringWidth(l, f, s) > name_w - 6 for l in lines) and s > 6:
            s -= 0.25
        entries.append((g, f, s, lines))
    pages = []
    cur, n = [], 0
    for e in entries:
        need = len(e[3])
        if n + need > per_page:
            pages.append(cur)
            cur, n = [], 0
        cur.append(e)
        n += need
    if cur:
        pages.append(cur)
    for p, ents in enumerate(pages):
        draw_text(c, m, h - m, f"Guest lookup — {ev.title}", design.pick("Jost-Medium", ev.title), 13)
        draw_text(c, w - m, h - m, f"Page {p + 1} of {len(pages)}", "Jost", 9, align="right", color=design.soft)
        draw_text(c, m, h - m - 16, "Alphabetical. For hosts and the welcome table if guests can't load the QR page.", "Jost-Light", 8.5, color=design.soft)
        y_top = h - m - 40
        r = 0
        for g, f, s, lines in ents:
            col = r // rows_per_col
            x = m + col * (col_w + gutter)
            if r % rows_per_col + len(lines) > rows_per_col:
                r = (col + 1) * rows_per_col
                col = r // rows_per_col
                x = m + col * (col_w + gutter)
            y = y_top - (r % rows_per_col) * line_h
            for k, ln in enumerate(lines):
                wd = draw_text(c, x, y - k * line_h, ln, f, s)
            lab = table_display(g.table)
            lf = design.pick("Jost", lab)
            ls = fit_size(lab, lf, tab_w - 4, size, 6)
            draw_text(c, x + col_w, y - (len(lines) - 1) * line_h, lab, lf, ls, align="right")
            c.saveState()
            c.setStrokeColor(Color(0.85, 0.85, 0.85))
            c.setLineWidth(0.3)
            c.line(x, y - (len(lines) - 1) * line_h - 4, x + col_w, y - (len(lines) - 1) * line_h - 4)
            c.restoreState()
            man.placed.append(Placed(g.name, g.table, p + 1, s, max(stringWidth(l, f, s) for l in lines), name_w - 6, f))
            r += len(lines)
        if preview:
            watermark(c, w, h)
        c.showPage()
    c.save()
    man.pages = len(pages)
    return buf.getvalue(), man
