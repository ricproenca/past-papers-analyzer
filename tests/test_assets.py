import pytest

from src import assets
from src.renderer import page, render
from conftest import make_paper

EXPECTED = ["circuit.js", "match.js", "paper.css", "paper.js", "stats.css", "stats.js", "topics.css", "topics.js"]


def test_static_directory_contents():
    assert sorted(p.name for p in assets.STATIC_DIR.iterdir()) == EXPECTED


@pytest.mark.parametrize("name", EXPECTED)
def test_assets_are_non_empty(name):
    assert assets.read_asset(name).strip()


def test_render_writes_the_static_files_byte_for_byte(tmp_path):
    render(make_paper(), tmp_path / "out" / "paper.html")
    for name in page.ASSET_FILES:
        assert (tmp_path / "out" / name).read_bytes() == (assets.STATIC_DIR / name).read_bytes()


def test_every_local_file_a_page_links_is_written(tmp_path):
    import re
    from conftest import make_question
    circuit = make_question("Q2", layout_type="AnnotatedDiagram", command="Draw", text="Draw a logic circuit.",
                            structure_data={"diagram_type": "circuit", "partial_elements": ["A", "B", "X"]})
    for paper in (make_paper(), make_paper([circuit])):
        html = page.render_html(paper)
        linked = set(re.findall(r'(?:src|href)="([^":]+\.(?:css|js))"', html))
        assert {"paper.css", "paper.js"} <= linked and linked <= set(page.ASSET_FILES)
