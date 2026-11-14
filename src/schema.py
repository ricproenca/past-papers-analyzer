import re
from collections import Counter

from .enricher import COMMAND_TIER, canonical_command
from .syllabus import TOPIC_NAMES, topic_in_paper

_QUESTION_KEYS_P1 = {"id", "text", "command", "objective", "marks", "visuals", "page", "layout_type", "structure_data"}
_QUESTION_KEYS_P2 = _QUESTION_KEYS_P1 | {"topic", "topic_name"}
_QUESTION_KEYS_P3 = _QUESTION_KEYS_P2 | {"answers"}
_ANSWER_KEYS = {"type", "visuals", "scoring_rule", "marking_points"}
_TOP_LEVEL_KEYS = {"board", "level", "subject_code", "subject_name", "variant", "questions", "qp", "ms"}
_VALID_OBJECTIVES = {"AO1", "AO2", "AO3"}
_ANSWER_TYPES = {"text", "diagram", "pseudocode", "MCQ"}
_VALID_LAYOUT_TYPES = {
    "SimpleSingleBlock", "MultiPartLabeledBlock", "NumberedMultiList",
    "InlineCloze", "MatrixGrid", "ValueTraceMatrix", "FixedRegisterArray",
    "TermDefinitionGrid", "LabelledPartResponse", "AnnotatedDiagram",
    "CodeBlockResponse", "LineMatching", "WorkingAnswer",
}
# "1(a)(i)" on the paper is "Q1a_i"; "10" is "Q10".
_ID_RE = re.compile(r"^Q\d{1,2}[a-z]?(_[ivx]+)?$")


def validate_phase_output(data: dict, phase: int) -> None:
    missing_top = _TOP_LEVEL_KEYS - data.keys()
    if missing_top:
        raise ValueError(f"Phase {phase} output missing top-level keys: {sorted(missing_top)}")

    questions = data.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError(f"Phase {phase} output 'questions' must be a list")

    required_q = {1: _QUESTION_KEYS_P1, 2: _QUESTION_KEYS_P2, 3: _QUESTION_KEYS_P3}[phase]
    duplicates = sorted(i for i, n in Counter(q.get("id") for q in questions if isinstance(q, dict)).items() if n > 1)
    if duplicates:
        raise ValueError(f"Phase {phase} output has duplicate question ids: {duplicates}")
    for i, q in enumerate(questions):
        qid = q.get("id", f"index {i}")

        missing_q = required_q - q.keys()
        if missing_q:
            raise ValueError(f"Phase {phase} question {qid!r} missing keys: {sorted(missing_q)}")

        if not isinstance(q.get("id"), str) or not _ID_RE.match(q["id"]):
            raise ValueError(f"Phase {phase} question {qid!r}: id must look like Q1, Q1a or Q1a_i")

        marks = q.get("marks")
        if not isinstance(marks, int) or isinstance(marks, bool):
            raise ValueError(f"Phase {phase} question {qid!r} 'marks' must be an integer, got {marks!r}")

        if q.get("objective") not in _VALID_OBJECTIVES:
            raise ValueError(
                f"Phase {phase} question {qid!r} has invalid objective: {q.get('objective')!r} "
                f"(must be one of {sorted(_VALID_OBJECTIVES)})"
            )

        if phase >= 1 and q.get("layout_type") not in _VALID_LAYOUT_TYPES:
            print(
                f"[!] New question type detected: {q.get('layout_type')!r} "
                f"(phase {phase}, question {qid!r}). Known types: {sorted(_VALID_LAYOUT_TYPES)}"
            )

        if phase >= 2 and q.get("topic") not in TOPIC_NAMES:
            raise ValueError(
                f"Phase {phase} question {qid!r} has unknown topic: {q.get('topic')!r} "
                f"(must be one of {sorted(TOPIC_NAMES)})"
            )

        if phase >= 2 and topic_in_paper(q.get("topic"), data.get("variant")) is False:
            print(f"[!] Question {qid!r}: topic {q.get('topic')} is outside Paper {str(data.get('variant'))[:1]}'s chapters")

        if canonical_command(q.get("command")) not in COMMAND_TIER:
            print(f"[!] Unmapped command word {q.get('command')!r} (question {qid!r}); "
                  f"add it to src/enricher.py and the prompt's command list")
        elif q.get("command") != canonical_command(q.get("command")):
            print(f"[!] Command {q.get('command')!r} (question {qid!r}) is not canonical; "
                  f"expected {canonical_command(q.get('command'))!r} (run postprocess.canonicalise_commands)")

        if phase >= 1 and not isinstance(q.get("structure_data"), dict):
            raise ValueError(
                f"Phase {phase} question {qid!r} 'structure_data' must be a dict"
            )

        for warning in _consistency_warnings(q):
            print(f"[!] Question {qid!r}: {warning}")

        if phase == 3 and isinstance(q.get("answers"), dict):
            answers = q["answers"]
            missing_a = _ANSWER_KEYS - answers.keys()
            if missing_a:
                raise ValueError(f"Phase 3 question {qid!r} answers missing keys: {sorted(missing_a)}")
            mps = answers.get("marking_points")
            if not isinstance(mps, list):
                raise ValueError(f"Phase 3 question {qid!r} 'marking_points' must be a list")
            for j, mp in enumerate(mps):
                if "text" not in mp or "marks" not in mp:
                    raise ValueError(
                        f"Phase 3 question {qid!r} marking_point[{j}] missing 'text' or 'marks'"
                    )

    total_marks = data.get("total_marks")
    if total_marks is not None:
        actual = sum(q.get("marks", 0) for q in questions)
        if actual != total_marks:
            print(
                f"Warning: Phase {phase}: sum of question marks ({actual}) "
                f"does not match total_marks ({total_marks})"
            )


