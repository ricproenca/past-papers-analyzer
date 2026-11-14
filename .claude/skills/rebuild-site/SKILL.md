---
name: rebuild-site
description: Rebuild and verify the generated HTML site (paper pages, topic pages, statistics page) after changing the renderer, the CSS/JS in src/static, the enrichment/statistics code, or any JSON in output/json. Use when the user asks to re-render, rebuild, regenerate or check the HTML pages, or after editing anything under src/renderer, src/static, src/enricher.py, src/statistics.py, generate_stats.py or generate_topics.py.
---

# Rebuild and verify the site (Phase 4)

Pages are generated from `output/json/*.json`; the committed HTML must equal what the
code generates (golden test `test_committed_html_matches_renderer`), so every change to
the renderer, `src/static/*` or the JSON is followed by a full rebuild and a commit of
the regenerated `output/html/`.

## Rebuild

```bash
python backfill_enrichment.py      # only if enricher/statistics/objective_marks logic changed (idempotent)
python render.py output/json       # paper pages + paper.css/js, circuit.js, match.js
python generate_stats.py           # statistics.html
python generate_topics.py          # topic_*.html + topics.html
```

## Verify

```bash
python scripts/check_site.py       # duplicate ids, missing local files, CDN tags without integrity,
                                   # widgets without their script, JS syntax (node --check)
pytest -q                          # golden HTML, escaping, renderer parsers
git diff --stat output/html        # expect only the pages your change should touch
```

Rules the checks enforce — keep them when editing templates:
- A widget's script is added by `renderer.interactive_script_tags()`: JointJS (+ its
  integrity hash) and `circuit.js` only with a circuit editor, `match.js` only with a
  line matcher. Use it on any new page type that shows question cards.
- Every external `<script>`/`<link>` is pinned to an exact version and carries
  `integrity="sha384-..." crossorigin="anonymous"`. To add or bump one, download the
  exact file and hash it: `curl -sL URL | openssl dgst -sha384 -binary | openssl base64 -A`.
  Check the URL is not a 404 first (the old `joint.css` link was).
- Cards on pages that mix papers are rendered with `source=` so their DOM ids and input
  names are paper-qualified (`0478_m24_qp_12-Q1`); paper pages keep plain ids, which
  the topic pages' links (`<paper>.html#Q1`) rely on.
- CSS/JS live in `src/static/`; never edit the copies in `output/html/` (overwritten).

For a visual check open the page (`open output/html/<stem>.html`); the circuit editor
needs network access for JointJS. Summarise what changed in the pages and ask before
committing.
