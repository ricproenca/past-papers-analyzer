AXES = [
    ("topic",          lambda q: q.get("topic")),
    ("difficulty",     lambda q: q.get("difficulty")),
    ("bloom_level",    lambda q: q.get("bloom_level")),
    ("cognitive_load", lambda q: q.get("cognitive_load")),
    ("objective",      lambda q: q.get("objective")),
    ("layout_type",    lambda q: q.get("layout_type")),
    ("command",        lambda q: q.get("command")),
    ("answer_type",    lambda q: (q.get("answers") or {}).get("type")),
]


def _group(questions, key_fn, value_fn):
    out = {}
    for q in questions:
        k = key_fn(q)
        if k is None or k == "":
            continue
        out[k] = out.get(k, 0) + value_fn(q)
    return out


def _median(values):
    n = len(values)
    if n == 0:
        return 0
    s = sorted(values)
    mid = n // 2
    if n % 2:
        return s[mid]
    avg = (s[mid - 1] + s[mid]) / 2
    return int(avg) if avg.is_integer() else avg


def compute_statistics(data: dict) -> dict:
    qs = data.get("questions", [])
    marks = lambda q: int(q.get("marks", 0) or 0)
    one = lambda q: 1

    stats = {}
    for name, getter in AXES:
        stats[f"marks_by_{name}"] = _group(qs, getter, marks)
        stats[f"count_by_{name}"] = _group(qs, getter, one)
    stats["marks_by_objective"] = _marks_by_objective(qs)
    return stats


def _marks_by_objective(qs) -> dict:
    """Marks per AO; a question with an objective_marks split (from the marking
    scheme) contributes to each objective it is marked against."""
    out = {}
    for q in qs:
        split = q.get("objective_marks")
        if isinstance(split, dict) and split:
            for ao, m in split.items():
                out[ao] = out.get(ao, 0) + int(m)
        elif q.get("objective"):
            out[q["objective"]] = out.get(q["objective"], 0) + int(q.get("marks", 0) or 0)
    return out


def compute_summary(data: dict) -> dict:
    qs = data.get("questions", [])
    marks = [int(q.get("marks", 0) or 0) for q in qs]
    topics = {q.get("topic") for q in qs if q.get("topic")}
    mcq_count = sum(
        1 for q in qs if (q.get("answers") or {}).get("type") == "MCQ"
    )
    return {
        "question_count": len(qs),
        "mcq_count": mcq_count,
        "mean_marks_per_question": round(sum(marks) / len(marks), 2) if marks else 0,
        "median_marks_per_question": _median(marks),
        "max_marks_per_question": max(marks) if marks else 0,
        "unique_topics_count": len(topics),
    }


def attach_statistics(data: dict) -> dict:
    data["summary"] = compute_summary(data)
    data["statistics"] = compute_statistics(data)
    return data
