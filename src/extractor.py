import json
from pathlib import Path

from . import pdf_reader, prompts, claude_client
from .schema import validate_phase_output


def _write_json(path: str | Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def extract(pdf_path: str, output_path: str, ms_path: str = None) -> None:
    stem = Path(output_path).with_suffix("")
    sidecar1 = Path(f"{stem}_phase1.json")
    sidecar2 = Path(f"{stem}_phase2.json")

    print(f"Reading PDF: {pdf_path}")
    pages = pdf_reader.extract_pages(pdf_path)
    print(f"Extracted {len(pages)} pages. Running Phase 1 (question extraction)...")

    system1, messages1 = prompts.build_phase1_messages(pages)
    phase1_json = claude_client.call(system1, messages1, label="Phase 1")
    phase1_data = json.loads(phase1_json)
    phase1_data["qp"] = Path(pdf_path).name
    phase1_data["ms"] = Path(ms_path).name if ms_path else None
    validate_phase_output(phase1_data, phase=1)
    _write_json(sidecar1, phase1_data)
    phase1_json_enriched = json.dumps(phase1_data, ensure_ascii=False)
    print("Phase 1 complete. Running Phase 2 (topic mapping)...")

    system2, messages2 = prompts.build_phase2_messages(phase1_json_enriched, pages)
    phase2_json = claude_client.call(system2, messages2, label="Phase 2")
    phase2_data = json.loads(phase2_json)
    phase2_data["qp"] = Path(pdf_path).name
    phase2_data["ms"] = Path(ms_path).name if ms_path else None
    validate_phase_output(phase2_data, phase=2)
    _write_json(sidecar2, phase2_data)
    phase2_json_enriched = json.dumps(phase2_data, ensure_ascii=False)

    final_data = phase2_data
    if ms_path:
        print("Phase 2 complete. Running Phase 3 (answer extraction)...")
        ms_pages = pdf_reader.extract_pages(ms_path)
        print(f"Marking scheme: {len(ms_pages)} pages read.")
        system3, messages3 = prompts.build_phase3_messages(phase2_json_enriched, ms_pages)
        phase3_json = claude_client.call(system3, messages3, label="Phase 3")
        phase3_data = json.loads(phase3_json)
        phase3_data["qp"] = Path(pdf_path).name
        phase3_data["ms"] = Path(ms_path).name
        validate_phase_output(phase3_data, phase=3)
        final_data = phase3_data
        print("Phase 3 complete.")
    else:
        print("Phase 2 complete.")

    _write_json(output_path, final_data)
    sidecar1.unlink(missing_ok=True)
    sidecar2.unlink(missing_ok=True)
    claude_client.print_totals()
    print(f"Output written to: {output_path}")
