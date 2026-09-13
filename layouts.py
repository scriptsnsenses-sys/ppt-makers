"""
Layouts — slide renderers for PPT Maker.

Each render_* function takes (prs, spec) and returns a python-pptx slide.
All functions are defensive: missing optional keys fall back to clean
defaults instead of raising, because the spec was already validated but
may still omit optional fields.

Design system:
    - 16:9 canvas (13.33 x 7.5 in)
    - White background, dark ink, muted gray, indigo accent
    - Calibri everywhere (universally available in PowerPoint)
"""

import io
import logging

from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

try:
    import requests
except Exception:  # pragma: no cover - requests is in requirements
    requests = None

log = logging.getLogger("ppt-maker.layouts")

# ---------------------------------------------------------------------------
# Canvas + palette
# ---------------------------------------------------------------------------

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)
MARGIN = Inches(0.6)
CONTENT_W = SLIDE_W - MARGIN * 2

INK = RGBColor(0x1A, 0x1F, 0x36)
MUTED = RGBColor(0x6B, 0x73, 0x8C)
ACCENT = RGBColor(0x57, 0x4B, 0xD1)
ACCENT_LIGHT = RGBColor(0xEE, 0xEC, 0xFB)
LINE = RGBColor(0xE2, 0xE4, 0xEF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CARD_FILL = RGBColor(0xFA, 0xFB, 0xFE)
DARK_BG = RGBColor(0x1A, 0x1F, 0x36)

FONT = "Calibri"

MAX_IMAGE_BYTES = 6 * 1024 * 1024


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _str(value, default=""):
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _blank_slide(prs):
    layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(layout)
    _set_bg(slide, WHITE)
    return slide


def _set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _box(slide, left, top, width, height):
    """Add a borderless textbox; return its text_frame (word-wrap on)."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    return tf


def _para(tf, text, size, color, bold=False, align=PP_ALIGN.LEFT,
          first=True, italic=False, space_after=Pt(2), space_before=Pt(0)):
    """Append (or reuse first) paragraph with consistent styling."""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.text = ""
    p.alignment = align
    p.space_after = space_after
    p.space_before = space_before
    run = p.add_run()
    run.text = str(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = FONT
    return p


def _card_shape(slide, left, top, width, height, fill=CARD_FILL,
                line=LINE, accent_top=True):
    from pptx.enum.shapes import MSO_SHAPE
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(1)
    shape.shadow.inherit = False
    if accent_top:
        bar = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, Inches(0.07)
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = ACCENT
        bar.line.fill.background()
    return shape


def _kicker(slide, text, top, align=PP_ALIGN.LEFT):
    if not text:
        return top
    tf = _box(slide, MARGIN, top, CONTENT_W, Inches(0.4))
    _para(tf, _str(text).upper(), 11, ACCENT, bold=True, align=align, first=True)
    return top + Inches(0.38)


def _section_title(slide, text, top, size=30, align=PP_ALIGN.LEFT):
    if not text:
        return top
    tf = _box(slide, MARGIN, top, CONTENT_W, Inches(1.0))
    _para(tf, text, size, INK, bold=True, align=align, first=True)
    return top + Inches(0.85)


def _bullet_list(tf, items, size=14, color=INK, first=False):
    for i, item in enumerate(items):
        p = tf.add_paragraph() if (i > 0 or not first) else tf.paragraphs[0]
        p.text = ""
        p.level = 0
        p.space_after = Pt(4)
        run = p.add_run()
        run.text = "\u2022  " + str(item).strip()
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = FONT


# ---------------------------------------------------------------------------
# hero — cover slide
# ---------------------------------------------------------------------------

def render_hero(prs, spec):
    slide = _blank_slide(prs)

    # Accent sidebar (formal SaaS cover, still prints well).
    from pptx.enum.shapes import MSO_SHAPE
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.42), SLIDE_H
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()

    kicker = _str(spec.get("kicker", "PRESENTATION"))
    title = _str(spec.get("title", "Untitled"))
    subtitle = _str(spec.get("subtitle", ""))
    presenter = _str(spec.get("presenter", ""))
    date = _str(spec.get("date", ""))

    top = Inches(1.5)
    if kicker:
        tf = _box(slide, Inches(1.2), top, Inches(10.5), Inches(0.5))
        _para(tf, kicker.upper(), 12, ACCENT, bold=True, first=True)
        top += Inches(0.5)

    tf = _box(slide, Inches(1.2), top, Inches(10.5), Inches(2.2))
    _para(tf, title, 44, INK, bold=True, first=True, space_after=Pt(8))
    top += Inches(1.9)

    if subtitle:
        tf = _box(slide, Inches(1.2), top, Inches(10.0), Inches(1.0))
        _para(tf, subtitle, 20, MUTED, first=True)
        top += Inches(0.9)

    meta = "  \u00b7  ".join([m for m in (presenter, date) if m])
    if meta:
        tf = _box(slide, Inches(1.2), Inches(6.35), Inches(10.5), Inches(0.5))
        _para(tf, meta, 13, MUTED, first=True)

    return slide


# ---------------------------------------------------------------------------
# statement — one big idea
# ---------------------------------------------------------------------------

def render_statement(prs, spec):
    slide = _blank_slide(prs)
    title = _str(spec.get("title", ""))
    kicker = _str(spec.get("kicker", ""))
    caption = _str(spec.get("caption", ""))

    top = Inches(1.4)
    if kicker:
        tf = _box(slide, MARGIN, top, CONTENT_W, Inches(0.5))
        _para(tf, kicker.upper(), 12, ACCENT, bold=True,
              align=PP_ALIGN.CENTER, first=True)
        top += Inches(0.55)

    tf = _box(slide, Inches(1.3), top, Inches(10.7), Inches(3.2))
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    _para(tf, title, 36, INK, bold=True, align=PP_ALIGN.CENTER, first=True)

    if caption:
        tf = _box(slide, Inches(1.3), Inches(5.3), Inches(10.7), Inches(0.8))
        _para(tf, caption, 16, MUTED, align=PP_ALIGN.CENTER,
              italic=True, first=True)
    return slide


# ---------------------------------------------------------------------------
# cards — grid of 1-6 cards
# ---------------------------------------------------------------------------

def render_cards(prs, spec):
    slide = _blank_slide(prs)
    top = Inches(0.55)
    top = _kicker(slide, _str(spec.get("kicker", "")), top)
    top = _section_title(slide, _str(spec.get("title", "")), top, size=28)

    cards = [c for c in (spec.get("cards") or []) if isinstance(c, dict)][:6]
    n = max(1, len(cards))
    cols = 3 if n > 2 else n
    rows = (n + cols - 1) // cols
    gap = Inches(0.3)
    avail_w = CONTENT_W - gap * (cols - 1)
    card_w = avail_w / cols
    card_h = min(Inches(3.4), Inches(4.6) / max(1, rows))
    grid_top = top + Inches(0.25)
    # Vertically center a single row a touch lower for balance.
    if rows == 1:
        grid_top += Inches(0.4)

    for idx, card in enumerate(cards):
        r, c = divmod(idx, cols)
        left = MARGIN + c * (card_w + gap)
        ctop = grid_top + r * (card_h + gap)
        _card_shape(slide, left, ctop, card_w, card_h)
        pad = Inches(0.3)
        tf = _box(slide, left + pad, ctop + Inches(0.35),
                  card_w - pad * 2, card_h - Inches(0.6))
        _para(tf, _str(card.get("title", "")), 17, INK, bold=True, first=True,
              space_after=Pt(6))
        body = _str(card.get("text", ""))
        if body:
            _para(tf, body, 13.5, MUTED, first=False, space_after=Pt(0))
    return slide


# ---------------------------------------------------------------------------
# process — numbered steps
# ---------------------------------------------------------------------------

def render_process(prs, spec):
    slide = _blank_slide(prs)
    top = Inches(0.55)
    top = _kicker(slide, _str(spec.get("kicker", "")), top)
    top = _section_title(slide, _str(spec.get("title", "")), top, size=28)

    steps = [s for s in (spec.get("steps") or []) if isinstance(s, dict)][:6]
    n = max(1, len(steps))
    gap = Inches(0.3)
    col_w = (CONTENT_W - gap * (n - 1)) / n
    y = top + Inches(0.4)

    for i, step in enumerate(steps):
        left = MARGIN + i * (col_w + gap)
        # Number badge
        from pptx.enum.shapes import MSO_SHAPE
        badge = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, left, y, Inches(0.55), Inches(0.55)
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = ACCENT
        badge.line.fill.background()
        tf = badge.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        _para(tf, str(i + 1), 16, WHITE, bold=True,
              align=PP_ALIGN.CENTER, first=True)

        tf = _box(slide, left, y + Inches(0.75), col_w, Inches(2.6))
        _para(tf, _str(step.get("title", "")), 16, INK, bold=True,
              first=True, space_after=Pt(6))
        body = _str(step.get("text", ""))
        if body:
            _para(tf, body, 13, MUTED, first=False)

        # Connector line between steps.
        if i < n - 1:
            cx = left + col_w + Inches(0.06)
            conn = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, cx, y + Inches(0.25),
                gap - Inches(0.12), Pt(3)
            )
            conn.fill.solid()
            conn.fill.fore_color.rgb = LINE
            conn.line.fill.background()
    return slide


# ---------------------------------------------------------------------------
# timeline — milestones
# ---------------------------------------------------------------------------

def render_timeline(prs, spec):
    slide = _blank_slide(prs)
    top = Inches(0.55)
    top = _kicker(slide, _str(spec.get("kicker", "")), top)
    top = _section_title(slide, _str(spec.get("title", "")), top, size=28)

    items = [m for m in (spec.get("milestones") or [])
             if isinstance(m, dict)][:6]
    n = max(1, len(items))
    gap = Inches(0.3)
    col_w = (CONTENT_W - gap * (n - 1)) / n
    y = top + Inches(0.7)

    # Horizontal rail.
    from pptx.enum.shapes import MSO_SHAPE
    rail = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, MARGIN, y, CONTENT_W, Pt(3)
    )
    rail.fill.solid()
    rail.fill.fore_color.rgb = LINE
    rail.line.fill.background()

    for i, ms in enumerate(items):
        left = MARGIN + i * (col_w + gap)
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, left + Inches(0.05), y - Inches(0.11),
            Inches(0.28), Inches(0.28)
        )
        dot.fill.solid()
        dot.fill.fore_color.rgb = ACCENT
        dot.line.fill.background()

        when = _str(ms.get("when", ""))
        tf = _box(slide, left, y + Inches(0.25), col_w, Inches(2.4))
        first = True
        if when:
            _para(tf, when.upper(), 11, ACCENT, bold=True,
                  first=True, space_after=Pt(4))
            first = False
        _para(tf, _str(ms.get("title", "")), 16, INK, bold=True,
              first=first, space_after=Pt(6))
        body = _str(ms.get("text", ""))
        if body:
            _para(tf, body, 13, MUTED, first=False)
    return slide


# ---------------------------------------------------------------------------
# comparison — two columns + verdict
# ---------------------------------------------------------------------------

def render_comparison(prs, spec):
    slide = _blank_slide(prs)
    top = Inches(0.55)
    top = _kicker(slide, _str(spec.get("kicker", "")), top)
    top = _section_title(slide, _str(spec.get("title", "")), top, size=28)

    cols = spec.get("columns") or []
    while len(cols) < 2:
        cols.append({})
    cols = cols[:2]

    gap = Inches(0.4)
    col_w = (CONTENT_W - gap) / 2
    y = top + Inches(0.3)
    fills = [ACCENT_LIGHT, CARD_FILL]

    for i, col in enumerate(cols):
        if not isinstance(col, dict):
            col = {}
        left = MARGIN + i * (col_w + gap)
        _card_shape(slide, left, y, col_w, Inches(3.9),
                    fill=fills[i % 2], accent_top=(i == 0))
        pad = Inches(0.35)
        tf = _box(slide, left + pad, y + Inches(0.35),
                  col_w - pad * 2, Inches(3.2))
        _para(tf, _str(col.get("heading", "")), 18, INK, bold=True,
              first=True, space_after=Pt(8))
        items = col.get("items") or []
        clean = [str(x).strip() for x in items
                 if str(x).strip()][:8]
        if clean:
            _bullet_list(tf, clean, size=14, first=False)

    verdict = _str(spec.get("verdict", ""))
    if verdict:
        from pptx.enum.shapes import MSO_SHAPE
        bar = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            MARGIN, Inches(6.0), CONTENT_W, Inches(0.75),
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = DARK_BG
        bar.line.fill.background()
        tf = bar.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        _para(tf, verdict, 14, WHITE, bold=False,
              align=PP_ALIGN.CENTER, first=True)
    return slide


# ---------------------------------------------------------------------------
# quote
# ---------------------------------------------------------------------------

def render_quote(prs, spec):
    slide = _blank_slide(prs)
    quote = _str(spec.get("quote", ""))
    author = _str(spec.get("author", ""))
    role = _str(spec.get("role", ""))

    tf = _box(slide, Inches(1.0), Inches(0.7), Inches(11.3), Inches(0.8))
    _para(tf, "\u201c", 72, ACCENT, bold=True,
          align=PP_ALIGN.CENTER, first=True)

    tf = _box(slide, Inches(1.6), Inches(1.9), Inches(10.1), Inches(2.8))
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    _para(tf, quote, 28, INK, italic=True,
          align=PP_ALIGN.CENTER, first=True)

    byline = " \u2014 ".join([b for b in (
        ("\u2014 " + author) if author else "", role) if b])
    if not byline and author:
        byline = "\u2014 " + author
    if byline:
        tf = _box(slide, Inches(1.6), Inches(4.9), Inches(10.1), Inches(0.7))
        _para(tf, byline, 15, MUTED, align=PP_ALIGN.CENTER, first=True)
    return slide


# ---------------------------------------------------------------------------
# metrics — big numbers
# ---------------------------------------------------------------------------

def render_metrics(prs, spec):
    slide = _blank_slide(prs)
    top = Inches(0.55)
    top = _kicker(slide, _str(spec.get("kicker", "")), top)
    top = _section_title(slide, _str(spec.get("title", "")), top, size=28)

    metrics = [m for m in (spec.get("metrics") or [])
               if isinstance(m, dict)][:8]
    n = max(1, len(metrics))
    per_row = 4 if n > 3 else n
    rows = (n + per_row - 1) // per_row
    gap = Inches(0.3)
    col_w = (CONTENT_W - gap * (per_row - 1)) / per_row
    row_h = Inches(2.1) if rows > 1 else Inches(2.6)
    y0 = top + Inches(0.4)

    for idx, m in enumerate(metrics):
        r, c = divmod(idx, per_row)
        # Center the last incomplete row.
        in_row = min(per_row, n - r * per_row)
        offset = (CONTENT_W - (in_row * col_w + (in_row - 1) * gap)) / 2
        left = MARGIN + offset + c * (col_w + gap)
        ctop = y0 + r * (row_h + gap)
        _card_shape(slide, left, ctop, col_w, row_h, accent_top=False)
        pad = Inches(0.3)
        tf = _box(slide, left + pad, ctop + Inches(0.25),
                  col_w - pad * 2, row_h - Inches(0.4))
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        _para(tf, _str(m.get("value", "")), 32, ACCENT, bold=True,
              align=PP_ALIGN.CENTER, first=True, space_after=Pt(4))
        _para(tf, _str(m.get("label", "")), 14, INK, bold=False,
              align=PP_ALIGN.CENTER, first=False, space_after=Pt(2))
        sub = _str(m.get("sub", ""))
        if sub:
            _para(tf, sub, 12, MUTED, align=PP_ALIGN.CENTER, first=False)
    return slide


# ---------------------------------------------------------------------------
# image — embedded image or placeholder
# ---------------------------------------------------------------------------

def _download_image(url):
    """Download an image URL safely. Returns bytes or None."""
    if requests is None:
        return None
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return None
    try:
        with requests.get(url, timeout=8, stream=True,
                           headers={"User-Agent": "ppt-maker/1.0"}) as resp:
            resp.raise_for_status()
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if ctype and not ctype.startswith("image/"):
                # Some hosts omit content-type; only reject clear non-images.
                if "octet" not in ctype:
                    log.info("Rejecting non-image content-type: %s", ctype)
                    return None
            buf = io.BytesIO()
            total = 0
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    log.info("Image exceeded %d bytes, skipping embed.",
                             MAX_IMAGE_BYTES)
                    return None
                buf.write(chunk)
            data = buf.getvalue()
            if len(data) < 128:
                return None
            return data
    except Exception as exc:
        log.info("Image download failed (%s): %s", url, exc)
        return None


def render_image(prs, spec):
    slide = _blank_slide(prs)
    top = Inches(0.55)
    top = _kicker(slide, _str(spec.get("kicker", "")), top)
    top = _section_title(slide, _str(spec.get("title", "")), top, size=28)

    frame_top = top + Inches(0.3)
    frame_h = Inches(4.3)
    frame_left = MARGIN
    frame_w = CONTENT_W

    data = _download_image(spec.get("image", ""))
    if data:
        try:
            slide.shapes.add_picture(
                io.BytesIO(data), frame_left, frame_top,
                width=frame_w, height=frame_h,
            )
        except Exception as exc:
            log.info("Embedding image failed: %s", exc)
            data = None

    if not data:
        from pptx.enum.shapes import MSO_SHAPE
        ph = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            frame_left, frame_top, frame_w, frame_h,
        )
        ph.fill.solid()
        ph.fill.fore_color.rgb = CARD_FILL
        ph.line.color.rgb = MUTED
        ph.line.width = Pt(1.5)
        # NOTE: python-pptx has no dashed-line API exposed reliably,
        # so we use a solid hairline + helper text instead.
        tf = ph.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        _para(tf, "Image placeholder", 18, MUTED, bold=True,
              align=PP_ALIGN.CENTER, first=True, space_after=Pt(6))
        _para(tf, "Add an image URL, or in PowerPoint use Insert \u2192 Pictures.",
              13, MUTED, align=PP_ALIGN.CENTER, first=False)

    caption = _str(spec.get("caption", ""))
    if caption:
        tf = _box(slide, MARGIN, frame_top + frame_h + Inches(0.2),
                  CONTENT_W, Inches(0.6))
        _para(tf, caption, 13, MUTED, italic=True,
              align=PP_ALIGN.CENTER, first=True)
    return slide


# ---------------------------------------------------------------------------
# closing
# ---------------------------------------------------------------------------

def render_closing(prs, spec):
    slide = _blank_slide(prs)
    _set_bg(slide, DARK_BG)

    title = _str(spec.get("title", "Thank you"))
    message = _str(spec.get("message", ""))
    email = _str(spec.get("email", ""))
    website = _str(spec.get("website", ""))

    # Thin accent rule above the headline.
    from pptx.enum.shapes import MSO_SHAPE
    rule = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(6.16), Inches(1.6), Inches(1.0), Pt(4)
    )
    rule.fill.solid()
    rule.fill.fore_color.rgb = ACCENT
    rule.line.fill.background()

    tf = _box(slide, Inches(1.3), Inches(2.0), Inches(10.7), Inches(1.6))
    _para(tf, title, 44, WHITE, bold=True,
          align=PP_ALIGN.CENTER, first=True)

    if message:
        tf = _box(slide, Inches(1.3), Inches(3.7), Inches(10.7), Inches(1.0))
        _para(tf, message, 20, RGBColor(0xC2, 0xC7, 0xDB),
              align=PP_ALIGN.CENTER, first=True)

    contact = "   \u00b7   ".join([c for c in (email, website) if c])
    if contact:
        tf = _box(slide, Inches(1.3), Inches(5.6), Inches(10.7), Inches(0.7))
        _para(tf, contact, 15, RGBColor(0xC2, 0xC7, 0xDB),
              align=PP_ALIGN.CENTER, first=True)
    return slide