def _consistency_warnings(q: dict) -> list[str]:
    """Cheap cross-field checks that catch likely extraction slips without failing the run."""
    out = []
    sd = q.get("structure_data") if isinstance(q.get("structure_data"), dict) else {}
    layout, marks = q.get("layout_type"), q.get("marks")
    if layout == "InlineCloze" and sd.get("inline_gap_count") != (q.get("text") or "").count("[blank]"):
        out.append(f"inline_gap_count={sd.get('inline_gap_count')} but text has "
                   f"{(q.get('text') or '').count('[blank]')} [blank] marker(s)")
    if layout == "SimpleSingleBlock" and isinstance(marks, int) and marks >= 3 and sd.get("line_count", 1) <= 1:
        out.append(f"a {marks}-mark question has a one-line answer space")
    answers = q.get("answers") if isinstance(q.get("answers"), dict) else None
    if answers:
        mps = answers.get("marking_points") or []
        if answers.get("type") not in _ANSWER_TYPES:
            out.append(f"answer type {answers.get('type')!r} is not one of {sorted(_ANSWER_TYPES)}")
        if any(not isinstance(m.get("marks"), int) or isinstance(m.get("marks"), bool) for m in mps if isinstance(m, dict)):
            out.append("a marking point has non-integer marks")
        if isinstance(marks, int) and marks > 0 and not mps:
            out.append(f"{marks}-mark question has no marking points")
        else:
            available = sum(m["marks"] for m in mps if isinstance(m, dict) and isinstance(m.get("marks"), int))
            if isinstance(marks, int) and mps and available < marks:
                out.append(f"marking points offer {available} mark(s) for a {marks}-mark question")
        if answers.get("type") == "MCQ" and len(mps) != 1:
            out.append(f"MCQ answer has {len(mps)} marking points (expected 1)")
    split = q.get("objective_marks")
    if split is not None and (not isinstance(split, dict) or set(split) - {"AO1", "AO2", "AO3"}
                              or sum(split.values()) != marks):
        out.append(f"objective_marks {split!r} does not split the question's {marks} mark(s) across AO1-AO3")
    if layout == "TermDefinitionGrid" and isinstance(marks, int) and sd.get("rows"):
        blanks = sum(1 for r in sd["rows"] for k in ("term", "definition") if isinstance(r, dict) and r.get(k) is None)
        if blanks != marks:
            out.append(f"{blanks} blank cell(s) but {marks} mark(s)")
    return out
