---
name: ship
description: Check, commit and push the pending work in this repo — run the tests and lint, regenerate the committed HTML or enrichment if the change requires it, make sure no staging or debug output is included, then commit and push to origin. Use when the user says "commit and push", "ship it", "push the changes" or asks to commit the current work.
---

# Check, commit, push

The repo commits generated files (`output/json`, `output/html`) that tests compare
with what the code produces, so a commit is only correct when they are in step.

## 1. See what changed

```bash
git status --short
git diff --stat
```

## 2. Regenerate what the change requires

| Changed | Run |
|---|---|
| `src/enricher.py`, `src/statistics.py`, `postprocess.fill_objective_marks`, or a JSON edited by hand | `python backfill_enrichment.py` |
| `src/renderer/`, `src/static/`, `src/syllabus.py` names, any `output/json/*.json` | `python render.py output/json && python generate_stats.py && python generate_topics.py` |
| `generate_stats.py` / `generate_topics.py` | the matching generator |

## 3. Check

```bash
uv run pytest -q
uv run pyflakes src tests scripts *.py
python scripts/check_site.py        # only if output/html changed
```

A failure stops here: report the output, do not commit. The golden tests
(`test_committed_html_matches_renderer`, `test_committed_enrichment_is_up_to_date`)
failing means step 2 was skipped, not that the test is wrong.

## 4. Stage

Stage by path, not `git add -A`. Never commit `output/staging/`, `output/debug/`,
`.env` or anything under `input/` (ignored — if one shows up in `git status`, the
ignore rules are broken; stop and say so). Check with `git diff --cached --stat`.

## 5. Commit and push

Message style, from the history: one lowercase line, no prefix, what changed in the
user's terms, parts separated by commas —
`phase 3: slimmer answers input, marking-point conventions, AO split, answers CLI`.
State counts (tests, papers) only after reading them from the command output.

```bash
git commit -m "<message>"
git push origin main
```

The remote uses the SSH host alias `github-ricproenca`; if the push fails on
authentication, report it instead of changing the remote URL. Finish with the commit
hash and `git status -sb` showing the branch in sync.
