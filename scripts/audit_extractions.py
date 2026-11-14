"""Audit extracted papers without calling the API.

Usage:
    python scripts/audit_extractions.py [output/json/*.json ...]

For every paper: schema validation, the consistency warnings from src/schema.py,
topics outside the paper's range, questions with no marking points, and a
one-line profile (questions, marks, AO split, layouts). Exit code 1 if any paper
fails validation.
"""

import collections
import contextlib
import glob
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schema import validate_phase_output  # noqa: E402


def audit(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    qs = data.get("questions", [])
    phase = 3 if data.get("ms") else 2
    buf = io.StringIO()
    ok = True
    try:
        with contextlib.redirect_stdout(buf):
            validate_phase_output(data, phase=phase)
    except ValueError as e:
        ok = False
        print(f"[FAIL] {path.name}: {e}")
    warnings = [l for l in buf.getvalue().splitlines() if l.strip()]
    ao = collections.Counter()
    for q in qs:
        ao[q.get("objective")] += q.get("marks") or 0
    layouts = collections.Counter(q.get("layout_type") for q in qs)
    print(f"{path.name}: {len(qs)} questions, {sum(q.get('marks') or 0 for q in qs)}/{data.get('total_marks')} marks, "
          f"AO {dict(sorted(ao.items(), key=str))}, layouts {dict(layouts.most_common(4))}")
    for w in warnings:
        print(f"    {w}")
    if phase == 3:
        empty = [q["id"] for q in qs if (q.get("marks") or 0) > 0 and not (q.get("answers") or {}).get("marking_points")]
        if empty:
            print(f"    [!] no marking points for {empty}")
    return ok


def main():
    paths = [Path(p) for p in (sys.argv[1:] or sorted(glob.glob("output/json/*.json")))]
    results = [audit(p) for p in paths]
    print(f"\n{sum(results)}/{len(results)} paper(s) valid")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
