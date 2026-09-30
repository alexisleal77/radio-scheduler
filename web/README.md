# web

Static, read-only evidence viewer. Reads the JSON files already written by
`scripts/demo.py`, `scripts/harness6g_demo.py`, and `scripts/baseline_run.py`
under `evidence/` and renders them as three sections (Delivery A, B, C), with
a PT/EN language toggle. No build step, no framework, no new dependency —
plain HTML/CSS/JS, consistent with this project's stdlib-only stack
(ADR-004).

It never executes anything and never writes anything — it only reads
already-committed evidence.

## Running it

Browsers block `fetch()` of local files opened via `file://`, so serve the
repository root with a plain HTTP server and open the page through it:

```
python3 -m http.server 8000
```

Then open <http://localhost:8000/web/> in a browser.

## Verifying the language toggle without a browser

```
node web/verify_toggle.js
```

Runs `app.js`'s real source (not a reimplementation) inside a minimal
simulated DOM, against the actual committed evidence JSON files, and
asserts the PT/EN toggle updates every static string, re-renders check
badges, and — the specific regression this checks for — never wipes the
dynamic `harness-source-path`/`baseline-source-path` `<code>` elements
when switching languages. Exits non-zero if any assertion fails. This
complements, rather than replaces, an actual visual check in a browser.

## Known limitation (documented, not hidden)

`app.js`'s `CONFIG` object hardcodes the current single evidence run for
Delivery B (`evidence/harness6g/demo-20260929T230957Z/`) and Delivery C
(`evidence/baseline/baseline-claude-code-native-4b22db6bc358/`). Re-running
`scripts/harness6g_demo.py` or `scripts/baseline_run.py` creates a new
timestamped/hashed directory, so `CONFIG.harnessPath` /
`CONFIG.baselinePath` need updating by hand to point at the new run.
Delivery A's path (`evidence/demo/results.json`) is stable — `scripts/demo.py`
always overwrites the same file.

This is a deliberate v0.1 simplification, not an oversight: browsing
multiple historical runs would need a generated index (e.g. a small script
scanning `evidence/` and writing `web/data/index.json`) — a natural next
increment if/when there is more than one run per delivery to compare.

## Status

Implemented (v0.1): read-only rendering of all three deliveries' evidence,
PT/EN toggle (persisted in `localStorage`), light/dark theme via
`prefers-color-scheme`. Not implemented: multi-run browsing/history, live
re-execution of scripts, any write path back into `evidence/`.
