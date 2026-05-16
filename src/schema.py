_QUESTION_KEYS_P1 = {"id", "text", "command", "objective", "marks", "visuals", "page", "layout_type", "structure_data"}
_QUESTION_KEYS_P2 = _QUESTION_KEYS_P1 | {"topic", "topic_name"}
_QUESTION_KEYS_P3 = _QUESTION_KEYS_P2 | {"answers"}
_ANSWER_KEYS = {"type", "visuals", "scoring_rule", "marking_points"}
_TOP_LEVEL_KEYS = {"board", "level", "subject_code", "subject_name", "variant", "questions", "qp", "ms"}
_VALID_OBJECTIVES = {"AO1", "AO2", "AO3"}
_VALID_LAYOUT_TYPES = {
    "SimpleSingleBlock", "MultiPartLabeledBlock", "NumberedMultiList",
    "InlineCloze", "MatrixGrid", "ValueTraceMatrix", "FixedRegisterArray",
    "TermDefinitionGrid", "LabelledPartResponse", "AnnotatedDiagram",
}


def validate_phase_output(data: dict, phase: int) -> None:
    missing_top = _TOP_LEVEL_KEYS - data.keys()
    if missing_top:
        raise ValueError(f"Phase {phase} output missing top-level keys: {sorted(missing_top)}")

    questions = data.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError(f"Phase {phase} output 'questions' must be a list")

    required_q = {1: _QUESTION_KEYS_P1, 2: _QUESTION_KEYS_P2, 3: _QUESTION_KEYS_P3}[phase]
    for i, q in enumerate(questions):
        qid = q.get("id", f"index {i}")

        missing_q = required_q - q.keys()
        if missing_q:
            raise ValueError(f"Phase {phase} question {qid!r} missing keys: {sorted(missing_q)}")

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

        if phase >= 1 and not isinstance(q.get("structure_data"), dict):
            raise ValueError(
                f"Phase {phase} question {qid!r} 'structure_data' must be a dict"
            )

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
