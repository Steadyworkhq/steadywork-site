"""Build the three public sample packages (fictional couples, synthetic guests)."""
import os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pypdfium2 as pdfium
from app.guestlist import parse_upload, suggest_mapping, apply_mapping
from app.render import EventInfo, render_chart, render_place_cards, render_qr_sign, render_backup_list

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("BASE_URL", "https://kindlyseatedco.com").rstrip("/")
SAMPLES = {
    "minimal": ("Ava Lindqvist & Jonah Mercer", date(2027, 6, 12), "Portland, Oregon", "small-numbered-64.csv", "18x24", "table", "letter"),
    "classic": ("Eleanor Hartwell & Samuel Okoro", date(2027, 9, 18), "Charleston", "medium-named-120.csv", "18x24", "table", "letter"),
    "botanical": ("Mía Castellanos & Priya Raman", date(2027, 5, 1), "Lake Como", "large-numbered-250.csv", "24x36", "table", "a4"),
}


def guests_for(fn):
    raw = parse_upload(fn, open(os.path.join(ROOT, "samples", fn), "rb").read())
    return apply_mapping(raw, suggest_mapping(raw))[0]


def png(pdf_bytes, page, out, long_edge):
    pg = pdfium.PdfDocument(pdf_bytes)[page]
    w, h = pg.get_size()
    pg.render(scale=long_edge / max(w, h)).to_pil().convert("RGB").save(out, optimize=True)


def main():
    for key, (title, d, venue, fn, size, layout, paper) in SAMPLES.items():
        out = os.path.join(ROOT, "app", "static", "samples", key)
        os.makedirs(out, exist_ok=True)
        gs = guests_for(fn)
        ev = EventInfo(title, d, venue, key, "intl" if paper == "a4" else "us")
        chart, _ = render_chart(ev, gs, size, layout)
        alpha, _ = render_chart(ev, gs, size, "alpha")
        cards, _ = render_place_cards(ev, gs, paper)
        sign, _ = render_qr_sign(ev, f"{BASE}/demo/{key}", paper)
        backup, _ = render_backup_list(ev, gs, paper)
        for name, data in [("seating-chart", chart), ("seating-chart-alphabetical", alpha), ("place-cards", cards), ("qr-sign", sign), ("guest-lookup-list", backup)]:
            open(os.path.join(out, name + ".pdf"), "wb").write(data)
        png(chart, 0, os.path.join(out, "chart.png"), 1100)
        png(cards, 1, os.path.join(out, "cards.png"), 700)
        png(sign, 0, os.path.join(out, "sign.png"), 700)
        print(key, len(gs))


if __name__ == "__main__":
    main()
