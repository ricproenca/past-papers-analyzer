import json
import subprocess
import sys

from conftest import make_paper, make_question, ROOT


def _run(script, *args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                          capture_output=True, text=True, cwd=ROOT)


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return p


def test_compare_identical_papers(tmp_path):
    a = _write(tmp_path, "a.json", make_paper())
    r = _run("compare_extractions.py", a, a)
    assert r.returncode == 0 and "identical 2/2" in r.stdout


def test_compare_flags_structural_differences(tmp_path):
    new = _write(tmp_path, "new.json", make_paper([make_question("Q1"), make_question("Q3")]))
    old = _write(tmp_path, "old.json", make_paper())
    r = _run("compare_extractions.py", new, old)
    assert r.returncode == 1 and "only in new ['Q3']" in r.stdout and "only in old ['Q2']" in r.stdout


def test_compare_reports_field_and_text_differences(tmp_path):
    new = _write(tmp_path, "new.json", make_paper([make_question("Q1", objective="AO2", text="Totally different words."),
                                                     make_question("Q2", marks=2)]))
    old = _write(tmp_path, "old.json", make_paper())
    r = _run("compare_extractions.py", new, old)
    assert r.returncode == 0 and "('Q1', 'objective', 'AO2', 'AO1')" in r.stdout and "--- Q1: text similarity" in r.stdout


def test_audit_reports_and_fails_on_invalid(tmp_path):
    good = _write(tmp_path, "good.json", make_paper())
    bad = _write(tmp_path, "bad.json", make_paper([make_question("Q1", topic="99.9")]))
    r = _run("audit_extractions.py", good, bad)
    assert r.returncode == 1 and "[FAIL] bad.json" in r.stdout and "1/2 paper(s) valid" in r.stdout


def test_syllabus_report_runs(tmp_path):
    a = _write(tmp_path, "a.json", make_paper(variant="12"))
    one = _run("syllabus_report.py", a)
    assert one.returncode == 0 and "Q1" in one.stdout and "syllabus {'AO1': 60" in one.stdout
    many = _run("syllabus_report.py", a, a)
    assert many.returncode == 0 and "Paper 1: marks per topic" in many.stdout


def test_check_site_flags_problems(tmp_path):
    (tmp_path / "paper.css").write_text("")
    (tmp_path / "good.html").write_text('<link href="paper.css"><div id="a"></div><div id="b"></div>')
    (tmp_path / "bad.html").write_text('<div id="a"></div><div id="a"></div><img src="missing.png">'
                                       '<script src="https://cdn.example.com/x.js"></script><div class="match-grid"></div>')
    r = _run("check_site.py", tmp_path)
    assert r.returncode == 1 and "[FAIL] bad.html" in r.stdout and "good.html" not in r.stdout
    for msg in ("duplicate ids: ['a']", "missing local file: missing.png", "without integrity hash", "['match.js'] not loaded"):
        assert msg in r.stdout


def test_committed_site_is_clean():
    r = _run("check_site.py", ROOT / "output" / "html")
    assert r.returncode == 0, r.stdout
