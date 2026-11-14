"""Extract per-page PNG snapshots of question-paper pages that contain visuals,
and annotate the JSON with a `visual_image` path each question's HTML renderer
can use to embed an <img>.

Conventions:
- One PNG per unique source page, written to `<html_dir>/<pdf_stem>/page-{N}.png`.
- Each question with non-empty `visuals` and a `page` gets `q["visual_image"]`
  set to a path relative to the HTML file (so the browser resolves it directly).
"""

import re
from pathlib import Path
from typing import Optional

from . import pdf_reader


# Detects an explicit cross-reference like "on page 6" or "See page 4" — not any
# "page N" ("a web page 3 times larger" is not a reference).
_PAGE_REF_RE = re.compile(r"\b(?:on|see|from|at|to)\s+page\s+(\d{1,3})\b", re.IGNORECASE)


def _explicit_page_ref(text: str) -> Optional[int]:
    """Return the explicit "page N" reference in `text`, if any."""
    m = _PAGE_REF_RE.search(text or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _visual_key(visuals: list) -> Optional[str]:
    """Normalised join of visual labels — used to group sub-questions that
    share the same diagram (e.g. Q7a/b/c all referencing "flowchart of …")."""
    parts = [str(v).strip().lower() for v in (visuals or []) if str(v).strip()]
    return "|".join(parts) if parts else None


_GROUP_RE = re.compile(r"^Q\d+")


def _group(q: dict) -> str:
    """Top-level question number: "Q7c_ii" -> "Q7"."""
    m = _GROUP_RE.match(str(q.get("id") or ""))
    return m.group(0) if m else str(q.get("id") or "")


def _questions_needing_visuals(data: dict) -> list[tuple[dict, int]]:
    """Pair each question with the page number whose PNG snapshot should be embedded.

    Only fires for an explicit cross-reference ("the algorithm on page 6") — the
    Cambridge pattern for diagrams that cannot be rendered as structured HTML
    (flowcharts, complex schematics). The reference is shared with (a) siblings that
    carry the same visual label and (b) every part of the same numbered question
    (Q7a, Q7b, Q7c_i ...) when any of its parts has a visual: the model's visual
    labels vary between runs, the question number does not.
    Visuals without a page reference (tables, sketches already covered by the layout
    renderers) are skipped, and so is a reference in a question with no visual at all.
    """
    questions = data.get("questions") or []
    shared_refs: dict[str, int] = {}
    group_refs: dict[str, int] = {}
    group_has_visual: set[str] = set()
    for q in questions:
        if q.get("visuals"):
            group_has_visual.add(_group(q))
        ref = _explicit_page_ref(q.get("text") or "")
        if not ref:
            continue
        group_refs.setdefault(_group(q), ref)
        key = _visual_key(q.get("visuals"))
        if key:
            shared_refs.setdefault(key, ref)

    out: list[tuple[dict, int]] = []
    for q in questions:
        own_visual = bool(q.get("visuals"))
        page = None
        if own_visual or _group(q) in group_has_visual:
            page = _explicit_page_ref(q.get("text") or "") or group_refs.get(_group(q))
        if not page and own_visual:
            page = shared_refs.get(_visual_key(q.get("visuals")) or "")
        if page:
            out.append((q, int(page)))
    return out


def attach_visual_images(
    data: dict,
    pdf_path: str | Path,
    html_output_dir: str | Path,
    *,
    dpi: int = 180,
) -> int:
    """Render the unique source pages of every question with `visuals` into
    `<html_output_dir>/<pdf_stem>/page-{N}.png` and stamp each affected question
    with `q["visual_image"] = "<pdf_stem>/page-{N}.png"`.

    Returns the number of questions annotated."""
    pdf_path = Path(pdf_path)
    html_output_dir = Path(html_output_dir)
    stem = pdf_path.stem
    visuals_dir = html_output_dir / stem

    pairs = _questions_needing_visuals(data)

    # Clear stale `visual_image` on questions that no longer qualify under
    # the current scoping rule (keeps re-runs idempotent after a rule change).
    keep_ids = {id(q) for q, _ in pairs}
    for q in data.get("questions") or []:
        if id(q) not in keep_ids and "visual_image" in q:
            del q["visual_image"]

    if not pairs:
        return 0

    page_nums = {page for _, page in pairs}
    rendered = pdf_reader.render_pages_to_pngs(pdf_path, page_nums, visuals_dir, dpi=dpi)

    count = 0
    for q, page in pairs:
        if page in rendered:
            q["visual_image"] = f"{stem}/page-{page}.png"
            count += 1
    return count


def find_source_pdf(qp_name: str, search_root: str | Path = "input") -> Optional[Path]:
    """Look up the source PDF for a JSON's `qp` filename by searching `search_root`
    recursively. Returns the first matching path, or None."""
    root = Path(search_root)
    if not root.exists():
        return None
    for candidate in root.rglob(qp_name):
        if candidate.is_file():
            return candidate
    return None
