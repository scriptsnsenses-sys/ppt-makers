"""
Slide layout renderers for PPT Maker.

Every renderer follows the same contract:

    render_<type>(prs, data) -> slide

where `prs` is a python-pptx Presentation and `data` is the slide's JSON
specification (dict). All text is placed as real text boxes / shape text,
so the resulting .pptx is fully editable in PowerPoint, Keynote, or
Google Slides — no images, no rendering tricks.
"""

import io
import math
from urllib.request import urlopen

from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.line import MSO_LINE

# ---------------------------------------------------------------------------
# Canvas & theme
# ---------------------------------------------------------------------------

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

INK          = RGBColor(0x1A, 0x1F, 0x36)   # headings
BODY_DK      = RGBColor(0x3A, 0x40, 0x58)   # body copy
MUTED        = RGBColor(0x6B, 0x73, 0x8C)   # secondary text
ACCENT       = RGBColor(0x6C, 0x5C, 0xE7)   # brand accent (violet)
ACCENT_SOFT  = RGBColor(0xEE, 0xEC, 0xFB)   # accent tint background
PAPER        = RGBColor(0xFF, 0xFF, 0xFF)
SOFT         = RGBColor(0xF5, 0xF6, 0xFB)   # card / panel fill
DARK         = RGBColor(0x17, 0x1A, 0x2C)   # dark slide background
DARK_2       = RGBColor(0x27, 0x2C, 0x47)   # decorative lines on dark
LIGHT_ON_DARK = RGBColor(0xC7, 0xCB, 0xE1)
WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
LINE         = RGBColor(0xE2, 0xE4, 0xEF)

HEAD_FONT = "Segoe UI"
BODY_FONT = "Segoe UI"

MARGIN = Inches(0.9)
CONTENT_W = SLIDE_W - 2 * MARGIN


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _s(value):
    return str(value).strip() if value is not None else ""


def _items(value):
    """Normalize a list of strings/objects into a list of dicts."""
    if not isinstance(value, list):
        return []
    out = []
    for v in value:
        if isinstance(v, str):
            out.append({"title": v})
        elif isinstance(v, dict):
            out.append(v)
    return out


def _txt(item, *keys):
    """First non-empty string among the given keys of an item dict."""
    for k in keys:
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _new_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])  # blank layout


