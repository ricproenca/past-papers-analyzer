COMMAND_TIER = {
    "State": 1, "Identify": 1, "Define": 1, "Name": 1, "List": 1,
    "Give": 1, "Tick": 1, "Circle": 1,
    "Describe": 2, "Outline": 2, "Sketch": 2, "Show": 2,
    "Explain": 3, "Suggest": 3, "Compare": 3, "Calculate": 3,
    "Trace": 3, "Write": 3, "Complete": 3,
    "Convert": 3, "Add": 3, "Draw": 3, "Design": 3,
    "Analyse": 4, "Evaluate": 4, "Justify": 4, "Discuss": 4,
}

BLOOM_MAP = {
    "State": "Remember", "Identify": "Remember", "Define": "Remember",
    "Name": "Remember", "List": "Remember",
    "Give": "Remember", "Tick": "Remember", "Circle": "Remember",
    "Describe": "Understand", "Outline": "Understand", "Explain": "Understand",
    "Suggest": "Apply", "Calculate": "Apply", "Trace": "Apply", "Complete": "Apply",
    "Convert": "Apply", "Add": "Apply", "Show": "Apply",
    "Compare": "Analyse", "Analyse": "Analyse",
    "Evaluate": "Evaluate", "Justify": "Evaluate", "Discuss": "Evaluate",
    "Write": "Create", "Sketch": "Create", "Design": "Create", "Draw": "Create",
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
    "CodeBlockResponse":     "High",
}


def canonical_command(command: str) -> str:
    """Map a raw command phrase onto a key of the maps above.

    Handles case differences and multi-word phrases such as
    "Complete and annotate the diagram" (-> "Complete"). Unknown commands are
    returned unchanged so the callers' defaults apply."""
    command = (command or "").strip()
    if command in COMMAND_TIER:
        return command
    first = command.split(" ", 1)[0].capitalize()
    return first if first in COMMAND_TIER else command


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
    command = canonical_command(q.get("command", ""))
    q["difficulty"] = _difficulty(command, q.get("marks", 0))
    q["bloom_level"] = _bloom(command)
    q["cognitive_load"] = _cognitive_load(q.get("layout_type", ""))
    return q


def enrich_paper(data: dict) -> dict:
    for q in data.get("questions", []):
        enrich_question(q)
    return data
