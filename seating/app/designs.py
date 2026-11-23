"""The three original designs. All artwork is drawn procedurally in vector form."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

from reportlab.lib.colors import Color, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

_FONT_FILES = {
    "Jost-Light": "JostLight.ttf",
    "Jost": "JostRegular.ttf",
    "Jost-Medium": "JostMedium.ttf",
    "EBGaramond": "EBGaramondRegular.ttf",
    "EBGaramond-Italic": "EBGaramondItalic.ttf",
    "EBGaramond-SemiBold": "EBGaramondSemiBold.ttf",
    "Cormorant-Medium": "CormorantGaramondMedium.ttf",
    "Cormorant-MediumItalic": "CormorantGaramondMediumItalic.ttf",
    "Cormorant-SemiBold": "CormorantGaramondSemiBold.ttf",
    "Lora": "LoraRegular.ttf",
    "Lora-Italic": "LoraItalic.ttf",
    "Lora-SemiBold": "LoraSemiBold.ttf",
    "DejaVuSans": "DejaVuSans.ttf",
    "DejaVuSerif": "DejaVuSerif.ttf",
}

_registered = False


def register_fonts() -> None:
    global _registered
    if _registered:
        return
    for name, fn in _FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, fn)))
    _registered = True


def font_has(fontname: str, text: str) -> bool:
    register_fonts()
    face = pdfmetrics.getFont(fontname).face
    cmap = face.charToGlyph
    return all((ord(ch) in cmap) or ch in "  " for ch in text)


@dataclass(frozen=True)
class Design:
    key: str
    label: str
    blurb: str
    title_font: str  # couple names
    kicker_font: str  # "Please find your seat"
    heading_font: str  # table headings
    name_font: str  # guest names
    small_font: str  # dates, footers
    fallback_font: str
    ink: Color
    accent: Color
    soft: Color
    upper_title: bool
    upper_headings: bool
    title_tracking: float  # em
    heading_tracking: float
    kicker_text: str

    def pick(self, fontname: str, text: str) -> str:
        """Use the design font unless it lacks a glyph; then use the fallback.

        We never drop a character: if even the fallback lacks it, the caller's
        coverage check reports it to the customer before purchase.
        """
        if font_has(fontname, text):
            return fontname
        return self.fallback_font


DESIGNS = {
    "minimal": Design(
        key="minimal",
        label="Minimal",
        blurb="Black and white, clean geometric type, generous space.",
        title_font="Jost-Light",
        kicker_font="Jost",
        heading_font="Jost-Medium",
        name_font="Jost-Light",
        small_font="Jost",
        fallback_font="DejaVuSans",
        ink=HexColor("#111111"),
        accent=HexColor("#111111"),
        soft=HexColor("#8a8a8a"),
        upper_title=True,
        upper_headings=True,
        title_tracking=0.18,
        heading_tracking=0.16,
        kicker_text="Please find your seat",
    ),
    "classic": Design(
        key="classic",
        label="Classic Serif",
        blurb="Traditional Garamond lettering with fine rules and a warm ink tone.",
        title_font="Cormorant-Medium",
        kicker_font="Cormorant-MediumItalic",
        heading_font="EBGaramond-SemiBold",
        name_font="EBGaramond",
        small_font="EBGaramond-Italic",
        fallback_font="DejaVuSerif",
        ink=HexColor("#2a2522"),
        accent=HexColor("#8c6d46"),
        soft=HexColor("#7a706a"),
        upper_title=True,
        upper_headings=True,
        title_tracking=0.12,
        heading_tracking=0.12,
        kicker_text="Please find your seat",
    ),
    "botanical": Design(
        key="botanical",
        label="Botanical",
        blurb="Soft serif type with restrained hand-drawn-style greenery.",
        title_font="Cormorant-MediumItalic",
        kicker_font="Lora-Italic",
        heading_font="Lora-SemiBold",
        name_font="Lora",
        small_font="Lora-Italic",
        fallback_font="DejaVuSerif",
        ink=HexColor("#2f3a31"),
        accent=HexColor("#6f8a6c"),
        soft=HexColor("#7d8a7c"),
        upper_title=False,
        upper_headings=False,
        title_tracking=0.0,
        heading_tracking=0.02,
        kicker_text="Find your seat",
    ),
}


# --------------------------------------------------------------------------
# Ornaments
# --------------------------------------------------------------------------

def _leaf(c, x, y, length, width, angle_deg):
    """An almond-shaped leaf with its base at (x, y)."""
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)

    def pt(u, v):
        return x + u * ca - v * sa, y + u * sa + v * ca

    p = c.beginPath()
    p.moveTo(*pt(0, 0))
    p.curveTo(*pt(length * 0.30, width * 0.62), *pt(length * 0.72, width * 0.52), *pt(length, 0))
    p.curveTo(*pt(length * 0.72, -width * 0.42), *pt(length * 0.30, -width * 0.50), *pt(0, 0))
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def sprig(c, x, y, length, angle_deg, color, leaves=7, mirror=False):
    """A gently curving stem with alternating leaves. Original procedural art."""
    c.saveState()
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineCap(1)
    a = math.radians(angle_deg)
    bend = -0.18 if mirror else 0.18
    pts = []
    n = 40
    for i in range(n + 1):
        t = i / n
        u = length * t
        v = length * bend * math.sin(math.pi * t) * 0.6
        pts.append((x + u * math.cos(a) - v * math.sin(a), y + u * math.sin(a) + v * math.cos(a)))
    c.setLineWidth(max(0.6, length / 160))
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    c.drawPath(p, stroke=1, fill=0)
    for k in range(leaves):
        t = 0.18 + 0.74 * k / max(1, leaves - 1)
        i = int(t * n)
        px, py = pts[i]
        qx, qy = pts[min(n, i + 1)]
        tang = math.degrees(math.atan2(qy - py, qx - px))
        side = 1 if k % 2 == 0 else -1
        size = length * (0.20 - 0.08 * t)
        _leaf(c, px, py, size, size * 0.42, tang + side * 48)
    _leaf(c, *pts[-1], length * 0.11, length * 0.05, math.degrees(a) + (6 if not mirror else -6))
    c.restoreState()


def corner_greenery(c, w, h, color, scale):
    s = scale
    sprig(c, w * 0.04, h - w * 0.02, s, -38, color, leaves=8)
    sprig(c, w * 0.04, h - w * 0.02, s * 0.62, -78, color, leaves=5, mirror=True)
    sprig(c, w * 0.96, h - w * 0.02, s, 180 + 38, color, leaves=8, mirror=True)
    sprig(c, w * 0.96, h - w * 0.02, s * 0.62, 180 + 78, color, leaves=5)


def bottom_greenery(c, cx, y, color, scale):
    sprig(c, cx - scale * 0.04, y, scale, 172, color, leaves=7, mirror=True)
    sprig(c, cx + scale * 0.04, y, scale, 8, color, leaves=7)


def classic_rule(c, cx, y, width, color, lw=0.6):
    c.saveState()
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(lw)
    d = max(2.2, width * 0.018)
    c.line(cx - width / 2, y, cx - d * 2.2, y)
    c.line(cx + d * 2.2, y, cx + width / 2, y)
    p = c.beginPath()
    p.moveTo(cx, y + d)
    p.lineTo(cx + d, y)
    p.lineTo(cx, y - d)
    p.lineTo(cx - d, y)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def minimal_rule(c, cx, y, width, color, lw=0.5):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.line(cx - width / 2, y, cx + width / 2, y)
    c.restoreState()


def divider(design: Design, c, cx, y, width, lw=0.6):
    if design.key == "classic":
        classic_rule(c, cx, y, width, design.accent, lw)
    elif design.key == "botanical":
        sprig(c, cx - 2, y, width / 2, 180, design.accent, leaves=5, mirror=True)
        sprig(c, cx + 2, y, width / 2, 0, design.accent, leaves=5)
    else:
        minimal_rule(c, cx, y, width, design.ink, lw)
