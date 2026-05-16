"""Generate a self-contained HTML review page from an extracted JSON file."""

import argparse
import json
from pathlib import Path

from src.renderer import render


def render_one(json_path: Path, output: str | None = None) -> Path:
    if output:
        out_path = Path(output)
    else:
        out_path = Path("output/html") / json_path.with_suffix(".html").name
    data = json.loads(json_path.read_text(encoding="utf-8"))
    render(data, out_path)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Render extracted JSON as an HTML review page.")
    parser.add_argument("json_path", help="Path to a JSON file or a folder containing JSON files")
    parser.add_argument("-o", "--output", help="Output HTML path (single-file mode only)")
    args = parser.parse_args()

    target = Path(args.json_path)

    if target.is_dir():
        files = sorted(target.glob("*.json"))
        if not files:
            print(f"No JSON files found in {target}")
            return
        for json_path in files:
            out_path = render_one(json_path)
            print(f"Rendered: {out_path}")
    else:
        out_path = render_one(target, args.output)
        print(f"Rendered: {out_path}")


if __name__ == "__main__":
    main()
