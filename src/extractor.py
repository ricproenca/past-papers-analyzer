import json
from pathlib import Path

from . import pdf_reader, prompts, claude_client, renderer, enricher, statistics, visuals
from .schema import validate_phase_output

_KEY_ORDER = ["board", "level", "subject_code", "subject_name", "variant", "qp", "ms", "total_marks", "summary", "statistics", "questions"]


def _reorder(data: dict) -> dict:
    return {k: data[k] for k in _KEY_ORDER if k in data}


def _write_json(path: str | Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


_EMPTY_ANSWER = {"type": "text", "visuals": [], "scoring_rule": None, "marking_points": []}


def _validated(data: dict, phase: int, raw: str, label: str) -> None:
    """Validate, saving the raw model response first if it is rejected."""
    try:
        validate_phase_output(data, phase=phase)
    except ValueError:
        print(f"Validation failed; raw response saved to {claude_client.save_debug(label, raw)}")
        raise


def _merge_answers(data: dict, answers_by_id: dict) -> None:
    """Attach each answer to its question in place. Extraction fields are never
    touched, so the answers call cannot alter them."""
    if not isinstance(answers_by_id, dict):
        raise ValueError("Phase 3 output must be a JSON object mapping question id -> answer")
    ids = [q.get("id") for q in data["questions"]]
    missing = [i for i in ids if i not in answers_by_id]
    extra = sorted(set(answers_by_id) - set(ids))
    if missing:
        print(f"Warning: Phase 3 returned no answer for {len(missing)} question(s): {missing}")
    if extra:
        print(f"Warning: Phase 3 returned answers for unknown ids (ignored): {extra}")
    for q in data["questions"]:
        q["answers"] = answers_by_id.get(q.get("id")) or dict(_EMPTY_ANSWER)


def extract(pdf_path: str, output_path: str, ms_path: str = None) -> None:
    print(f"Reading PDF: {pdf_path}")
    pages = pdf_reader.extract_pages(pdf_path)
    print(f"Extracted {len(pages)} pages. Running Phase 1+2 (extraction + topic mapping)...")

    system12, messages12 = prompts.build_phase12_messages(pages)
    phase12_json = claude_client.call(system12, messages12, label="Phase 1+2")
    phase12_data = json.loads(phase12_json)
    phase12_data["qp"] = Path(pdf_path).name
    phase12_data["ms"] = Path(ms_path).name if ms_path else None
    phase12_data = _reorder(phase12_data)
    _validated(phase12_data, 2, phase12_json, "Phase 1+2")
    phase12_json_enriched = json.dumps(phase12_data, ensure_ascii=False)

    final_data = phase12_data
    if ms_path:
        print("Phase 1+2 complete. Running Phase 3 (answer extraction)...")
        ms_pages = pdf_reader.extract_pages(ms_path)
        print(f"Marking scheme: {len(ms_pages)} pages read.")
        system3, messages3 = prompts.build_phase3_messages(phase12_json_enriched, ms_pages)
        phase3_json = claude_client.call(system3, messages3, label="Phase 3")
        _merge_answers(phase12_data, json.loads(phase3_json))
        _validated(phase12_data, 3, phase3_json, "Phase 3")
        final_data = phase12_data
        print("Phase 3 complete.")
    else:
        print("Phase 1+2 complete.")

    enricher.enrich_paper(final_data)
    statistics.attach_statistics(final_data)

    json_path = Path(output_path)
    if json_path.parent.name == "json":
        html_path = json_path.parent.parent / "html" / json_path.with_suffix(".html").name
    else:
        html_path = json_path.with_suffix(".html")

    n_visuals = visuals.attach_visual_images(final_data, pdf_path, html_path.parent)
    if n_visuals:
        print(f"Rendered visuals for {n_visuals} question(s).")

    final_data = _reorder(final_data)
    _write_json(output_path, final_data)
    claude_client.print_totals()
    print(f"Output written to: {output_path}")

    print("Running Phase 4 (HTML rendering)...")
    renderer.render(final_data, html_path)
    print(f"HTML written to: {html_path}")
