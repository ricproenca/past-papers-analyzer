"""Report how papers map onto the syllabus — topics and assessment objectives.

Usage:
    python scripts/syllabus_report.py                     # coverage across every paper
    python scripts/syllabus_report.py output/json/X.json  # one paper, question by question

Across papers: marks per topic for Paper 1 and Paper 2, topics never examined, and
each paper's AO split against the syllabus weighting. For one paper: every question
with its topic, AO, marks and instruction line, so the mapping can be checked against
src/syllabus.py (TOPIC_CONTENT, AO_DEFINITIONS).
"""

import collections
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.syllabus import AO_WEIGHTING, PAPER_CHAPTERS, TOPIC_NAMES  # noqa: E402


def _paper_no(data) -> str:
    return str(data.get("variant") or "")[:1]


def _instruction(text: str) -> str:
    lines = [l.strip() for l in (text or "").split("\n") if l.strip() and "|" not in l]
    for l in reversed(lines):
        if re.match(r"^[A-Z][a-z]+\b", l) and len(l) > 15:
            return l
    return lines[-1] if lines else ""


def ao_split(questions) -> dict:
    c = collections.Counter()
    for q in questions:
        split = q.get("objective_marks")
        if isinstance(split, dict) and split:
            for ao, m in split.items():
                c[ao] += m
        else:
            c[q.get("objective")] += q.get("marks") or 0
    total = sum(c.values()) or 1
    return {ao: round(100 * c.get(ao, 0) / total) for ao in ("AO1", "AO2", "AO3")}


def one_paper(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"{path.name} — Paper {_paper_no(data)}, {len(data['questions'])} questions")
    for q in data["questions"]:
        split = q.get("objective_marks")
        ao = "+".join(f"{k}:{v}" for k, v in split.items()) if isinstance(split, dict) and split else q.get("objective")
        print(f"  {q['id']:8} {q.get('marks'):>2}m  {q.get('topic'):5} {ao:13} {q.get('command', ''):9} {_instruction(q.get('text'))[:90]}")
    print(f"\nAO split {ao_split(data['questions'])} vs syllabus {AO_WEIGHTING.get(_paper_no(data))}")


def all_papers(paths) -> None:
    by_paper = collections.defaultdict(collections.Counter)
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        n = _paper_no(data)
        for q in data["questions"]:
            by_paper[n][q.get("topic")] += q.get("marks") or 0
        print(f"{Path(p).name:24} AO {ao_split(data['questions'])}  syllabus {AO_WEIGHTING.get(n)}")
    for n, counts in sorted(by_paper.items()):
        chapters = PAPER_CHAPTERS.get(n, range(0))
        print(f"\nPaper {n}: marks per topic across papers")
        for code, name in TOPIC_NAMES.items():
            if int(code.split(".")[0]) in chapters:
                bar = "#" * (counts.get(code, 0) // 5)
                print(f"  {code:5} {name[:42]:42} {counts.get(code, 0):4}  {bar}")
        never = [c for c in TOPIC_NAMES if int(c.split(".")[0]) in chapters and not counts.get(c)]
        print(f"  never examined: {never or '-'}")


def main():
    args = sys.argv[1:]
    if len(args) == 1:
        one_paper(Path(args[0]))
    else:
        all_papers(args or sorted(glob.glob("output/json/*.json")))


if __name__ == "__main__":
    main()
