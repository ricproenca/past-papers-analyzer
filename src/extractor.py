import copy
import json
import re
from pathlib import Path

from . import pdf_reader, postprocess, prompts, claude_client, renderer, enricher, statistics, visuals
from .schema import validate_phase_output

_KEY_ORDER = ["board", "level", "subject_code", "subject_name", "variant", "qp", "ms", "total_marks", "summary", "statistics", "questions"]
_EMPTY_ANSWER = {"type": "text", "visuals": [], "scoring_rule": None, "marking_points": []}


def _reorder(data: dict) -> dict:
    return {k: data[k] for k in _KEY_ORDER if k in data}


def _write_json(path: str | Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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
        q["answers"] = answers_by_id.get(q.get("id")) or copy.deepcopy(_EMPTY_ANSWER)


# --- Phase 1+2: extraction + topic mapping -----------------------------------------

def prepare_phase12(pdf_path: str, vision: bool = False) -> dict:
    """Read the PDF and build the request. Returns a job dict used by finish_phase12."""
    print(f"Reading PDF: {pdf_path}")
    pages = pdf_reader.extract_pages(pdf_path)
    images = None
    if vision:
        diagram_pages = [p["page"] for p in pages if p.get("has_diagram")]
        images = pdf_reader.render_pages_to_png_bytes(pdf_path, diagram_pages)
        print(f"Attaching {len(images)} diagram page image(s): {sorted(images)}")
    system, messages = prompts.build_phase12_messages(pages, images)
    return {"pdf_path": pdf_path, "pages": pages, "system": system, "messages": messages}


def finish_phase12(job: dict, raw_json: str, ms_path: str | None) -> dict:
    """Parse the model's response, fill in everything deterministic, validate."""
    data = json.loads(raw_json)
    data["qp"] = Path(job["pdf_path"]).name
    data["ms"] = Path(ms_path).name if ms_path else None
    unmatched = postprocess.postprocess_phase12(data, job["pages"])
    if unmatched:
        print(f"Warning: could not pair TermDefinitionGrid question(s) {unmatched} with a PDF table; "
              f"their rows were left as the model wrote them")
    data = _reorder(data)
    _validated(data, 2, raw_json, "Phase 1+2")
    return data


# --- Phase 3: marking-scheme answers -------------------------------------------------

def prepare_phase3(data: dict, ms_path: str):
    ms_pages = pdf_reader.drop_ms_preamble(pdf_reader.extract_pages(ms_path))
    print(f"Marking scheme: {len(ms_pages)} answer page(s) read.")
    return prompts.build_phase3_messages(json.dumps(data, ensure_ascii=False), ms_pages)


def finish_phase3(data: dict, raw_json: str) -> dict:
    _merge_answers(data, json.loads(raw_json))
    _validated(data, 3, raw_json, "Phase 3")
    return data


# --- enrichment, visuals, output -----------------------------------------------------

def finalize(data: dict, pdf_path: str, output_path: str, show_totals: bool = True) -> None:
    enricher.enrich_paper(data)
    statistics.attach_statistics(data)

    json_path = Path(output_path)
    if json_path.parent.name == "json":
        html_path = json_path.parent.parent / "html" / json_path.with_suffix(".html").name
    else:
        html_path = json_path.with_suffix(".html")

    n_visuals = visuals.attach_visual_images(data, pdf_path, html_path.parent)
    if n_visuals:
        print(f"Rendered visuals for {n_visuals} question(s).")

    data = _reorder(data)
    _write_json(output_path, data)
    if show_totals:
        claude_client.print_totals()
    print(f"Output written to: {output_path}")

    print("Running Phase 4 (HTML rendering)...")
    renderer.render(data, html_path)
    print(f"HTML written to: {html_path}")


# --- drivers -----------------------------------------------------------------------

def extract(pdf_path: str, output_path: str, ms_path: str = None, vision: bool = False) -> None:
    """Extract one paper, one request at a time."""
    claude_client.reset_totals()  # so the [total] line is per paper, not per batch
    job = prepare_phase12(pdf_path, vision)
    print(f"Running Phase 1+2 (extraction + topic mapping) for {Path(pdf_path).name}...")
    raw = claude_client.call(job["system"], job["messages"], label="Phase 1+2")
    data = finish_phase12(job, raw, ms_path)

    if ms_path:
        print("Phase 1+2 complete. Running Phase 3 (answer extraction)...")
        system3, messages3 = prepare_phase3(data, ms_path)
        data = finish_phase3(data, claude_client.call(system3, messages3, label="Phase 3"))
        print("Phase 3 complete.")
    else:
        print("Phase 1+2 complete.")
    finalize(data, pdf_path, output_path)


def _batch_id(pdf_path: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", Path(pdf_path).stem)[:64]


def extract_batch(papers: list[tuple[str, str, str | None]], vision: bool = False, poll_seconds: float = 30.0) -> list[tuple[str, Exception]]:
    """Extract many papers through the Batch API: all Phase 1+2 requests in one
    batch, then all Phase 3 requests in a second. Half price, but results arrive
    asynchronously (minutes to hours). `papers` is [(pdf_path, output_path, ms_path)].
    Returns [(pdf name, error)] for the papers that failed."""
    failures: dict[str, Exception] = {}
    jobs, ms_of, out_of = {}, {}, {}

    for pdf, out, ms in papers:
        cid = _batch_id(pdf)
        try:
            jobs[cid] = prepare_phase12(pdf, vision)
            ms_of[cid], out_of[cid] = ms, out
        except Exception as e:
            failures[Path(pdf).name] = e

    data = {}
    if jobs:
        raw = claude_client.call_batch({c: (j["system"], j["messages"]) for c, j in jobs.items()},
                                       label="Phase 1+2 batch", poll_seconds=poll_seconds)
        for cid, result in raw.items():
            name = Path(jobs[cid]["pdf_path"]).name
            if isinstance(result, Exception):
                failures[name] = result
                continue
            try:
                data[cid] = finish_phase12(jobs[cid], result, ms_of[cid])
            except Exception as e:
                failures[name] = e

    stage3 = {}
    for cid, d in data.items():
        if ms_of[cid]:
            try:
                stage3[cid] = prepare_phase3(d, ms_of[cid])
            except Exception as e:
                failures[Path(jobs[cid]["pdf_path"]).name] = e
    if stage3:
        raw = claude_client.call_batch(stage3, label="Phase 3 batch", poll_seconds=poll_seconds)
        for cid, result in raw.items():
            name = Path(jobs[cid]["pdf_path"]).name
            if isinstance(result, Exception):
                failures[name] = result
                data.pop(cid, None)
                continue
            try:
                data[cid] = finish_phase3(data[cid], result)
            except Exception as e:
                failures[name] = e
                data.pop(cid, None)

    for cid, d in data.items():
        if Path(jobs[cid]["pdf_path"]).name in failures:
            continue
        try:
            Path(out_of[cid]).parent.mkdir(parents=True, exist_ok=True)
            finalize(d, jobs[cid]["pdf_path"], out_of[cid], show_totals=False)   # call_batch already printed the totals
        except Exception as e:
            failures[Path(jobs[cid]["pdf_path"]).name] = e
    return list(failures.items())
