"""Compare two extractions of the same paper (e.g. a fresh run against the committed JSON).

Usage:
    python scripts/compare_extractions.py NEW.json OLD.json [--show N]

Prints per-field agreement, text similarity, objective balance, answer agreement and
the questions that differ most, so a re-extraction can be judged before it replaces
the committed file. Exit code 1 when the question ids or marks differ (structural
regression); 0 otherwise.
"""

import argparse
import collections
import difflib
import json
import re
import sys
from pathlib import Path

FIELDS = ("marks", "page", "topic", "command", "objective", "layout_type")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _ao_marks(questions) -> dict:
    c = collections.Counter()
    for q in questions:
        split = q.get("objective_marks")
        if isinstance(split, dict) and split:
            c.update(split)                      # marking-scheme split (e.g. AO2 9 + AO3 6)
        else:
            c[q.get("objective")] += q.get("marks") or 0
    return dict(sorted(c.items(), key=lambda kv: str(kv[0])))


def compare(new: dict, old: dict, show: int = 8) -> int:
    N = {q["id"]: q for q in new["questions"]}
    O = {q["id"]: q for q in old["questions"]}
    common = [i for i in O if i in N]
    only_new, only_old = sorted(set(N) - set(O)), sorted(set(O) - set(N))
    print(f"questions: new {len(N)}, old {len(O)}; only in new {only_new or '-'}; only in old {only_old or '-'}")
    print(f"total_marks: new {new.get('total_marks')} (sum {sum(q.get('marks') or 0 for q in N.values())}), "
          f"old {old.get('total_marks')} (sum {sum(q.get('marks') or 0 for q in O.values())})")
    for f in FIELDS:
        same = sum(1 for i in common if N[i].get(f) == O[i].get(f))
        print(f"  {f:12} {same}/{len(common)}")

    sims = {i: difflib.SequenceMatcher(None, _norm(N[i].get("text")), _norm(O[i].get("text"))).ratio() for i in common}
    if sims:
        print(f"  text         mean similarity {sum(sims.values())/len(sims):.3f}, "
              f"identical {sum(1 for r in sims.values() if r == 1)}/{len(sims)}")
    with_answers = [i for i in common if N[i].get("answers") and O[i].get("answers")]
    if with_answers:
        same_mp = sum(1 for i in with_answers
                      if [(m.get("text", "").strip(), m.get("marks")) for m in N[i]["answers"].get("marking_points", [])]
                      == [(m.get("text", "").strip(), m.get("marks")) for m in O[i]["answers"].get("marking_points", [])])
        print(f"  answers      marking points identical {same_mp}/{len(with_answers)}")
    print(f"  AO by marks  new {_ao_marks(N.values())}  old {_ao_marks(O.values())}")

    diffs = [(i, f, N[i].get(f), O[i].get(f)) for i in common for f in FIELDS if N[i].get(f) != O[i].get(f)]
    if diffs:
        print("\nfield differences (id, field, new, old):")
        for d in diffs[:40]:
            print("  ", d)
    worst = sorted((r, i) for i, r in sims.items() if r < 0.95)[:show]
    for r, i in worst:
        print(f"\n--- {i}: text similarity {r:.2f}")
        print("  new:", N[i].get("text", "")[:400].replace("\n", " / "))
        print("  old:", O[i].get("text", "")[:400].replace("\n", " / "))

    structural = bool(only_new or only_old) or any(N[i].get("marks") != O[i].get("marks") for i in common)
    return 1 if structural else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("new")
    ap.add_argument("old")
    ap.add_argument("--show", type=int, default=8, help="how many most-different question texts to print")
    args = ap.parse_args()
    new = json.loads(Path(args.new).read_text(encoding="utf-8"))
    old = json.loads(Path(args.old).read_text(encoding="utf-8"))
    sys.exit(compare(new, old, args.show))


if __name__ == "__main__":
    main()
