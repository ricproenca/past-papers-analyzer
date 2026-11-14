import re
from collections import Counter

import generate_topics as gt
from conftest import make_question


def test_topic_page_has_unique_ids_and_loads_widget_scripts():
    src1 = {"paper": "0478_m24_qp_12", "session": "m24", "variant": "12", "year": "2024", "paper_num": "1"}
    src2 = {"paper": "0478_s25_qp_11", "session": "s25", "variant": "11", "year": "2025", "paper_num": "1"}
    match_text = ("Draw one line from each device to its use.\nDevice | Use\nMouse | Pointing\n"
                  "Speaker | Sound output\nScanner | Digitising")
    qs = [(make_question("Q1", topic="3.2", topic_name="Input and Output Devices", difficulty="Low"), src1),
          (make_question("Q1", topic="3.2", topic_name="Input and Output Devices", difficulty="Low"), src2),
          (make_question("Q2", topic="3.2", topic_name="Input and Output Devices", command="Draw", text=match_text,
                         layout_type="LineMatching", structure_data={}, difficulty="Low"), src1)]
    html = gt.build_topic_page("3", qs)
    ids = re.findall(r'\sid="([^"]+)"', html)
    assert not [i for i, c in Counter(ids).items() if c > 1]
    assert 'class="match-grid"' in html and '<script src="match.js"></script>' in html and "joint.min.js" not in html
