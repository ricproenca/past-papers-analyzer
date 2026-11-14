"""Shared HTML helpers: badges, pipe-table detection/rendering, code stems and prose paragraphs."""

import re
from html import escape


def _badge(text, cls):
    return f'<span class="badge {cls}">{escape(str(text))}</span>'


_SQL_KEYWORD_RE = re.compile(
    r"^\s*(SELECT|FROM|WHERE|ORDER\s+BY|GROUP\s+BY|HAVING|INSERT|UPDATE|DELETE|"
    r"CREATE|DROP|ALTER|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|SET|VALUES|INTO)\b",
    re.IGNORECASE,
)
# Cambridge pseudocode: every line starts with a 2-digit line number then a space then content
# e.g. "01 DECLARE Numbers : ARRAY[1:1000] OF INTEGER"
_PSEUDOCODE_LINE_RE = re.compile(r"^\s*\d{2}\s+\S")


# ============================================================================
# Layout-specific input renderers
# ============================================================================

def _pipe_table_lines(lines: list[str]) -> list[str] | None:
    """If `lines` (non-empty, already-stripped) form a valid pipe-table —
    2+ rows, every row contains '|', all rows have the same '|'-separated
    column count, ≥2 columns — return the same list. Otherwise None.

    Single source of truth for pipe-table detection. Used by both:
    - `_maybe_pipe_table` to render genuine reference tables in prose stems
    - `_strip_pipe_tables` to remove pipe-mirrors of tables already rendered
      by a structured layout renderer (MatrixGrid / ValueTraceMatrix /
      TermDefinitionGrid)."""
    if len(lines) < 2:
        return None
    if not all("|" in ln for ln in lines):
        return None
    col_counts = [len(ln.split("|")) for ln in lines]
    if len(set(col_counts)) != 1 or col_counts[0] < 2:
        return None
    return lines


def _find_pipe_table_blocks(text: str) -> list[tuple[int, int]]:
    """Scan `text` line-by-line and return [(start, end_exclusive), ...] index
    ranges of every contiguous pipe-table run, where a run is the maximal
    sequence of non-blank '|'-containing lines that share the same column
    count. Runs shorter than 2 lines, or with fewer than 2 columns, are
    skipped — matching the `_pipe_table_lines` predicate."""
    raw_lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(raw_lines):
        if "|" not in raw_lines[i] or not raw_lines[i].strip():
            i += 1
            continue
        start = i
        first_cols = len(raw_lines[i].split("|"))
        j = i + 1
        while (
            j < len(raw_lines)
            and raw_lines[j].strip()
            and "|" in raw_lines[j]
            and len(raw_lines[j].split("|")) == first_cols
        ):
            j += 1
        if j - start >= 2 and first_cols >= 2:
            blocks.append((start, j))
        i = max(j, i + 1)
    return blocks


def _strip_pipe_tables(text: str) -> str:
    """Drop every detected pipe-table run from `text`. Used by layouts that
    own a structured table renderer so the model's pipe-mirror in the text
    field doesn't render as a duplicate `ref-table` above the real one."""
    if not text or "|" not in text:
        return text
    blocks = _find_pipe_table_blocks(text)
    if not blocks:
        return text
    raw_lines = text.splitlines()
    drop = [False] * len(raw_lines)
    for start, end in blocks:
        for k in range(start, end):
            drop[k] = True
    return "\n".join(ln for ln, d in zip(raw_lines, drop) if not d).strip()


def _strip_trailing_partial_mockup(text: str, partial_elements: list) -> str:
    """Drop trailing non-blank lines whose whitespace-tokens are all members of
    `partial_elements`. Used by circuit AnnotatedDiagrams where the JSON text
    ends with a textual mockup of the partial diagram (e.g. `A` / `B   Z` / `C`)
    that's now redundant because the JointJS canvas renders the labels as pads."""
    if not text or not partial_elements:
        return text
    tokens = {str(p).strip() for p in partial_elements if str(p).strip()}
    if not tokens:
        return text
    lines = text.splitlines()
    i = len(lines)
    while i > 0:
        line = lines[i - 1]
        stripped = line.strip()
        if not stripped:
            i -= 1
            continue
        parts = stripped.split()
        if not parts or not all(p in tokens for p in parts):
            break
        i -= 1
    return "\n".join(lines[:i]).rstrip()


def _maybe_pipe_table(paragraph: str) -> str | None:
    """If `paragraph` is a pipe-separated reference table, return rendered
    <table class="ref-table"> HTML. Otherwise return None.

    First line is treated as the header row. This handles reference tables
    embedded in question stems (e.g. Q2a's "Letter | Statement" lookup
    table) that aren't part of the answer structure."""
    lines = [ln.strip() for ln in paragraph.splitlines() if ln.strip()]
    if _pipe_table_lines(lines) is None:
        return None

    def _cells(ln: str) -> list[str]:
        parts = [c.strip() for c in ln.split("|")]
        # Strip empty boundary cells produced by leading/trailing pipes (| a | b | → ['','a','b',''])
        while parts and not parts[0]:
            parts.pop(0)
        while parts and not parts[-1]:
            parts.pop()
        return parts

    th_html = "".join(f"<th>{escape(c)}</th>" for c in _cells(lines[0]))
    body_html = "".join(
        "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in _cells(ln)) + "</tr>"
        for ln in lines[1:]
    )
    return (
        f'<table class="ref-table"><thead><tr>{th_html}</tr></thead>'
        f'<tbody>{body_html}</tbody></table>'
    )


def _maybe_code_block(paragraph: str) -> str | None:
    """Render `paragraph` as <pre class="code-stem"> when it looks like code.

    Detects two patterns:
    - SQL: every line starts with a SQL keyword (SELECT, FROM, WHERE, …)
    - Cambridge pseudocode: every line starts with a 2-digit line number ("01 DECLARE …")
    Returns None when neither pattern matches."""
    lines = [ln for ln in paragraph.splitlines() if ln.strip()]
    if not lines:
        return None
    if all(_SQL_KEYWORD_RE.match(ln) for ln in lines):
        return f'<pre class="code-stem">{escape(paragraph)}</pre>'
    if len(lines) >= 2 and all(_PSEUDOCODE_LINE_RE.match(ln) for ln in lines):
        return f'<pre class="code-stem">{escape(paragraph)}</pre>'
    return None


def _render_prose_paragraphs(text: str, css_class: str = "q-text") -> str:
    """Split prose on blank lines and emit one <p class="..."> per paragraph.

    Paragraphs that look like a pipe-separated reference table are rendered as
    <table>; SQL or Cambridge pseudocode blocks are rendered as <pre class="code-stem">."""
    if not text or not text.strip():
        return ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    parts = []
    for p in paragraphs:
        table_html = _maybe_pipe_table(p)
        if table_html:
            parts.append(table_html)
            continue
        code_html = _maybe_code_block(p)
        if code_html:
            parts.append(code_html)
            continue
        parts.append(f'<p class="{css_class}">{escape(p)}</p>')
    return "".join(parts)
