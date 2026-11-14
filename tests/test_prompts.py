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
    text = prompts.build_pdf_text([{"page": 3, "text": "t", "has_table": True, "has_image": True}])
    assert text.startswith("[Page 3] [Contains table(s)] [Contains image(s)/diagram(s)]\nt")
