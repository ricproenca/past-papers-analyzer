"""Bring committed JSONs up to date with the deterministic pipeline steps, without API calls:
canonical command words, LineMatching layouts, TermDefinitionGrid contents copied from the
PDF (when the source PDF is under input/), objective_marks, enrichment and statistics.
Idempotent: re-running it leaves the files unchanged."""

import glob
import json
from pathlib import Path

from src import enricher, pdf_reader, postprocess, statistics, visuals
from src.extractor import _reorder


def backfill(data: dict) -> list[str]:
    """Apply every deterministic step to one paper in place; returns notes to print."""
    notes = []
    postprocess.canonicalise_commands(data)
    for qid in postprocess.fix_line_matching_layouts(data):
        notes.append(f"{qid}: relabelled LineMatching")
    if any(q.get("layout_type") == "TermDefinitionGrid" for q in data.get("questions", [])):
        pdf = visuals.find_source_pdf(data.get("qp") or "")
        if pdf is None:
            notes.append(f"TermDefinitionGrid rows not refreshed: {data.get('qp')} not found under input/")
        else:
            unmatched = postprocess.fill_term_def_grids(data, pdf_reader.extract_pages(str(pdf)))
            if unmatched:
                notes.append(f"TermDefinitionGrid {unmatched} could not be paired with a PDF table; left as is")
    postprocess.fill_objective_marks(data)
    enricher.enrich_paper(data)
    statistics.attach_statistics(data)
    return notes


def main() -> None:
    paths = sorted(glob.glob("output/json/*.json"))
    if not paths:
        print("No JSON files found in output/json/")
        return
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        notes = backfill(data)
        Path(path).write_text(json.dumps(_reorder(data), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"enriched: {path}")
        for note in notes:
            print(f"  [!] {note}")


if __name__ == "__main__":
    main()
