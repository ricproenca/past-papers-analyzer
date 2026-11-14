"""Re-extract only the marking-scheme answers (Phase 3) for papers already extracted.

Usage:
    python answers.py output/json/0478_w25_qp_12.json                 # marking scheme found under input/
    python answers.py output/json/X.json -ms path/to/X_ms.pdf
    python answers.py output/json/X.json -o output/staging/X.json     # write elsewhere (compare first)
    python answers.py output/json                                     # every paper in a folder

Phase 1+2 data (questions, topics, objectives) is kept as it is; only `answers`,
`objective_marks`, the enrichment/statistics and the HTML page are rebuilt.
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.extractor import refresh_answers  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_path", help="An extracted paper JSON, or a folder of them")
    ap.add_argument("--marking-scheme", "-ms", help="Marking scheme PDF (single-file mode only)")
    ap.add_argument("--output", "-o", help="Write here instead of overwriting (single-file mode only)")
    ap.add_argument("--model", "-m", help="Claude model to use")
    args = ap.parse_args()
    if args.model:
        os.environ["CLAUDE_MODEL"] = args.model

    target = Path(args.json_path)
    if target.is_dir():
        failed = []
        for path in sorted(target.glob("*.json")):
            try:
                refresh_answers(str(path))
            except Exception as e:
                print(f"[FAILED] {path.name}: {type(e).__name__}: {e}")
                failed.append(path.name)
        if failed:
            raise SystemExit(f"{len(failed)} paper(s) failed: {', '.join(failed)}")
    else:
        if not target.is_file():
            ap.error(f"not found: {target}")
        refresh_answers(str(target), args.marking_scheme, args.output)


if __name__ == "__main__":
    main()
