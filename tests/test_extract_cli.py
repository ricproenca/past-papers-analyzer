import threading

import pytest

import extract as cli


@pytest.fixture
def folder(tmp_path, monkeypatch):
    d = tmp_path / "in"
    d.mkdir()
    for n in ("a_qp_1", "b_qp_2", "c_qp_3"):
        (d / f"{n}.pdf").write_bytes(b"x")
    (d / "a_ms_1.pdf").write_bytes(b"x")
    monkeypatch.chdir(tmp_path)
    return d


def run(monkeypatch, *argv):
    monkeypatch.setattr("sys.argv", ["extract.py", *argv])
    cli.main()


def test_folder_mode_pairs_marking_schemes_and_passes_vision(folder, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "extract", lambda pdf, out, ms_path=None, vision=False: calls.append((pdf.split("/")[-1], ms_path and ms_path.split("/")[-1], vision)))
    run(monkeypatch, str(folder), "--vision")
    assert calls == [("a_qp_1.pdf", "a_ms_1.pdf", True), ("b_qp_2.pdf", None, True), ("c_qp_3.pdf", None, True)]


def test_failures_are_reported_and_exit_non_zero(folder, monkeypatch, capsys):
    def fake(pdf, out, ms_path=None, vision=False):
        if "b_qp" in pdf:
            raise RuntimeError("boom")
    monkeypatch.setattr(cli, "extract", fake)
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, str(folder))
    assert exc.value.code == 1
    assert "1 of 3 paper(s) failed: b_qp_2.pdf" in capsys.readouterr().out


def test_skip_existing(folder, monkeypatch):
    (folder.parent / "output" / "json").mkdir(parents=True)
    (folder.parent / "output" / "json" / "a_qp_1.json").write_text("{}")
    calls = []
    monkeypatch.setattr(cli, "extract", lambda pdf, out, **k: calls.append(pdf.split("/")[-1]))
    run(monkeypatch, str(folder), "--skip-existing")
    assert calls == ["b_qp_2.pdf", "c_qp_3.pdf"]


def test_workers_run_the_first_paper_alone_then_the_rest_in_parallel(folder, monkeypatch):
    order, barrier_hit = [], threading.Event()
    lock = threading.Lock()
    started = []

    def fake(pdf, out, ms_path=None, vision=False):
        name = pdf.split("/")[-1]
        with lock:
            started.append(name)
        if name != "a_qp_1.pdf":
            order.append(name)
            if len(order) == 2:
                barrier_hit.set()
            assert barrier_hit.wait(5), "the remaining papers should be running concurrently"
        else:
            assert started == ["a_qp_1.pdf"]          # nothing else has started yet
    monkeypatch.setattr(cli, "extract", fake)
    run(monkeypatch, str(folder), "--workers", "2")
    assert sorted(order) == ["b_qp_2.pdf", "c_qp_3.pdf"]


def test_batch_flag_uses_the_batch_driver(folder, monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "extract_batch", lambda papers, vision=False: seen.update(papers=papers, vision=vision) or [])
    run(monkeypatch, str(folder), "--batch", "--vision")
    names = [(p.split("/")[-1], ms and ms.split("/")[-1]) for p, _, ms in seen["papers"]]
    assert names == [("a_qp_1.pdf", "a_ms_1.pdf"), ("b_qp_2.pdf", None), ("c_qp_3.pdf", None)] and seen["vision"] is True


def test_batch_failures_exit_non_zero(folder, monkeypatch):
    monkeypatch.setattr(cli, "extract_batch", lambda papers, vision=False: [("b_qp_2.pdf", RuntimeError("x"))])
    with pytest.raises(SystemExit):
        run(monkeypatch, str(folder), "--batch")


def test_invalid_workers_rejected(folder, monkeypatch):
    with pytest.raises(SystemExit):
        run(monkeypatch, str(folder), "--workers", "0")