def _paint(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def _box(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def _para(tf, text, size, color, bold=False, font=BODY_FONT,
          align=PP_ALIGN.LEFT, space_before=0, space_after=0,
          line_spacing=None, first=False, italic=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    if line_spacing:
        p.line_spacing = line_spacing
    r = p.add_run()
    r.text = str(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font
    r.font.color.rgb = color
    return p


def _shape(slide, shape_type, x, y, w, h, fill=None, line_color=None, line_w=None):
    sp = slide.shapes.add_shape(shape_type, x, y, w, h)
    sp.shadow.inherit = False
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line_color is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line_color
        sp.line.width = line_w or Pt(1)
    return sp


def _header(slide, data):
    """Kicker + title block used by all content slides."""
    kicker = _s(data.get("kicker"))
    y = Inches(0.62)
    if kicker:
        tf = _box(slide, MARGIN, y, CONTENT_W, Inches(0.32))
        _para(tf, kicker.upper(), 11.5, ACCENT, bold=True, font=HEAD_FONT, first=True)
        y = Inches(1.0)
    title = _s(data.get("title"))
    if title:
        tf = _box(slide, MARGIN, y, CONTENT_W, Inches(0.75))
        _para(tf, title, 29, INK, bold=True, font=HEAD_FONT, first=True)
        _shape(slide, MSO_SHAPE.RECTANGLE, MARGIN, y + Inches(0.66),
               Inches(0.55), Inches(0.055), fill=ACCENT)


def _header_done_y(data):
    """Vertical position where slide content may begin."""
    return Inches(2.0)


# ---------------------------------------------------------------------------
# Slide renderers
# ---------------------------------------------------------------------------

def render_hero(prs, data):
    slide = _new_slide(prs)
    _paint(slide, DARK)

    # Left accent spine + decorative rings in the bottom-right corner.
    _shape(slide, MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.14), SLIDE_H, fill=ACCENT)
    _shape(slide, MSO_SHAPE.OVAL, SLIDE_W - Inches(2.6), SLIDE_H - Inches(3.6),
           Inches(5.2), Inches(5.2), line_color=DARK_2, line_w=Pt(1.25))
    _shape(slide, MSO_SHAPE.OVAL, SLIDE_W - Inches(1.4), SLIDE_H - Inches(2.0),
           Inches(2.6), Inches(2.6), line_color=DARK_2, line_w=Pt(1.25))
    _shape(slide, MSO_SHAPE.OVAL, SLIDE_W - Inches(0.75), SLIDE_H - Inches(1.3),
           Inches(0.44), Inches(0.44), fill=ACCENT)

    kicker = _s(data.get("kicker")) or "PRESENTATION"
    tf = _box(slide, Inches(1.25), Inches(1.85), Inches(9.5), Inches(0.4))
    _para(tf, kicker.upper(), 12, ACCENT, bold=True, font=HEAD_FONT, first=True)

    tf = _box(slide, Inches(1.25), Inches(2.35), Inches(10.2), Inches(1.9))
    _para(tf, _s(data.get("title")) or "Untitled", 40, WHITE, bold=True,
          font=HEAD_FONT, line_spacing=1.05, first=True)

    subtitle = _s(data.get("subtitle"))
    if subtitle:
        tf = _box(slide, Inches(1.25), Inches(4.3), Inches(9.2), Inches(1.0))
        _para(tf, subtitle, 17, LIGHT_ON_DARK, line_spacing=1.2, first=True)

    meta = "  \u00b7  ".join(
        p for p in (_s(data.get("presenter")), _s(data.get("date"))) if p
    )
    if meta:
        tf = _box(slide, Inches(1.25), Inches(6.35), Inches(9.2), Inches(0.4))
        _para(tf, meta, 13, LIGHT_ON_DARK, first=True)
    return slide


def render_statement(prs, data):
    slide = _new_slide(prs)
    _paint(slide, PAPER)

    kicker = _s(data.get("kicker"))
    if kicker:
        tf = _box(slide, MARGIN, Inches(1.5), CONTENT_W, Inches(0.35))
        _para(tf, kicker.upper(), 11.5, ACCENT, bold=True, font=HEAD_FONT, first=True)

    _shape(slide, MSO_SHAPE.RECTANGLE, MARGIN, Inches(2.4), Inches(0.09),
           Inches(2.5), fill=ACCENT)

    tf = _box(slide, MARGIN + Inches(0.55), Inches(2.35), Inches(10.2), Inches(2.7))
    _para(tf, _s(data.get("title")), 32, INK, bold=True, font=HEAD_FONT,
          line_spacing=1.15, first=True)

    caption = _s(data.get("caption"))
    if caption:
        tf = _box(slide, MARGIN + Inches(0.55), Inches(5.35), Inches(9.5), Inches(0.5))
        _para(tf, caption, 14, MUTED, first=True)
    return slide


def _card(slide, x, y, w, h, item):
    card = _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h,
                  fill=SOFT, line_color=LINE)
    try:
        card.adjustments[0] = 0.055
    except Exception:
        pass

    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x + Inches(0.32), y + Inches(0.35),
           Inches(0.42), Inches(0.09), fill=ACCENT)

    tf = _box(slide, x + Inches(0.32), y + Inches(0.62), w - Inches(0.64), Inches(0.5))
    _para(tf, _txt(item, "title", "heading"), 16, INK, bold=True,
          font=HEAD_FONT, first=True)

    text = _txt(item, "text", "description", "body")
    if text:
        tf = _box(slide, x + Inches(0.32), y + Inches(1.18),
                  w - Inches(0.64), h - Inches(1.5))
        _para(tf, text, 12.5, MUTED, line_spacing=1.15, first=True)


def render_cards(prs, data):
    slide = _new_slide(prs)
    _paint(slide, PAPER)
    _header(slide, data)

    cards = _items(data.get("cards"))
    n = len(cards)
    if n == 0:
        return slide

    cols = 1 if n == 1 else (3 if n in (3, 5, 6) else 2)
    rows = math.ceil(n / cols)
    gap = Inches(0.25)
    top = _header_done_y(data)
    bottom = Inches(6.85)

    card_w = (CONTENT_W - gap * (cols - 1)) // cols
    card_h = (bottom - top - gap * (rows - 1)) // rows
    card_h = min(card_h, Inches(2.75))

    for i, item in enumerate(cards):
        r, c = divmod(i, cols)
        x = MARGIN + c * (card_w + gap)
        y = top + r * (card_h + gap)
        _card(slide, x, y, card_w, card_h, item)
    return slide


def render_process(prs, data):
    slide = _new_slide(prs)
    _paint(slide, PAPER)
    _header(slide, data)

    steps = _items(data.get("steps"))
    n = len(steps)
    if n == 0:
        return slide

    slot_w = CONTENT_W // n
    cy = Inches(3.05)

    # Connector line behind the numbered circles.
    first_cx = MARGIN + slot_w // 2
    last_cx = MARGIN + slot_w * (n - 1) + slot_w // 2
    _shape(slide, MSO_SHAPE.RECTANGLE, first_cx, cy - Inches(0.011),
           last_cx - first_cx, Inches(0.022), fill=LINE)

    d = Inches(0.72)
    for i, step in enumerate(steps):
        cx = MARGIN + slot_w * i + slot_w // 2
        circ = _shape(slide, MSO_SHAPE.OVAL, cx - d // 2, cy - d // 2, d, d,
                      fill=ACCENT)
        tf = circ.text_frame
        tf.word_wrap = False
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        _para(tf, str(i + 1), 18, WHITE, bold=True, font=HEAD_FONT,
              align=PP_ALIGN.CENTER, first=True)

        box_w = slot_w - Inches(0.35)
        tf = _box(slide, cx - box_w // 2, cy + Inches(0.75), box_w, Inches(0.55))
        _para(tf, _txt(step, "title", "step"), 15, INK, bold=True,
              font=HEAD_FONT, align=PP_ALIGN.CENTER, first=True)

        text = _txt(step, "text", "description")
        if text:
            tf = _box(slide, cx - box_w // 2, cy + Inches(1.35), box_w, Inches(1.7))
            _para(tf, text, 11.5, MUTED, align=PP_ALIGN.CENTER,
                  line_spacing=1.15, first=True)
    return slide


def render_timeline(prs, data):
    slide = _new_slide(prs)
    _paint(slide, PAPER)
    _header(slide, data)

    milestones = _items(data.get("milestones"))
    n = len(milestones)
    if n == 0:
        return slide

    slot_w = CONTENT_W // n
    line_y = Inches(4.4)

    first_cx = MARGIN + slot_w // 2
    last_cx = MARGIN + slot_w * (n - 1) + slot_w // 2
    _shape(slide, MSO_SHAPE.RECTANGLE, first_cx, line_y - Inches(0.011),
           last_cx - first_cx, Inches(0.022), fill=LINE)

    dot = Inches(0.2)
    box_w = slot_w - Inches(0.4)

    for i, m in enumerate(milestones):
        cx = MARGIN + slot_w * i + slot_w // 2
        _shape(slide, MSO_SHAPE.OVAL, cx - dot // 2, line_y - dot // 2,
               dot, dot, fill=ACCENT)

        when = _txt(m, "when", "date", "label")
        title = _txt(m, "title", "event")
        text = _txt(m, "text", "description")

        if i % 2 == 0:  # label above the line
            tf = _box(slide, cx - box_w // 2, Inches(2.35), box_w, Inches(1.8),
                      anchor=MSO_ANCHOR.BOTTOM)
        else:           # label below the line
            tf = _box(slide, cx - box_w // 2, line_y + Inches(0.35), box_w, Inches(1.8))

        if when:
            _para(tf, when, 11, ACCENT, bold=True, font=HEAD_FONT, first=True)
        if title:
            _para(tf, title, 14, INK, bold=True, font=HEAD_FONT,
                  space_before=3 if when else 0)
        if text:
            _para(tf, text, 11, MUTED, space_before=3, line_spacing=1.1)
    return slide


def _panel(slide, x, y, w, h, col, accent):
    fill = ACCENT_SOFT if accent else SOFT
    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=fill, line_color=LINE)

    heading = _txt(col, "heading", "title")
    tf = _box(slide, x + Inches(0.38), y + Inches(0.42), w - Inches(0.76), Inches(0.5))
    _para(tf, heading, 17, ACCENT if accent else INK, bold=True,
          font=HEAD_FONT, first=True)

    _shape(slide, MSO_SHAPE.RECTANGLE, x + Inches(0.38), y + Inches(0.98),
           w - Inches(0.76), Inches(0.018), fill=LINE)

    items = col.get("items")
    if isinstance(items, list) and items:
        tf = _box(slide, x + Inches(0.38), y + Inches(1.25),
                  w - Inches(0.76), h - Inches(1.55))
        for j, raw in enumerate(items):
            text = raw if isinstance(raw, str) else _txt(raw, "text", "title")
            text = text.strip()
            if not text:
                continue
            _para(tf, "\u2022  " + text, 12.5, BODY_DK,
                  space_before=0 if j == 0 else 8, line_spacing=1.15, first=(j == 0))


def render_comparison(prs, data):
    slide = _new_slide(prs)
    _paint(slide, PAPER)
    _header(slide, data)

    cols = data.get("columns")
    cols = [c for c in cols if isinstance(c, dict)] if isinstance(cols, list) else []
    if len(cols) < 2:
        cols = cols + [{} for _ in range(2 - len(cols))]

    gap = Inches(0.35)
    panel_w = (CONTENT_W - gap) // 2
    top = _header_done_y(data)
    panel_h = Inches(3.6)

    _panel(slide, MARGIN, top, panel_w, panel_h, cols[0], accent=True)
    _panel(slide, MARGIN + panel_w + gap, top, panel_w, panel_h, cols[1], accent=False)

    verdict = _s(data.get("verdict"))
    if verdict:
        bar = _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, MARGIN, Inches(5.95),
                     CONTENT_W, Inches(0.75), fill=DARK)
        tf = bar.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = Inches(0.35)
        tf.margin_top = tf.margin_bottom = 0
        _para(tf, verdict, 13, WHITE, bold=True, first=True)
    return slide


def render_quote(prs, data):
    slide = _new_slide(prs)
    _paint(slide, PAPER)

    # Oversized decorative opening quote mark.
    tf = _box(slide, MARGIN, Inches(0.95), Inches(2.2), Inches(2.2))
    _para(tf, "\u201c", 120, ACCENT_SOFT, bold=True, font=HEAD_FONT, first=True)

    quote = _s(data.get("quote")) or _s(data.get("title"))
    tf = _box(slide, MARGIN + Inches(1.0), Inches(2.2), Inches(10.0), Inches(2.7))
    _para(tf, quote, 25, INK, line_spacing=1.25, first=True)

    author = _s(data.get("author"))
    if author:
        tf = _box(slide, MARGIN + Inches(1.0), Inches(5.35), Inches(9.0), Inches(0.4))
        _para(tf, "\u2014  " + author, 14, ACCENT, bold=True, first=True)
    role = _s(data.get("role"))
    if role:
        tf = _box(slide, MARGIN + Inches(1.0), Inches(5.8), Inches(9.0), Inches(0.4))
        _para(tf, role, 12, MUTED, first=True)
    return slide


def render_metrics(prs, data):
    slide = _new_slide(prs)
    _paint(slide, PAPER)
    _header(slide, data)

    metrics = _items(data.get("metrics"))
    n = len(metrics)
    if n == 0:
        return slide

    cols = n if n <= 4 else (3 if n <= 6 else 4)
    rows = math.ceil(n / cols)
    gap = Inches(0.3)
    top = Inches(2.15)
    bottom = Inches(6.7)

    cell_w = (CONTENT_W - gap * (cols - 1)) // cols
    cell_h = (bottom - top - gap * (rows - 1)) // rows

    for i, m in enumerate(metrics):
        r, c = divmod(i, cols)
        x = MARGIN + c * (cell_w + gap)
        y = top + r * (cell_h + gap)

        value = _txt(m, "value", "number")
        label = _txt(m, "label", "name")
        sub = _txt(m, "sub", "note", "description")

        tf = _box(slide, x, y + Inches(0.25), cell_w, Inches(0.85))
        _para(tf, value, 36, ACCENT, bold=True, font=HEAD_FONT,
              align=PP_ALIGN.CENTER, first=True)

        _shape(slide, MSO_SHAPE.RECTANGLE, x + cell_w // 2 - Inches(0.25),
               y + Inches(1.18), Inches(0.5), Inches(0.03), fill=ACCENT)

        tf = _box(slide, x, y + Inches(1.35), cell_w, Inches(0.4))
        _para(tf, label, 13.5, INK, bold=True, font=HEAD_FONT,
              align=PP_ALIGN.CENTER, first=True)

        if sub:
            tf = _box(slide, x, y + Inches(1.78), cell_w, Inches(0.6))
            _para(tf, sub, 11, MUTED, align=PP_ALIGN.CENTER,
                  line_spacing=1.1, first=True)
    return slide


def _try_fetch_image(url):
    """Optionally fetch a remote image (http/https) as BytesIO, or None."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    try:
        with urlopen(url, timeout=6) as resp:  # noqa: S310 (URL validated above)
            data = resp.read(6 * 1024 * 1024 + 1)
        if len(data) > 6 * 1024 * 1024:
            return None
        return io.BytesIO(data)
    except Exception:
        return None


def render_image(prs, data):
    slide = _new_slide(prs)
    _paint(slide, PAPER)
    _header(slide, data)

    x, y = MARGIN, Inches(2.05)
    w, h = CONTENT_W, Inches(3.85)

    stream = _try_fetch_image(data.get("image"))
    placed = False
    if stream is not None:
        try:
            pic = slide.shapes.add_picture(stream, x, y)
            scale = min(w / pic.width, h / pic.height)
            pic.width = int(pic.width * scale)
            pic.height = int(pic.height * scale)
            pic.left = int(x + (w - pic.width) / 2)
            pic.top = int(y + (h - pic.height) / 2)
            placed = True
        except Exception:
            placed = False

    if not placed:
        ph = _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h,
                    fill=SOFT, line_color=LINE)
        ph.line.width = Pt(1.25)
        try:
            ph.line.dash_style = MSO_LINE.DASH
        except Exception:
            pass
        tf = ph.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = Inches(0.4)
        tf.margin_top = tf.margin_bottom = Inches(0.2)
        _para(tf, "Image", 16, MUTED, bold=True, font=HEAD_FONT,
              align=PP_ALIGN.CENTER, first=True)
        _para(tf, "Drop your picture here (Insert \u2192 Pictures in PowerPoint)",
              11.5, MUTED, align=PP_ALIGN.CENTER, space_before=6)
        url = _s(data.get("image"))
        if url:
            _para(tf, url, 10.5, MUTED, align=PP_ALIGN.CENTER, space_before=6)

    caption = _s(data.get("caption"))
    if caption:
        tf = _box(slide, MARGIN, Inches(6.15), CONTENT_W, Inches(0.4))
        _para(tf, caption, 12, MUTED, align=PP_ALIGN.CENTER, first=True)
    return slide


def render_closing(prs, data):
    slide = _new_slide(prs)
    _paint(slide, DARK)

    _shape(slide, MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.14), SLIDE_H, fill=ACCENT)
    _shape(slide, MSO_SHAPE.OVAL, SLIDE_W - Inches(3.0), -Inches(1.4),
           Inches(4.4), Inches(4.4), line_color=DARK_2, line_w=Pt(1.25))
    _shape(slide, MSO_SHAPE.OVAL, SLIDE_W - Inches(1.5), -Inches(0.5),
           Inches(2.2), Inches(2.2), line_color=DARK_2, line_w=Pt(1.25))

    tf = _box(slide, Inches(1.25), Inches(2.55), Inches(10.4), Inches(1.2))
    _para(tf, _s(data.get("title")) or "Thank you", 40, WHITE, bold=True,
          font=HEAD_FONT, first=True)

    message = _s(data.get("message"))
    if message:
        tf = _box(slide, Inches(1.25), Inches(3.85), Inches(9.2), Inches(0.9))
        _para(tf, message, 16, LIGHT_ON_DARK, line_spacing=1.2, first=True)

    contacts = "   \u00b7   ".join(
        c for c in (_s(data.get("email")), _s(data.get("website")),
                    _s(data.get("phone"))) if c
    )
    if contacts:
        tf = _box(slide, Inches(1.25), Inches(5.6), Inches(10.4), Inches(0.45))
        _para(tf, contacts, 13, ACCENT, bold=True, first=True)
    return slide
