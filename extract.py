import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.extractor import extract


def extract_one(pdf_path: Path, output: str | None = None, ms_path: str | None = None) -> Path:
    out = Path(output) if output else Path("output/json") / (pdf_path.stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    extract(str(pdf_path), str(out), ms_path=ms_path)
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Extract questions from Cambridge exam PDFs using Claude."
    )
    parser.add_argument("pdf_path", help="Path to an exam paper PDF or a folder of PDFs")
    parser.add_argument("--output", "-o", help="Output JSON path (single-file mode only)")
    parser.add_argument("--marking-scheme", "-ms", help="Marking scheme PDF (single-file mode only)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Folder mode: skip papers whose output JSON already exists (resume a batch)")
    parser.add_argument("--model", "-m", help="Claude model to use (default: claude-sonnet-4-6)")
    args = parser.parse_args()

    if args.model:
        os.environ["CLAUDE_MODEL"] = args.model

    target = Path(args.pdf_path)

    if target.is_dir():
        qp_files = sorted(target.glob("*_qp_*.pdf"))
        if not qp_files:
            parser.error(f"No question-paper PDFs (*_qp_*.pdf) found in {target}")
        failed = []
        for pdf in qp_files:
            if args.skip_existing and (Path("output/json") / (pdf.stem + ".json")).exists():
                print(f"Skipping (already extracted): {pdf.name}")
                continue
            ms_candidate = pdf.parent / pdf.name.replace("_qp_", "_ms_")
            ms = str(ms_candidate) if ms_candidate.is_file() else None
            if ms:
                print(f"Processing: {pdf.name} + {ms_candidate.name}")
            else:
                print(f"Processing: {pdf.name} (no marking scheme found)")
            try:
                extract_one(pdf, ms_path=ms)
            except Exception as e:  # keep going: one bad paper shouldn't abort the batch
                print(f"[FAILED] {pdf.name}: {type(e).__name__}: {e}")
                failed.append(pdf.name)
        if failed:
            print(f"\n{len(failed)} of {len(qp_files)} paper(s) failed: {', '.join(failed)}")
            raise SystemExit(1)
    else:
        if not target.is_file():
            parser.error(f"Exam paper PDF not found: {target}")
        if args.marking_scheme and not Path(args.marking_scheme).is_file():
            parser.error(f"Marking scheme PDF not found: {args.marking_scheme}")
        extract_one(target, output=args.output, ms_path=args.marking_scheme)


if __name__ == "__main__":
    main()
