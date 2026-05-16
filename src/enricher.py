COMMAND_TIER = {
    "State": 1, "Identify": 1, "Define": 1, "Name": 1, "List": 1,
    "Describe": 2, "Outline": 2, "Sketch": 2,
    "Explain": 3, "Suggest": 3, "Compare": 3, "Calculate": 3,
    "Trace": 3, "Write": 3, "Complete": 3,
    "Analyse": 4, "Evaluate": 4, "Justify": 4, "Discuss": 4,
}

BLOOM_MAP = {
    "State": "Remember", "Identify": "Remember", "Define": "Remember",
    "Name": "Remember", "List": "Remember",
    "Describe": "Understand", "Outline": "Understand", "Explain": "Understand",
    "Suggest": "Apply", "Calculate": "Apply", "Trace": "Apply", "Complete": "Apply",
    "Compare": "Analyse", "Analyse": "Analyse",
    "Evaluate": "Evaluate", "Justify": "Evaluate", "Discuss": "Evaluate",
    "Write": "Create", "Sketch": "Create", "Design": "Create",
}

LOAD_MAP = {
    "SimpleSingleBlock":     "Low",
    "MatrixGrid":            "Low",
    "TermDefinitionGrid":    "Medium",
    "MultiPartLabeledBlock": "Medium",
    "NumberedMultiList":     "Medium",
    "InlineCloze":           "Medium",
    "LabelledPartResponse":  "Medium",
    "FixedRegisterArray":    "Medium",
    "ValueTraceMatrix":      "High",
    "AnnotatedDiagram":      "High",
}


def _difficulty(command: str, marks: int) -> str:
    tier = COMMAND_TIER.get(command, 2)
    marks_score = 1 if marks <= 1 else (2 if marks <= 3 else 3)
    total = tier + marks_score
    if total <= 3:
        return "Low"
    if total <= 5:
        return "Medium"
    return "High"


def _bloom(command: str) -> str:
    return BLOOM_MAP.get(command, "Understand")


def _cognitive_load(layout_type: str) -> str:
    return LOAD_MAP.get(layout_type, "Medium")


def enrich_question(q: dict) -> dict:
    q["difficulty"] = _difficulty(q.get("command", ""), q.get("marks", 0))
    q["bloom_level"] = _bloom(q.get("command", ""))
    q["cognitive_load"] = _cognitive_load(q.get("layout_type", ""))
    return q


def enrich_paper(data: dict) -> dict:
    for q in data.get("questions", []):
        enrich_question(q)
    return data
