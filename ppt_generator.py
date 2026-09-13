"""
PPT Generator — assembles a .pptx from a validated presentation spec.

Responsibilities:
    - create the Presentation object
    - set slide dimensions (16:9)
    - dispatch each slide to the matching layout renderer in layouts.py
    - add footers / speaker notes
    - save to bytes and return them
"""

from io import BytesIO

from pptx import Presentation
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN

import layouts

RENDERERS = {
    "hero": layouts.render_hero,
    "statement": layouts.render_statement,
    "cards": layouts.render_cards,
    "process": layouts.render_process,
    "timeline": layouts.render_timeline,
    "comparison": layouts.render_comparison,
    "quote": layouts.render_quote,
    "metrics": layouts.render_metrics,
    "image": layouts.render_image,
    "closing": layouts.render_closing,
}

# Slide types that look like full-bleed "bookends" and skip the footer.
FOOTER_SKIP = {"hero", "closing"}


def generate_pptx(spec):
    """Render a validated spec dict and return the .pptx file as bytes."""
    prs = Presentation()
    prs.slide_width = layouts.SLIDE_W
    prs.slide_height = layouts.SLIDE_H
    core = prs.core_properties
    try:
        core.title = str(spec.get("title", ""))[:255]
        core.subject = "Generated with PPT Maker"
        core.author = "PPT Maker"
    except Exception:
        pass

    slides = spec.get("slides", [])
    total = len(slides)
    deck_title = str(spec.get("title", "")).strip()

    for page, slide_spec in enumerate(slides, start=1):
        if not isinstance(slide_spec, dict):
            raise ValueError(f"slides[{page - 1}]: must be an object.")
        slide_type = slide_spec.get("type")
        renderer = RENDERERS.get(slide_type)
        if renderer is None:
            raise ValueError(f"slides[{page - 1}].type: unknown type {slide_type!r}.")
        slide = renderer(prs, slide_spec)

        _add_notes(slide, slide_spec)
        if slide_type not in FOOTER_SKIP:
            _add_footer(slide, deck_title, page, total)

    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _add_notes(slide, spec):
    """Attach speaker notes if the slide spec contains a 'notes' string."""
    notes = spec.get("notes")
    if isinstance(notes, str) and notes.strip():
        slide.notes_slide.notes_text_frame.text = notes.strip()


def _add_footer(slide, deck_title, page, total):
    """Small, unobtrusive footer: deck title (left) + page number (right)."""
    if deck_title:
        tf = layouts._box(slide, layouts.MARGIN, Inches(7.02), Inches(8), Inches(0.32))
        layouts._para(tf, deck_title, 9.5, layouts.MUTED, first=True)
    tf = layouts._box(
        slide,
        layouts.SLIDE_W - layouts.MARGIN - Inches(1.2),
        Inches(7.02),
        Inches(1.2),
        Inches(0.32),
    )
    layouts._para(tf, f"{page} / {total}", 9.5, layouts.MUTED,
                  align=PP_ALIGN.RIGHT, first=True)