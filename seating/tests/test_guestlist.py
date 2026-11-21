import io
import unicodedata
import openpyxl
from app.guestlist import (parse_upload, suggest_mapping, apply_mapping, validate, clean_table, match_key,
                           alpha_sorted, Guest, clean_name)
from conftest import sample_bytes


def load(text=None, data=None, fn="x.csv"):
    raw = parse_upload(fn, data) if data is not None else parse_upload(None, pasted=text)
    m = suggest_mapping(raw)
    return raw, m, apply_mapping(raw, m)[0]


def test_detects_columns_with_headers():
    raw, m, gs = load(data=sample_bytes("large-numbered-250.csv"))
    assert m["full"] == 0 and m["table"] == 1
    assert len(gs) == 250


def test_detects_columns_without_headers_and_reversed_order():
    raw, m, gs = load("4, Ana López\n4, Ben Ng\n2, Siobhán Ní Bhriain\n2, Zoë Ödegaard\n")
    assert not raw.has_header
    assert m["table"] == 0 and m["full"] == 1
    assert [g.name for g in gs][0] == "Ana López"


def test_split_first_last_columns():
    raw, m, gs = load("First Name,Last Name,Table\nJosé,García,3\nAnn,de la Cruz,Head Table\n")
    assert m["mode"] == "split"
    assert gs[0].name == "José García" and gs[0].last == "García"
    assert gs[1].table == "Head Table"


def test_preserves_spelling_accents_and_case():
    names = ["mcKenzie O'NEIL", "ÉLODIE du Pré", "Łukasz Żółć", "da Silva, João"]
    text = "Name\tTable\n" + "\n".join(f"{n}\t1" for n in names)
    _, _, gs = load(text)
    assert [g.name for g in gs] == names


def test_nfc_normalisation_does_not_change_appearance():
    decomposed = "Zoë Odé"  # e + combining marks
    assert clean_name(decomposed) == unicodedata.normalize("NFC", decomposed)
    assert clean_name(decomposed) == "Zoë Odé"


def test_table_canonicalisation():
    assert clean_table("Table 5") == "5"
    assert clean_table("05") == "5"
    assert clean_table(5.0) == "5"
    assert clean_table("#12") == "12"
    assert clean_table("Rosemary") == "Rosemary"
    assert clean_table("Head Table") == "Head Table"
    assert clean_table("") == ""


def test_missing_tables_flagged_not_invented():
    _, _, gs = load(data=sample_bytes("messy-with-missing.csv"))
    r = validate(gs)
    assert len(r.missing_table) == 3
    assert r.blocking
    assert all(gs[i].table == "" for i in r.missing_table)


def test_duplicates_flagged_never_merged():
    _, _, gs = load("Name,Table\nJosé García,1\njose garcia,2\nJosé García,3\nAna,1\n")
    r = validate(gs)
    assert len(gs) == 4  # nothing merged
    assert len(r.duplicate_groups) == 1 and len(r.duplicate_groups[0]) == 3


def test_xlsx_upload():
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Guest", "Table #"]); ws.append(["Renée Côté", 7]); ws.append(["Dagný Þórsdóttir", 7.0]); ws.append(["Kai", "Sage"])
    buf = io.BytesIO(); wb.save(buf)
    _, m, gs = load(data=buf.getvalue(), fn="list.xlsx")
    assert [(g.name, g.table) for g in gs] == [("Renée Côté", "7"), ("Dagný Þórsdóttir", "7"), ("Kai", "Sage")]


def test_cp1252_csv_is_read_with_warning():
    data = "Name,Table\nRenée Côté,1\n".encode("cp1252")
    raw = parse_upload("x.csv", data)
    assert raw.warnings and raw.rows[0][0] == "Renée Côté"


def test_pasted_dash_format():
    _, _, gs = load("Ana López - 4\nBen Ng - Table 2\n")
    assert [(g.name, g.table) for g in gs] == [("Ana López", "4"), ("Ben Ng", "2")]


def test_alpha_sort_accent_insensitive():
    gs = [Guest("Zed Ábel", "1"), Guest("Amy Zane", "1"), Guest("Bo Éclair", "1"), Guest("Cy Abbot", "1")]
    assert [g.name for g in alpha_sorted(gs, "last")] == ["Cy Abbot", "Zed Ábel", "Bo Éclair", "Amy Zane"]


def test_match_key_handles_special_letters():
    assert match_key("Søren Łukasz") == match_key("soren lukasz")
