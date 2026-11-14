from src import prompts


def _cached(system):
    return [b for b in system if b.get("cache_control")]


def test_phase12_system_prompt_is_cached_and_large_enough():
    system, messages = prompts.build_phase12_messages([{"page": 1, "text": "x", "has_table": False, "has_image": False}])
    assert len(_cached(system)) == 1
    assert len(system[0]["text"]) // 4 > 1024      # rough token estimate: above the minimum cacheable prefix
    assert messages[0]["role"] == "user" and "[Page 1]" in messages[0]["content"]


def test_phase3_system_prompt_is_not_marked_for_caching():
    system, messages = prompts.build_phase3_messages('{"questions": []}', [{"page": 1, "text": "ms", "has_table": False, "has_image": False}])
    assert _cached(system) == []
    assert '{"questions": []}' in messages[0]["content"] and "[Page 1]" in messages[0]["content"]


def test_page_flags_appear_in_the_header():
    text = prompts.build_pdf_text([{"page": 3, "text": "t", "has_table": True, "has_image": True, "has_diagram": True}])
    assert text.startswith("[Page 3] [Contains table(s)] [Contains image(s)] [Likely contains a diagram/drawing]\nt")


def test_blank_pages_are_not_sent():
    pages = [{"page": 1, "text": "cover", "has_table": False, "has_image": False},
             {"page": 2, "text": "  \n", "has_table": False, "has_image": False},
             {"page": 3, "text": "", "has_table": True, "has_image": False}]
    out = prompts.build_pdf_text(pages)
    assert "[Page 1]" in out and "[Page 2]" not in out and "[Page 3]" in out      # a page with a table is kept


def test_command_list_in_prompt_is_the_enrichers():
    from src.enricher import COMMAND_TIER
    assert "<<COMMAND_LIST>>" not in prompts.PHASE12_SYSTEM
    assert ", ".join(COMMAND_TIER) in prompts.PHASE12_SYSTEM


def test_phase12_prompt_contract():
    sp = prompts.PHASE12_SYSTEM
    assert "OBJECTIVES" in sp and "STEMS" not in sp
    assert "always include the parent question's context" in sp
    assert "Do NOT output the topic name" in sp and "TERM_DEF_TABLE_DATA" not in sp
    assert '"topic_name"' not in sp.split("LAYOUT TYPES")[0]       # no longer a requested key


def test_vision_messages_attach_images():
    pages = [{"page": 1, "text": "t", "has_table": False, "has_image": False}]
    _, plain = prompts.build_phase12_messages(pages)
    assert isinstance(plain[0]["content"], str)
    _, withimg = prompts.build_phase12_messages(pages, {5: b"\x89PNGdata", 2: b"\x89PNGmore"})
    blocks = withimg[0]["content"]
    assert blocks[0]["type"] == "text" and [b["type"] for b in blocks[1:]] == ["text", "image", "text", "image"]
    assert "page 2" in blocks[1]["text"] and blocks[2]["source"]["media_type"] == "image/png"


def test_phase3_prompt_states_marking_point_conventions():
    sp = prompts.PHASE3_SYSTEM
    assert '"1(a)(i)"' in sp and "Never merge alternatives" in sp and "TOP of that band" in sp
    assert len(sp) // 4 < 1024          # still below the minimum cacheable prefix, so no cache_control


# --- docs stay in step with the code ------------------------------------------

import re

from src.schema import _VALID_LAYOUT_TYPES
from conftest import ROOT


def test_prompt_describes_every_layout():
    for layout in _VALID_LAYOUT_TYPES:
        assert re.search(rf"^{layout} —", prompts.PHASE12_SYSTEM, re.M), layout
    assert f"exactly one of the {len(_VALID_LAYOUT_TYPES)} types" in prompts.PHASE12_SYSTEM


def test_question_types_doc_lists_exactly_the_valid_layouts():
    doc = (ROOT / "docs" / "questions_types.md").read_text(encoding="utf-8")
    assert set(re.findall(r"^### \d+\. (\w+)", doc, re.M)) == _VALID_LAYOUT_TYPES


def test_extractor_doc_lists_exactly_the_valid_layouts():
    doc = (ROOT / "docs" / "question_extractor.md").read_text(encoding="utf-8")
    section = doc.split("\n## Layouts\n", 1)[1].split("\n## ", 1)[0]
    assert set(re.findall(r"^\| `(\w+)` \|", section, re.M)) == _VALID_LAYOUT_TYPES
