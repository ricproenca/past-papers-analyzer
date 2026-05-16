import json
from pathlib import Path

from . import pdf_reader, prompts, claude_client, renderer
from .schema import validate_phase_output

_KEY_ORDER = ["board", "level", "subject_code", "subject_name", "variant", "qp", "ms", "total_marks", "questions"]


def _reorder(data: dict) -> dict:
    return {k: data[k] for k in _KEY_ORDER if k in data}


def _write_json(path: str | Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


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
    validate_phase_output(phase12_data, phase=2)
    phase12_json_enriched = json.dumps(phase12_data, ensure_ascii=False)

    final_data = phase12_data
    if ms_path:
        print("Phase 1+2 complete. Running Phase 3 (answer extraction)...")
        ms_pages = pdf_reader.extract_pages(ms_path)
        print(f"Marking scheme: {len(ms_pages)} pages read.")
        system3, messages3 = prompts.build_phase3_messages(phase12_json_enriched, ms_pages)
        phase3_json = claude_client.call(system3, messages3, label="Phase 3")
        phase3_data = json.loads(phase3_json)
        phase3_data["qp"] = Path(pdf_path).name
        phase3_data["ms"] = Path(ms_path).name
        phase3_data = _reorder(phase3_data)
        validate_phase_output(phase3_data, phase=3)
        final_data = phase3_data
        print("Phase 3 complete.")
    else:
        print("Phase 1+2 complete.")

    _write_json(output_path, final_data)
    claude_client.print_totals()
    print(f"Output written to: {output_path}")

    print("Running Phase 4 (HTML rendering)...")
    json_path = Path(output_path)
    if json_path.parent.name == "json":
        html_path = json_path.parent.parent / "html" / json_path.with_suffix(".html").name
    else:
        html_path = json_path.with_suffix(".html")
    renderer.render(final_data, html_path)
    print(f"HTML written to: {html_path}")
