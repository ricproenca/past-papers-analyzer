_QUESTION_KEYS_P1 = {"id", "text", "command", "objective", "marks", "visuals", "page"}
_QUESTION_KEYS_P2 = _QUESTION_KEYS_P1 | {"topic", "topic_name"}
_QUESTION_KEYS_P3 = _QUESTION_KEYS_P2 | {"answers"}
_ANSWER_KEYS = {"type", "visuals", "scoring_rule", "marking_points"}
_TOP_LEVEL_KEYS = {"board", "level", "subject_code", "subject_name", "variant", "questions", "qp", "ms"}
_VALID_OBJECTIVES = {"AO1", "AO2", "AO3"}


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
