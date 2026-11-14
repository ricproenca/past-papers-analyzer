import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.extractor import extract, extract_batch


def output_path(pdf_path: Path, output: str | None = None) -> Path:
    out = Path(output) if output else Path("output/json") / (pdf_path.stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def extract_one(pdf_path: Path, output: str | None = None, ms_path: str | None = None, vision: bool = False) -> Path:
    out = output_path(pdf_path, output)
    extract(str(pdf_path), str(out), ms_path=ms_path, vision=vision)
    return out


def find_marking_scheme(pdf: Path) -> Path | None:
    candidate = pdf.parent / pdf.name.replace("_qp_", "_ms_")
    return candidate if candidate.is_file() else None


def main():
    parser = argparse.ArgumentParser(
        description="Extract questions from Cambridge exam PDFs using Claude."
    )
    parser.add_argument("pdf_path", help="Path to an exam paper PDF or a folder of PDFs")
    parser.add_argument("--output", "-o", help="Output JSON path (single-file mode only)")
    parser.add_argument("--marking-scheme", "-ms", help="Marking scheme PDF (single-file mode only)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Folder mode: skip papers whose output JSON already exists (resume a batch)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Folder mode: process this many papers in parallel (default 1; mind your rate limits)")
    parser.add_argument("--batch", action="store_true",
                        help="Folder mode: use the Batch API (half price, results arrive asynchronously)")
    parser.add_argument("--resume-phase12", metavar="BATCH_ID",
                        help="With --batch: collect this already-submitted Phase 1+2 batch instead of submitting a new one")
    parser.add_argument("--resume-phase3", metavar="BATCH_ID",
                        help="With --batch: collect this already-submitted Phase 3 batch (needs --resume-phase12 too)")
    parser.add_argument("--vision", action="store_true",
                        help="Also send images of pages that contain diagrams (more input tokens, better diagram data)")
    parser.add_argument("--model", "-m", help="Claude model to use (default: claude-sonnet-4-6)")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    if (args.resume_phase12 or args.resume_phase3) and not args.batch:
        parser.error("--resume-phase12/--resume-phase3 need --batch")
    if args.resume_phase3 and not args.resume_phase12:
        parser.error("--resume-phase3 needs --resume-phase12 (the answers are attached to that extraction)")

    if args.model:
        os.environ["CLAUDE_MODEL"] = args.model

    target = Path(args.pdf_path)

    if target.is_dir():
        if args.output or args.marking_scheme:
            parser.error("--output and --marking-scheme are for a single PDF; a folder writes to output/json/ "
                         "and pairs marking schemes by file name")
        qp_files = sorted(target.glob("*_qp_*.pdf"))
        if not qp_files:
            parser.error(f"No question-paper PDFs (*_qp_*.pdf) found in {target}")
        todo = []
        for pdf in qp_files:
            if args.skip_existing and (Path("output/json") / (pdf.stem + ".json")).exists():
                print(f"Skipping (already extracted): {pdf.name}")
                continue
            ms = find_marking_scheme(pdf)
            print(f"Queued: {pdf.name} + {ms.name}" if ms else f"Queued: {pdf.name} (no marking scheme found)")
            todo.append((pdf, ms))

        failed = []
        if args.batch:
            papers = [(str(pdf), str(output_path(pdf)), str(ms) if ms else None) for pdf, ms in todo]
            resume = {k: v for k, v in (("phase12", args.resume_phase12), ("phase3", args.resume_phase3)) if v}
            extra = {"resume": resume} if resume else {}
            failed = [(name, e) for name, e in extract_batch(papers, vision=args.vision, **extra)]
        else:
            def run(item):
                pdf, ms = item
                try:
                    extract_one(pdf, ms_path=str(ms) if ms else None, vision=args.vision)
                    return None
                except Exception as e:  # keep going: one bad paper shouldn't abort the batch
                    print(f"[FAILED] {pdf.name}: {type(e).__name__}: {e}")
                    return (pdf.name, e)

            if args.workers > 1 and len(todo) > 1:
                # First paper alone so the cached system prompt is written once; the rest read it.
                results = [run(todo[0])]
                with ThreadPoolExecutor(max_workers=args.workers) as pool:
                    results += list(pool.map(run, todo[1:]))
            else:
                results = [run(item) for item in todo]
            failed = [r for r in results if r]

        if failed:
            print(f"\n{len(failed)} of {len(todo)} paper(s) failed: {', '.join(n for n, _ in failed)}")
            for name, err in failed:
                print(f"  {name}: {type(err).__name__}: {err}")
            raise SystemExit(1)
    else:
        if not target.is_file():
            parser.error(f"Exam paper PDF not found: {target}")
        if args.batch or args.skip_existing or args.workers != 1:
            parser.error("--batch, --workers and --skip-existing are for a folder of PDFs")
        if args.marking_scheme and not Path(args.marking_scheme).is_file():
            parser.error(f"Marking scheme PDF not found: {args.marking_scheme}")
        extract_one(target, output=args.output, ms_path=args.marking_scheme, vision=args.vision)


if __name__ == "__main__":
    main()
