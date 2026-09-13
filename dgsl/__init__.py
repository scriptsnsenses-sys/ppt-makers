"""DGSL (DG Slide Language) v1.0 — declarative presentations as code.

Pipeline: source -> lexer -> parser -> compiler -> IR -> renderer -> .pptx.
DGSL is pure data (no code execution), so compiling untrusted source is
safe by construction: the worst input produces a validation error.
"""

from .compiler import Compiler
from .errors import DGSLError
from .lexer import lex
from .parser import Parser
from .renderer import render_pptx as _render

MAX_DGSL_CHARS = 200_000


class DGSL_IR:
    """Compiled presentation: title, meta, slides, warnings."""

    def __init__(self, title, meta, slides, warnings):
        self.title = title
        self.meta = meta
        self.slides = slides
        self.warnings = list(warnings)

    @classmethod
    def from_dict(cls, data):
        return cls(data.get("title", "Untitled"),
                   data.get("meta", {}),
                   data.get("slides", []),
                   data.get("warnings", []))


class _Slide:
    def __init__(self, data):
        self.name = data.get("name", "")
        self.background = data.get("background")
        self.notes = data.get("notes", "")
        self.elements = data.get("elements", [])
        self.line = data.get("line")


def compile_dgsl(source):
    """Parse + compile DGSL source into a DGSL_IR. Raises DGSLError."""
    if not isinstance(source, str) or not source.strip():
        raise DGSLError("provide a non-empty DGSL document")
    if len(source) > MAX_DGSL_CHARS:
        raise DGSLError(f"DGSL source is too long ({len(source)} chars, "
                        f"max {MAX_DGSL_CHARS})")
    tokens = lex(source)
    program = Parser(tokens).parse()
    data = Compiler().compile(program)
    return DGSL_IR(data["title"], data["meta"],
                   [_Slide(s) for s in data["slides"]], data["warnings"])


def render_dgsl_pptx(ir):
    """Render a DGSL_IR (or its raw dict) and return the .pptx bytes."""
    if isinstance(ir, dict):
        ir = DGSL_IR.from_dict(ir)
    return _render(ir)


__all__ = ["DGSL_IR", "DGSLError", "MAX_DGSL_CHARS", "compile_dgsl",
           "render_dgsl_pptx"]
