from src import prompts, syllabus as sy


def test_every_topic_has_content():
    assert set(sy.TOPIC_CONTENT) == set(sy.TOPIC_NAMES)
    assert all(len(v) > 20 for v in sy.TOPIC_CONTENT.values())


def test_official_placements_the_old_prompt_got_wrong():
    # from the 0478 syllabus: embedded systems are 3.1, cloud storage is 3.3, SQL has no AVG/LIKE
    assert "embedded systems" in sy.TOPIC_CONTENT["3.1"]
    assert "cloud storage" in sy.TOPIC_CONTENT["3.3"] and "cloud" not in sy.TOPIC_CONTENT["3.4"]
    assert "AVG" not in sy.TOPIC_CONTENT["9.2"] and "LIKE" not in sy.TOPIC_CONTENT["9.2"]


def test_prompt_blocks_are_generated_from_the_syllabus_module():
    sp = prompts.PHASE12_SYSTEM
    assert sy.topics_prompt_block() in sp and sy.objectives_prompt_block() in sp
    for code, name in sy.TOPIC_NAMES.items():
        assert f"{code} {name} — {sy.TOPIC_CONTENT[code]}" in sp
    assert sy.AO_DEFINITIONS["AO2"] in sp and "Paper 1: AO1 60%, AO2 20%, AO3 20%" in sp


def test_topic_in_paper():
    assert sy.topic_in_paper("3.1", "12") is True
    assert sy.topic_in_paper("7.2", "12") is False
    assert sy.topic_in_paper("10.3", "22") is True
    assert sy.topic_in_paper("1.1", None) is None and sy.topic_in_paper(None, "12") is None
    assert sy.topic_in_paper("x", "12") is None


def test_weightings_sum_to_100():
    assert all(sum(w.values()) == 100 for w in sy.AO_WEIGHTING.values())
