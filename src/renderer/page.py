"""Whole-page rendering and writing the page plus its static assets."""

import re
from html import escape
from pathlib import Path

from ..assets import read_asset
from ..syllabus import SESSION_LETTER_NAMES

from .question import (
    render_question_card,
)

ASSET_FILES = ("paper.css", "paper.js", "circuit.js", "match.js")
PAPER_CSS = read_asset("paper.css")
PAPER_JS = read_asset("paper.js")


def _parse_session_label(qp: str) -> str:
    """Parse 'm25' / 's24' from a qp filename into 'March 2025' / 'Summer 2024'."""
    m = re.search(r"_([msw])(\d{2})_qp_", qp or "")
    if not m:
        return ""
    letter, yy = m.groups()
    name = SESSION_LETTER_NAMES.get(letter, letter)
    return f"{name} 20{yy}"


def render_html(data: dict) -> str:
    board = escape(data.get("board", ""))
    level = escape(data.get("level", ""))
    subject = escape(data.get("subject_name", ""))
    code = escape(data.get("subject_code", ""))
    variant = escape(str(data.get("variant", "")))
    total = data.get("total_marks", "?")
    qp = data.get("qp", "")

    paper_num = variant[:1] if variant else ""
    variant_num = variant[1:2] if len(variant) >= 2 else ""
    session_label = _parse_session_label(qp)

    parts = [f"{board} {level} {subject} ({code})"]
    if paper_num:
        parts.append(f"Paper {paper_num}")
    if variant_num:
        parts.append(f"Variant {variant_num}")
    if session_label:
        parts.append(session_label)
    title = " · ".join(parts)

    questions = data.get("questions", [])
    q_cards = "\n".join(render_question_card(q) for q in questions)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="paper.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@joint/core@4.2.4/dist/joint.css">
</head>
<body>
<div class="page">
  <div class="paper-header">
    <h1>{title}</h1>
    <p>{len(questions)} questions &nbsp;·&nbsp; {total} marks total</p>
  </div>
  {q_cards}
</div>
<script src="paper.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@joint/core@4.2.4/dist/joint.min.js"></script>
<script src="circuit.js"></script>
<script src="match.js"></script>
</body>
</html>"""


def _write_assets(directory: Path) -> None:
    for name in ASSET_FILES:
        # newline="" keeps the bytes identical to src/static/<name>
        with open(directory / name, "w", encoding="utf-8", newline="") as f:
            f.write(read_asset(name))


def render(data: dict, output_path: str | Path) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_assets(out.parent)
    out.write_text(render_html(data), encoding="utf-8")
