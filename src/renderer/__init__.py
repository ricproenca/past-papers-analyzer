"""Render extracted exam JSON as self-contained HTML review pages.

Layout of the package:
    text.py      shared helpers (badges, pipe tables, code stems, prose)
    layouts.py   one renderer per layout_type + dispatch table
    matching.py  "draw lines to match" detection and rendering
    question.py  a single question card
    page.py      whole page, plus writing the static assets next to it

The CSS/JS the pages load live in src/static/ (see src/assets.py).
"""

from .page import PAPER_CSS, PAPER_JS, interactive_script_tags, render, render_html
from .question import render_question_card

__all__ = ["PAPER_CSS", "PAPER_JS", "interactive_script_tags", "render", "render_html", "render_question_card"]
