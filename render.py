"""Generate a self-contained HTML review page from an extracted JSON file."""

import argparse
import json
from pathlib import Path

from src.renderer import render


def main():
    parser = argparse.ArgumentParser(description="Render extracted JSON as an HTML review page.")
    parser.add_argument("json_path", help="Path to extracted JSON file")
    parser.add_argument("-o", "--output", help="Output HTML path (default: output/html/<stem>.html)")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path("output/html") / json_path.with_suffix(".html").name

    data = json.loads(json_path.read_text(encoding="utf-8"))
    render(data, out_path)
    print(f"Rendered: {out_path}")


if __name__ == "__main__":
    main()
