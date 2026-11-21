"""Guest-list import, column detection, and validation.

Everything here is deterministic. Nothing is sent to an AI provider.

Rules we never break:
  * Names keep their original spelling, accents and capitalisation. We only
    trim surrounding whitespace and apply Unicode NFC normalisation (which does
    not change how a name looks; it makes "é" typed as e + combining accent
    render with the font's real "é" glyph).
  * Duplicate-looking names are *flagged*, never merged.
  * Missing table assignments are *flagged*, never invented.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field

MAX_GUESTS = 250
MAX_NAME_LEN = 120
MAX_TABLE_LEN = 40

# --------------------------------------------------------------------------
# Normalisation helpers
# --------------------------------------------------------------------------

def clean_name(raw) -> str:
    """Trim + NFC only. Never changes spelling or case."""
    if raw is None:
        return ""
    s = str(raw)
    s = unicodedata.normalize("NFC", s)
    # Replace non-breaking / odd whitespace at the ends only.
    return s.strip(" \t\r\n   ﻿")


def match_key(name: str) -> str:
    """Key used for duplicate detection and guest lookup.

    Case-, accent- and punctuation-insensitive, so "José García" and
    "jose garcia" produce the same key. This key is *only* used for comparison;
    it is never displayed or stored in place of the real name.
    """
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.casefold()
    # Some letters don't decompose: map the common ones.
    s = s.translate(str.maketrans({"ø": "o", "ł": "l", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe", "ı": "i", "þ": "th", "ð": "d"}))
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"[\s_]+", " ", s)
    return s.strip()


def sort_key(text: str) -> tuple:
    return (match_key(text), text)


_TABLE_PREFIX = re.compile(r"^\s*(?:table|tbl|mesa|tisch|tavolo|table no\.?|table #|#)\s*", re.I)


def clean_table(raw) -> str:
    """Canonical table label.

    "5", "5.0" (from Excel), "Table 5", "table 05", "#5" -> "5".
    Named tables ("Rosemary", "Head Table") are kept as typed.
    """
    if raw is None:
        return ""
    if isinstance(raw, float) and raw.is_integer():
        raw = int(raw)
    s = unicodedata.normalize("NFC", str(raw)).strip(" \t\r\n ")
    if not s:
        return ""
    m = re.fullmatch(r"(\d+)(?:\.0+)?", s)
    if m:
        return str(int(m.group(1)))
    stripped = _TABLE_PREFIX.sub("", s)
    m = re.fullmatch(r"(\d+)", stripped)
    if m and stripped != s:
        return str(int(m.group(1)))
    return s


def table_is_numbered(label: str) -> bool:
    return label.isdigit()


def table_display(label: str) -> str:
    return f"Table {label}" if table_is_numbered(label) else label


def table_sort_key(label: str) -> tuple:
    # Numbered tables first in numeric order, then named tables alphabetically.
    if table_is_numbered(label):
        return (0, int(label), "")
    return (1, 0, match_key(label))


# --------------------------------------------------------------------------
# Reading files
# --------------------------------------------------------------------------

@dataclass
class RawTable:
    headers: list[str]
    rows: list[list[str]]
    has_header: bool
    warnings: list[str] = field(default_factory=list)


def _decode(data: bytes) -> tuple[str, str | None]:
    for enc in ("utf-8-sig",):
        try:
            return data.decode(enc), None
        except UnicodeDecodeError:
            pass
    # UTF-16 exports from Excel ("Unicode text") start with a BOM.
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16"), None
    # Windows Excel "CSV" export is usually cp1252.
    return data.decode("cp1252", errors="replace"), (
        "Your file was not saved as UTF-8, so we read it as Windows-1252. "
        "Please check accented names carefully in the next step, or re-export as "
        "'CSV UTF-8'."
    )


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def read_xlsx(data: bytes) -> list[list[str]]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    for ws in wb.worksheets:
        rows = [[_cell(c) for c in r] for r in ws.iter_rows(values_only=True)]
        rows = [r for r in rows if any(c.strip() for c in r)]
        if rows:
            return rows
    return []


def read_delimited(text: str) -> list[list[str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        return []
    sample = "\n".join(lines[:30])
    if "\t" in sample:
        delim = "\t"
    else:
        try:
            delim = csv.Sniffer().sniff(sample, delimiters=",;|").delimiter
        except csv.Error:
            delim = None
    if delim is None:
        # Pasted lines like "Ana López - 4" or "Ana López  4" or just names.
        out = []
        for ln in lines:
            m = re.match(r"^(.*?)\s*(?:[-–—:]\s*|\s{2,})(?:table\s*)?([\w ]{1,40})\s*$", ln, re.I)
            if m and m.group(1).strip():
                out.append([m.group(1), m.group(2)])
            else:
                out.append([ln])
        return out
    return [row for row in csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)]


HEADER_HINTS = {
    "full": ["full name", "guest name", "guest", "name", "names", "nombre", "invitee", "attendee"],
    "first": ["first name", "first", "given name", "firstname", "fname", "first_name"],
    "last": ["last name", "last", "surname", "family name", "lastname", "lname", "last_name"],
    "table": ["table", "table number", "table no", "table #", "table name", "tbl", "seat", "seating", "assigned table", "table assignment", "mesa"],
}


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-.:#]+", " ", h.strip().casefold())).strip()


def _header_role(h: str) -> str | None:
    n = _norm_header(h)
    if not n:
        return None
    for role in ("first", "last", "table", "full"):
        for hint in HEADER_HINTS[role]:
            if n == _norm_header(hint):
                return role
    if "table" in n:
        return "table"
    if "first" in n:
        return "first"
    if "last" in n or "surname" in n:
        return "last"
    if "name" in n or "guest" in n:
        return "full"
    return None


def parse_upload(filename: str | None, data: bytes | None = None, pasted: str | None = None) -> RawTable:
    warnings: list[str] = []
    if pasted is not None:
        rows = read_delimited(unicodedata.normalize("NFC", pasted))
    else:
        assert data is not None
        name = (filename or "").lower()
        if name.endswith((".xlsx", ".xlsm")) or data[:2] == b"PK":
            rows = read_xlsx(data)
        elif name.endswith(".xls"):
            raise ValueError("Old .xls files aren't supported. In Excel choose File → Save As → .xlsx or CSV UTF-8.")
        else:
            text, warn = _decode(data)
            if warn:
                warnings.append(warn)
            rows = read_delimited(text)
    rows = [[c if isinstance(c, str) else _cell(c) for c in r] for r in rows]
    width = max((len(r) for r in rows), default=0)
    rows = [r + [""] * (width - len(r)) for r in rows]
    # Drop columns that are entirely empty.
    keep = [i for i in range(width) if any(r[i].strip() for r in rows)]
    rows = [[r[i] for i in keep] for r in rows]
    if not rows:
        return RawTable([], [], False, warnings + ["We couldn't find any rows."])
    first = rows[0]
    has_header = any(_header_role(c) for c in first) and not any(
        clean_table(c).isdigit() for c in first
    )
    if has_header:
        headers = [c.strip() or f"Column {i+1}" for i, c in enumerate(first)]
        body = rows[1:]
    else:
        headers = [f"Column {i+1}" for i in range(len(first))]
        body = rows
    return RawTable(headers, body, has_header, warnings)


# --------------------------------------------------------------------------
# Column mapping suggestion (deterministic; customer must confirm)
# --------------------------------------------------------------------------

def _looks_like_table(values: list[str]) -> float:
    vals = [v for v in values if v.strip()]
    if not vals:
        return 0.0
    hits = 0
    for v in vals:
        t = clean_table(v)
        if t.isdigit() and int(t) < 1000:
            hits += 1
        elif len(t) <= 20 and len(t.split()) <= 3:
            hits += 0.3
    distinct = len(set(clean_table(v) for v in vals))
    # Tables repeat (several guests per table); only judge that on longer lists.
    repetition = 1.0 if len(vals) < 10 or distinct < len(vals) * 0.6 else 0.4
    return hits / len(vals) * repetition


def _looks_like_name(values: list[str]) -> float:
    vals = [v for v in values if v.strip()]
    if not vals:
        return 0.0
    hits = sum(1 for v in vals if re.search(r"[^\W\d_]", v) and not clean_table(v).isdigit())
    distinct = len(set(vals)) / len(vals)
    return hits / len(vals) * distinct


def suggest_mapping(raw: RawTable) -> dict:
    """Return {"mode": "full"|"split", "full": i, "first": i, "last": i, "table": i}."""
    roles: dict[str, int] = {}
    if raw.has_header:
        for i, h in enumerate(raw.headers):
            r = _header_role(h)
            if r and r not in roles:
                roles[r] = i
    cols = list(zip(*raw.rows)) if raw.rows else []
    if "table" not in roles and cols:
        scores = [(_looks_like_table(list(c)), i) for i, c in enumerate(cols) if i not in roles.values()]
        scores.sort(reverse=True)
        if scores and scores[0][0] >= 0.5:
            roles["table"] = scores[0][1]
    if "full" not in roles and not ("first" in roles and "last" in roles) and cols:
        scores = [(_looks_like_name(list(c)), i) for i, c in enumerate(cols) if i not in roles.values()]
        scores.sort(reverse=True)
        if scores and scores[0][0] > 0.3:
            roles["full"] = scores[0][1]
    mode = "split" if ("first" in roles and "last" in roles and "full" not in roles) else "full"
    return {
        "mode": mode,
        "full": roles.get("full"),
        "first": roles.get("first"),
        "last": roles.get("last"),
        "table": roles.get("table"),
    }


# --------------------------------------------------------------------------
# Applying a confirmed mapping
# --------------------------------------------------------------------------

@dataclass
class Guest:
    name: str
    table: str  # canonical label, "" if missing
    last: str = ""  # optional explicit last name for sorting
    row: int = 0  # 1-based source row, for error messages


def apply_mapping(raw: RawTable, mapping: dict) -> tuple[list[Guest], list[str]]:
    guests: list[Guest] = []
    problems: list[str] = []
    offset = 2 if raw.has_header else 1
    for idx, r in enumerate(raw.rows):
        def col(key):
            i = mapping.get(key)
            if i is None or i == "" or int(i) >= len(r):
                return ""
            return r[int(i)]

        if mapping.get("mode") == "split":
            first, last = clean_name(col("first")), clean_name(col("last"))
            name = " ".join(p for p in (first, last) if p)
        else:
            name, last = clean_name(col("full")), ""
        table = clean_table(col("table"))
        if not name:
            if table:
                problems.append(f"Row {idx + offset}: table '{table}' has no name, so the row was skipped.")
            continue
        guests.append(Guest(name=name, table=table, last=last, row=idx + offset))
    return guests, problems


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

@dataclass
class Report:
    missing_table: list[int]  # indexes into guests
    duplicate_groups: list[list[int]]  # each group: indexes sharing a match key
    too_long: list[int]
    too_many: bool
    table_counts: dict[str, int]

    @property
    def blocking(self) -> bool:
        return bool(self.missing_table or self.too_long or self.too_many)


def validate(guests: list[Guest]) -> Report:
    missing = [i for i, g in enumerate(guests) if not g.table]
    groups: dict[str, list[int]] = {}
    for i, g in enumerate(guests):
        groups.setdefault(match_key(g.name), []).append(i)
    dups = [v for v in groups.values() if len(v) > 1]
    too_long = [i for i, g in enumerate(guests) if len(g.name) > MAX_NAME_LEN or len(g.table) > MAX_TABLE_LEN]
    counts: dict[str, int] = {}
    for g in guests:
        if g.table:
            counts[g.table] = counts.get(g.table, 0) + 1
    counts = dict(sorted(counts.items(), key=lambda kv: table_sort_key(kv[0])))
    return Report(missing, dups, too_long, len(guests) > MAX_GUESTS, counts)


def dup_group_id(guests: list[Guest], group: list[int]) -> str:
    return match_key(guests[group[0]].name)


# --------------------------------------------------------------------------
# Sorting for outputs
# --------------------------------------------------------------------------

def surname_of(g: Guest) -> str:
    if g.last:
        return g.last
    parts = g.name.split()
    return parts[-1] if parts else g.name


def alpha_sorted(guests: list[Guest], by: str = "last") -> list[Guest]:
    if by == "first":
        return sorted(guests, key=lambda g: (match_key(g.name), g.name, table_sort_key(g.table)))
    return sorted(
        guests,
        key=lambda g: (match_key(surname_of(g)), match_key(g.name), g.name, table_sort_key(g.table)),
    )


def grouped_by_table(guests: list[Guest], by: str = "last") -> list[tuple[str, list[Guest]]]:
    tables: dict[str, list[Guest]] = {}
    for g in guests:
        tables.setdefault(g.table, []).append(g)
    return [(t, alpha_sorted(tables[t], by)) for t in sorted(tables, key=table_sort_key)]


def letter_of(g: Guest, by: str) -> str:
    base = surname_of(g) if by == "last" else g.name
    k = match_key(base)
    return k[:1].upper() if k and k[0].isalpha() else "#"
