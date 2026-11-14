import pytest

from src import enricher as e
from src.schema import _VALID_LAYOUT_TYPES
from conftest import make_question, PAPER_PATHS


def test_command_maps_cover_the_same_commands():
    assert set(e.COMMAND_TIER) == set(e.BLOOM_MAP)


def test_every_layout_type_has_a_cognitive_load():
    assert _VALID_LAYOUT_TYPES <= set(e.LOAD_MAP)


@pytest.mark.parametrize("command,marks,expected", [
    ("State", 1, "Low"), ("State", 4, "Medium"), ("Describe", 2, "Medium"),
    ("Explain", 4, "High"), ("Evaluate", 1, "Medium"), ("Evaluate", 6, "High"),
    ("Nonsense", 1, "Low"), ("Nonsense", 4, "Medium"),   # unknown command defaults to tier 2
])
def test_difficulty(command, marks, expected):
    assert e._difficulty(command, marks) == expected


@pytest.mark.parametrize("raw,expected", [
    ("State", "State"), ("give", "Give"), ("  Draw ", "Draw"),
    ("Complete and annotate the diagram", "Complete"), ("Zzz qqq", "Zzz qqq"), ("", ""), (None, ""),
])
def test_normalise_command(raw, expected):
    assert e._normalise_command(raw) == expected


def test_former_gaps_are_mapped():
    # Regression: these commands used to fall through to the defaults.
    for cmd in ("Give", "Tick", "Circle", "Show", "Convert", "Add", "Draw", "Design"):
        assert cmd in e.COMMAND_TIER and cmd in e.BLOOM_MAP


def test_enrich_question_sets_all_three_fields():
    q = e.enrich_question(make_question(command="Give", marks=1, layout_type="CodeBlockResponse"))
    assert (q["difficulty"], q["bloom_level"], q["cognitive_load"]) == ("Low", "Remember", "High")


def test_every_extracted_command_is_known():
    """Fails when a new paper introduces a command word the enricher doesn't map."""
    import json
    unknown = {}
    for path in PAPER_PATHS:
        for q in json.loads(path.read_text(encoding="utf-8"))["questions"]:
            cmd = e._normalise_command(q.get("command"))
            if cmd not in e.COMMAND_TIER:
                unknown.setdefault(q.get("command"), path.name)
    assert not unknown, f"add these command words to src/enricher.py: {unknown}"
