"""Generate a self-contained HTML review page from an extracted JSON file."""

import argparse
import json
from pathlib import Path

from src.renderer import render
from src.visuals import attach_visual_images, find_source_pdf


def _ensure_visual_images(data: dict, html_dir: Path) -> bool:
    """Render PDF page snapshots for any question with `visuals` and return
    True if the JSON was modified. Always re-resolves so a smarter page-ref
    heuristic (or a moved PDF) is picked up on re-runs."""
    questions = data.get("questions") or []
    if not any(q.get("visuals") for q in questions):
        return False
    qp = data.get("qp")
    if not qp:
        print("  (no `qp` field on JSON; skipping visual extraction)")
        return False
    pdf = find_source_pdf(qp)
    if pdf is None:
        print(f"  (source PDF {qp!r} not found under input/; skipping visual extraction)")
        return False
    before = [q.get("visual_image") for q in questions]
    n = attach_visual_images(data, pdf, html_dir)
    after = [q.get("visual_image") for q in questions]
    changed = before != after
    if n:
        print(f"  Rendered visuals for {n} question(s) from {pdf.name}")
    return changed


def render_one(json_path: Path, output: str | None = None) -> Path:
    if output:
        out_path = Path(output)
    else:
        out_path = Path("output/html") / json_path.with_suffix(".html").name
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if _ensure_visual_images(data, out_path.parent):
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    render(data, out_path)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Render extracted JSON as an HTML review page.")
    parser.add_argument("json_path", help="Path to a JSON file or a folder containing JSON files")
    parser.add_argument("-o", "--output", help="Output HTML path (single-file mode only)")
    args = parser.parse_args()

    target = Path(args.json_path)

    if target.is_dir():
        files = sorted(target.glob("*.json"))
        if not files:
            print(f"No JSON files found in {target}")
            return
        failed = []
        for json_path in files:
            try:
                out_path = render_one(json_path)
                print(f"Rendered: {out_path}")
            except Exception as e:   # one bad file must not stop the others
                print(f"[FAILED] {json_path.name}: {type(e).__name__}: {e}")
                failed.append(json_path.name)
        if failed:
            raise SystemExit(f"{len(failed)} file(s) failed to render: {', '.join(failed)}")
    else:
        out_path = render_one(target, args.output)
        print(f"Rendered: {out_path}")


if __name__ == "__main__":
    main()
