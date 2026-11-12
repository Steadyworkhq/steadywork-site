import math
import pytest
import pypdfium2 as pdfium
from pypdf import PdfReader
import io
from datetime import date
from app.guestlist import parse_upload, suggest_mapping, apply_mapping, Guest
from app.render import (EventInfo, render_chart, render_place_cards, render_qr_sign, render_backup_list,
                        CHART_SIZES, PAPERS, SIGN_SIZES)
from conftest import sample_bytes

LONG = "Maximiliana Alejandra Montgomery-Castellanos de la Peña-Würthemberger"
WORD = "Wolfeschlegelsteinhausenbergerdorff"


def guests(fn="large-numbered-250.csv"):
    raw = parse_upload(fn, sample_bytes(fn))
    gs = apply_mapping(raw, suggest_mapping(raw))[0]
    return gs


def ev(design):
    return EventInfo("Ava Lindqvist & Jonah Mercer", date(2027, 6, 12), "Portland", design)


def text_of(pdf):
    doc = pdfium.PdfDocument(pdf)
    return "\n".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))


def check_all_placed(man, gs):
    # Each guest object placed exactly once; duplicates-by-name placed as many times as they occur.
    from collections import Counter
    want = Counter((g.name, g.table) for g in gs)
    got = Counter((p.name, p.table) for p in man.placed)
    assert got == want
    for p in man.placed:
        assert p.width <= p.max_width + 0.01, f"clipped: {p.name} {p.width} > {p.max_width}"


@pytest.mark.parametrize("design", ["minimal", "classic", "botanical"])
@pytest.mark.parametrize("layout", ["table", "alpha"])
def test_chart_every_guest_no_clipping(design, layout):
    gs = guests() 
    pdf, man = render_chart(ev(design), gs, "18x24", layout)
    check_all_placed(man, gs)
    txt = text_of(pdf).replace("\r", "").replace("\n", " ")
    import unicodedata
    norm = " ".join(unicodedata.normalize("NFC", txt).split())
    for g in gs:
        # wrapped names split across lines; check each word
        for w in g.name.split():
            assert w in norm, w


@pytest.mark.parametrize("design", ["minimal", "classic", "botanical"])
def test_long_names_and_single_long_word(design):
    gs = [Guest(LONG, "1"), Guest(WORD, "1"), Guest("Þór Ó Súilleabháin", "Head Table"), Guest("Nguyễn Thị Minh Khai", "2"), Guest("Zoë", "2")]
    for fn, kw in ((render_chart, {"size_key": "16x20"}), (render_place_cards, {"paper": "letter"}), (render_place_cards, {"paper": "a4"}), (render_backup_list, {})):
        pdf, man = fn(ev(design), gs, **kw)
        check_all_placed(man, gs)


def test_two_guests_same_name_both_appear_everywhere():
    gs = [Guest("Jamie Lee", "1"), Guest("Jamie Lee", "4"), Guest("Ana Ruiz", "1")]
    for fn in (render_chart, render_place_cards, render_backup_list):
        _, man = fn(ev("classic"), gs)
        assert sum(1 for p in man.placed if p.name == "Jamie Lee") == 2


@pytest.mark.parametrize("size", list(CHART_SIZES))
def test_chart_physical_dimensions(size):
    _, w, h = CHART_SIZES[size]
    pdf, man = render_chart(ev("minimal"), guests("small-numbered-64.csv"), size)
    r = PdfReader(io.BytesIO(pdf))
    for p in r.pages:
        assert abs(float(p.mediabox.width) - w) < 0.01 and abs(float(p.mediabox.height) - h) < 0.01
    # 18x24 in = 1296 x 1728 pt
    if size == "18x24":
        assert (round(w), round(h)) == (1296, 1728)


@pytest.mark.parametrize("paper,dims", [("letter", (612, 792)), ("a4", (595.28, 841.89))])
def test_card_and_backup_page_sizes(paper, dims):
    for fn in (render_place_cards, render_backup_list):
        pdf, _ = fn(ev("botanical"), guests("small-numbered-64.csv"), paper=paper)
        for p in PdfReader(io.BytesIO(pdf)).pages:
            assert abs(float(p.mediabox.width) - dims[0]) < 0.05 and abs(float(p.mediabox.height) - dims[1]) < 0.05


def test_fonts_embedded():
    pdf, _ = render_place_cards(ev("classic"), guests("small-numbered-64.csv"))
    r = PdfReader(io.BytesIO(pdf))
    seen = 0
    for page in r.pages:
        fonts = page["/Resources"]["/Font"]
        for f in fonts.values():
            f = f.get_object()
            assert f["/Subtype"] in ("/Type0", "/TrueType"), f["/Subtype"]
            if f["/Subtype"] == "/TrueType":
                fd = f["/FontDescriptor"].get_object()
                assert "/FontFile2" in fd, f["/BaseFont"]
                seen += 1
    assert seen > 0


def test_place_cards_paginate():
    gs = guests()
    pdf, man = render_place_cards(ev("minimal"), gs, "letter")
    assert man.pages == math.ceil(250 / 4) + 1
    check_all_placed(man, gs)


def test_backup_list_paginates_and_contains_all():
    gs = guests()
    pdf, man = render_backup_list(ev("minimal"), gs, "letter")
    assert man.pages >= 2
    check_all_placed(man, gs)


@pytest.mark.parametrize("size", list(CHART_SIZES))
@pytest.mark.parametrize("layout", ["table", "alpha"])
def test_chart_names_never_below_minimum_size(size, layout):
    from app.render import MIN_NAME_PT
    gs = guests() + [Guest(LONG, "3"), Guest(WORD, "4")]
    _, man = render_chart(ev("classic"), gs, size, layout)
    check_all_placed(man, gs)
    assert min(p.size for p in man.placed) >= MIN_NAME_PT - 0.26


def test_large_list_small_poster_splits_rather_than_shrinking():
    gs = guests()
    pdf, man = render_chart(ev("classic"), gs, "16x20", "table")
    check_all_placed(man, gs)
    assert man.font_size >= 11
    if man.pages > 1:
        assert man.warnings


def test_qr_decodes_to_guest_url():
    import zxingcpp
    url = "http://localhost:5000/s/AbC123_xyz-QwErTy"
    for paper in ("letter", "a4"):
        for d in ("minimal", "classic", "botanical"):
            pdf, _ = render_qr_sign(ev(d), url, paper)
            img = pdfium.PdfDocument(pdf)[0].render(scale=1.5).to_pil()
            res = zxingcpp.read_barcodes(img)
            assert [r.text for r in res] == [url]
            p = PdfReader(io.BytesIO(pdf)).pages[0]
            assert abs(float(p.mediabox.width) - SIGN_SIZES[paper][1]) < 0.05


def test_preview_watermark_present_only_in_preview():
    gs = guests("small-numbered-64.csv")
    pdf, _ = render_chart(ev("minimal"), gs, "18x24", preview=True)
    assert "PREVIEW" in text_of(pdf)
    pdf, _ = render_chart(ev("minimal"), gs, "18x24", preview=False)
    assert "PREVIEW" not in text_of(pdf)


def test_deterministic_output():
    gs = guests("small-numbered-64.csv")
    a, _ = render_chart(ev("botanical"), gs, "18x24")
    b, _ = render_chart(ev("botanical"), gs, "18x24")
    # reportlab embeds a timestamp/ID; compare page content via text + manifest instead
    assert text_of(a) == text_of(b)
