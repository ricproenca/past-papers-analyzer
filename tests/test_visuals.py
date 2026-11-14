from src import visuals as v
from conftest import make_paper, make_question


def test_explicit_page_ref():
    assert v._explicit_page_ref("see the flowchart on Page 12.") == 12
    assert v._explicit_page_ref("no reference here") is None
    assert v._explicit_page_ref(None) is None
    assert v._explicit_page_ref("homepage 3") is None       # word boundary


def test_visual_key_normalises():
    assert v._visual_key([" Flowchart ", "", "TABLE"]) == "flowchart|table"
    assert v._visual_key([]) is None and v._visual_key(None) is None


def test_siblings_sharing_a_visual_inherit_the_page_ref():
    qs = [
        make_question("Q7a", text="Study the flowchart on page 6.", visuals=["flowchart"]),
        make_question("Q7b", text="State the output.", visuals=["Flowchart"]),
        make_question("Q8", text="Describe X.", visuals=["table"]),          # visual, but no page ref
        make_question("Q9", text="See page 4.", visuals=[]),                  # ref, but no visual
    ]
    pairs = v._questions_needing_visuals(make_paper(qs))
    assert [(q["id"], page) for q, page in pairs] == [("Q7a", 6), ("Q7b", 6)]


def test_attach_visual_images(monkeypatch, tmp_path):
    seen = {}

    def fake_render(pdf, pages, out_dir, dpi):
        seen.update(pages=set(pages), out_dir=out_dir)
        return {p: out_dir / f"page-{p}.png" for p in pages}

    monkeypatch.setattr(v.pdf_reader, "render_pages_to_pngs", fake_render)
    qs = [make_question("Q1", text="on page 6", visuals=["d"]),
          make_question("Q2", text="on page 6", visuals=["d"]),
          make_question("Q3", visuals=[], visual_image="stale/page-1.png")]
    paper = make_paper(qs)
    n = v.attach_visual_images(paper, tmp_path / "0478_m25_qp_12.pdf", tmp_path / "html")
    assert n == 2 and seen["pages"] == {6}                                    # one PNG per unique page
    assert qs[0]["visual_image"] == qs[1]["visual_image"] == "0478_m25_qp_12/page-6.png"
    assert "visual_image" not in qs[2]                                        # stale value cleared


def test_find_source_pdf(tmp_path):
    (tmp_path / "sub").mkdir()
    pdf = tmp_path / "sub" / "a_qp_1.pdf"
    pdf.write_bytes(b"x")
    assert v.find_source_pdf("a_qp_1.pdf", tmp_path) == pdf
    assert v.find_source_pdf("missing.pdf", tmp_path) is None
    assert v.find_source_pdf("a_qp_1.pdf", tmp_path / "nope") is None


def test_parts_of_the_same_question_share_the_page_ref_whatever_their_visual_labels():
    # m25_qp_22 Q7: only Q7b says "on page 6" and the model labelled the visual on Q7a only.
    qs = [
        make_question("Q7a", text="This flowchart represents an algorithm.", visuals=["Flowchart: START -> ..."]),
        make_question("Q7b", text="State the purpose of the algorithm on page 6.", visuals=[]),
        make_question("Q7c_i", text="There are problems with the given algorithm.", visuals=[]),
        make_question("Q8", text="Write the program.", visuals=[]),
    ]
    pairs = v._questions_needing_visuals(make_paper(qs))
    assert [(q["id"], page) for q, page in pairs] == [("Q7a", 6), ("Q7b", 6), ("Q7c_i", 6)]


def test_page_ref_needs_a_reference_phrase():
    assert v._explicit_page_ref("A web page 3 times larger is loaded.") is None
    assert v._explicit_page_ref("the algorithm on page 6") == 6 and v._explicit_page_ref("See page 12.") == 12
