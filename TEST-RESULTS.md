# Local acceptance · 25 November 2026

**27 pytest cases passed.** Two full API smoke runs executed the pinned quantized CPU model. Four Chrome acceptance groups passed, including a real server-process restart. The public viewer and the video use saved SAMPLE evidence from those runs. Live Sprite, Pinecone and Box acceptance remains open.

## Commands and observed output

Run from the repository root. Python 3.13.5, ONNX Runtime 1.32.0, Pillow 13.0.0, NumPy 2.5.5, Node 24.22.1. The installed Google Chrome executable was used.

```text
$ .local/venv/bin/python -m pytest -q --basetemp=.local/tmp/pytest
...........................                                              [100%]
27 passed, 1 warning in 5.50s
```

The warning comes from FastAPI’s Starlette TestClient integration using httpx. Unit tests block socket connects and DNS lookups. Coverage includes pinned assets and preprocessing, bit-for-bit repeatability of 1,000 probabilities and top five, all seven deterministic transforms, mild-test ordering, memory-promoted ordering, escalation, no-drop stopping, missing/invalid labels, baseline retakes, report hashes, budget limits, concurrent duplicate steps, reopening persistent storage, cross-run cache reuse and read-only access. Gateway tests simulate success, 403/429/503, timeout and malformed responses, explicit outbox retry, Box version caching, partial intake failure and HTML upload. [Full pytest output](evidence/pytest.txt) · [Test source](tests/)

```text
$ (cd web && npm run build)
> tsc --noEmit && vite build
vite v8.3.8 building client environment for production...
✓ 17 modules transformed.
✓ built in 188ms

$ node web/browser.mjs
PASS desktop saved report, paired images and remembered test order
PASS mobile layout and trial selection
PASS authenticated browser run, actual server restart, stale-step replay and continuation
PASS zero browser uncaught errors
```

The browser exercised the compiled app at 1440×1000 and 390×844. It opened an authenticated session, started a run and computed its baseline. The test terminated Uvicorn, started a new process on the same SQLite directory, replayed cursor zero, verified the original trial ID and continued from cursor one. The reopened run contained exactly two trials. [Browser output](evidence/browser.txt) · [Desktop screenshot](evidence/desktop.png) · [Mobile screenshot](evidence/mobile.png)

```text
$ .local/venv/bin/python scripts/smoke.py --data .local/acceptance --snapshot
SAMPLE SET 6f3c957474624b65bd20953bd90d5148 CPU ms 294.34
FOLLOW-UP cbc525073dc649719ca36671f7ad3e2b CPU ms 111.389
wall_s 1.529 process_cpu_s 1.461 max_rss_kib 123712 persistent_bytes 8189560
```

The smoke used FastAPI’s normal import, run and single-step endpoints in-process with a new empty local database. `--snapshot` packaged the resulting JSON and hash-verified PNGs into the demo. Repeat with another empty directory and omit that flag to preserve the committed replay. UUIDs and timings vary. Both runs logged a LOCAL/MOCK query and upsert. There were 25 new model evaluations, zero cache hits, 405.730 ms total measured inference CPU, 1.461 s process CPU for both complete loops and 1.529 s elapsed. Peak process RSS was 123,712 KiB. The 8,189,560 bytes of persistent files include SQLite and generated reports, excluding installed packages and model assets. The model digest and pinned preprocessing config were verified before inference. [Complete smoke output](evidence/smoke.txt) · [First run JSON](demo/session.json) · [Follow-up JSON](demo/followup.json)

## Findings by photo and transform

The first set comprised two photos each of teapots, goblets, vases, pitchers, bells and guitars. Of those twelve, only guitar 1918.374 matched its accepted top-one ID. The agent stopped each of the other eleven at baseline with `BASELINE_DISAGREES`. The smoke log lists every original and its actual top-one ID. The separately imported follow-up was another correctly classified guitar. The application classifies the full working image after pinned preprocessing. Camera tests modify the working image before inference.

| Photo | Input | Top one | Top-one score | Accepted guitar score |
|---|---|---|---:|---:|
| 1918.374 | Original | Acoustic guitar | 65.10% | 65.10% |
| 1918.374 | Blur radius 1.2 | Acoustic guitar | 89.42% | 89.42% |
| 1918.374 | Brightness ×0.65 | Komodo dragon | 33.77% | 5.08% |
| 1918.374 | JPEG quality 30 | Komodo dragon | 35.42% | 19.98% |
| 1918.374 | Rotation 8° | Acoustic guitar | 39.34% | 39.34% |
| 1918.374 | Brightness ×0.35 | Knee pad | 19.41% | 10.85% |
| 1918.374 | Brightness ×0.16 | Knee pad | 24.75% | 1.22% |
| 1918.370 | Original | Acoustic guitar | 60.44% | 60.44% |
| 1918.370 | Brightness ×0.65, recalled first | Acoustic guitar | 66.38% | 66.38% |
| 1918.370 | Blur radius 1.2 | Acoustic guitar | 82.68% | 82.68% |
| 1918.370 | JPEG quality 30 | Acoustic guitar | 49.78% | 49.78% |
| 1918.370 | Colour cast level 1 | Acoustic guitar | 55.88% | 55.88% |
| 1918.370 | JPEG quality 12 | Acoustic guitar | 45.85% | 45.85% |
| 1918.370 | JPEG quality 4 | Violin | 93.84% | 0.86% |

The local memory match had cosine similarity **0.984281** and referred to the first guitar’s low-light trial. It changed the second session’s order from blur-first to low-light-first. That mild test preserved the class. Among the mild probes, JPEG caused the largest probability loss, so the agent escalated it. Quality 4 produced `WRONG_TOP1_GE_070` and a retake request. The 70% threshold is an operational rule on a softmax score. The samples were curated, the photographs were acquired under museum conditions, and these measurements do not estimate general accuracy or calibration.

## Verification boundary

The source model revision is `3ba07f12712fa58fd6b3d661f9909c9e332c5005`. Its input is `pixel_values`, output is `logits`, and softmax is applied once. Public downloads, source CC0 records, local model execution, persistence, frontend and offline adapters were checked. Local process restart is proven. Sprite billing, service wake, checkpoint restore, authenticated Pinecone write/read visibility, and Box OAuth/list/download/upload behavior require an authorized live run. [Exact setup and acceptance gates](DEPLOY.md)

## Clean committed archive

An independent extraction of local build commit `520cb65` fetched the pinned model from its public revision and ran the two-session smoke in a fresh database. All **25 trials** reproduced the saved top-five IDs and scores exactly, together with the trial PNG hashes and both decision reason-code sequences. All relative links in the project’s top-level Markdown resolved in that archive. FFprobe verified the walkthrough as H.264, 1280×800, 76.000 seconds and 352,439 bytes.
