"""Detection and rendering of "draw lines to match" questions (wired up by static/match.js)."""

import re
from html import escape

from .text import (
    _find_pipe_table_blocks,
)



_LINE_MATCH_PROMPT_RE = re.compile(
    r"draw\s+(?:\w+\s+)?lines?\s+from\s+each", re.IGNORECASE
)


def _slug_key(text: str) -> str:
    """Stable, attribute-safe key for a matcher item — keeps alphanumerics and
    collapses everything else to single underscores. Used for data-key so the
    JS can find boxes by their original text reliably."""
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9]+", "_", text)).strip("_") or "x"


def _extract_line_match_columns(text: str) -> tuple[str, str, list[str], list[str]] | None:
    """If `text` contains a 2-column pipe-table with a header + ≥3 data rows,
    return (left_header, right_header, left_items, right_items). Else None.
    The data rows are NOT pre-matched pairs — each cell is an independent
    item in its column (matching what Cambridge prints on the page)."""
    blocks = _find_pipe_table_blocks(text)
    if not blocks:
        return None
    raw = text.splitlines()
    for start, end in blocks:
        rows = [raw[i] for i in range(start, end)]
        if len(rows) < 4:  # header + ≥3 data rows
            continue
        parsed = []
        for ln in rows:
            cells = [c.strip() for c in ln.split("|")]
            while cells and not cells[0]:
                cells.pop(0)
            while cells and not cells[-1]:
                cells.pop()
            if len(cells) != 2:
                break
            parsed.append(cells)
        else:
            header, *data = parsed
            left_items = [r[0] for r in data if r[0]]
            right_items = [r[1] for r in data if r[1]]
            if len(left_items) >= 2 and len(right_items) >= 2:
                return header[0], header[1], left_items, right_items
    return None


def _is_line_match(q, text: str) -> tuple[str, str, list[str], list[str]] | None:
    """Heuristic: a Cambridge "draw lines to match" question is `command=Draw`,
    its text has a "draw … line(s) from each" phrase, and the text contains a
    2-column pipe-table."""
    if (q.get("command") or "").strip().lower() != "draw":
        return None
    if not _LINE_MATCH_PROMPT_RE.search(text or ""):
        return None
    return _extract_line_match_columns(text or "")


def _render_line_matching(q, columns):
    """Two columns of clickable boxes + an SVG overlay where the student draws
    lines between matching items. Wired up by `match.js`."""
    left_header, right_header, left_items, right_items = columns
    qid = escape(q.get("id", ""))

    def _col(side, header, items):
        box_html = "".join(
            f'<button type="button" class="match-box" '
            f'data-side="{side}" data-key="{escape(_slug_key(item))}">'
            f'{escape(item)}</button>'
            for item in items
        )
        col_cls = "match-col-left" if side == "L" else "match-col-right"
        return (
            f'<div class="match-col {col_cls}">'
            f'<div class="match-col-label">{escape(header)}</div>'
            f'{box_html}'
            f'</div>'
        )

    left_total = len(left_items)
    return (
        f'<div class="q-input">'
        f'<div class="match-grid" data-qid="{qid}">'
        f'{_col("L", left_header, left_items)}'
        f'<svg class="match-lines" aria-hidden="true"></svg>'
        f'{_col("R", right_header, right_items)}'
        f'<div class="match-toolbar">'
        f'<span class="match-count">0 / {left_total} lines drawn</span>'
        f'<button type="button" class="match-clear">Clear all lines</button>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
