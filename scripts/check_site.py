"""Static checks of the generated site in output/html (no browser, no API).

Usage:
    python scripts/check_site.py [output/html]

Checks every page for: duplicate element ids, local references (CSS/JS/PNG) that do
not exist, external scripts/stylesheets without an integrity hash, widgets whose
script is not loaded (circuit editor -> JointJS + circuit.js, line matcher -> match.js),
and the syntax of every bundled .js file (with `node --check`, when node is installed).
Exit code 1 if anything fails.
"""

import collections
import re
import shutil
import subprocess
import sys
from pathlib import Path

WIDGETS = {'class="circuit-editor"': ("joint.min.js", "circuit.js"), 'class="match-grid"': ("match.js",)}


def check_page(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8")
    problems = []
    ids = re.findall(r'\sid="([^"]+)"', html)
    dup = sorted(i for i, c in collections.Counter(ids).items() if c > 1)
    if dup:
        problems.append(f"duplicate ids: {dup[:6]}{' ...' if len(dup) > 6 else ''}")
    for ref in re.findall(r'(?:src|href)="([^"#:?]+\.(?:css|js|png))"', html):
        if not (path.parent / ref).exists():
            problems.append(f"missing local file: {ref}")
    for tag in re.findall(r"<(?:script|link)\b[^>]*(?:src|href)=\"https?://[^>]*>", html):
        if "integrity=" not in tag:
            problems.append(f"external resource without integrity hash: {re.search(r'(?:src|href)=\"([^\"]+)', tag).group(1)}")
    for marker, scripts in WIDGETS.items():
        if marker in html:
            missing = [s for s in scripts if s not in html.split(marker, 1)[1] and f'{s}"' not in html]
            if missing:
                problems.append(f"{marker} present but {missing} not loaded")
    return problems


def check_js(directory: Path) -> list[str]:
    node = shutil.which("node")
    if not node:
        return []
    out = []
    for js in sorted(directory.glob("*.js")):
        r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
        if r.returncode:
            out.append(f"{js.name}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'syntax error'}")
    return out


def main():
    directory = Path(sys.argv[1] if len(sys.argv) > 1 else "output/html")
    pages = sorted(directory.glob("*.html"))
    failed = 0
    for page in pages:
        problems = check_page(page)
        if problems:
            failed += 1
            print(f"[FAIL] {page.name}")
            for p in problems:
                print(f"    {p}")
    js_problems = check_js(directory)
    for p in js_problems:
        print(f"[FAIL] {p}")
    print(f"{len(pages) - failed}/{len(pages)} page(s) clean; JS syntax {'ok' if not js_problems else 'FAILED'}"
          f"{'' if shutil.which('node') else ' (node not installed, not checked)'}")
    sys.exit(1 if failed or js_problems else 0)


if __name__ == "__main__":
    main()
